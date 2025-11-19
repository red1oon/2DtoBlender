# Viewport Snapshot Tool

Pure Python 3D renderer for federation database geometry. Renders to PNG **without launching Blender** - uses only numpy + PIL.

## Features

- **No external dependencies**: Pure software rasterization (numpy + PIL only)
- **No display required**: Works headless on servers
- **Discipline filtering**: Show/hide disciplines like Bonsai Outliner
- **Color by discipline**: Visual differentiation of ARC/STR/MEP systems
- **Directional lighting**: Shading for depth perception
- **Camera presets**: iso, top, front, side, se
- **Hi-res support**: Up to 8K (7680x4320) and beyond
- **Backface culling**: Only renders front-facing surfaces
- **Z-buffering**: Proper depth ordering - obscured elements automatically hidden
- **Floor filtering**: Render specific floor levels for interior inspection
- **Bounding box**: Zoom into specific XY regions for close-up views

## Installation

```bash
cd /home/red1/Documents/bonsai/2Dto3D/ViewportSnapshot
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
./venv/bin/python viewport_snapshot.py <database.db>
```

### Common Examples

```bash
# Isometric view (default)
./venv/bin/python viewport_snapshot.py DatabaseFiles/Terminal1_ARC_STR.db

# Top-down view
./venv/bin/python viewport_snapshot.py DatabaseFiles/Terminal1_ARC_STR.db --angle top

# Higher resolution
./venv/bin/python viewport_snapshot.py DatabaseFiles/Terminal1_ARC_STR.db --resolution 2560x1440

# Surface elements only (walls, slabs, roofs, windows, doors)
./venv/bin/python viewport_snapshot.py DatabaseFiles/Terminal1_ARC_STR.db --surface-only

# Show only specific disciplines (like Bonsai Outliner)
./venv/bin/python viewport_snapshot.py enhanced_federation.db --discipline ARC
./venv/bin/python viewport_snapshot.py enhanced_federation.db --discipline ARC,STR

# Exclude disciplines (show everything except ARC and STR)
./venv/bin/python viewport_snapshot.py enhanced_federation.db --exclude ARC,STR

# Combined filters
./venv/bin/python viewport_snapshot.py enhanced_federation.db \
    --surface-only \
    --discipline ARC \
    --resolution 2560x1440 \
    --angle iso
```

## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--angle` | `-a` | Camera preset: iso, top, front, side, se | iso |
| `--distance` | `-d` | Camera distance multiplier (zoom) | 1.0 |
| `--resolution` | `-r` | Output resolution WxH | 1920x1080 |
| `--output` | `-o` | Output file path | Auto-generated |
| `--surface-only` | `-s` | Only surface elements | False |
| `--discipline` | `-D` | Disciplines to show (comma-separated) | All |
| `--exclude` | `-X` | Disciplines to hide (comma-separated) | None |
| `--color-by` | `-c` | Color by 'class' or 'discipline' | class |
| `--floor` | `-f` | Filter by floor Z level (meters) | None |
| `--floor-tolerance` | | Z tolerance for floor filtering | 2.0 |
| `--bbox` | `-b` | Bounding box: minX,minY,maxX,maxY | None |

## Camera Angles

- **iso**: Isometric view (default) - good overview
- **top**: Top-down plan view
- **front**: Front elevation
- **side**: Side elevation
- **se**: South-east isometric

## Output

Screenshots are saved to `Screenshots/` directory with timestamp:
```
Screenshots/Terminal1_ARC_STR_20251119_185349.png
```

## Use Cases

### Autonomous Audit Cycles

```bash
# 1. Regenerate database from DXF
python Scripts/generate_database.py

# 2. Render snapshot for visual inspection
./venv/bin/python viewport_snapshot.py output.db --surface-only

# 3. Claude reads the PNG and analyzes geometry
# (via Read tool on the PNG file)
```

### Discipline Review

```bash
# Review only architectural elements
./venv/bin/python viewport_snapshot.py model.db --discipline ARC --surface-only

# Review MEP systems (hide ARC/STR)
./venv/bin/python viewport_snapshot.py model.db --exclude ARC,STR

# Review structural only
./venv/bin/python viewport_snapshot.py model.db --discipline STR
```

### Floor and Region Filtering

For large models (230m+ scenes), filter by floor and region to inspect small elements:

```bash
# Ground floor only (Z=0m, default tolerance 2m)
./venv/bin/python viewport_snapshot.py model.db --floor 0 --angle top

# Level 1 (Z=4m) with tighter tolerance
./venv/bin/python viewport_snapshot.py model.db --floor 4 --floor-tolerance 1.5

# Specific XY region (20x30m area)
./venv/bin/python viewport_snapshot.py model.db --bbox="-10,-20,10,10"

# Combined: Ground floor, specific region, discipline colors
./venv/bin/python viewport_snapshot.py model.db \
    --floor 0 \
    --bbox="-10,-20,10,10" \
    --angle top \
    --color-by discipline
```

**Note**: Use `=` syntax for bbox with negative values (e.g., `--bbox="-10,-20,10,10"`).

## Performance

Vectorized numpy rasterization enables fast rendering even at high resolutions:

| Elements | Resolution | Time |
|----------|------------|------|
| 6 | 1080p | ~instant |
| 647 | 4K | ~0.8 seconds |
| 647 | 8K | ~3.5 seconds |
| 35,000 | 1080p | ~2-3 minutes |

For large models, use `--surface-only` and/or discipline filters to reduce mesh count.

**Note**: Despite long render times for large models, the tool maintains full surface detail with proper occlusion - obscured elements behind visible surfaces are automatically filtered out via z-buffering.

## Requirements

- Python 3.8+
- numpy
- pillow (PIL)

## Technical Notes

- Pure software rasterization - no GPU/OpenGL
- Vectorized numpy operations for performance
- Barycentric coordinate interpolation for triangle filling
- Z-buffer for depth sorting (obscured elements filtered)
- Backface culling via screen-space winding order
- Directional lighting with ambient + diffuse shading
- Supports both JSON-encoded and raw binary geometry BLOBs

## Discipline Colors

When using `--color-by discipline`:

| Discipline | Color | Description |
|------------|-------|-------------|
| ARC | Light Gray | Architecture |
| STR | Blue | Structural |
| FP | Red | Fire Protection |
| SP | Light Red | Sprinkler |
| ELEC | Yellow | Electrical |
| ACMV | Teal | HVAC |
| REB | Brown | Rebar |
| CW | Light Blue | Curtain Wall |
| LPG | Purple | LPG |
