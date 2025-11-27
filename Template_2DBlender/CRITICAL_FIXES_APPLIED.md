# Critical Fixes Applied - Addressing Expert Diagnostic
**Date:** 2025-11-26
**Reference:** documentation/CRITICAL_DIAGNOSTIC_WHERE_IT_BREAKS.md

---

## 🚨 PROBLEM #4 CONFIRMED: OBJECT_TYPE NAMING MISMATCH

**Status:** ❌ **CRITICAL BLOCKER IDENTIFIED**

### What We Generate

```json
{
  "object_type": "door_900x2100_lod300",
  "object_type": "door_750x2100_lod300",
  "object_type": "window_1200x1000_lod300",
  "object_type": "window_1800x1000_lod300",
  "object_type": "window_600x500_lod300"
}
```

### What Library Actually Contains

| Our Generated Type | Library Actual Type | Match? |
|-------------------|---------------------|--------|
| `door_900x2100_lod300` | `door_single` (900×2100) | ❌ NO |
| `door_750x2100_lod300` | `door_louvre_750` (750×2100) | ❌ NO |
| `window_1200x1000_lod300` | `window_aluminum_2panel_1200x1000` | ❌ NO |
| `window_1800x1000_lod300` | `window_aluminum_3panel_1800x1000` | ❌ NO |
| `window_600x500_lod300` | `window_aluminum_tophung_600x500` | ❌ NO |

**Impact:** Stage 8 (Blender import) will fail with "geometry not found" for ALL 14 objects.

---

## SOLUTION OPTIONS

### Option A: Update Generation Logic (Recommended)

Create dimension-to-library mapping:

```python
# In convert_master_to_blender.py
DOOR_LIBRARY_MAPPING = {
    (900, 2100): "door_single",           # Generic single door
    (750, 2100): "door_louvre_750",       # Bathroom door (louvred)
}

WINDOW_LIBRARY_MAPPING = {
    (1800, 1000): "window_aluminum_3panel_1800x1000",  # W1: Kitchen
    (1200, 1000): "window_aluminum_2panel_1200x1000",  # W2: Bedrooms
    (600, 500): "window_aluminum_tophung_600x500",     # W3: Bathrooms
}

def get_library_object_type(element_type, width_mm, height_mm):
    """Get actual library object_type for given dimensions."""
    if element_type == "door":
        return DOOR_LIBRARY_MAPPING.get((width_mm, height_mm), f"door_single")
    elif element_type == "window":
        return WINDOW_LIBRARY_MAPPING.get((width_mm, height_mm), f"window_single")
    else:
        # Fallback to generic naming
        return f"{element_type}_{width_mm}x{height_mm}_lod300"
```

### Option B: Add Missing Types to Library

Add entries to object_catalog:

```sql
-- Create generic lod300 entries that match our naming
INSERT INTO object_catalog (object_type, geometry_hash, ifc_class, width_mm, height_mm, ...)
SELECT
    'door_900x2100_lod300' as object_type,
    geometry_hash,
    'IfcDoor' as ifc_class,
    900 as width_mm,
    2100 as height_mm,
    ...
FROM object_catalog
WHERE object_type = 'door_single' AND width_mm = 900 AND height_mm = 2100
LIMIT 1;
```

### Option C: Create Lookup View

```sql
CREATE VIEW object_library_lookup AS
SELECT
    'door_' || width_mm || 'x' || height_mm || '_lod300' as standard_name,
    object_type as library_name,
    geometry_hash,
    width_mm,
    height_mm
FROM object_catalog
WHERE category IN ('door', 'window');

-- Now queries can use standard_name
```

---

## IMMEDIATE ACTION: Fix convert_master_to_blender.py

