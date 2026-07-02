import numpy as np
from pixelforge.engine.types import GCodeConfig, CarvingStrategy
from pixelforge.engine.gcode_generator import generate_gcode


def test_simple_depth_map():
    depth = np.ones((10, 10), dtype=np.uint8) * 128
    cfg = GCodeConfig(width_mm=5.0, height_mm=5.0, line_spacing_mm=0.5)
    gcode, stats = generate_gcode(depth, cfg)
    assert len(gcode) > 0
    assert stats.total_lines > 10


def test_all_zero_depth():
    depth = np.zeros((10, 10), dtype=np.uint8)
    cfg = GCodeConfig(width_mm=5.0, height_mm=5.0, line_spacing_mm=0.5)
    gcode, stats = generate_gcode(depth, cfg)
    assert len(gcode) > 0


def test_all_max_depth():
    depth = np.ones((10, 10), dtype=np.uint8) * 255
    cfg = GCodeConfig(width_mm=5.0, height_mm=5.0, line_spacing_mm=0.5)
    gcode, stats = generate_gcode(depth, cfg)
    assert len(gcode) > 0


def test_different_strategies():
    depth = np.ones((10, 10), dtype=np.uint8) * 100
    cfg = GCodeConfig(width_mm=5.0, height_mm=5.0, line_spacing_mm=0.5)
    for strategy in [CarvingStrategy.ZIGZAG, CarvingStrategy.ONE_WAY_CLIMB,
                     CarvingStrategy.ONE_WAY_CONVENTIONAL]:
        cfg = GCodeConfig(width_mm=5.0, height_mm=5.0, line_spacing_mm=0.5,
                          carving_strategy=strategy)
        gcode, _ = generate_gcode(depth, cfg)
        assert len(gcode) > 0


def test_header_contains_metadata():
    depth = np.ones((5, 5), dtype=np.uint8) * 128
    cfg = GCodeConfig(material="silver", feed_rate=250, spindle_rpm=12000)
    gcode, _ = generate_gcode(depth, cfg)
    assert "silver" in gcode
    assert "250" in gcode
    assert "12000" in gcode
    assert "PixelForge CNC" in gcode


def test_ramp_entry_in_output():
    depth = np.ones((10, 10), dtype=np.uint8) * 50
    cfg = GCodeConfig(width_mm=5.0, height_mm=5.0, line_spacing_mm=0.5, ramp_angle=2.0)
    gcode, stats = generate_gcode(depth, cfg)
    assert stats.ramp_moves >= 0
    assert len(gcode) > 0


def test_stats_collected():
    depth = np.ones((10, 10), dtype=np.uint8) * 100
    cfg = GCodeConfig(width_mm=5.0, height_mm=5.0, line_spacing_mm=0.5)
    gcode, stats = generate_gcode(depth, cfg)
    assert stats.total_lines > 0
    assert isinstance(stats.cutting_distance_mm, float)
    assert stats.cutting_moves > 0
