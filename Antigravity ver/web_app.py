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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PIL import Image, ExifTags

from bktree import BKTree
from hash_logic import generate_hash


# Global Application State
STATE = {
    "folder": None,
    "bktree": BKTree(),
    "all_images": {},     # file_path -> img_hash
    "thumbnails": {},     # file_path -> JPEG bytes
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


def index_folder(folder_path: str):
    """Scans folder, extracts 100-bit perceptual hashes, and constructs the BK-Tree."""
    if not os.path.isdir(folder_path):
        return False, "Folder does not exist"

    STATE["folder"] = folder_path
    STATE["all_images"].clear()
    STATE["thumbnails"].clear()
    STATE["recycle_bin"].clear()
    STATE["main_target"] = None
    STATE["main_hash"] = None
    STATE["bktree"] = BKTree()

    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    filenames = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)])

    for fname in filenames:
        fpath = os.path.join(folder_path, fname)
        img_hash = generate_hash(fpath)
        if img_hash is not None:
            STATE["all_images"][fpath] = img_hash
            STATE["bktree"].add(img_hash, fpath)

            # Generate memory-cached thumbnail
            try:
                with Image.open(fpath) as img:
                    img.thumbnail((320, 240))
                    buf = io.BytesIO()
                    img.convert("RGB").save(buf, format="JPEG", quality=80)
                    STATE["thumbnails"][fpath] = buf.getvalue()
            except Exception as e:
                print(f"Thumbnail error for {fpath}: {e}")

    return True, f"Indexed {len(STATE['all_images'])} images into BK-Tree"


def get_exif_data(fpath: str) -> dict:
    """Extracts camera metadata and formatting details."""
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
        stat = os.stat(fpath)
        out["size_mb"] = round(stat.st_size / (1024 * 1024), 2)

        with Image.open(fpath) as img:
            out["dimensions"] = f"{img.width} x {img.height} px"
            out["format"] = img.format or "JPEG"

            raw_exif = img.getexif()
            if raw_exif:
                exif = {}
                for tag_id, val in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    exif[tag_name] = val
                if 0x8769 in raw_exif:
                    for tag_id, val in raw_exif.get_ifd(0x8769).items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        exif[tag_name] = val

                cam = f"{exif.get('Make', '')} {exif.get('Model', '')}".strip()
                if cam:
                    out["camera"] = cam
                out["date"] = exif.get("DateTimeOriginal", exif.get("DateTime", "N/A"))

                f_num = exif.get("FNumber")
                if f_num:
                    out["aperture"] = f"f/{float(f_num):.1f}"

                exp = exif.get("ExposureTime")
                if exp:
                    exp_val = float(exp)
                    out["shutter"] = f"1/{int(round(1/exp_val))}s" if 0 < exp_val < 1 else f"{exp_val}s"

                iso = exif.get("ISOSpeedRatings")
                if iso:
                    out["iso"] = str(iso)

                focal = exif.get("FocalLength")
                if focal:
                    out["focal"] = f"{float(focal):.0f}mm"
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
                if view_mode == "bin" and is_binned:
                    items.append({
                        "path": fpath,
                        "filename": os.path.basename(fpath),
                        "hash": str(h),
                        "is_binned": True,
                    })
                elif view_mode == "library" and not is_binned:
                    items.append({
                        "path": fpath,
                        "filename": os.path.basename(fpath),
                        "hash": str(h),
                        "is_binned": False,
                    })

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
            if target_path and os.path.isfile(target_path):
                mime, _ = mimetypes.guess_type(target_path)
                with open(target_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime or "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
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
                sim = max(0, 100 - dist)
                results.append({
                    "path": m_path,
                    "filename": os.path.basename(m_path),
                    "distance": dist,
                    "similarity": sim,
                    "is_target": (m_path == target_path),
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
            target_path = params.get("target", [STATE["main_target"]])[0]
            tolerance = int(params.get("tolerance", [12])[0])
            target_h = STATE["all_images"].get(target_path) if target_path else None
            graph_data = STATE["bktree"].get_tree_graph(target_hash=target_h, tolerance=tolerance)
            self._send_json(graph_data)

        # 7. API: EXIF Metadata
        elif path == "/api/exif":
            target_path = params.get("path", [None])[0]
            if target_path:
                self._send_json(get_exif_data(target_path))
            else:
                self._send_json({"error": "No path provided"}, status=400)

        # 8. Serve Frontend (SPA index.html)
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

