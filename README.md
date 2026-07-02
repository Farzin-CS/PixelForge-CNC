<p align="center">
  <h1 align="center">PixelForge CNC</h1>
  <p align="center">
    <strong>Professional Image to G-code Converter with Real-Time Engraving Simulation</strong>
  </p>
  <p align="center">
    Convert ANY image into CNC-ready G-code with photorealistic variable-depth shading.
    See exactly how your engraving will look before touching the machine.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenCV-4.8%2B-green?logo=opencv" />
  <img src="https://img.shields.io/badge/AI-rembg-purple" />
  <img src="https://img.shields.io/badge/Output-TAP%20%7C%20G--code-orange" />
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-blueviolet" />
  <img src="https://img.shields.io/badge/Language-EN%20%7C%20FA-brightgreen" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

---

## Why PixelForge CNC?

Most image-to-gcode tools produce **flat cartoon outlines** with no depth or shading. PixelForge CNC uses **variable-depth raster engraving** with a **real-time metallic simulation** so you see the final result before running the machine. 2D modes use the same raster engine at coarse settings for a blocky pixel-art look.

| Traditional Tools | PixelForge CNC |
|---|---|
| Edge detection only | Variable-depth raster engraving |
| Flat outline preview | Realistic metallic surface simulation |
| Manual parameter tuning | Material presets with one-click config |
| Single language | English and Persian (Farsi) |
| Basic raster path | Zig-zag, climb, and conventional strategies |
| Vertical plunge only | Configurable Z-axis ramping |

---

## Features

### Core

- **4 Processing Modes** -- Portrait (face crop), Full image, Center crop, Fit to dimensions
- **Variable-depth G-code** -- Pixel brightness maps directly to engraving depth
- **TAP format output** -- Compatible with Mach3, LinuxCNC, GRBL, Fanuc, Siemens
- **AI background removal** -- GPU-accelerated (CUDA / CoreML / DirectML auto-detected) — background stays uncut
- **Detail Level slider** -- Controls coarseness from binary silhouette to smooth 8-level raster
- **2 Engraving Modes** -- 3D variable-depth raster + 2D coarse raster (same engine, low detail)
- **Rapid traversal optimization** -- G0 rapid moves over zero-depth areas
- **Z-axis ramping** -- Angled tool entry to prevent bit breakage

### Carving Strategies

- **Zig-Zag (Boustrophedon)** -- Alternates cutting direction each row
- **One-Way Climb** -- Always cuts in the same direction (climb milling)
- **One-Way Conventional** -- Always cuts in the same direction (conventional milling)

### Simulation & Preview

- **Real-time engraving simulation** -- Metallic surface rendering with 3-point lighting
- **3 preview tabs** -- Original, Engraving Preview, Depth Map
- **Zoom & pan** -- Scroll wheel zoom, drag to pan when zoomed in
- **Material-specific appearance** -- Each material renders with correct color and reflectivity

### Material System

- **8 material presets** -- Gold, Silver, Copper, Brass, Aluminum, Steel, Acrylic, Wood
- **Auto-configured CNC parameters** -- Spindle speed, feed rate, depth, spacing, plunge rate
- **Recommended tool bits** -- Suggested cutting tool for each material
- **Full override control** -- Manually adjust any parameter

### Smart Analysis

- **Image complexity analysis** -- Edge density, contrast, detail level, portrait detection
- **Suggestions, not overrides** -- Smart analysis recommends values; you choose to apply them
- **One-click "Apply Suggestions"** -- Adopt recommended spacing, depth, gamma, and mode
- **Transparency** -- Success dialog shows exactly which settings were used

### Internationalization

- **Bilingual interface** -- English and Persian (Farsi)
- **One-click language toggle** -- Switch instantly, all labels and messages translated

### Professional

- **Dark-themed GUI** -- Modern CustomTkinter interface for extended use
- **Config save/load** -- Save presets for different projects and materials
- **Keyboard shortcuts** -- Ctrl+O, Ctrl+P, Ctrl+S
- **Cancel button** -- Abort processing at any time during conversion
- **Non-blocking processing** -- Background threading keeps UI responsive during conversion

---

## Quick Start

### Installation

```bash
git clone https://github.com/Farzin-CS/PixelForge-CNC.git
cd PixelForge-CNC
pip install -r requirements.txt
```

### Launch

**Option 1 -- Double-click launcher (Windows)**

Double-click `launch.bat` in the project folder.

**Option 2 -- Command line**

```bash
python run.py
```

**Option 3 -- Build standalone .exe**

```bash
pip install pyinstaller
python build_exe.py
```

The executable will be created at `dist/PixelForge CNC.exe`. Share this single file with anyone -- no Python installation needed.

> First run downloads the AI background removal model (~200 MB). Only happens once.\
> GPU acceleration is auto-detected (CUDA > CoreML > DirectML > CPU). No manual config needed.

---

## Material Presets

| Material | RPM | Feed (mm/min) | Max Depth (mm) | Spacing (mm) | Recommended Bit |
|----------|-----|---------------|----------------|--------------|-----------------|
| **Gold** | 10,000 | 200 | -0.08 | 0.05 | V-bit 30 deg |
| **Silver** | 12,000 | 250 | -0.10 | 0.06 | V-bit 30 deg |
| **Copper** | 9,000 | 220 | -0.10 | 0.06 | V-bit 45 deg |
| **Brass** | 10,000 | 230 | -0.10 | 0.06 | V-bit 30 deg |
| **Aluminum** | 15,000 | 400 | -0.15 | 0.08 | V-bit 60 deg |
| **Steel** | 8,000 | 150 | -0.06 | 0.05 | Carbide V-bit 30 deg |
| **Acrylic** | 18,000 | 500 | -0.20 | 0.10 | Diamond drag bit |
| **Wood** | 12,000 | 600 | -0.30 | 0.12 | V-bit 45 deg or laser |

