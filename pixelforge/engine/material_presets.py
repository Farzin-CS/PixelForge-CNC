"""
material_presets.py
==================
PixelForge CNC -- Material presets and configuration management.

Provides professional CNC parameters per material type, configuration
loading/saving, and conversion to the typed GCodeConfig dataclass.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np

from pixelforge.engine.types import CarvingStrategy, GCodeConfig, EngravingMode


# ============================================================
# MATERIAL PRESETS -- Professional CNC parameters per material
# ============================================================
MATERIAL_PRESETS: dict[str, dict[str, Any]] = {
    "gold": {
        "spindle_rpm": 10000,
        "feed_rate": 200.0,
        "plunge_rate": 100.0,
        "max_depth": -0.08,
        "safe_z": 2.0,
        "line_spacing_mm": 0.05,
        "recommended_bit": "V-bit 30 deg",
        "base_color": np.array([30, 180, 240], dtype=np.float64),
        "specular_strength": 0.7,
        "roughness": 0.25,
        "ambient": 0.15,
        "fresnel": 0.6,
    },
    "silver": {
        "spindle_rpm": 12000,
        "feed_rate": 250.0,
        "plunge_rate": 120.0,
        "max_depth": -0.10,
        "safe_z": 2.0,
        "line_spacing_mm": 0.06,
        "recommended_bit": "V-bit 30 deg",
        "base_color": np.array([190, 195, 205], dtype=np.float64),
        "specular_strength": 0.8,
        "roughness": 0.2,
        "ambient": 0.12,
        "fresnel": 0.7,
    },
    "copper": {
        "spindle_rpm": 9000,
        "feed_rate": 220.0,
        "plunge_rate": 110.0,
        "max_depth": -0.10,
        "safe_z": 2.0,
        "line_spacing_mm": 0.06,
        "recommended_bit": "V-bit 45 deg",
        "base_color": np.array([40, 120, 210], dtype=np.float64),
        "specular_strength": 0.55,
        "roughness": 0.3,
        "ambient": 0.18,
        "fresnel": 0.5,
    },
    "brass": {
        "spindle_rpm": 10000,
        "feed_rate": 230.0,
        "plunge_rate": 110.0,
        "max_depth": -0.10,
        "safe_z": 2.0,
        "line_spacing_mm": 0.06,
        "recommended_bit": "V-bit 30 deg",
        "base_color": np.array([35, 170, 235], dtype=np.float64),
        "specular_strength": 0.6,
        "roughness": 0.28,
        "ambient": 0.16,
        "fresnel": 0.55,
    },
    "aluminum": {
        "spindle_rpm": 15000,
        "feed_rate": 400.0,
        "plunge_rate": 200.0,
        "max_depth": -0.15,
        "safe_z": 3.0,
        "line_spacing_mm": 0.08,
        "recommended_bit": "V-bit 60 deg",
        "base_color": np.array([200, 205, 215], dtype=np.float64),
        "specular_strength": 0.75,
        "roughness": 0.18,
        "ambient": 0.1,
        "fresnel": 0.65,
    },
    "steel": {
        "spindle_rpm": 8000,
        "feed_rate": 150.0,
        "plunge_rate": 80.0,
        "max_depth": -0.06,
        "safe_z": 3.0,
        "line_spacing_mm": 0.05,
        "recommended_bit": "Carbide V-bit 30 deg",
        "base_color": np.array([140, 148, 158], dtype=np.float64),
        "specular_strength": 0.45,
        "roughness": 0.4,
        "ambient": 0.2,
        "fresnel": 0.4,
    },
    "acrylic": {
        "spindle_rpm": 18000,
        "feed_rate": 500.0,
        "plunge_rate": 250.0,
        "max_depth": -0.20,
        "safe_z": 3.0,
        "line_spacing_mm": 0.10,
        "recommended_bit": "Diamond drag bit",
        "base_color": np.array([220, 225, 235], dtype=np.float64),
        "specular_strength": 0.35,
        "roughness": 0.12,
        "ambient": 0.08,
        "fresnel": 0.8,
    },
    "wood": {
        "spindle_rpm": 12000,
        "feed_rate": 600.0,
        "plunge_rate": 300.0,
        "max_depth": -0.30,
        "safe_z": 3.0,
        "line_spacing_mm": 0.12,
        "recommended_bit": "V-bit 45 deg or laser",
        "base_color": np.array([50, 115, 175], dtype=np.float64),
        "specular_strength": 0.2,
        "roughness": 0.55,
        "ambient": 0.25,
        "fresnel": 0.3,
    },
}

DEFAULT_MATERIAL: str = "gold"


def apply_material_preset(material_name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Apply a material preset's CNC parameters to a config dict.

    Args:
        material_name: Key into MATERIAL_PRESETS.
        cfg: Mutable config dict to update in-place.

    Returns:
        The updated config dict.
    """
    preset = MATERIAL_PRESETS.get(material_name, MATERIAL_PRESETS[DEFAULT_MATERIAL])
    cfg["material"] = material_name
    cfg["spindle_rpm"] = preset["spindle_rpm"]
    cfg["feed_rate"] = preset["feed_rate"]
    cfg["plunge_rate"] = preset["plunge_rate"]
    cfg["max_depth"] = preset["max_depth"]
    cfg["safe_z"] = preset["safe_z"]
    cfg["line_spacing_mm"] = preset["line_spacing_mm"]
    return cfg


