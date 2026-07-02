"""Core engine: G-code generation, image processing, CNC simulation."""

from pixelforge.engine.types import (
    CarvingStrategy,
    CuttingDirection,
    EngravingMode,
    GCodeConfig,
    GCodeStats,
    ToolpathSegment,
    ContourPath,
)
from pixelforge.engine.gcode_generator import generate_gcode
from pixelforge.engine.image_processor import (
    load_image,
    preprocess_image,
    enhance_image,
    resize_to_engraving,
    remove_background,
)
from pixelforge.engine.material_presets import (
    MATERIAL_PRESETS,
    DEFAULT_MATERIAL,
    apply_material_preset,
    load_config,
    save_config,
    to_gcode_config,
)
from pixelforge.engine.simulation import (
    render_engraving_preview,
    analyze_image,
    get_smart_suggestions,
)
from pixelforge.engine.depth_map import (
    generate_depth_map,
    generate_depth_map_opencv,
    generate_depth_map_midas,
)
from pixelforge.engine.material_sim import (
    simulate_material_preview,
    simulate_line_engraving,
    simulate_relief_engraving,
    get_material_texture,
)
from pixelforge.engine.settings import (
    load_settings,
    save_settings,
    settings_to_config,
    config_to_settings,
    DEFAULT_SETTINGS,
)
from pixelforge.engine.contour_tracer import (
    extract_contours,
    convert_to_line_art,
)
from pixelforge.engine.gcode_2d import (
    generate_gcode_2d,
)
