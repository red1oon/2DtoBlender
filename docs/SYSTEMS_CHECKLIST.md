# 2DtoBlender SYSTEMS CHECKLIST
# ================================
# MANDATORY READING before every coding session
# Last updated: 2025-11-29
# 
# This file captures hard-won lessons. VIOLATIONS WILL CAUSE REGRESSIONS.

## ============================================
## RULE 0: THE PRIME DIRECTIVE
## ============================================

**NO MANUAL COORDINATE ENTRY. EVER.**

Everything must be derivable from:
1. PDF source (Layer 1)
2. Extracted annotations (Layer 2)
3. Calculated/derived values (Layer 3+)

If you're typing a coordinate number → STOP → Find its source.


## ============================================
## ARCHITECTURAL DECISIONS (DO NOT REVERSE)
## ============================================

### ❌ GRIDTRUTH IS ELIMINATED
- **Decision date**: 2025-11-29
- **Reason**: Was a separate data structure that drifted from annotations
- **Replacement**: Derive ALL spatial data directly from annotations DB
- **Check**: `grep -r "gridtruth\|GridTruth\|grid_truth" --include="*.py"`
- **Expected result**: ZERO matches in active code (only in archived/deprecated)

### ✅ FIVE-LAYER ARCHITECTURE
```
LAYER 5: FIFTH-D Classification (IFC class, discipline, phase, cost)
         ↑ classifies
LAYER 4: Templates (room patterns, object placement rules)
         ↑ instantiates  
LAYER 3: Derived Spatial (room bounds, scale, building envelope)
         ↑ calculates from
LAYER 2: Annotations DB (extracted text, lines, rectangles)
         ↑ extracts from
LAYER 1: PDF Source (immutable truth)
```

### ✅ FIFTH-D FRAMEWORK (ALL OBJECTS MUST HAVE)
Every object requires:
- `ifc_class`: IfcDoor, IfcWall, IfcFurniture, etc.
- `ifc_predefined_type`: DOOR, WALL, etc.
- `discipline`: ARC, MEP, PLUM, STR
- `group`: Doors, Walls, Fixtures, etc.
- `room_id`: Which room it belongs to
- `phase`: 1C_structure, 2_openings, 3_electrical, 4_plumbing, 6_furniture

### ✅ ANNOTATION-DERIVED POSITIONING
Object positions come from:
1. Text labels in PDF → annotation DB → room assignment
2. Room bounds derived from wall lines in annotations
3. Template rules for relative positioning within rooms

NOT from:
- ❌ Hardcoded coordinates
- ❌ GridTruth lookups
- ❌ Manual JSON editing


## ============================================
## GEOMETRY DATABASE RULES
## ============================================

### ✅ BLOB FORMAT (VALIDATED 2025-11-29)
```python
# Correct format:
vertices = np.array([...], dtype=np.float32)  # Nx3
faces = np.array([...], dtype=np.int32)       # Mx3 (triangles)

# Pack as:
blob = struct.pack('II', num_verts, num_faces) + verts.tobytes() + faces.tobytes()
```

### ❌ CORRUPTION PATTERNS TO AVOID
- Face count = vertices/9 → WRONG (was 94% of DB corrupted)
- Faces should be ~2x vertex count for typical meshes
- Vertex blob size = num_verts × 3 × 4 bytes (float32)
- Face blob size = num_faces × 3 × 4 bytes (int32)

### ✅ GEOMETRY PIVOT POINTS
- Furniture/fixtures: CENTERED (origin at geometric center)
- Walls: CORNER origin at START point (watch rotation!)
- Slabs/roofs: CORNER origin (position is corner, not center)

### ✅ PARAMETRIC STRUCTURAL ELEMENTS
Floor, ceiling, roof MUST read from `building_envelope`:
```python
# CORRECT:
width = json_data['building_envelope']['width']   # 9.7m
depth = json_data['building_envelope']['depth']   # 7.0m

# WRONG:
object_type = "slab_6x4_150_lod300"  # Hardcoded size!
```


## ============================================
## VALIDATION CHECKPOINTS
## ============================================

### BEFORE EVERY PR/COMMIT:
```bash
# 1. No GridTruth references
grep -r "gridtruth\|GridTruth\|grid_truth" --include="*.py" src/
# Expected: No matches

# 2. No hardcoded coordinates in generation code
grep -rn "position.*=.*\[.*[0-9]\+\.[0-9]\+.*\]" --include="*.py" src/
# Review each match - should reference variables, not literals

# 3. Run groundwork validator
python validate_groundwork.py output.json --geometry-db bim_geometries.db
# Expected: PASS or PASS WITH WARNINGS (no FAIL)

# 4. Geometry DB integrity
python -c "
import sqlite3
conn = sqlite3.connect('bim_geometries.db')
cur = conn.cursor()
cur.execute('SELECT name, LENGTH(vertices), LENGTH(faces) FROM geometries LIMIT 5')
for name, v, f in cur.fetchall():
    print(f'{name}: verts={v} bytes, faces={f} bytes')
"
# Verify sizes are reasonable (not 1/3 expected)
```