def load_config(config_path: str = "gcode_config.json") -> dict[str, Any]:
    """Load configuration from a JSON file, falling back to defaults.

    Args:
        config_path: Path to the JSON config file.

    Returns:
        Merged configuration dictionary.
    """
    cfg: dict[str, Any] = {
        "mode": "portrait",
        "material": DEFAULT_MATERIAL,
        "width_mm": 20.0,
        "height_mm": 25.0,
        "safe_z": 2.0,
        "start_z": 0.3,
        "max_depth": -0.12,
        "feed_rate": 300.0,
        "plunge_rate": 150.0,
        "spindle_rpm": 10000,
        "line_spacing_mm": 0.08,
        "remove_background": True,
        "contrast_enhance": True,
        "bilateral_filter": True,
        "sharpen_edges": True,
        "gamma": 0.80,
        "invert": False,
        "skip_threshold": 0.005,
        "light_angle": 45.0,
        "smart_settings": True,
        "carving_strategy": "zigzag",
        "ramp_angle": 2.0,
    }
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def save_config(cfg: dict[str, Any], config_path: str = "gcode_config.json") -> None:
    """Save configuration to a JSON file.

    Args:
        cfg: Configuration dictionary to serialize.
        config_path: Destination file path.
    """
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)


def to_gcode_config(cfg: dict[str, Any]) -> GCodeConfig:
    """Convert a mutable config dict to an immutable GCodeConfig dataclass.

    Args:
        cfg: Configuration dictionary (e.g. from UI or JSON).

    Returns:
        Frozen GCodeConfig instance for use by the G-code generator.
    """
    strategy_str = cfg.get("carving_strategy", "zigzag")
    strategy_map = {
        "zigzag": CarvingStrategy.ZIGZAG,
        "climb": CarvingStrategy.ONE_WAY_CLIMB,
        "conventional": CarvingStrategy.ONE_WAY_CONVENTIONAL,
    }
    strategy = strategy_map.get(strategy_str, CarvingStrategy.ZIGZAG)

    engraving_mode_str = cfg.get("engraving_mode", "raster_3d")
    engraving_mode_map = {
        "raster_3d": EngravingMode.RASTER_3D,
        "contour_2d": EngravingMode.CONTOUR_2D,
        "line_art": EngravingMode.LINE_ART,
    }
    engraving_mode = engraving_mode_map.get(engraving_mode_str, EngravingMode.RASTER_3D)

    return GCodeConfig(
        width_mm=float(cfg.get("width_mm", 20.0)),
        height_mm=float(cfg.get("height_mm", 25.0)),
        max_depth=float(cfg.get("max_depth", -0.12)),
        safe_z=float(cfg.get("safe_z", 2.0)),
        start_z=float(cfg.get("start_z", 0.3)),
        feed_rate=float(cfg.get("feed_rate", 300.0)),
        plunge_rate=float(cfg.get("plunge_rate", 150.0)),
        spindle_rpm=int(cfg.get("spindle_rpm", 10000)),
        line_spacing_mm=float(cfg.get("line_spacing_mm", 0.08)),
        skip_threshold=float(cfg.get("skip_threshold", 0.005)),
        material=cfg.get("material", DEFAULT_MATERIAL),
        carving_strategy=strategy,
        ramp_angle=float(cfg.get("ramp_angle", 2.0)),
        ramp_height=float(cfg.get("start_z", 0.3)),
        rapid_feed=float(cfg.get("rapid_feed", 5000.0)),
        engraving_mode=engraving_mode,
        contour_simplify_epsilon=float(cfg.get("contour_simplify_epsilon", 0.5)),
        min_contour_area=float(cfg.get("min_contour_area", 1.0)),
        line_width_mm=float(cfg.get("line_width_mm", 0.2)),
        contour_passes=int(cfg.get("contour_passes", 1)),
        lead_in_out=bool(cfg.get("lead_in_out", True)),
    )
