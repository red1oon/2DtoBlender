# CRITICAL DIAGNOSTIC: Where the Spec Actually Breaks
**Date:** 2025-11-26
**Purpose:** Identify WHY objects are missing, misaligned, wrongly oriented, wrong size

---

## 🚨 PROBLEM #1: ELEMENT COUNT CONTRADICTION

The spec contradicts itself on element count:

| Location | Count | Breakdown |
|----------|-------|-----------|
| Section 1.2 | 14 elements | - |
| Section 8 (TB-LKTN) | 14 elements | 7 doors + 7 windows |
| Section 4.1 (MASTER_SPEC) | 17 elements | 7 doors + 10 windows |
| Section 5.5 (MASTER_SPEC) | 17 expected | jq check expects 17 |
| Section 11.3 (TB-LKTN) | 14 expected | jq check expects 14 |

**IMPACT:** Developer doesn't know target. If code expects 17 but JSON has 14, 3 objects "missing".

**FIX:** Single authoritative count: **14 elements (7 doors + 7 windows)**

---

## 🚨 PROBLEM #2: COORDINATE SYSTEM UNDEFINED

The spec NEVER explicitly defines coordinate transformation:

```
PDF Coordinates:     → Y increases DOWN (standard PDF)
Grid Coordinates:    → Y increases UP? (A-E = X, 1-5 = Y)
Blender Coordinates: → Z is UP (industry standard)
```

**Questions not answered:**
1. Is Y in master_template.json the same as Y in Blender?
2. When position.y = 0.0, is that SOUTH wall (bottom) or NORTH wall (top)?
3. Does grid row "1" map to y=0.0 or y=8.5?

**Current implied mapping (from code):**
- Grid 1 = y=0.0 (SOUTH)
- Grid 5 = y=8.5 (NORTH)

**IMPACT:** If developer assumes PDF Y-down convention, all objects flip vertically.

**FIX:** Add explicit section:
```
COORDINATE SYSTEM:
- Origin (0,0,0) = Southwest corner at ground floor
- X-axis: West → East (Grid A → E)
- Y-axis: South → North (Grid 1 → 5)  
- Z-axis: Floor → Ceiling (UP)
- Units: Meters
```

---

## 🚨 PROBLEM #3: ROTATION IS INCOMPLETE

Current rotation mapping:
```python
WALL_ROTATION = {
    "NORTH": 0,
    "SOUTH": 0,
    "EAST": 90,
    "WEST": 90
}
```

**What this DOESN'T specify:**
1. Rotation axis (around Z? around local Y?)
2. Rotation direction (CW or CCW when viewed from above?)
3. What is 0° reference? (facing +X? facing +Y? facing -Y?)
4. How does "inward"/"outward" swing affect rotation?
5. Is NORTH door facing into room (south) or out of room (north)?

**Example confusion:**
- SOUTH wall door, swing="inward"
- Should door face INTO room (north) = 0° or 180°?
- Should hinge be on left or right?

**IMPACT:** Doors face wrong direction, swing wrong way.

**FIX:** Define explicit door orientation:
```
DOOR ORIENTATION:
- Rotation 0° = Door frame parallel to X-axis, door opens toward +Y
- Rotation 90° = Door frame parallel to Y-axis, door opens toward +X
- "inward" = Opens INTO the room (toward room center)
- "outward" = Opens OUT of room (away from room center)

For SOUTH wall door (swing inward):
- Rotation = 0° (frame along X-axis)
- Door swings toward +Y (into room)
- Hinge on WEST side of opening
```

---

## 🚨 PROBLEM #4: OBJECT_TYPE NAMING MISMATCH

Spec defines object_type generation:
```python
def door_to_object_type(width_mm, height_mm):
    return f"door_{width_mm}x{height_mm}_lod300"
    # Example: "door_900x2100_lod300"
```

**But does object_catalog actually contain this EXACT string?**