### BEFORE BLENDER IMPORT:
1. Run `validate_groundwork.py` → must PASS
2. Check structural coverage (floor/roof/ceiling match building size)
3. Verify no objects outside building envelope


## ============================================
## COMMON REGRESSION PATTERNS
## ============================================

### Pattern 1: "Just use GridTruth for now"
- **Symptom**: Import pulls from grid_positions table or GridTruth class
- **Why it's wrong**: GridTruth was eliminated; annotations are source of truth
- **Fix**: Trace back to annotation extraction, derive from there

### Pattern 2: "Hardcode this one coordinate"
- **Symptom**: Magic numbers in position calculations
- **Why it's wrong**: Violates Rule 0, breaks reproducibility
- **Fix**: Find source in PDF, extract via annotation, calculate

### Pattern 3: "Copy geometry from template"
- **Symptom**: Structural elements use fixed-size templates
- **Why it's wrong**: Buildings vary; slab_6x4 ≠ building_9.7x7.0
- **Fix**: Generate geometry from building_envelope dimensions

### Pattern 4: "It worked before"
- **Symptom**: Old code path still referenced somewhere
- **Why it's wrong**: Creates dependency on deprecated systems
- **Fix**: Full grep for old patterns, remove all references


## ============================================
## FILE DEPENDENCIES (ACTIVE CODE ONLY)
## ============================================

```
extraction_engine.py
    → reads: PDF file
    → writes: annotations DB, JSON output
    → MUST NOT: reference GridTruth

template_engine.py  
    → reads: room bounds from annotations-derived data
    → writes: object placements to JSON
    → MUST NOT: use hardcoded room coordinates

geometry_generator.py
    → reads: building_envelope from JSON
    → writes: bim_geometries.db
    → MUST NOT: use fixed-size structural templates

blender_lod300_import.py
    → reads: JSON, bim_geometries.db
    → writes: Blender scene
    → MUST NOT: recalculate positions (trust JSON)

validate_groundwork.py
    → reads: JSON, optionally geometry DB
    → writes: PASS/FAIL verdict
    → RUN THIS BEFORE EVERY IMPORT
```


## ============================================
## QUICK DIAGNOSTIC COMMANDS
## ============================================

```bash
# What's the building size?
jq '.building_envelope | {width, depth}' output.json

# What structural objects exist?
jq '.objects[] | select(.object_type | contains("slab") or contains("roof")) | {name, object_type, position}' output.json

# Are there GridTruth remnants?
grep -rn "GridTruth\|grid_truth\|gridtruth" --include="*.py" .

# Geometry DB sanity check
sqlite3 bim_geometries.db "SELECT name, LENGTH(vertices)/12 as verts, LENGTH(faces)/12 as faces FROM geometries WHERE name LIKE '%slab%'"

# Objects per room
jq '.objects | group_by(.room_id) | map({room: .[0].room_id, count: length})' output.json
```


## ============================================
## WHEN IN DOUBT
## ============================================

**CHECK THE COMPLETE SPECS DOCUMENT FIRST.**

Location: `TB-LKTN_COMPLETE_SPECIFICATION.md` (project root)

The specs document is the AUTHORITATIVE SOURCE for:
- Architectural decisions and rationale
- Data structures and formats
- Pipeline stages and dependencies
- Coordinate systems and transformations
- IFC classification rules
- Template structure

**DO NOT GUESS. DO NOT ASSUME. READ THE SPECS.**

If specs and code disagree → SPECS WIN → Fix the code.
If specs are unclear → ASK before implementing.
If specs are missing something → ADD IT after discussion.

### ⚠️ STAY WITHIN PROJECT STRUCTURE

**DO NOT reference sources outside this project.**
- ❌ No external tutorials/blogs for "how it should work"
- ❌ No assumptions based on other BIM/IFC projects
- ❌ No inventing solutions from general knowledge
- ✅ Use ONLY: project code, specs, and documentation

**IF STUCK → ASK FOR EXPERT HELP**
- Don't spin wheels guessing
- Don't implement "temporary" workarounds
- Request clarification from project lead
- Better to pause than introduce regressions


## ============================================
## CONTACTS & RESOURCES
## ============================================

- **Complete Specs**: `TB-LKTN_COMPLETE_SPECIFICATION.md` ← READ THIS WHEN IN DOUBT
- **Transcript of architectural decisions**: /mnt/transcripts/2025-11-29-*.txt
- **Validator script**: validate_groundwork.py
- **GitHub**: https://github.com/red1oon/2DtoBlender


## ============================================
## SESSION START CHECKLIST
## ============================================

Before starting any coding:

[ ] Read this entire file
[ ] Read `TB-LKTN_COMPLETE_SPECIFICATION.md` if unfamiliar with architecture
[ ] Run: `grep -r "gridtruth" --include="*.py" src/` (expect: 0 matches)
[ ] Confirm current JSON passes: `python validate_groundwork.py output.json`
[ ] Note building_envelope dimensions for this project
[ ] Understand which layer you're working on (1-5)

If ANY check fails → FIX FIRST before proceeding.

**IF IN DOUBT ABOUT ANYTHING → READ TB-LKTN_COMPLETE_SPECIFICATION.md FIRST**
