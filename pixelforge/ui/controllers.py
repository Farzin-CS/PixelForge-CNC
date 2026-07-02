from __future__ import annotations

import os
from tkinter import filedialog
from typing import Any

import cv2
from PIL import Image

from pixelforge.engine.material_presets import (
    MATERIAL_PRESETS,
    DEFAULT_MATERIAL,
    load_config,
    save_config,
    apply_material_preset,
)
from pixelforge.engine.image_processor import load_image
from pixelforge.engine.simulation import analyze_image, get_smart_suggestions
from pixelforge.ui.workers import ProcessingWorker, WorkerProgress


class AppController:
    def __init__(self, view):
        self.view = view
        self.worker: ProcessingWorker | None = None
        self.current_result = None
        self.image_path: str | None = None
        self.original_image = None

    def _get_initial_dir(self) -> str:
        return self.view._settings.get("last_directory", "")

    def on_browse_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Image",
            initialdir=self._get_initial_dir(),
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            self.image_path = path
            self.view._settings["last_directory"] = os.path.dirname(path)

            image = load_image(path)
            self.original_image = image

            h, w = image.shape[:2]
            size_kb = os.path.getsize(path) / 1024
            info = f"{w}x{h} px  |  {size_kb:.1f} KB"

            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)

            self.view.show_original(pil_img, info, os.path.basename(path))

            analysis = analyze_image(image)
            suggestions = get_smart_suggestions(analysis)
            self.view.update_smart_display(analysis, suggestions)

        except Exception as e:
            self.view.show_error("Load Error", f"Could not load image:\n{e}")

    def on_apply_suggestions(self) -> None:
        if self.view._smart_suggestions is None:
            return
        s = self.view._smart_suggestions
        if "mode" in s:
            self.view._mode_var.set(s["mode"])
        if "line_spacing_mm" in s:
            self.view._spacing_entry.set(s["line_spacing_mm"])
        if "max_depth" in s:
            self.view._depth_entry.set(s["max_depth"])
        if "gamma" in s:
            self.view._gamma_var.set(s["gamma"])
        self.view.set_status("Smart suggestions applied")

    def on_run_conversion(self) -> None:
        if not self.image_path or not os.path.exists(self.image_path):
            self.view.show_warning("No Image", "Please open an image first.")
            return

        if self.worker and self.worker.is_alive:
            return

        config = self.view.get_config()

        try:
            w = float(config.get("width_mm", 0))
            h = float(config.get("height_mm", 0))
            if w <= 0 or h <= 0:
                self.view.show_warning(
                    "Invalid Dimensions",
                    "Width and height must be greater than zero.",
                )
                return

            engraving_mode = config.get("engraving_mode", "raster_3d")
            if engraving_mode == "raster_3d":
                depth = float(config.get("max_depth", 0))
                if depth > 0:
                    self.view.show_warning(
                        "Invalid Depth",
                        "Max depth must be negative (e.g. -0.12).",
                    )
                    return
        except (ValueError, TypeError):
            self.view.show_warning(
                "Invalid Input",
                "Please check that all numeric fields contain valid numbers.",
            )
            return

        self.worker = ProcessingWorker(self.image_path, config)
        self.worker.start()
        self.view.start_processing()
        self._poll_progress()

    def _poll_progress(self) -> None:
        if not self.worker:
            return

        while not self.worker.progress_queue.empty():
            try:
                progress: WorkerProgress = self.worker.progress_queue.get_nowait()
                self.view.update_progress(progress.percent, progress.message)
            except Exception:
                break

        if self.worker.is_alive:
            self.view.root.after(50, self._poll_progress)
        elif self.worker.error:
            self.view.stop_processing()
            self.view.show_error(
                "Processing Error",
                f"Conversion failed:\n{self.worker.error}",
                details=self.worker.error,
            )
        elif self.worker.result:
            self.current_result = self.worker.result
            self.view.stop_processing()
            self.view.show_result(self.worker.result)

    def on_save_gcode(self) -> None:
        if not self.current_result or not self.current_result.gcode:
            self.view.show_warning("No Result", "Run processing first.")
            return

        path = filedialog.asksaveasfilename(
            title="Save G-code",
            initialdir=self._get_initial_dir(),
            defaultextension=".tap",
            filetypes=[("TAP", "*.tap"), ("NC", "*.nc"), ("All", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w") as f:
                f.write(self.current_result.gcode)
            self.view.set_status(f"Saved: {os.path.basename(path)}")
        except PermissionError:
            self.view.show_error(
                "Permission Error",
                f"Cannot write to:\n{path}\n\nCheck file permissions.",
            )
        except Exception as e:
            self.view.show_error("Save Error", f"Could not save:\n{e}")

    def on_save_gcode_from_dialog(self) -> None:
        self.on_save_gcode()

    def on_save_preview(self) -> None:
        if not self.current_result or not self.current_result.engraving_preview:
            self.view.show_warning("No Result", "Run processing first.")
            return

        path = filedialog.asksaveasfilename(
            title="Save Preview",
            initialdir=self._get_initial_dir(),
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All", "*.*")],
        )
        if not path:
            return

        try:
            cv2.imwrite(path, self.current_result.engraving_preview)
            self.view.set_status(f"Preview saved: {os.path.basename(path)}")
        except Exception as e:
            self.view.show_error("Save Error", f"Could not save preview:\n{e}")

    def on_save_config(self) -> None:
        config = self.view.get_config()
        try:
            save_config(config)
            self.view.set_status("Config saved")
        except Exception as e:
            self.view.show_error("Config Error", f"Could not save config:\n{e}")

    def on_load_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Load Config",
            initialdir=self._get_initial_dir(),
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
        )
        if not path:
            return

        try:
            config = load_config(path)
            self.view.apply_config(config)
            self.view.set_status(f"Config loaded: {os.path.basename(path)}")
        except Exception as e:
            self.view.show_error("Config Error", f"Could not load config:\n{e}")

    def on_material_change(self, material_name: str) -> None:
        preset = MATERIAL_PRESETS.get(material_name, MATERIAL_PRESETS[DEFAULT_MATERIAL])
        self.view.update_cnc_from_material(preset)
