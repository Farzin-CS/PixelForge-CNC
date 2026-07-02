from __future__ import annotations

import cv2
import numpy as np

from pixelforge.engine.types import ContourPath, ProgressCallback


def extract_contours(
    gray: np.ndarray,
    simplify_epsilon: float = 0.5,
    min_area: float = 1.0,
    invert: bool = False,
    progress_callback: ProgressCallback = None,
) -> list[ContourPath]:
    if progress_callback:
        progress_callback(0.0, "Thresholding image...")

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if invert:
        binary = 255 - binary

    if progress_callback:
        progress_callback(0.2, "Finding contours...")

    contours, hierarchy = cv2.findContours(
        binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    if progress_callback:
        progress_callback(0.4, f"Processing {len(contours)} contours...")

    result: list[ContourPath] = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        epsilon = simplify_epsilon
        simplified = cv2.approxPolyDP(contour, epsilon, True)

        points = [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]
        if len(points) < 3:
            continue

        is_closed = cv2.arcLength(contour, True) > 0
        result.append(ContourPath(points=points, is_closed=is_closed, depth_mm=0.0))

        if progress_callback and i % 50 == 0:
            progress_callback(
                0.4 + 0.3 * (i / max(len(contours), 1)),
                f"Processing contour {i + 1}/{len(contours)}",
            )

    if progress_callback:
        progress_callback(0.7, f"Found {len(result)} contours")

    def _contour_area(c: ContourPath) -> float:
        xs = [p[0] for p in c.points]
        ys = [p[1] for p in c.points]
        return (max(xs) - min(xs)) * (max(ys) - min(ys)) if xs and ys else 0

    result.sort(key=_contour_area, reverse=True)
    return result


def convert_to_line_art(
    gray: np.ndarray,
    edge_low: int = 50,
    edge_high: int = 150,
    min_line_length: int = 10,
    progress_callback: ProgressCallback = None,
) -> list[ContourPath]:
    if progress_callback:
        progress_callback(0.0, "Detecting edges...")

    edges = cv2.Canny(gray, edge_low, edge_high)

    if progress_callback:
        progress_callback(0.2, "Thinning edges...")

    try:
        skeleton = cv2.ximgproc.thinning(edges)
        if skeleton is None:
            skeleton = edges
    except Exception:
        skeleton = edges

    if progress_callback:
        progress_callback(0.4, "Tracing paths...")

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(skeleton, 8)

    result: list[ContourPath] = []
    for label_id in range(1, num_labels):
        if stats[label_id, cv2.CC_STAT_AREA] < min_line_length:
            continue

        ys, xs = np.where(labels == label_id)
        if len(xs) < 2:
            continue

        coords = list(zip(xs.tolist(), ys.tolist()))
        result.append(ContourPath(points=coords, is_closed=False, depth_mm=0.0))

        if progress_callback and label_id % 50 == 0:
            progress_callback(
                0.4 + 0.4 * (label_id / max(num_labels, 1)),
                f"Tracing line {label_id}/{num_labels}",
            )

    if progress_callback:
        progress_callback(0.8, f"Found {len(result)} line segments")

    return result