---

## GUI Walkthrough

### 1. Load an Image

Click **Browse** or press `Ctrl+O`. Supports JPG, PNG, BMP, TIFF, WebP.

### 2. Select Processing Mode

| Mode | Use Case |
|------|----------|
| Portrait | Face photos -- auto-detects and crops the face |
| Full Image | Logos, signatures, text -- uses entire image |
| Center Crop | Patterns, art -- square crop from center |
| Fit to Size | Landscapes -- fits to output dimensions |

### 3. Choose Engraving Mode

Select **Raster 3D** for variable-depth engraving or **Contour/Line Art** for 2D coarse raster. The 2D mode uses the same raster engine with low detail for a flat blocky look.

### 4. Choose Material

Select from the material dropdown. CNC parameters auto-populate. Override any value if needed.

### 5. Configure Dimensions

Set the physical engraving area (width x height in mm) and line spacing.

### 6. Set Detail Level

The **Detail Level** slider (0.0–1.0) controls coarseness:
- **0.0** — Binary (2-level), very coarse spacing, pixelated → fast, blocky result
- **0.5** — 4 levels, moderate coarseness
- **1.0** — Smooth 8-level raster, finest detail

### 7. Select Carving Strategy (3D only)

Choose between Zig-Zag (boustrophedon), One-Way Climb, or One-Way Conventional milling paths.

### 8. Run Conversion

Click **RUN CONVERSION** or press `Ctrl+P`. Three preview tabs update:

- **Original** -- your source image
- **Engraving Preview** -- realistic simulation of the engraved result
- **Depth Map** -- the processed grayscale used for G-code generation

Use the zoom controls (+/-/Fit) and scroll wheel to inspect details. Drag to pan when zoomed in.

### 7. Save

Save the G-code file (.tap or .nc) and send it to your CNC machine.

---

## Project Structure

```
pixelforge-cnc/
    run.py                          # Entry point (run this)
    pixelforge/
        engine/
            gcode_generator.py      # G-code generation with toolpath optimization
            image_processor.py      # Image loading, enhancement, background removal
            material_presets.py     # Material definitions and config management
            simulation.py           # Engraving preview simulation
            types.py                # Shared dataclasses, enums, typed config
        ui/
            app.py                  # Main CustomTkinter application (MVC: View)
            controllers.py          # MVC Controller - bridges UI events to engine
            dialogs.py              # Custom error/success modal dialogs
            theme.py                # Color palette and CustomTkinter theme
            translations.py         # English/Persian translation strings
            widgets.py              # Reusable custom widgets (preview, entries)
            workers.py              # Background worker threads with progress
    gcode_config.json               # Default configuration
    requirements.txt                # Python dependencies
    pixelforge.ico                  # Application icon
    launch.bat                      # Windows launcher (double-click to run)
    build_exe.py                    # Build standalone .exe (optional)
    README.md                       # This file
```

---

## How It Works

```
Input Image
    |
    v
Preprocessing (portrait / full / center / fit)
    |
    v
AI Background Removal (GPU-accelerated, optional)
    |
    v
4-Stage Enhancement (CLAHE, Bilateral, Unsharp, Gamma)
    |
    v
+---> [3D Mode] Resize & generate variable-depth G-code
|         |
|         +---> Engraving Simulation (metallic preview)
|         +---> G-code with Z ramping, strategies, rapids
|
+---> [2D Mode] Posterize + downscale + coarse spacing
          |
          +---> 2D contour preview (bone colormap)
          +---> Raster G-code (same 3D engine, coarse settings)
                  |
                  v
            .tap file for CNC machine
```

---

## Engraving Simulation

The simulation engine renders a realistic preview using:

- **Surface normals** computed from depth gradients (Sobel operators, multi-scale)
- **Lambertian diffuse lighting** for base illumination
- **Blinn-Phong specular highlights** for metallic reflections
- **Schlick Fresnel approximation** for edge reflectivity
- **Screen-space ambient occlusion** for depth perception
- **Material-specific** base color, roughness, and reflectivity
- **Micro-surface brushing pattern** simulating directional machining
- **Scan line texture** matching the actual line spacing

No external 3D engines required. Pure numpy + OpenCV.

---

## Compatible CNC Controllers

| Controller | Compatible |
|-----------|------------|
| Mach3 / Mach4 | Yes |
| LinuxCNC | Yes |
| GRBL | Yes |
| Fanuc | Yes (minor header edit) |
| Siemens 840D | Yes (minor header edit) |

---

## Pre-Run Checklist

- [ ] Open the engraving preview -- verify clarity and contrast
- [ ] Test on scrap material first
- [ ] Start with shallow depth (-0.05mm) and increase gradually
- [ ] Verify safe_z clears clamps and fixtures
- [ ] Set machine zero (X=0, Y=0) at top-left corner
- [ ] Match width/height to actual material dimensions

---

## License

MIT -- free to use, modify, and distribute.
