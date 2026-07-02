from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from pixelforge.engine.types import (
    EngravingMode,
    ProgressCallback,
)
from pixelforge.engine.image_processor import (
    load_image,
    preprocess_image,
    enhance_image,
    resize_to_engraving,
    remove_background,
)
from pixelforge.engine.material_presets import apply_material_preset
from pixelforge.engine.simulation import render_engraving_preview, analyze_image
from pixelforge.engine.gcode_generator import generate_gcode


@dataclass
class WorkerProgress:
    percent: float
    message: str
    stage: str


@dataclass
class WorkerResult:
    gcode: str
    stats: Any
    depth_map: np.ndarray | None
    engraving_preview: np.ndarray | None
    contour_preview: np.ndarray | None
    analysis: dict[str, Any]
    config: dict[str, Any]
    image_dims: str


class ProcessingWorker:
    def __init__(self, image_path: str, config: dict[str, Any]):
        self.image_path = image_path
        self.config = config
        self.progress_queue: queue.Queue[WorkerProgress] = queue.Queue()
        self._result: WorkerResult | None = None
        self._error: str | None = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    @property
    def result(self) -> WorkerResult | None:
        with self._lock:
            return self._result

    @result.setter
    def result(self, value: WorkerResult | None) -> None:
        with self._lock:
            self._result = value

    @property
    def error(self) -> str | None:
        with self._lock:
            return self._error

    @error.setter
    def error(self, value: str | None) -> None:
        with self._lock:
            self._error = value

    def _emit(self, percent: float, message: str, stage: str) -> None:
        if not self._cancel.is_set():
            self.progress_queue.put(WorkerProgress(percent, message, stage))

    def _check_cancel(self) -> None:
        if self._cancel.is_set():
            self._emit(0.0, "Cancelled", "cancelled")
            raise RuntimeError("Cancelled by user")

    def _run(self) -> None:
        try:
            self._emit(0.02, "Loading image...", "loading")
            image = load_image(self.image_path)
            h, w = image.shape[:2]
            self._check_cancel()

            apply_material_preset(self.config.get("material", "gold"), self.config)

            self._emit(0.05, "Analyzing image...", "processing")
            analysis = analyze_image(image)
            self._check_cancel()

            self._emit(0.10, "Preprocessing...", "processing")
            image = preprocess_image(image, self.config)

            if self.config.get("remove_background", False):
                self._emit(0.15, "Removing background...", "processing")
                image, _ = remove_background(
                    image,
                    progress_callback=lambda p, m: self._emit(
                        0.15 + p * 0.20, m, "processing"
                    ),
                )
                self._check_cancel()

            self._emit(0.40, "Enhancing image...", "processing")
            gray = enhance_image(image, self.config)
            self._check_cancel()

            engraving_mode = EngravingMode(self.config.get("engraving_mode", "raster_3d"))

            if engraving_mode == EngravingMode.RASTER_3D:
                self._run_3d(image, gray, analysis)
            else:
                self._run_2d(image, gray, analysis, engraving_mode)

        except Exception as e:
            if self._cancel.is_set():
                self._emit(0.0, "Cancelled", "cancelled")
            else:
                self.error = str(e)
                self._emit(0.0, str(e), "error")

    def _run_3d(self, image_bgr: np.ndarray, gray: np.ndarray,
                analysis: dict[str, Any]) -> None:
        cfg = self.config
        detail = float(cfg.get("detail_level", 0.5))

        self._emit(0.48, "Enhancing depth map...", "processing")
        lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe_clip = 1.5 + detail * 3.0
        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
        l = clahe.apply(l)
        gray_enhanced = cv2.bilateralFilter(l, d=9, sigmaColor=75, sigmaSpace=75)
        self._check_cancel()

        spacing_mul = 2.5 - detail * 1.5
        effective_spacing = cfg["line_spacing_mm"] * spacing_mul

        gray = resize_to_engraving(
            gray_enhanced, cfg["width_mm"], cfg["height_mm"], effective_spacing
        )
        self._check_cancel()

        self._emit(0.55, "Generating G-code...", "generating")
        from pixelforge.engine.material_presets import to_gcode_config
        gcode_config = to_gcode_config(cfg)
        gcode, stats = generate_gcode(
            gray, gcode_config,
            progress_callback=lambda p, m: self._emit(0.55 + p * 0.35, m, "generating"),
        )
        self._check_cancel()

        self._emit(0.92, "Rendering preview...", "generating")
        preview = render_engraving_preview(gray, cfg)

        self.result = WorkerResult(
            gcode=gcode, stats=stats, depth_map=gray,
            engraving_preview=preview, contour_preview=None,
            analysis=analysis, config=cfg.copy(),
            image_dims=f"{gray.shape[1]}x{gray.shape[0]}",
        )
        self._emit(1.0, "Complete", "done")

    def _run_2d(self, image_bgr: np.ndarray, gray: np.ndarray,
                analysis: dict[str, Any], mode: EngravingMode) -> None:
        cfg = self.config
        detail = float(cfg.get("detail_level", 0.5))

        self._emit(0.48, "Preparing coarse raster...", "processing")
        lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        gray_2d = cv2.bilateralFilter(l, d=9, sigmaColor=75, sigmaSpace=75)
        self._check_cancel()

        num_levels = max(2, int(2 + detail * 8))
        bin_edges = np.linspace(0, 255, num_levels + 1)
        gray_2d = np.digitize(gray_2d, bin_edges[1:-1]) * (255 // num_levels)
        gray_2d = gray_2d.astype(np.uint8)
        self._check_cancel()

        scale_pct = 0.20 + detail * 0.60
        h, w = gray_2d.shape
        small_w = max(4, int(w * scale_pct))
        small_h = max(4, int(h * scale_pct))
        gray_small = cv2.resize(gray_2d, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
        gray_scaled = cv2.resize(gray_small, (w, h), interpolation=cv2.INTER_NEAREST)
        self._check_cancel()

        h_mm, w_mm = cfg["height_mm"], cfg["width_mm"]
        target_h = int(h_mm * 10)
        target_w = int(target_h * (w / h)) if h > 0 else int(w_mm * 10)
        gray_scaled = cv2.resize(gray_scaled, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
        self._check_cancel()

        spacing_mul = 3.0 - detail * 2.0
        effective_spacing = cfg["line_spacing_mm"] * spacing_mul
        gray_raster = resize_to_engraving(
            gray_scaled, w_mm, h_mm, effective_spacing
        )
        self._check_cancel()

        self._emit(0.65, "Generating 2D G-code via raster...", "generating")
        from pixelforge.engine.material_presets import to_gcode_config
        gcode_config = to_gcode_config(cfg)
        gcode, stats = generate_gcode(
            gray_raster, gcode_config,
            progress_callback=lambda p, m: self._emit(0.65 + p * 0.25, m, "generating"),
        )
        self._check_cancel()

        self._emit(0.92, "Rendering preview...", "generating")
        contour_preview = cv2.cvtColor(
            cv2.applyColorMap(gray_raster, cv2.COLORMAP_BONE),
            cv2.COLOR_BGR2RGB,
        )
        preview_rgb = cv2.resize(contour_preview, (target_w, target_h),
                                  interpolation=cv2.INTER_NEAREST)

        self.result = WorkerResult(
            gcode=gcode, stats=stats, depth_map=gray_raster,
            engraving_preview=None, contour_preview=preview_rgb,
            analysis=analysis, config=cfg.copy(),
            image_dims=f"{gray_raster.shape[1]}x{gray_raster.shape[0]}",
        )
        self._emit(1.0, "Complete", "done")
