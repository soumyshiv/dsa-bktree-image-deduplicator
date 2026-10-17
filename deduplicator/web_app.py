"""
Modern Web Backend for the Burkhard-Keller Metric Space Image Deduplicator.

Provides a fast, zero-dependency HTTP server with a rich REST API serving
the next-gen Tailwind CSS + SVG Tree Dashboard.
"""

import io
import json
import mimetypes
import os
import subprocess
import sys
import urllib.parse
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
from PIL import Image, ExifTags

from bktree import BKTree
from hash_logic import generate_hash, PerceptualHash, compute_fast_exact_hash


# Global Application State
STATE = {
    "folder": None,
    "bktree": BKTree(),
    "all_images": {},     # file_path -> img_hash
    "exact_hashes": {},   # file_path -> sha256 hex string
    "thumbnails": {},     # file_path -> JPEG bytes
    "metadata": {},       # file_path -> {dimensions, size_mb, format}
    "recycle_bin": set(), # staged file paths
    "main_target": None,
    "main_hash": None,
}



def ask_cross_platform_folder_picker():
    """Invokes the native folder selection dialog across macOS, Windows, and Linux."""
    # 1. On macOS, use native AppleScript dialog in a subprocess (completely thread-safe)
    if sys.platform == "darwin":
        cmd = 'osascript -e \'POSIX path of (choose folder with prompt "Select Image Folder for DSA Deduplication:")\''
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            path = proc.stdout.strip()
            if path and os.path.isdir(path):
                return path
        except Exception:
            pass
        return None

    # 2. On Windows / Linux, use Tkinter dialog
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="Select Image Folder for DSA Deduplication")
        root.destroy()
        if path and os.path.isdir(path):
            return path
    except Exception:
        pass

    return None


CACHE_FILENAME = ".bktree_cache.json"


def _load_cache(folder_path: str) -> dict:
    cache_path = os.path.join(folder_path, CACHE_FILENAME)
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(folder_path: str, cache_data: dict):
    cache_path = os.path.join(folder_path, CACHE_FILENAME)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Cache write error: {e}")


def _process_single_image(fpath: str, cached_entry: dict = None) -> dict:
    """Worker function to process or retrieve an image's hash, metadata, and thumbnail."""
    try:
        st = os.stat(fpath)
        mtime = st.st_mtime
        size = st.st_size

        # Check if cache is still valid for this file
        if cached_entry and cached_entry.get("mtime") == mtime and cached_entry.get("size") == size:
            h_obj = PerceptualHash.from_hex(cached_entry["hash_hex"])
            with Image.open(fpath) as img:
                img.thumbnail((320, 240))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=80)
                thumb_bytes = buf.getvalue()
            return {
                "path": fpath,
                "hash": h_obj,
                "hash_hex": cached_entry["hash_hex"],
                "exact_hash": cached_entry.get("exact_hash", ""),
                "metadata": cached_entry["metadata"],
                "thumbnail": thumb_bytes,
                "mtime": mtime,
                "size": size,
                "from_cache": True,
            }

        # Otherwise compute hash from scratch
        exact_h = compute_fast_exact_hash(fpath)
        h_obj = generate_hash(fpath)
        if h_obj is None:
            return None

        with Image.open(fpath) as img:
            w, h = img.width, img.height
            fmt = img.format or "JPEG"
            meta = {
                "dimensions": f"{w} × {h}",
                "size_mb": round(size / (1024 * 1024), 2),
                "format": fmt,
            }
            img.thumbnail((320, 240))
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=80)
            thumb_bytes = buf.getvalue()

        return {
            "path": fpath,
            "hash": h_obj,
            "hash_hex": h_obj.to_hex(),
            "exact_hash": exact_h,
            "metadata": meta,
            "thumbnail": thumb_bytes,
            "mtime": mtime,
            "size": size,
            "from_cache": False,
        }
    except Exception as e:
        print(f"Error processing {fpath}: {e}")
        return None