Possible mismatches:
- `door_900x2100_lod300` vs `Door_900x2100_LOD300` (case)
- `door_900x2100_lod300` vs `door_900_2100_lod300` (separator)
- `door_900x2100_lod300` vs `door_0.9x2.1` (units)
- `door_900x2100_lod300` vs `IfcDoor_900x2100` (prefix)

**IMPACT:** Objects "missing" because library lookup fails.

**FIX:** Add validation step:
```bash
# BEFORE running pipeline, verify ALL object_types exist:
echo "door_900x2100_lod300" | while read type; do
  sqlite3 Ifc_Object_Library.db \
    "SELECT object_type FROM object_catalog WHERE object_type = '$type';"
done
```

---

## 🚨 PROBLEM #5: POSITION REFERENCE POINT UNDEFINED

When placing a door at position (2.2, 0.0, 0.0):

**Where on the door is this point?**
- Center of door leaf?
- Hinge corner (bottom)?
- Center of door opening?
- Left edge of frame?

Different CAD systems use different reference points:
- Revit: Insertion point (usually center-bottom of opening)
- AutoCAD: User-defined origin
- Blender: Object origin (usually geometric center)

**IMPACT:** Door placed 450mm off (half door width) if reference wrong.

**FIX:** Specify in schema:
```json
{
  "position": {"x": 2.2, "y": 0.0, "z": 0.0},
  "reference_point": "center_bottom_of_opening"
}
```

And in Blender import:
```python
# Adjust for door geometry origin
door_center_offset = door_width / 2
actual_position = position - door_center_offset
```

---

## 🚨 PROBLEM #6: GEOMETRY SCALE/UNITS MISMATCH

**master_template.json uses:**
- `width_mm: 900` (millimeters)
- `position.x: 2.2` (meters)

**object_catalog stores:**
- `width_mm: 900` (millimeters)
- vertices BLOB (what units?)

**Blender expects:**
- Meters (typically)

**Questions:**
1. Are vertices in the BLOB stored in millimeters or meters?
2. Does blender_lod300_import.py apply scale factor?
3. If geometry is in mm and position is in m, objects are 1000x too big.

**IMPACT:** Objects appear as tiny dots or fill entire scene.

**FIX:** Document in base_geometries:
```sql
-- Add comment or column
CREATE TABLE base_geometries (
    ...
    vertices BLOB NOT NULL,  -- Packed floats in METERS (not mm!)
    ...
    geometry_units TEXT DEFAULT 'meters'
);
```

---

## 🚨 PROBLEM #7: NO VISUAL VALIDATION STEP

The spec has bash jq validation, but NO visual check:

```bash
# Current: Just checks counts
jq '.door_placements | length' master_template.json  # Returns 7, "passes"
```

**But this doesn't catch:**
- Door placed inside wall (wrong Y by 0.15m)
- Door facing wrong direction (rotation off by 180°)
- Door floating above floor (Z = 0.1 instead of 0.0)

**FIX:** Add visual validation step:
```python
# validation/visual_check.py
def generate_2d_placement_diagram(master_template):
    """Generate top-down SVG showing all placements"""
    # Draw building envelope
    # Draw room boundaries
    # Draw doors as rectangles with swing arc
    # Draw windows as lines on exterior walls
    # Output: placement_verification.svg
```

Then human reviews SVG BEFORE Blender import.

---

## 🚨 PROBLEM #8: LIBRARY GEOMETRY ORIGIN VARIES

Different objects in object_catalog may have different local origins:

| Object | Expected Origin | Actual Origin? |
|--------|-----------------|----------------|
| Door | Center-bottom of frame | ??? |
| Window | Center-bottom of frame | ??? |
| Toilet | Center of bowl, floor level | ??? |
| Basin | Center-back, at rim height | ??? |

If library objects have inconsistent origins, placement logic fails.

**IMPACT:** Each object type misaligned differently.

