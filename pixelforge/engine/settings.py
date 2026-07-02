"""
settings.py
===========
PixelForge CNC -- Application settings persistence.

Manages saving and loading of UI state and user configurations
to/from a settings.json file. Ensures the app remembers all
user preferences across sessions.

Preserves the "no automatic file saving" design principle:
settings are only written when the user explicitly saves, or
on clean application exit.
"""

from __future__ import annotations

import json
import os
from typing import Any
from pathlib import Path


# Default settings structure with all supported keys
DEFAULT_SETTINGS: dict[str, Any] = {
    # Window geometry
    "window_width": 1200,
    "window_height": 780,
    "window_x": None,
    "window_y": None,

    # Language
    "language": "en",

    # Processing mode
    "mode": "full",

    # Material
    "material": "gold",

    # Output dimensions
    "width_mm": 20.0,
    "height_mm": 25.0,
    "line_spacing_mm": 0.05,

    # CNC parameters
    "max_depth": -0.08,
    "safe_z": 2.0,
    "feed_rate": 200.0,
    "spindle_rpm": 10000,
    "plunge_rate": 100.0,
    "ramp_angle": 2.0,

    # Carving strategy
    "carving_strategy": "zigzag",

    # Image processing
    "remove_background": False,
    "contrast_enhance": True,
    "sharpen_edges": True,
    "bilateral_filter": True,
    "invert": False,
    "gamma": 0.80,

    # Smart settings
    "smart_settings": True,

    # Preview
    "preview_tab": "original",

    # Depth map method
    "depth_method": "opencv",

    # Simulation mode (line or relief)
    "simulation_mode": "relief",

    # Scroll speed multiplier
    "scroll_speed_multiplier": 3,

    # Detail level: 0.0 = low detail (simpler), 1.0 = high detail (more sensitive)
    "detail_level": 0.5,

    # Last opened directory
    "last_directory": "",
}


def get_settings_path() -> Path:
    """Get the path to the settings.json file.

    Located in the same directory as the application entry point.

    Returns:
        Path to settings.json.
    """
    return Path(__file__).parent.parent.parent / "settings.json"


def load_settings(path: str | Path | None = None) -> dict[str, Any]:
    """Load settings from disk, falling back to defaults.

    If the file doesn't exist or is corrupt, returns default settings.
    Unknown keys in the file are preserved (forward compatibility).

    Args:
        path: Optional path to settings file. Uses default if None.

    Returns:
        Merged settings dictionary.
    """
    settings = DEFAULT_SETTINGS.copy()
    filepath = Path(path) if path else get_settings_path()

    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                settings.update(loaded)
        except (json.JSONDecodeError, OSError):
            pass  # Corrupt file, use defaults

    return settings


def save_settings(settings: dict[str, Any], path: str | Path | None = None) -> bool:
    """Save settings to disk.

    Only called when the user explicitly saves or on clean app exit.
    Preserves unknown keys for forward compatibility.

    Args:
        settings: Settings dictionary to save.
        path: Optional path to settings file. Uses default if None.

    Returns:
        True if saved successfully, False on error.
    """
    filepath = Path(path) if path else get_settings_path()

    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def settings_to_config(settings: dict[str, Any]) -> dict[str, Any]:
    """Convert app settings dict to engine config dict.

    Maps UI setting keys to the config keys expected by the engine.

    Args:
        settings: Application settings dictionary.

    Returns:
        Config dictionary compatible with the G-code engine.
    """
    return {
        "mode": settings.get("mode", "full"),
        "material": settings.get("material", "gold"),
        "width_mm": settings.get("width_mm", 20.0),
        "height_mm": settings.get("height_mm", 25.0),
        "line_spacing_mm": settings.get("line_spacing_mm", 0.05),
        "max_depth": settings.get("max_depth", -0.08),
        "safe_z": settings.get("safe_z", 2.0),
        "feed_rate": settings.get("feed_rate", 200.0),
        "spindle_rpm": settings.get("spindle_rpm", 10000),
        "plunge_rate": settings.get("plunge_rate", 100.0),
        "ramp_angle": settings.get("ramp_angle", 2.0),
        "carving_strategy": settings.get("carving_strategy", "zigzag"),
        "remove_background": settings.get("remove_background", False),
        "contrast_enhance": settings.get("contrast_enhance", True),
        "sharpen_edges": settings.get("sharpen_edges", True),
        "bilateral_filter": settings.get("bilateral_filter", True),
        "invert": settings.get("invert", False),
        "gamma": settings.get("gamma", 0.80),
        "smart_settings": settings.get("smart_settings", True),
        "detail_level": settings.get("detail_level", 0.5),
        "skip_threshold": 0.005,
        "start_z": 0.3,
    }


def config_to_settings(config: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    """Merge engine config back into app settings.

    Args:
        config: Engine config dictionary.
        settings: Current app settings to update.

    Returns:
        Updated settings dictionary.
    """
    for key in ["mode", "material", "width_mm", "height_mm", "line_spacing_mm",
                "max_depth", "safe_z", "feed_rate", "spindle_rpm", "plunge_rate",
                "ramp_angle", "carving_strategy", "remove_background",
                "contrast_enhance", "sharpen_edges", "bilateral_filter",
                 "invert", "gamma", "smart_settings", "detail_level"]:
        if key in config:
            settings[key] = config[key]
    return settings