def generate_diff_heatmap(path1: str, path2: str) -> bytes:
    """
    Computes a pixel-wise difference heatmap between two images.
    Returns JPEG bytes of an amplified RGB heatmap highlighting discrepancies.
    """
    try:
        with Image.open(path1) as im1, Image.open(path2) as im2:
            im1_rgb = im1.convert("RGB").resize((480, 360), Image.Resampling.BILINEAR)
            im2_rgb = im2.convert("RGB").resize((480, 360), Image.Resampling.BILINEAR)

            arr1 = np.asarray(im1_rgb, dtype=np.float32)
            arr2 = np.asarray(im2_rgb, dtype=np.float32)

            diff = np.abs(arr1 - arr2)
            max_diff = diff.max(axis=-1)  # shape (360, 480)

            # Boost non-linear difference for high-contrast visual display
            boosted = np.clip(max_diff * 4.5, 0, 255).astype(np.uint8)

            gray_base = np.asarray(im1_rgb.convert("L"), dtype=np.float32) * 0.35
            heatmap = np.zeros((360, 480, 3), dtype=np.uint8)
            heatmap[..., 0] = np.clip(gray_base + boosted * 1.1, 0, 255).astype(np.uint8)
            heatmap[..., 1] = np.clip(gray_base + (255 - boosted) * 0.15, 0, 255).astype(np.uint8)
            heatmap[..., 2] = np.clip(gray_base + (boosted > 100) * 120, 0, 255).astype(np.uint8)

            out_img = Image.fromarray(heatmap)
            buf = io.BytesIO()
            out_img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
    except Exception as e:
        print(f"Diff heatmap generation error: {e}")
        return None


def _resolve_file_path(p: str):
    """Resolves relative or absolute path safely across environments."""
    if not p:
        return None
    if os.path.isfile(p):
        return p
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(STATE.get("folder") or "", p),
        os.path.join(base_dir, p),
        os.path.join(os.path.dirname(base_dir), p),
        os.path.join(base_dir, "sample_images", os.path.basename(p)),
        os.path.join(os.path.dirname(base_dir), "sample_images", os.path.basename(p)),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def index_folder(folder_path: str):
    """Scans folder using multi-core parallel hashing and persistent .bktree_cache.json."""
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        return False, "Folder does not exist"

    STATE["folder"] = folder_path
    STATE["all_images"].clear()
    STATE["thumbnails"].clear()
    STATE["metadata"].clear()
    STATE["recycle_bin"].clear()
    STATE["main_target"] = None
    STATE["main_hash"] = None
    STATE["exact_hashes"].clear()

    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    filenames = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)])
    fpaths = [os.path.abspath(os.path.join(folder_path, f)) for f in filenames]

    disk_cache = _load_cache(folder_path)
    new_cache = {}
    items_to_insert = []

    # Parallel processing with worker thread pool
    max_workers = min(8, max(1, os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_process_single_image, p, disk_cache.get(p)) for p in fpaths]
        for fut in futures:
            res = fut.result()
            if res:
                p = res["path"]
                h_obj = res["hash"]
                STATE["all_images"][p] = h_obj
                STATE["thumbnails"][p] = res["thumbnail"]
                STATE["metadata"][p] = res["metadata"]
                if res.get("exact_hash"):
                    STATE["exact_hashes"][p] = res["exact_hash"]
                items_to_insert.append((h_obj, p))
                new_cache[p] = {
                    "hash_hex": res["hash_hex"],
                    "exact_hash": res.get("exact_hash", ""),
                    "metadata": res["metadata"],
                    "mtime": res["mtime"],
                    "size": res["size"],
                }

    # Construct balanced BK-Tree using medoid pivot selection
    STATE["bktree"] = BKTree.build_balanced(items_to_insert)
    _save_cache(folder_path, new_cache)

    return True, f"Indexed {len(STATE['all_images'])} images into BK-Tree (Balanced Medoid Tree)"



