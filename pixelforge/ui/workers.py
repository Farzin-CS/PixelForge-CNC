from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from pixelforge.engine.types import (
    GCodeConfig,
    EngravingMode,
    ContourPath,
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
from pixelforge.engine.contour_tracer import extract_contours, convert_to_line_art
from pixelforge.engine.gcode_2d import generate_gcode_2d


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

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

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
        self.progress_queue.put(WorkerProgress(percent, message, stage))

    def _run(self) -> None:
        try:
            self._emit(0.02, "Loading image...", "loading")
            image = load_image(self.image_path)
            h, w = image.shape[:2]

            apply_material_preset(self.config.get("material", "gold"), self.config)

            self._emit(0.05, "Analyzing image...", "processing")
            analysis = analyze_image(image)

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

            self._emit(0.40, "Enhancing image...", "processing")
            gray = enhance_image(image, self.config)

            engraving_mode = EngravingMode(self.config.get("engraving_mode", "raster_3d"))

            if engraving_mode == EngravingMode.RASTER_3D:
                self._run_3d(gray, analysis)
            else:
                self._run_2d(image, gray, analysis, engraving_mode)

        except Exception as e:
            self.error = str(e)
            self._emit(0.0, str(e), "error")

    def _run_3d(self, gray: np.ndarray, analysis: dict[str, Any]) -> None:
        cfg = self.config
        gray = resize_to_engraving(
            gray, cfg["width_mm"], cfg["height_mm"], cfg["line_spacing_mm"]
        )

        self._emit(0.55, "Generating G-code...", "generating")
        from pixelforge.engine.material_presets import to_gcode_config
        gcode_config = to_gcode_config(cfg)
        gcode, stats = generate_gcode(
            gray, gcode_config,
            progress_callback=lambda p, m: self._emit(0.55 + p * 0.35, m, "generating"),
        )

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

        h, w = gray.shape
        target_h = int(cfg["height_mm"] * 10)
        target_w = int(target_h * (w / h)) if h > 0 else int(cfg["width_mm"] * 10)
        gray_scaled = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        if mode == EngravingMode.LINE_ART:
            self._emit(0.50, "Converting to line art...", "processing")
            contours = convert_to_line_art(
                gray_scaled,
                edge_low=int(cfg.get("edge_low", 50)),
                edge_high=int(cfg.get("edge_high", 150)),
                progress_callback=lambda p, m: self._emit(0.50 + p * 0.20, m, "processing"),
            )
        else:
            self._emit(0.50, "Extracting contours...", "processing")
            contours = extract_contours(
                gray_scaled,
                simplify_epsilon=float(cfg.get("contour_simplify_epsilon", 0.5)),
                min_area=float(cfg.get("min_contour_area", 1.0)),
                invert=cfg.get("invert", False),
                progress_callback=lambda p, m: self._emit(0.50 + p * 0.20, m, "processing"),
            )

        scale_x = cfg["width_mm"] / target_w if target_w > 0 else 1.0
        scale_y = cfg["height_mm"] / target_h if target_h > 0 else 1.0

        scaled_contours: list[ContourPath] = []
        for c in contours:
            scaled = [(px * scale_x, py * scale_y) for px, py in c.points]
            scaled_contours.append(ContourPath(
                points=scaled, is_closed=c.is_closed, depth_mm=cfg.get("max_depth", -0.1)
            ))

        self._emit(0.75, "Generating 2D G-code...", "generating")
        from pixelforge.engine.material_presets import to_gcode_config
        gcode_config = to_gcode_config(cfg)
        gcode, stats = generate_gcode_2d(
            scaled_contours, gcode_config,
            progress_callback=lambda p, m: self._emit(0.75 + p * 0.20, m, "generating"),
        )

        self._emit(0.95, "Rendering contour preview...", "generating")
        contour_preview = self._render_contour_preview(scaled_contours, target_w, target_h)

        self.result = WorkerResult(
            gcode=gcode, stats=stats, depth_map=gray_scaled,
            engraving_preview=None, contour_preview=contour_preview,
            analysis=analysis, config=cfg.copy(),
            image_dims=f"{target_w}x{target_h}",
        )
        self._emit(1.0, "Complete", "done")

    def _render_contour_preview(
        self, contours: list[ContourPath], width: int, height: int
    ) -> np.ndarray:
        preview = np.ones((height, width, 3), dtype=np.uint8) * 15
        for contour in contours:
            if len(contour.points) < 2:
                continue
            pts_list = []
            for px, py in contour.points:
                sx = int(px * width / max(c.points[-1][0] + 1 for c in contours if c.points))
                sy = int(py * height / max(c.points[-1][1] + 1 for c in contours if c.points))
                sx = max(0, min(width - 1, sx))
                sy = max(0, min(height - 1, sy))
                pts_list.append([sx, sy])
            if len(pts_list) < 2:
                continue
            pts = np.array(pts_list, dtype=np.int32).reshape(-1, 1, 2)
            if contour.is_closed and len(pts_list) > 2:
                cv2.polylines(preview, [pts], True, (233, 69, 96), 1)
            else:
                cv2.polylines(preview, [pts], False, (46, 204, 113), 1)
        return preview
