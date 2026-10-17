import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ExifTags
from hash_logic import generate_hash
from bktree import BKTree


class DeduplicatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DSA Project: BK-Tree Image Deduplicator")
        self.geometry("1300x840")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Grid Layout: Left (Images, weight=3), Right (Controls & Metadata, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)

        # ==========================================
        # LEFT PANEL: Interactive Image Grid
        # ==========================================
        self.image_frame = ctk.CTkScrollableFrame(
            self,
            label_text="Library Grid (Load a folder to begin)"
        )
        self.image_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # ==========================================
        # RIGHT PANEL: Controls, Bin & EXIF Metadata
        # ==========================================
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(
            self.control_frame,
            text="Load a folder to begin",
            font=("Helvetica", 13, "bold"),
            wraplength=280
        )
        self.status_label.pack(pady=(12, 8))

        # 1. Folder Loader
        self.load_btn = ctk.CTkButton(
            self.control_frame,
            text="Load Image Folder",
            command=self.load_folder
        )
        self.load_btn.pack(pady=3, fill="x", padx=15)

        # 2. Navigation Bar (Library View & Recycle Bin View)
        self.nav_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.nav_frame.pack(pady=3, fill="x", padx=15)
        self.nav_frame.grid_columnconfigure((0, 1), weight=1)

        self.show_all_btn = ctk.CTkButton(
            self.nav_frame,
            text="All Photos (Library)",
            fg_color="#3a3a3a",
            hover_color="#505050",
            command=self.show_library_view,
            state="disabled"
        )
        self.show_all_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.bin_view_btn = ctk.CTkButton(
            self.nav_frame,
            text="Recycle Bin (0)",
            fg_color="#4a3525",
            hover_color="#634630",
            command=self.show_bin_view,
            state="disabled"
        )
        self.bin_view_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # 3. Find Duplicates Button (Locks a selected photo as Main Target)
        self.find_dups_btn = ctk.CTkButton(
            self.control_frame,
            text="Find Duplicates for Selected Photo",
            fg_color="#1f538d",
            hover_color="#296ab3",
            command=self.lock_selected_as_main,
            state="disabled"
        )
        self.find_dups_btn.pack(pady=(6, 3), fill="x", padx=15)

        # 4. Similarity Threshold Slider (0 to 35 out of 100 bits)
        self.slider_label = ctk.CTkLabel(
            self.control_frame,
            text="Hamming Distance Tolerance: 12 (≥88% Match)",
            font=("Helvetica", 13, "bold")
        )
        self.slider_label.pack(pady=(10, 2))

        self.slider = ctk.CTkSlider(
            self.control_frame,
            from_=0,
            to=35,
            number_of_steps=35,
            command=self.on_slider_change
        )
        self.slider.set(12)
        self.slider.pack(pady=3, fill="x", padx=15)

        # 5. Multi-Selection & Batch Culling Controls
        self.actions_label = ctk.CTkLabel(
            self.control_frame,
            text="Multi-Select & Batch Actions (⌘+Click Range)",
            font=("Helvetica", 12, "bold")
        )
        self.actions_label.pack(pady=(10, 3))

        # Select All / Deselect All Bar
        self.sel_helper_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.sel_helper_frame.pack(pady=3, fill="x", padx=15)
        self.sel_helper_frame.grid_columnconfigure((0, 1), weight=1)

        self.select_all_btn = ctk.CTkButton(
            self.sel_helper_frame,
            text="Select All (⌘A)",
            fg_color="#3a3a3a",
            hover_color="#505050",
            height=28,
            command=self.select_all_visible,
            state="disabled"
        )
        self.select_all_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.deselect_all_btn = ctk.CTkButton(
            self.sel_helper_frame,
            text="Deselect All",
            fg_color="#3a3a3a",
            hover_color="#505050",
            height=28,
            command=self.deselect_all,
            state="disabled"
        )
        self.deselect_all_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # Move to Bin Button (Works in both Library & Compare Views)
        self.move_to_bin_btn = ctk.CTkButton(
            self.control_frame,
            text="Move Selected to Bin (0)",
            fg_color="#b85d19",
            hover_color="#d46d20",
            command=self.move_selected_to_bin,
            state="disabled"
        )
        self.move_to_bin_btn.pack(pady=4, fill="x", padx=15)

        # Bin Management Sub-frame (Restore / Delete Forever)
        self.bin_actions_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.bin_actions_frame.pack(pady=3, fill="x", padx=15)
        self.bin_actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.restore_btn = ctk.CTkButton(
            self.bin_actions_frame,
            text="Restore Selected",
            fg_color="#2d7d46",
            hover_color="#389c57",
            command=self.restore_selected_from_bin,
            state="disabled"
        )
        self.restore_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.delete_selected_btn = ctk.CTkButton(
            self.bin_actions_frame,
            text="Delete Forever",
            fg_color="#a82020",
            hover_color="#c92828",
            command=self.permanently_delete_selected,
            state="disabled"
        )
        self.delete_selected_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self.empty_bin_btn = ctk.CTkButton(
            self.control_frame,
            text="Empty Entire Recycle Bin",
            fg_color="#6e1414",
            hover_color="#8f1a1a",
            command=self.empty_recycle_bin,
            state="disabled"
        )
        self.empty_bin_btn.pack(pady=3, fill="x", padx=15)

        # 6. EXIF Metadata Panel
        self.meta_title = ctk.CTkLabel(
            self.control_frame,
            text="EXIF Metadata (Last Clicked)",
            font=("Helvetica", 14, "bold")
        )
        self.meta_title.pack(pady=(10, 3))

        self.meta_box = ctk.CTkTextbox(
            self.control_frame,
            font=("Menlo", 12),
            activate_scrollbars=True
        )
        self.meta_box.pack(pady=(0, 10), padx=15, fill="both", expand=True)
        self.update_metadata_box(
            "Controls Guide:\n"
            "• Single Click: Select image (click again to deselect).\n"
            "• Command (⌘) + Click: Select a whole range ('bunch') from your last clicked image to the current one!\n"
            "• Command + A: Select all visible images.\n"
            "• Find Duplicates: Select 1 image in Library and click 'Find Duplicates for Selected Photo'."
        )

        # ==========================================
        # BACKEND STATE & MODIFIER TRACKING
        # ==========================================
        self.bktree = BKTree()
        self.all_images = {}          # file_path -> img_hash
        self.thumbnails = {}          # file_path -> CTkImage
        self.recycle_bin = set()      # Set of file_paths in internal Recycle Bin

        self.view_mode = "library"    # "library", "compare", or "bin"
        self.main_path = None         # Locked Main Target image for duplicate search
        self.main_hash = None
        self.selected_paths = set()   # Multi-selected file_paths in current view
        self.last_anchor_path = None  # Anchor image for Command+Click range selection
        self.inspected_path = None    # Most recently clicked image (for EXIF)

        self.current_grid_paths = []
        self.card_buttons = {}        # file_path -> CTkButton

        # Track macOS Command (⌘) and Shift (⇧) keys for range multi-selection
        self.modifier_held = False
        self.last_mouse_state = 0
        self.bind_all("<ButtonPress-1>", self._record_mouse_state, add="+")
        self.bind_all("<KeyPress>", self._on_key_press, add="+")
        self.bind_all("<KeyRelease>", self._on_key_release, add="+")
        self.bind_all("<Command-a>", lambda e: self.select_all_visible())
        self.bind_all("<Command-A>", lambda e: self.select_all_visible())

    # ==========================================
    # KEYBOARD / COMMAND-CLICK RANGE DETECTION
    # ==========================================
    def _record_mouse_state(self, event):
        self.last_mouse_state = getattr(event, "state", 0)

    def _on_key_press(self, event):
        if event.keysym in ("Meta_L", "Meta_R", "Super_L", "Super_R", "Shift_L", "Shift_R"):
            self.modifier_held = True

    def _on_key_release(self, event):
        if event.keysym in ("Meta_L", "Meta_R", "Super_L", "Super_R", "Shift_L", "Shift_R"):
            self.modifier_held = False

    def is_range_modifier_active(self):
        state_mod = (self.last_mouse_state & 0x0001) or (self.last_mouse_state & 0x0008) or (self.last_mouse_state & 0x0010)
        return bool(self.modifier_held or state_mod)

    # ==========================================
    # FOLDER LOADING & BK-TREE BUILD
    # ==========================================
    def rebuild_bktree(self):
        self.bktree = BKTree()
        for path, img_hash in self.all_images.items():
            self.bktree.add(img_hash, path)

    def load_folder(self):
        folder = filedialog.askdirectory(title="Select Image Folder")
        if not folder:
            return

        self.status_label.configure(text="Hashing images & building BK-Tree...")
        self.update()

        self.all_images.clear()
        self.thumbnails.clear()
        self.recycle_bin.clear()
        self.selected_paths.clear()
        self.main_path = None
        self.main_hash = None
        self.last_anchor_path = None
        self.inspected_path = None

        valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')

        for filename in sorted(os.listdir(folder)):
            if filename.lower().endswith(valid_extensions):
                path = os.path.join(folder, filename)
                img_hash = generate_hash(path)

                if img_hash is not None:
                    self.all_images[path] = img_hash
                    try:
                        img_data = Image.open(path)
                        img_data.thumbnail((220, 165))
                        self.thumbnails[path] = ctk.CTkImage(
                            light_image=img_data,
                            dark_image=img_data,
                            size=img_data.size
                        )
                    except Exception as e:
                        print(f"Thumbnail error for {path}: {e}")

        self.rebuild_bktree()
        self.show_all_btn.configure(state="normal")
        self.bin_view_btn.configure(state="normal")
        self.update_bin_counter()
        self.show_library_view()

    # ==========================================
    # VIEW MODES (LIBRARY, COMPARE, RECYCLE BIN)
    # ==========================================
    def show_library_view(self):
        self.view_mode = "library"
        self.main_path = None
        self.main_hash = None
        self.selected_paths.clear()
        self.last_anchor_path = None
        self.inspected_path = None

        active_paths = [p for p in self.all_images.keys() if p not in self.recycle_bin]
        self.image_frame.configure(label_text=f"Library View — All Active Photos ({len(active_paths)})")

        self.render_grid(active_paths)
        self.update_ui_state()

    def lock_selected_as_main(self):
        target = None
        if len(self.selected_paths) == 1:
            target = next(iter(self.selected_paths))
        elif self.inspected_path and self.inspected_path in self.all_images:
            target = self.inspected_path

        if not target:
            return

        self.main_path = target
        self.main_hash = self.all_images.get(target)
        self.selected_paths.clear()
        self.last_anchor_path = None
        self.inspected_path = target
        self.view_mode = "compare"

        self.update_metadata_box(self.extract_metadata(target))
        self.refresh_compare_grid()

    def show_bin_view(self):
        self.view_mode = "bin"
        self.selected_paths.clear()
        self.last_anchor_path = None
        self.inspected_path = None

        binned_paths = sorted(list(self.recycle_bin))
        self.image_frame.configure(label_text=f"Internal Recycle Bin ({len(binned_paths)} photo(s) staged)")

        self.render_grid(binned_paths)
        self.update_ui_state()

    # ==========================================
    # CLICK TOGGLE & COMMAND+CLICK RANGE LOGIC
    # ==========================================
    def on_thumbnail_click(self, path):
        self.inspected_path = path
        self.update_metadata_box(self.extract_metadata(path))

        if self.view_mode == "compare" and path == self.main_path:
            self.update_ui_state()
            return

        if (
            self.is_range_modifier_active()
            and self.last_anchor_path in self.current_grid_paths
            and path in self.current_grid_paths
        ):
            idx1 = self.current_grid_paths.index(self.last_anchor_path)
            idx2 = self.current_grid_paths.index(path)
            start, end = min(idx1, idx2), max(idx1, idx2)
            range_paths = [
                p for p in self.current_grid_paths[start : end + 1]
                if not (self.view_mode == "compare" and p == self.main_path)
            ]

            all_already_selected = all(p in self.selected_paths for p in range_paths)
            for p in range_paths:
                if all_already_selected:
                    self.selected_paths.discard(p)
                else:
                    self.selected_paths.add(p)
                self.update_card_appearance(p)
        else:
            if path in self.selected_paths:
                self.selected_paths.remove(path)
            else:
                self.selected_paths.add(path)
            self.last_anchor_path = path
            self.update_card_appearance(path)

        self.update_ui_state()

    def select_all_visible(self):
        if not self.current_grid_paths:
            return
        for path in self.current_grid_paths:
            if self.view_mode == "compare" and path == self.main_path:
                continue
            self.selected_paths.add(path)
            self.update_card_appearance(path)
        self.update_ui_state()

    def deselect_all(self):
        prev = list(self.selected_paths)
        self.selected_paths.clear()
        for path in prev:
            self.update_card_appearance(path)
        self.update_ui_state()

    def on_slider_change(self, val):
        tolerance = int(float(val))
        self.slider_label.configure(
            text=f"Hamming Distance Tolerance: {tolerance} (≥{100 - tolerance}% Match)"
        )
        if self.view_mode == "compare" and self.main_hash is not None:
            self.refresh_compare_grid()

    def refresh_compare_grid(self):
        if not self.main_hash:
            return

        tolerance = int(float(self.slider.get()))
        raw_matches = self.bktree.search(self.main_hash, tolerance)
        matches = [p for p in raw_matches if p not in self.recycle_bin]

        matches.sort(key=lambda p: (0 if p == self.main_path else 1, self.main_hash - self.all_images[p]))

        visible_set = set(matches)
        self.selected_paths = {p for p in self.selected_paths if p in visible_set and p != self.main_path}

        main_name = os.path.basename(self.main_path)
        self.image_frame.configure(
            label_text=f"Duplicates for Main Image: {main_name} ({len(matches)} shown | Tolerance: {tolerance} / ≥{100 - tolerance}% Match)"
        )

        self.render_grid(matches)
        self.update_ui_state()

    # ==========================================
    # BATCH RECYCLE BIN & DISK DELETION
    # ==========================================
    def move_selected_to_bin(self):
        if not self.selected_paths:
            return

        for path in list(self.selected_paths):
            if path != self.main_path:
                self.recycle_bin.add(path)

        self.selected_paths.clear()
        self.last_anchor_path = None
        self.update_bin_counter()

        if self.view_mode == "compare":
            self.inspected_path = self.main_path
            self.update_metadata_box(self.extract_metadata(self.main_path))
            self.refresh_compare_grid()
        elif self.view_mode == "library":
            self.show_library_view()

    def restore_selected_from_bin(self):
        if not self.selected_paths:
            return

        for path in list(self.selected_paths):
            self.recycle_bin.discard(path)

        self.selected_paths.clear()
        self.last_anchor_path = None
        self.inspected_path = None
        self.update_bin_counter()
        self.update_metadata_box("Selected photo(s) restored to the Library.")
        self.show_bin_view()

    def permanently_delete_selected(self):
        if not self.selected_paths:
            return

        count = len(self.selected_paths)
        confirm = messagebox.askyesno(
            "Confirm Permanent Deletion",
            f"Are you sure you want to permanently delete {count} selected photo(s) from your actual folder?\n\nThis action cannot be undone."
        )
        if not confirm:
            return

        deleted = 0
        for path in list(self.selected_paths):
            try:
                os.remove(path)
                self.recycle_bin.discard(path)
                self.all_images.pop(path, None)
                self.thumbnails.pop(path, None)
                deleted += 1
            except Exception as e:
                print(f"Error deleting {path}: {e}")

        self.selected_paths.clear()
        self.last_anchor_path = None
        self.inspected_path = None
        self.rebuild_bktree()
        self.update_bin_counter()
        self.update_metadata_box(f"Permanently deleted {deleted} selected photo(s) from disk.")
        self.show_bin_view()

    def empty_recycle_bin(self):
        if not self.recycle_bin:
            return

        count = len(self.recycle_bin)
        confirm = messagebox.askyesno(
            "Empty Recycle Bin",
            f"Are you sure you want to permanently delete ALL {count} photo(s) in the Recycle Bin from your actual folder?\n\nThis action cannot be undone."
        )
        if not confirm:
            return

        deleted = 0
        for path in list(self.recycle_bin):
            try:
                os.remove(path)
                self.recycle_bin.discard(path)
                self.all_images.pop(path, None)
                self.thumbnails.pop(path, None)
                deleted += 1
            except Exception as e:
                print(f"Error deleting {path}: {e}")

        self.selected_paths.clear()
        self.last_anchor_path = None
        self.inspected_path = None
        self.rebuild_bktree()
        self.update_bin_counter()
        self.update_metadata_box(f"Emptied Recycle Bin: {deleted} photo(s) deleted from disk.")
        self.show_bin_view()

    def update_bin_counter(self):
        self.bin_view_btn.configure(text=f"Recycle Bin ({len(self.recycle_bin)})")

    # ==========================================
    # UI STATE & BUTTON UPDATES
    # ==========================================
    def update_ui_state(self):
        sel_count = len(self.selected_paths)

        if self.view_mode in ("library", "compare"):
            if sel_count == 1:
                sel_file = os.path.basename(next(iter(self.selected_paths)))
                self.find_dups_btn.configure(
                    state="normal",
                    text=f"Find Duplicates for '{sel_file}'"
                )
            else:
                self.find_dups_btn.configure(
                    state="disabled",
                    text="Select 1 Photo to Find Duplicates"
                )
        else:
            self.find_dups_btn.configure(state="disabled", text="Find Duplicates for Selected Photo")

        if self.view_mode == "library":
            total_lib = len(self.current_grid_paths)
            self.status_label.configure(
                text=f"Library Mode | Selected: {sel_count} of {total_lib}\n(Click to toggle • ⌘+Click for range)"
            )
            self.select_all_btn.configure(state="normal" if total_lib > 0 else "disabled")
            self.deselect_all_btn.configure(state="normal" if sel_count > 0 else "disabled")
            self.move_to_bin_btn.configure(
                state="normal" if sel_count > 0 else "disabled",
                text=f"Move Selected to Bin ({sel_count})" if sel_count > 0 else "Select Photos to Move to Bin"
            )
            self.restore_btn.configure(state="disabled", text="Restore Selected")
            self.delete_selected_btn.configure(state="disabled", text="Delete Forever")
            self.empty_bin_btn.configure(state="disabled")

        elif self.view_mode == "compare":
            main_name = os.path.basename(self.main_path) if self.main_path else "None"
            self.status_label.configure(
                text=f"Main Target Locked: {main_name}\nSelected Duplicates: {sel_count} (⌘+Click range)"
            )
            has_dups = len(self.current_grid_paths) > 1
            self.select_all_btn.configure(state="normal" if has_dups else "disabled")
            self.deselect_all_btn.configure(state="normal" if sel_count > 0 else "disabled")
            self.move_to_bin_btn.configure(
                state="normal" if sel_count > 0 else "disabled",
                text=f"Move Selected to Bin ({sel_count})" if sel_count > 0 else "Click Duplicates to Select"
            )
            self.restore_btn.configure(state="disabled", text="Restore Selected")
            self.delete_selected_btn.configure(state="disabled", text="Delete Forever")
            self.empty_bin_btn.configure(state="disabled")

        elif self.view_mode == "bin":
            bin_total = len(self.recycle_bin)
            self.status_label.configure(
                text=f"Recycle Bin | Selected: {sel_count} of {bin_total}\n(Click to toggle • ⌘+Click for range)"
            )
            self.select_all_btn.configure(state="normal" if bin_total > 0 else "disabled")
            self.deselect_all_btn.configure(state="normal" if sel_count > 0 else "disabled")
            self.move_to_bin_btn.configure(state="disabled", text="Already in Recycle Bin")

            if sel_count > 0:
                self.restore_btn.configure(state="normal", text=f"Restore ({sel_count})")
                self.delete_selected_btn.configure(state="normal", text=f"Delete Forever ({sel_count})")
            else:
                self.restore_btn.configure(state="disabled", text="Restore Selected")
                self.delete_selected_btn.configure(state="disabled", text="Delete Forever")

            self.empty_bin_btn.configure(state="normal" if bin_total > 0 else "disabled")

    # ==========================================
    # GRID RENDERING & CARD STYLING
    # ==========================================
    def get_card_style(self, path):
        filename = os.path.basename(path)
        if self.view_mode == "compare":
            dist = self.main_hash - self.all_images[path]
            sim = max(0, 100 - dist)
            if path == self.main_path:
                return f"{filename}\n[MAIN TARGET — 100%]", "#1f538d"  # Blue
            elif path in self.selected_paths:
                return f"{filename}\n[✓ SELECTED — {sim}% (Dist: {dist})]", "#b85d19"  # Amber
            else:
                return f"{filename}\nSimilarity: {sim}% (Dist: {dist})", "#2b2b2b"
        elif self.view_mode == "bin":
            if path in self.selected_paths:
                return f"{filename}\n[✓ SELECTED IN BIN]", "#8f2424"  # Red
            else:
                return f"{filename}\n(In Recycle Bin)", "#2b2b2b"
        else:  # Library View
            if path in self.selected_paths:
                return f"{filename}\n[✓ SELECTED]", "#b85d19"  # Amber
            else:
                return filename, "#2b2b2b"

    def update_card_appearance(self, path):
        btn = self.card_buttons.get(path)
        if btn:
            caption, card_color = self.get_card_style(path)
            btn.configure(text=caption, fg_color=card_color)

    def render_grid(self, file_paths):
        for widget in self.card_buttons.values():
            widget.destroy()
        self.card_buttons.clear()
        self.current_grid_paths = list(file_paths)

        for idx, path in enumerate(file_paths):
            ctk_img = self.thumbnails.get(path)
            if not ctk_img:
                continue

            caption, card_color = self.get_card_style(path)

            btn = ctk.CTkButton(
                self.image_frame,
                image=ctk_img,
                text=caption,
                compound="top",
                fg_color=card_color,
                hover_color="#3b6ea5",
                width=235,
                height=210,
                corner_radius=8,
                command=lambda p=path: self.on_thumbnail_click(p)
            )
            btn.grid(row=idx // 3, column=idx % 3, padx=10, pady=10)
            self.card_buttons[path] = btn

    # ==========================================
    # EXIF METADATA EXTRACTION
    # ==========================================
    def extract_metadata(self, path):
        lines = []
        try:
            stat = os.stat(path)
            size_mb = stat.st_size / (1024 * 1024)
            lines.append(f"File: {os.path.basename(path)}")

            if self.view_mode == "compare" and self.main_path:
                if path == self.main_path:
                    lines.append("Role: LOCKED MAIN TARGET (100%)")
                else:
                    dist = self.main_hash - self.all_images[path]
                    lines.append(f"Role: DUPLICATE ({100 - dist}% Match | Dist: {dist})")

            lines.append(f"Size: {size_mb:.2f} MB")

            img = Image.open(path)
            lines.append(f"Dimensions: {img.width} x {img.height} px")
            lines.append(f"Format: {img.format}")
            lines.append(f"100-bit Hash: {str(self.all_images.get(path))}")
            lines.append("-" * 28)

            exif_data = {}
            raw_exif = img.getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    exif_data[tag_name] = value
                if 0x8769 in raw_exif:
                    for tag_id, value in raw_exif.get_ifd(0x8769).items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[tag_name] = value

            camera = f"{exif_data.get('Make', '')} {exif_data.get('Model', '')}".strip()
            lines.append(f"Camera: {camera if camera else 'N/A'}")
            lines.append(f"Date: {exif_data.get('DateTimeOriginal', exif_data.get('DateTime', 'N/A'))}")

            f_num = exif_data.get('FNumber')
            lines.append(f"Aperture: f/{float(f_num):.1f}" if f_num else "Aperture: N/A")

            exp = exif_data.get('ExposureTime')
            if exp:
                exp_val = float(exp)
                shutter = f"1/{int(round(1/exp_val))} sec" if 0 < exp_val < 1 else f"{exp_val} sec"
                lines.append(f"Shutter Speed: {shutter}")
            else:
                lines.append("Shutter Speed: N/A")

            lines.append(f"ISO: {exif_data.get('ISOSpeedRatings', 'N/A')}")

            focal = exif_data.get('FocalLength')
            lines.append(f"Focal Length: {float(focal):.0f} mm" if focal else "Focal Length: N/A")

        except Exception as e:
            lines.append(f"\nError reading EXIF: {e}")

        return "\n".join(lines)

    def update_metadata_box(self, text):
        self.meta_box.configure(state="normal")
        self.meta_box.delete("1.0", "end")
        self.meta_box.insert("1.0", text)
        self.meta_box.configure(state="disabled")


if __name__ == "__main__":
    app = DeduplicatorApp()
    app.mainloop()