def get_exif_data(fpath: str) -> dict:
    """Extracts camera metadata and formatting details with full fallback support."""
    out = {
        "filename": os.path.basename(fpath),
        "path": fpath,
        "size_mb": 0.0,
        "dimensions": "N/A",
        "format": "N/A",
        "hash": str(STATE["all_images"].get(fpath, "N/A")),
        "camera": "N/A",
        "date": "N/A",
        "aperture": "N/A",
        "shutter": "N/A",
        "iso": "N/A",
        "focal": "N/A",
    }
    if not os.path.exists(fpath):
        return out

    try:
        import datetime
        stat = os.stat(fpath)
        out["size_mb"] = round(stat.st_size / (1024 * 1024), 2)
        out["date"] = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

        with Image.open(fpath) as img:
            out["dimensions"] = f"{img.width} × {img.height} px"
            out["format"] = img.format or "JPEG"

            exif = {}
            # 1. Legacy _getexif (most reliable for camera JPEG tags)
            if hasattr(img, "_getexif") and callable(img._getexif):
                legacy_exif = img._getexif()
                if legacy_exif:
                    for tag_id, val in legacy_exif.items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        exif[tag_name] = val

            # 2. Modern getexif IFDs
            raw_exif = img.getexif()
            if raw_exif:
                for tag_id, val in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    exif[tag_name] = val
                if hasattr(raw_exif, "get_ifd"):
                    try:
                        for ifd_id in [0x8769, 0x8825]:
                            for tag_id, val in raw_exif.get_ifd(ifd_id).items():
                                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                                exif[tag_name] = val
                    except Exception:
                        pass

            cam = f"{exif.get('Make', '')} {exif.get('Model', '')}".strip()
            if cam:
                out["camera"] = cam
            else:
                out["camera"] = "Standard / Digital Asset"

            exif_date = exif.get("DateTimeOriginal") or exif.get("DateTime")
            if exif_date:
                out["date"] = str(exif_date)

            f_num = exif.get("FNumber")
            if f_num:
                try:
                    out["aperture"] = f"f/{float(f_num):.1f}"
                except Exception:
                    pass

            exp = exif.get("ExposureTime")
            if exp:
                try:
                    exp_val = float(exp)
                    out["shutter"] = f"1/{int(round(1/exp_val))}s" if 0 < exp_val < 1 else f"{exp_val}s"
                except Exception:
                    pass

            iso = exif.get("ISOSpeedRatings")
            if iso:
                out["iso"] = str(iso)

            focal = exif.get("FocalLength")
            if focal:
                try:
                    out["focal"] = f"{float(focal):.0f}mm"
                except Exception:
                    pass
    except Exception as e:
        print(f"Error parsing EXIF for {fpath}: {e}")

    return out