```python
#!/usr/bin/env python3
"""
UPDATED: Use actual library object_types instead of generated names
"""

import json
from pathlib import Path

# Library mapping (verified against Ifc_Object_Library.db)
DOOR_TYPES = {
    (900, 2100): "door_single",
    (750, 2100): "door_louvre_750",
}

WINDOW_TYPES = {
    (1800, 1000): "window_aluminum_3panel_1800x1000",
    (1200, 1000): "window_aluminum_2panel_1200x1000",
    (600, 500): "window_aluminum_tophung_600x500",
}

WALL_ROTATION = {
    "NORTH": 0,
    "SOUTH": 0,
    "EAST": 90,
    "WEST": 90
}

def get_library_object_type(door_window_type, width_mm, height_mm):
    """Map dimensions to actual library object_type."""
    if door_window_type == "door":
        library_type = DOOR_TYPES.get((width_mm, height_mm))
        if not library_type:
            print(f"⚠️  WARNING: No library mapping for door {width_mm}x{height_mm}, using 'door_single'")
            return "door_single"
        return library_type
    elif door_window_type == "window":
        library_type = WINDOW_TYPES.get((width_mm, height_mm))
        if not library_type:
            print(f"⚠️  WARNING: No library mapping for window {width_mm}x{height_mm}, using 'window_single'")
            return "window_single"
        return library_type
    else:
        return f"{door_window_type}_{width_mm}x{height_mm}_lod300"

def convert_door(door):
    """Convert door placement to Blender format."""
    width_mm = door.get('width_mm', 900)
    height_mm = door.get('height_mm', 2100)

    return {
        "name": door['element_id'],
        "object_type": get_library_object_type("door", width_mm, height_mm),
        "position": door['position'],
        "orientation": WALL_ROTATION.get(door['wall'], 0),
        "phase": "opening",
        "room": door['room'],
        "wall": door['wall'],
        "dimensions": {
            "width_mm": width_mm,
            "height_mm": height_mm
        }
    }

def convert_window(window):
    """Convert window placement to Blender format."""
    width_mm = window.get('width_mm', 1200)
    height_mm = window.get('height_mm', 1000)

    return {
        "name": window['element_id'],
        "object_type": get_library_object_type("window", width_mm, height_mm),
        "position": window['position'],
        "orientation": WALL_ROTATION.get(window['wall'], 0),
        "phase": "opening",
        "room": window['room'],
        "wall": window['wall'],
        "dimensions": {
            "width_mm": width_mm,
            "height_mm": height_mm
        },
        "sill_height_mm": window.get('sill_height_mm', 900)
    }

def main():
    print("=" * 80)
    print("CONVERT MASTER_TEMPLATE.JSON TO BLENDER FORMAT (UPDATED)")
    print("=" * 80)

    # Load master template
    with open('master_template.json', 'r') as f:
        template = json.load(f)

    doors = template.get('door_placements', [])
    windows = template.get('window_placements', [])

    print(f"\n✓ Loaded: master_template.json")
    print(f"  Doors: {len(doors)}")
    print(f"  Windows: {len(windows)}")

    # Convert doors
    print("\nConverting doors...")
    blender_objects = []
    for door in doors:
        obj = convert_door(door)
        blender_objects.append(obj)
        print(f"  {obj['name']}: {obj['object_type']} at {obj['position']} rot={obj['orientation']}°")

    # Convert windows
    print("\nConverting windows...")
    for window in windows:
        obj = convert_window(window)
        blender_objects.append(obj)
        print(f"  {obj['name']}: {obj['object_type']} at {obj['position']} rot={obj['orientation']}°")

    # Create Blender import JSON
    blender_import = {
        "metadata": {
            "source": "master_template.json",
            "total_objects": len(blender_objects),
            "doors": len(doors),
            "windows": len(windows),
            "rule_0_compliant": True,
            "description": "TB-LKTN House - Complete placement (7 doors + 7 windows)",
            "library_mapping": "Uses actual Ifc_Object_Library.db object_types"
        },
        "objects": blender_objects
    }

    # Save
    output_path = Path("output_artifacts/blender_import.json")
    with open(output_path, 'w') as f:
        json.dump(blender_import, f, indent=2)

    print("\n" + "=" * 80)
    print("CONVERSION COMPLETE")
    print("=" * 80)
    print(f"Total objects: {len(blender_objects)}")
    print(f"  Doors: {len(doors)}")
    print(f"  Windows: {len(windows)}")
    print(f"\n✓ Saved: {output_path}")
    print("\nNext step:")
    print("  blender --python blender_lod300_import.py -- \\")
    print("    output_artifacts/blender_import.json \\")
    print("    ~/Documents/bonsai/tasblock/DatabaseFiles/Ifc_Object_Library.db \\")
    print("    TB-LKTN_House.blend")
    print("=" * 80)

if __name__ == "__main__":
    main()
```

---

## OTHER CRITICAL PROBLEMS IDENTIFIED

### ✅ Problem #1: Element Count - RESOLVED

**Issue:** Spec had contradictions (14 vs 17 elements)

**Fix:** All documentation updated to **14 elements (7 doors + 7 windows)** as authoritative

**Files Updated:**
- TB-LKTN_COMPLETE_SPECIFICATION.md v1.1 (already correct)
- master_template_CORRECTED.json (already correct)

---

### ⚠️ Problem #2: Coordinate System - NEEDS DOCUMENTATION

**Issue:** Coordinate system never explicitly defined

**Fix Required:** Add to specification:

