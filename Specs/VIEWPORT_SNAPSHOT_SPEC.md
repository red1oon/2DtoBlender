# Viewport Snapshot Tool - Project Specification

## Overview

Render federation database geometry to PNG **without launching Blender**. This enables autonomous audit cycles where Claude can "see" the model without human intervention.

## Goal

Replace this workflow:
```
Human → Launch Blender → Load .blend → Take screenshot → Show Claude
```

With this:
```
Script → Read DB → Reconstruct meshes → Render PNG → Claude reads image
```

## Technical Requirements

### Input
- SQLite database with instanced geometry pattern
- Tables: `elements_meta`, `element_geometry`, `base_geometries`

### Output
- PNG image file (default 1920x1080)
- Saved to `Screenshots/` with timestamp

### Camera Controls
- Angle presets: `iso`, `top`, `front`, `side`, `se`
- Distance multiplier (zoom)
- Resolution setting

## Current Issue

The `base_geometries` table stores vertices/faces as **binary BLOBs**, not JSON strings:

```sql
CREATE TABLE base_geometries (
    geometry_hash TEXT PRIMARY KEY,
    vertices BLOB NOT NULL,  -- Binary data
    faces BLOB NOT NULL,     -- Binary data
    ...
)
```

The generator (`generate_arc_str_database.py`) uses `json.dumps().encode()` to create these BLOBs:

```python
vertices_blob = json.dumps(vertices).encode('utf-8')
```

But when reading back, `json.loads(blob)` fails because SQLite returns raw bytes.

## Solution Options

### Option A: Fix the Reader (Recommended)
Decode the BLOB properly:
```python
vertices = json.loads(vertices_blob.decode('utf-8'))
faces = json.loads(faces_blob.decode('utf-8'))
```

### Option B: Change Storage Format
Store as TEXT instead of BLOB:
```python
# In generator:
cursor.execute("INSERT INTO base_geometries ... VALUES (?, ?, ?)",
               (hash, json.dumps(vertices), json.dumps(faces)))
```

## Implementation Tasks

1. **Fix BLOB decoding** in `audit_viewport_truth.py`
   - Add `.decode('utf-8')` before `json.loads()`
   - Handle edge cases (empty geometry, malformed data)

2. **Test mesh reconstruction**
   - Verify vertices/faces load correctly
   - Check mesh validity with trimesh

3. **Implement rendering**
   - Use trimesh's `scene.save_image()` or fallback to PIL projection
   - May need `pyrender` or `pyglet` for proper 3D rendering

4. **Add camera controls**
   - Implement `get_camera_transform()` for each angle preset
   - Test different views match expected output

5. **Color by IFC class**
   - Apply consistent colors matching Blender materials
   - Handle transparency for windows/glass

## Dependencies

```bash
pip install trimesh pillow numpy scipy
# Optional for better rendering:
pip install pyrender pyglet
```

## Usage

```bash
# Basic usage
./venv/bin/python Scripts/audit_viewport_truth.py DatabaseFiles/Terminal1_ARC_STR.db

# With options
./venv/bin/python Scripts/audit_viewport_truth.py DatabaseFiles/Terminal1_ARC_STR.db \
    --angle iso \
    --distance 2.0 \
    --resolution 1920x1080 \
    --output Screenshots/my_snapshot.png
```

## Expected Output

```
Loading database: DatabaseFiles/Terminal1_ARC_STR.db
Loaded 795 meshes from database
Rendering with angle=iso, distance=2.0

Snapshot saved: Screenshots/Terminal1_ARC_STR_20251119_183000.png
```

## Success Criteria

1. Renders 795 elements from Terminal1_ARC_STR.db
2. Output visually similar to Blender viewport (same geometry, colors)
3. No Blender process launched
4. Execution time < 10 seconds
5. Works on headless server (no display required)

## Files

- `Scripts/audit_viewport_truth.py` - Main script (partially implemented)
- `Scripts/audit_database.py` - Reference for DB schema queries
- `DatabaseFiles/Terminal1_ARC_STR.db` - Test database

## Why This Matters

Enables **fully autonomous audit cycles**:
1. Regenerate database
2. Run text audit (metrics, checklist)
3. Run viewport snapshot (visual)
4. Claude analyzes both
5. Fixes issues, repeats

No human needs to launch Blender - the entire DXF→DB→Audit→Fix cycle runs automatically.

## Reference

- Existing code: `/home/red1/Documents/bonsai/2Dto3D/Scripts/audit_viewport_truth.py`
- Working audit: `/home/red1/Documents/bonsai/2Dto3D/Scripts/audit_database.py`
- Generator: `/home/red1/Documents/bonsai/2Dto3D/Scripts/generate_arc_str_database.py`
- Venv with deps: `/home/red1/Documents/bonsai/2Dto3D/venv/`