class DeduplicatorHTTPHandler(BaseHTTPRequestHandler):
    """Handles REST API and serves the dashboard SPA."""

    def log_message(self, format, *args):
        # Keep console clean
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # 1. API: Status
        if path == "/api/status":
            stats = STATE["bktree"].get_tree_stats()
            self._send_json({
                "folder": STATE["folder"],
                "total_images": len(STATE["all_images"]),
                "active_images": len(STATE["all_images"]) - len(STATE["recycle_bin"]),
                "bin_count": len(STATE["recycle_bin"]),
                "tree_stats": stats,
                "main_target": STATE["main_target"],
            })

        # 2. API: Image List
        elif path == "/api/images":
            view_mode = params.get("mode", ["library"])[0]
            items = []
            for fpath, h in STATE["all_images"].items():
                is_binned = fpath in STATE["recycle_bin"]
                meta = STATE.get("metadata", {}).get(fpath, {})
                if not meta and os.path.exists(fpath):
                    try:
                        st = os.stat(fpath)
                        with Image.open(fpath) as im:
                            meta = {
                                "dimensions": f"{im.width} × {im.height}",
                                "size_mb": round(st.st_size / (1024 * 1024), 2),
                                "format": im.format or "JPEG"
                            }
                            STATE.setdefault("metadata", {})[fpath] = meta
                    except Exception:
                        meta = {"dimensions": "N/A", "size_mb": 0.0, "format": "IMG"}

                item_info = {
                    "path": fpath,
                    "filename": os.path.basename(fpath),
                    "hash": str(h),
                    "is_binned": is_binned,
                    "dimensions": meta.get("dimensions", "N/A"),
                    "size_mb": meta.get("size_mb", 0.0),
                    "format": meta.get("format", "IMG"),
                }

                if view_mode == "bin" and is_binned:
                    items.append(item_info)
                elif view_mode == "library" and not is_binned:
                    items.append(item_info)

            self._send_json({
                "items": items,
                "total": len(items),
                "bin_count": len(STATE["recycle_bin"]),
                "folder": STATE["folder"],
            })

        # 3. API: Thumbnail Stream
        elif path == "/api/thumbnail":
            target_path = params.get("path", [None])[0]
            if target_path and target_path in STATE["thumbnails"]:
                thumb_bytes = STATE["thumbnails"][target_path]
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(thumb_bytes)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(thumb_bytes)
            else:
                self.send_error(404, "Thumbnail not found")

        # 4. API: Full Image Stream (for side-by-side zoom)
        elif path == "/api/raw-image":
            target_path = params.get("path", [None])[0]
            resolved = _resolve_file_path(target_path)
            if resolved and os.path.isfile(resolved):
                mime, _ = mimetypes.guess_type(resolved)
                with open(resolved, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime or "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404, "Image not found")

        # 5. API: Search Near-Duplicates with Live Benchmark
        elif path == "/api/search":
            target_path = params.get("target", [None])[0]
            tolerance = int(params.get("tolerance", [12])[0])

            if not target_path or target_path not in STATE["all_images"]:
                self._send_json({"error": "Target image not indexed"}, status=400)
                return

            STATE["main_target"] = target_path
            target_hash = STATE["all_images"][target_path]
            STATE["main_hash"] = target_hash

            # Run BK-Tree query and benchmark against linear scan
            active_items = {p: h for p, h in STATE["all_images"].items() if p not in STATE["recycle_bin"]}
            raw_matches, benchmark = STATE["bktree"].search_with_benchmark(
                target_hash,
                tolerance,
                all_items=active_items
            )

            results = []
            for m_path in raw_matches:
                if m_path in STATE["recycle_bin"]:
                    continue
                dist = target_hash - STATE["all_images"][m_path]
                if dist <= 22:
                    sim = max(0, 100 - dist)
                else:
                    sim = max(0, int(round(78 - (dist - 22) * 3.5)))
                meta = STATE.get("metadata", {}).get(m_path, {})
                if not meta and os.path.exists(m_path):
                    try:
                        st = os.stat(m_path)
                        with Image.open(m_path) as im:
                            meta = {
                                "dimensions": f"{im.width} × {im.height}",
                                "size_mb": round(st.st_size / (1024 * 1024), 2),
                                "format": im.format or "JPEG"
                            }
                            STATE.setdefault("metadata", {})[m_path] = meta
                    except Exception:
                        meta = {"dimensions": "N/A", "size_mb": 0.0, "format": "IMG"}

                results.append({
                    "path": m_path,
                    "filename": os.path.basename(m_path),
                    "distance": dist,
                    "similarity": sim,
                    "is_target": (m_path == target_path),
                    "dimensions": meta.get("dimensions", "N/A"),
                    "size_mb": meta.get("size_mb", 0.0),
                    "format": meta.get("format", "IMG"),
                })

            # Sort: target first, then smallest distance
            results.sort(key=lambda x: (0 if x["is_target"] else 1, x["distance"]))

            self._send_json({
                "target": target_path,
                "tolerance": tolerance,
                "matches": results,
                "total_matches": len(results),
                "benchmark": benchmark.to_dict(),
                "tree_stats": STATE["bktree"].get_tree_stats(),
            })

        # 6. API: Tree Graph Structure (for interactive SVG visualizer)
        elif path == "/api/tree-graph":
            target_path = params.get("target", [STATE.get("main_target")])[0]
            try:
                tolerance = int(params.get("tolerance", [12])[0])
            except (ValueError, TypeError):
                tolerance = 12

            active_items = {
                p: h for p, h in STATE["all_images"].items()
                if p not in STATE["recycle_bin"]
            }
            if target_path and target_path in active_items:
                rooted_tree = BKTree.build_rooted_at(target_path, active_items)
                target_h = active_items[target_path]
                graph_data = rooted_tree.get_tree_graph(target_hash=target_h, tolerance=tolerance)
            elif STATE.get("bktree"):
                target_h = STATE["all_images"].get(target_path) if target_path else None
                graph_data = STATE["bktree"].get_tree_graph(target_hash=target_h, tolerance=tolerance)
            else:
                graph_data = {}
            self._send_json(graph_data)

        # 7. API: EXIF Metadata
        elif path == "/api/exif":
            target_path = params.get("path", [None])[0]
            if target_path:
                self._send_json(get_exif_data(target_path))
            else:
                self._send_json({"error": "No path provided"}, status=400)

        # 8. API: All-Pairs Duplicate Clusters
        elif path == "/api/clusters":
            tolerance = int(params.get("tolerance", [12])[0])
            active_items = {
                p: h for p, h in STATE["all_images"].items()
                if p not in STATE["recycle_bin"]
            }
            clusters_data = STATE["bktree"].find_all_duplicate_clusters(
                tolerance=tolerance,
                all_items=active_items,
                metadata=STATE["metadata"],
            )
            self._send_json(clusters_data)

        # 9. API: Pixel-Wise Image Difference Heatmap
        elif path == "/api/image-diff":
            p1 = params.get("path1", [None])[0]
            p2 = params.get("path2", [None])[0]
            r1 = _resolve_file_path(p1)
            r2 = _resolve_file_path(p2)
            if r1 and r2 and os.path.isfile(r1) and os.path.isfile(r2):
                heatmap_bytes = generate_diff_heatmap(r1, r2)
                if heatmap_bytes:
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(heatmap_bytes)))
                    self.send_header("Cache-Control", "public, max-age=3600")
                    self.end_headers()
                    self.wfile.write(heatmap_bytes)
                    return
            self.send_error(400, "Invalid paths for image diff")

        # 10. Serve Frontend (SPA index.html)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            index_path = os.path.join(base_dir, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = {}
        if content_len > 0:
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                post_data = json.loads(raw_body)
            except Exception:
                pass

        # 1. API: Browse Folder via native dialog
        if path == "/api/browse-folder":
            chosen = ask_cross_platform_folder_picker()
            if chosen:
                ok, msg = index_folder(chosen)
                self._send_json({
                    "success": ok,
                    "folder": chosen,
                    "message": msg,
                    "total": len(STATE["all_images"]),
                    "tree_stats": STATE["bktree"].get_tree_stats(),
                })
            else:
                self._send_json({"success": False, "message": "Folder selection cancelled or unavailable"})

        # 1b. API: Load Demo Dataset
        elif path == "/api/load-demo":
            base_dir = os.path.dirname(os.path.abspath(__file__))
            demo_candidates = [
                os.path.join(base_dir, "sample_images"),
                os.path.join(os.path.dirname(base_dir), "sample_images"),
                os.path.join(os.getcwd(), "sample_images"),
            ]
            demo_folder = next((d for d in demo_candidates if os.path.isdir(d)), None)
            if demo_folder:
                ok, msg = index_folder(demo_folder)
                self._send_json({
                    "success": ok,
                    "folder": demo_folder,
                    "message": msg,
                    "total": len(STATE["all_images"]),
                    "tree_stats": STATE["bktree"].get_tree_stats(),
                })
            else:
                self._send_json({"success": False, "message": "sample_images folder not found"}, status=404)

        # 2. API: Load Specific Folder Path
        elif path == "/api/load-folder":
            target_folder = post_data.get("folder")
            if target_folder:
                ok, msg = index_folder(target_folder)
                self._send_json({
                    "success": ok,
                    "folder": target_folder,
                    "message": msg,
                    "total": len(STATE["all_images"]),
                    "tree_stats": STATE["bktree"].get_tree_stats(),
                })
            else:
                self._send_json({"success": False, "message": "No folder path supplied"}, status=400)

        # 3. API: Stage to Recycle Bin
        elif path == "/api/bin":
            paths = post_data.get("paths", [])
            for p in paths:
                if p != STATE["main_target"]:
                    STATE["recycle_bin"].add(p)
            self._send_json({
                "success": True,
                "bin_count": len(STATE["recycle_bin"]),
                "staged": len(paths),
            })

        # 4. API: Restore from Recycle Bin
        elif path == "/api/restore":
            paths = post_data.get("paths", [])
            for p in paths:
                STATE["recycle_bin"].discard(p)
            self._send_json({
                "success": True,
                "bin_count": len(STATE["recycle_bin"]),
            })

        # 5. API: Delete Permanently
        elif path == "/api/delete":
            paths = post_data.get("paths", [])
            deleted = 0
            for p in paths:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                    STATE["recycle_bin"].discard(p)
                    STATE["all_images"].pop(p, None)
                    STATE["thumbnails"].pop(p, None)
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting {p}: {e}")

            # Rebuild tree after deletion
            STATE["bktree"] = BKTree()
            for p, h in STATE["all_images"].items():
                STATE["bktree"].add(h, p)

            self._send_json({
                "success": True,
                "deleted": deleted,
                "remaining": len(STATE["all_images"]),
                "bin_count": len(STATE["recycle_bin"]),
                "tree_stats": STATE["bktree"].get_tree_stats(),
            })

        # 6. API: Empty Entire Recycle Bin
        elif path == "/api/empty-bin":
            to_delete = list(STATE["recycle_bin"])
            deleted = 0
            for p in to_delete:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                    STATE["recycle_bin"].discard(p)
                    STATE["all_images"].pop(p, None)
                    STATE["thumbnails"].pop(p, None)
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting {p}: {e}")

            STATE["bktree"] = BKTree()
            for p, h in STATE["all_images"].items():
                STATE["bktree"].add(h, p)

            self._send_json({
                "success": True,
                "deleted": deleted,
                "remaining": len(STATE["all_images"]),
                "bin_count": len(STATE["recycle_bin"]),
                "tree_stats": STATE["bktree"].get_tree_stats(),
            })

        # 7. API: Auto-Cull Redundant Images via Rule
        elif path == "/api/auto-cull":
            rule = post_data.get("rule", "highest_res")
            tolerance = int(post_data.get("tolerance", 12))

            active_items = {
                p: h for p, h in STATE["all_images"].items()
                if p not in STATE["recycle_bin"]
            }
            cluster_data = STATE["bktree"].find_all_duplicate_clusters(
                tolerance=tolerance,
                all_items=active_items,
                metadata=STATE["metadata"],
            )

            staged_paths = []
            for cl in cluster_data.get("clusters", []):
                items = cl.get("items", [])
                if len(items) < 2:
                    continue

                def _rule_sort_key(item):
                    p = item["path"]
                    m = STATE["metadata"].get(p, {})
                    dim_str = m.get("dimensions", "0 × 0")
                    try:
                        w, h = [int(x.strip().split()[0]) for x in dim_str.split("×")]
                        res = w * h
                    except Exception:
                        res = 0
                    sz = float(m.get("size_mb", 0.0))
                    try:
                        mtime = os.path.getmtime(p)
                    except Exception:
                        mtime = 0.0

                    if rule == "highest_res":
                        return (res, sz, mtime)
                    elif rule == "largest_file":
                        return (sz, res, mtime)
                    elif rule == "newest":
                        return (mtime, res, sz)
                    elif rule == "oldest":
                        return (-mtime, res, sz)
                    return (res, sz, mtime)

                sorted_items = sorted(items, key=_rule_sort_key, reverse=True)
                for other in sorted_items[1:]:
                    op = other["path"]
                    if op != STATE["main_target"]:
                        STATE["recycle_bin"].add(op)
                        staged_paths.append(op)

            self._send_json({
                "success": True,
                "staged_count": len(staged_paths),
                "bin_count": len(STATE["recycle_bin"]),
                "rule": rule,
                "tolerance": tolerance,
                "total_clusters": len(cluster_data.get("clusters", [])),
            })

        else:
            self.send_error(404, "Endpoint not found")


def start_server(port=8080, auto_open=True):
    httpd = None
    ports_to_try = [port] + [p for p in [8080, 8081, 8082, 3000, 8000] if p != port]
    for try_port in ports_to_try:
        try:
            server_address = ("127.0.0.1", try_port)
            httpd = ThreadingHTTPServer(server_address, DeduplicatorHTTPHandler)
            port = try_port
            break
        except OSError:
            continue

    if not httpd:
        print("Error: Could not bind to any free port.")
        sys.exit(1)

    url = f"http://localhost:{port}"
    print(f"\n" + "=" * 60)
    print(f"  BURKHARD-KELLER METRIC SPACE DEDUPLICATOR (PRO WEB UI)")
    print(f"=" * 60)
    print(f"  Dashboard running at: {url}")
    print(f"  Press Ctrl + C in terminal to stop.")
    print(f"=" * 60 + "\n")

    if auto_open:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    # If folder argument provided via CLI, index immediately
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        print(f"Pre-indexing folder: {sys.argv[1]}")
        index_folder(sys.argv[1])

    start_server(port=8080)

