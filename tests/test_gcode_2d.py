from pixelforge.engine.types import ContourPath, GCodeConfig, EngravingMode
from pixelforge.engine.gcode_2d import generate_gcode_2d


def test_single_closed_contour():
    cfg = GCodeConfig(
        width_mm=10.0, height_mm=10.0, max_depth=-0.1,
        feed_rate=200.0, plunge_rate=100.0, safe_z=2.0,
    )
    contours = [
        ContourPath(points=[(0, 0), (5, 0), (5, 5), (0, 5)], is_closed=True, depth_mm=-0.1),
    ]
    gcode, stats = generate_gcode_2d(contours, cfg)
    assert len(gcode) > 0
    assert stats.contour_count == 1
    assert stats.cutting_moves > 0
    assert "G1" in gcode
    assert "G0" in gcode
    assert "T1 M6" in gcode


def test_no_contours():
    cfg = GCodeConfig()
    gcode, stats = generate_gcode_2d([], cfg)
    assert stats.contour_count == 0
    assert len(gcode) > 0


def test_multiple_passes():
    cfg = GCodeConfig(contour_passes=3, max_depth=-0.3)
    contours = [
        ContourPath(points=[(0, 0), (5, 0), (5, 5)], is_closed=False, depth_mm=-0.3),
    ]
    gcode, stats = generate_gcode_2d(contours, cfg)
    assert stats.contour_count == 1
    assert stats.cutting_moves > 0


def test_multiple_contours():
    cfg = GCodeConfig()
    contours = [
        ContourPath(points=[(0, 0), (2, 0), (2, 2)], is_closed=True, depth_mm=-0.1),
        ContourPath(points=[(5, 5), (7, 5), (7, 7)], is_closed=True, depth_mm=-0.1),
    ]
    gcode, stats = generate_gcode_2d(contours, cfg)
    assert stats.contour_count == 2
    assert stats.cutting_moves >= 6


def test_open_contour():
    cfg = GCodeConfig()
    contours = [
        ContourPath(points=[(0, 0), (10, 0), (10, 10)], is_closed=False, depth_mm=-0.1),
    ]
    gcode, stats = generate_gcode_2d(contours, cfg)
    assert stats.cutting_moves >= 2


def test_output_contains_header():
    cfg = GCodeConfig(material="wood", feed_rate=600)
    contours = [
        ContourPath(points=[(1, 1), (2, 2)], is_closed=False, depth_mm=-0.2),
    ]
    gcode, _ = generate_gcode_2d(contours, cfg)
    assert "PixelForge CNC" in gcode
    assert "wood" in gcode
    assert "600" in gcode


def test_stats_cutting_distance():
    cfg = GCodeConfig()
    contours = [
        ContourPath(points=[(0, 0), (10, 0)], is_closed=False, depth_mm=-0.1),
    ]
    _, stats = generate_gcode_2d(contours, cfg)
    assert stats.cutting_distance_mm > 0