**FIX:** Standardize in object_catalog:
```sql
ALTER TABLE object_catalog ADD COLUMN origin_x REAL DEFAULT 0.0;
ALTER TABLE object_catalog ADD COLUMN origin_y REAL DEFAULT 0.0;
ALTER TABLE object_catalog ADD COLUMN origin_z REAL DEFAULT 0.0;
ALTER TABLE object_catalog ADD COLUMN origin_description TEXT;
-- e.g., "center_bottom_of_bounding_box"
```

---

## 🚨 PROBLEM #9: PLACEMENT_RULES NOT CONNECTED TO PIPELINE

Section 13 defines beautiful placement_rules table:
```sql
object_type: 'door_single'
alignment_type: 'bottom'
rotation_method: 'wall_normal'
```

**But the pipeline (Stages 1-8) never queries this table!**

Looking at the pipeline:
- Stage 4: `corrected_door_placement.py` uses hardcoded Python rules
- Stage 7: `convert_master_to_blender.py` uses hardcoded WALL_ROTATION dict
- Stage 8: `blender_lod300_import.py` only queries geometry, not rules

**IMPACT:** Database rules ignored. Hardcoded Python determines behavior.

**FIX:** Modify Stage 7/8 to query placement_rules:
```python
def get_rotation(object_type, wall):
    # Query database instead of hardcoded dict
    rule = db.execute("""
        SELECT rotation_method, rotation_offset_degrees 
        FROM placement_rules 
        WHERE object_type = ?
    """, (object_type,)).fetchone()
    
    if rule['rotation_method'] == 'wall_normal':
        return WALL_NORMAL_ROTATIONS[wall] + rule['rotation_offset_degrees']
```

---

## 🚨 PROBLEM #10: NO ERROR HANDLING FOR MISSING GEOMETRY

What happens when object_catalog lookup fails?

```python
# Current (implied):
geometry = db.query("SELECT * FROM base_geometries WHERE geometry_hash = ?", hash)
# If geometry is None, code probably crashes or silently skips
```

**No logging, no fallback, no error collection.**

**IMPACT:** Objects silently disappear with no indication why.

**FIX:** Add explicit error handling:
```python
def fetch_geometry(object_type):
    result = db.query(...)
    if result is None:
        logger.error(f"MISSING GEOMETRY: {object_type}")
        MISSING_OBJECTS.append(object_type)
        return create_placeholder_cube(object_type)  # Visible error marker
    return result
```

---

## DIAGNOSTIC CHECKLIST

Before next build, verify:

- [ ] Element count matches everywhere (14)
- [ ] Coordinate system documented (origin, axes, units)
- [ ] Rotation fully specified (axis, direction, reference, swing)
- [ ] Object_type strings match EXACTLY in object_catalog
- [ ] Position reference point defined
- [ ] Geometry units documented (meters in BLOB)
- [ ] Visual validation step added
- [ ] Library geometry origins consistent
- [ ] Pipeline actually queries placement_rules table
- [ ] Error handling logs missing objects

---

## RECOMMENDED IMMEDIATE ACTIONS

1. **Print object_catalog contents:**
   ```bash
   sqlite3 Ifc_Object_Library.db "SELECT object_type FROM object_catalog;"
   ```
   Compare EXACTLY to generated object_type strings.

2. **Add coordinate system diagram to spec**

3. **Create visual validation SVG before Blender import**

4. **Add verbose logging to blender_lod300_import.py:**
   ```python
   for obj in objects:
       print(f"Placing {obj.name} at {obj.position} rotation {obj.rotation}")
       geometry = fetch_geometry(obj.object_type)
       if geometry is None:
           print(f"  ERROR: No geometry for {obj.object_type}")
           continue
       print(f"  OK: Found geometry hash {geometry.hash}")
   ```

5. **Test ONE door in isolation before full import**

---

**The spec looks complete but has critical IMPLICIT assumptions that break when developer interprets differently.**