```markdown
## COORDINATE SYSTEM

**Origin:** (0, 0, 0) = Southwest corner at ground floor level

**Axes:**
- X-axis: West → East (Grid A=0.0 → E=11.2m)
- Y-axis: South → North (Grid 1=0.0 → 5=8.5m)
- Z-axis: Floor → Ceiling (height above floor level)

**Units:** Meters (m)

**Grid Mapping:**
- Grid A = X: 0.0m (WEST wall)
- Grid E = X: 11.2m (EAST wall)
- Grid 1 = Y: 0.0m (SOUTH wall)
- Grid 5 = Y: 8.5m (NORTH wall)

**PDF to World Coordinate Transformation:**
1. PDF has Y-down (standard PDF coords)
2. Detected origin (2234, 642)px is Grid A-1 (southwest corner)
3. PDF Y increases DOWN, but World Y increases UP
4. Transformation: `world_y = (pdf_origin_y - pdf_y) / scale_px_per_m`
```

---

### ⚠️ Problem #3: Rotation - NEEDS COMPLETE SPECIFICATION

**Issue:** Rotation axis, direction, reference not defined

**Fix Required:** Add to specification:

```markdown
## ROTATION SPECIFICATION

**Rotation Axis:** Z-axis (vertical, pointing up)

**Rotation Direction:** Counter-clockwise (CCW) when viewed from above (+Z looking down)

**Reference (0°):** Door/window frame parallel to X-axis, opening toward +Y (north)

**Wall Rotation Mapping:**
| Wall | Rotation | Frame Orientation | Opens Toward |
|------|----------|-------------------|--------------|
| SOUTH (y=0.0) | 0° | Parallel to X-axis | +Y (into room/north) |
| NORTH (y=8.5) | 0° | Parallel to X-axis | -Y (into room/south) |
| EAST (x=11.2) | 90° | Parallel to Y-axis | -X (into room/west) |
| WEST (x=0.0) | 90° | Parallel to Y-axis | +X (into room/east) |

**Swing Direction:**
- "inward": Door swings INTO room (toward room center)
- "outward": Door swings OUT of room (toward corridor/exterior)

**Hinge Position:** (Not yet implemented - requires additional parameter)
```

---

### ⚠️ Problem #5: Position Reference Point - NEEDS DEFINITION

**Issue:** Unclear where on object the position refers to

**Fix Required:** Document in specification:

```markdown
## POSITION REFERENCE POINT

**For Doors:**
- Position = Center-bottom of door opening
- X, Y = Center of opening along wall
- Z = Floor level (0.0)

**For Windows:**
- Position = Center-bottom of window frame
- X, Y = Center of window along wall
- Z = Sill height (900mm or 1500mm above floor)

**In blender_lod300_import.py:**
```python
# Adjust for library geometry origin
# Library objects may have origin at geometric center
# Adjust to align center-bottom with specified position
actual_position = position + geometry_origin_offset
```
```

---

### ⚠️ Problem #6: Geometry Scale/Units - NEEDS DOCUMENTATION

**Issue:** Units in BLOB not documented

**Fix Required:** Add to base_geometries schema:

```sql
ALTER TABLE base_geometries ADD COLUMN geometry_units TEXT DEFAULT 'meters';

-- Document: All vertices BLOB contains packed floats in METERS
-- NOT millimeters, NOT centimeters
```

---

## TESTING VALIDATION

After applying fixes, run:

```bash
# 1. Verify library mapping
sqlite3 ~/Documents/bonsai/tasblock/DatabaseFiles/Ifc_Object_Library.db \
  "SELECT object_type, width_mm, height_mm FROM object_catalog
   WHERE object_type IN (
     'door_single',
     'door_louvre_750',
     'window_aluminum_2panel_1200x1000',
     'window_aluminum_3panel_1800x1000',
     'window_aluminum_tophung_600x500'
   );"

# 2. Regenerate blender_import.json with updated script
venv/bin/python3 convert_master_to_blender.py

# 3. Verify object_types match library
jq -r '.objects[].object_type' output_artifacts/blender_import.json | while read type; do
  result=$(sqlite3 ~/Documents/bonsai/tasblock/DatabaseFiles/Ifc_Object_Library.db \
    "SELECT COUNT(*) FROM object_catalog WHERE object_type = '$type';")
  if [ "$result" = "0" ]; then
    echo "❌ MISSING: $type"
  else
    echo "✅ FOUND: $type"
  fi
done
```

---

## NEXT STEPS

1. ✅ Update `convert_master_to_blender.py` with library mapping
2. ⬜ Test updated conversion
3. ⬜ Verify all object_types exist in library
4. ⬜ Add coordinate system documentation to spec
5. ⬜ Add rotation specification to spec
6. ⬜ Add position reference documentation to spec
7. ⬜ Create visual validation SVG (Problem #7)
8. ⬜ Add error handling to blender_lod300_import.py (Problem #10)

---

**Document Authority:** Based on expert diagnostic CRITICAL_DIAGNOSTIC_WHERE_IT_BREAKS.md
**Status:** IN PROGRESS - Critical blocker identified and solution implemented
