# Unified BIM Schema - Migration Plan

## The BIM5D Big Picture

**The Fundamental Equations:**

```
[CORE-D]   +  [THIRD-D]   =  [IFC]
   2D            3D           3D Model
  WHAT          WHERE         Placed

[IFC]      +  [FOURTH-D]  =  [BIM-4D]
3D Model         4D          Construction
Placed          WHEN          Sequence

[BIM-4D]   +  [FIFTH-D]   =  [FULL-BIM5D]
4D Model         5D           Complete
Sequenced       HOW MUCH      BIM Model
                (Cost/Class)
```

### The Five Dimensions (Corrected Nomenclature)

```
┌─────────────────────────────────────────────────────────────────┐
│                    BIM5D ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [CORE-D]: 2D - Object Library (WHAT exists)                    │
│            Dimension: 2D                                        │
│            Question: WHAT?                                      │
│            ▸ LOD300 meshes (.blend files)                       │
│            ▸ Object types (door_900_lod300, roof_slab_lod300)   │
│            ▸ Properties, dimensions, materials                  │
│            ▸ IFC class templates                                │
│            Source: Ifc_Object_Library.db                        │
│            Tag: [CORE-D] or [2D]                                │
│            ⚠️  INCOMPLETE ALONE - no positions!                 │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [THIRD-D]: 3D - Spatial Geometry (WHERE it goes)               │
│             Dimension: 3D                                       │
│             Question: WHERE?                                    │
│             ▸ building_envelope (X,Y,Z boundaries)              │
│             ▸ room_bounds (spatial relationships)               │
│             ▸ elevations (Z-heights)                            │
│             ▸ Grid lines (structural grid)                      │
│             Source: GridTruth.json                              │
│             Tag: [THIRD-D] or [3D]                              │
│             ⚠️  INCOMPLETE ALONE - just coordinates!            │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [IFC]: 3D Model = [CORE-D] + [THIRD-D]                        │
│         Placed Model = WHAT + WHERE                             │
│         door_900_lod300 @ [3.04, 2.17, 0.0] = Actual door      │
│         Result: Federation.db or Blender scene                  │
│         Tag: [IFC] or [3D-MODEL]                                │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [FOURTH-D]: 4D - Time/Sequence (WHEN it's built)               │
│              Dimension: 4D                                      │
│              Question: WHEN?                                    │
│              ▸ Phases (1B, 1C, 2, 3...)                         │
│              ▸ Sequence (construction order)                    │
│              ▸ Dependencies (doors need walls)                  │
│              ▸ Mandatory flags (must exist)                     │
│              Source: master_reference_template.json             │
│              Tag: [FOURTH-D] or [4D]                            │
│              ⚠️  INCOMPLETE ALONE - needs [IFC] to sequence!    │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [BIM-4D]: Construction Model = [IFC] + [FOURTH-D]              │
│            Time-Sequenced = Placed Model + Schedule             │
│            Result: 4D construction simulation                   │
│            Tag: [BIM-4D] or [4D-MODEL]                          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [FIFTH-D]: 5D - Classification/Cost (HOW MUCH)                 │
│             Dimension: 5D                                       │
│             Question: HOW MUCH? (cost/class)                    │
│             ▸ IFC classes (IfcDoor, IfcSlab)                    │
│             ▸ Disciplines (ARC, STR, MEP, PLUM)                 │
│             ▸ UBBL compliance                                   │
│             ▸ Material specs (for BOQ/costing)                  │
│             Source: ifc_naming_layer.json                       │
│             Tag: [FIFTH-D] or [5D]                              │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [FULL-BIM5D]: Complete Model = [BIM-4D] + [FIFTH-D]            │
│                All dimensions integrated                        │
│                WHAT + WHERE + WHEN + HOW MUCH                   │
│                Result: Production-ready BIM model               │
│                Tag: [FULL-BIM5D]                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                        VISUAL FLOW

         [CORE-D]          [THIRD-D]         [FOURTH-D]        [FIFTH-D]
            2D                3D                 4D               5D
           WHAT              WHERE              WHEN           HOW MUCH
            │                  │                  │                │
            │    ┌─────────────┘                  │                │
            ▼    ▼                                │                │
          ┌────────┐                              │                │
          │ [IFC]  │◄─────────────────────────────┘                │
          │  3D    │                                               │
          │ Model  │                                               │
          └────┬───┘                                               │
               │                                                   │
               ▼                                                   │
          ┌─────────┐                                              │
          │[BIM-4D] │◄─────────────────────────────────────────────┘
          │   4D    │
          │Complete │
          └─────────┘
```

### Tag Reference

Use these tags in code comments and documentation:

| Tag | Dimension | Question | Meaning | Example File |
|-----|-----------|----------|---------|--------------|
| `[CORE-D]` or `[2D]` | 2D | WHAT? | Object Library - fundamental object definitions | `Ifc_Object_Library.db` |
| `[THIRD-D]` or `[3D]` | 3D | WHERE? | GridTruth - spatial geometry | `GridTruth.json` |
| `[IFC]` or `[3D-MODEL]` | 3D Model | - | [CORE-D] + [THIRD-D] = Placed 3D model | `Federation.db`, Blender |
| `[FOURTH-D]` or `[4D]` | 4D | WHEN? | Construction sequence (phases, dependencies) | See combined file below ⬇️ |
| `[BIM-4D]` or `[4D-MODEL]` | 4D Model | - | [IFC] + [FOURTH-D] = Time-sequenced model | `unified_model.py` intermediate |
| `[FIFTH-D]` or `[5D]` | 5D | HOW MUCH? | IFC naming layer - classification/cost | `ifc_naming_layer.json` |
| `[FULL-BIM5D]` | Complete | - | All dimensions integrated | `unified_model.py` output |

**Combined Dimension Files:**
| File | Contains | Dimensions |
|------|----------|------------|
| `master_reference_template.json` | Object types + Construction sequence | **[CORE-D + FOURTH-D]** (WHAT + WHEN) |

**Extraction Sources (Input only, not core dimensions):**
| Source | Purpose |
|--------|---------|
| `TB-LKTN HOUSE.pdf` | Extract labels (D1, W1) and schedules → populate [CORE-D] and [THIRD-D] |
| `Enhanced_primitive.db` | PDF text primitives database → intermediate extraction data |

### Master Reference Template = [CORE-D + FOURTH-D]

**CRITICAL:** `master_reference_template.json` is a **combined file** containing both dimensions:

```json
{
  "item": "Main Entrance Door",
  "object_type": "door_900_lod300",      // [CORE-D] WHAT exists
  "mandatory": true,                     // [FOURTH-D] Must exist
  "phase": "2_openings",                 // [FOURTH-D] WHEN built
  "sequence": 15,                        // [FOURTH-D] Construction order
  "dependencies": ["walls"],             // [FOURTH-D] Needs walls first
  "detection_id": "SCHEDULE_REFERENCE"   // How to find it
}
```

This design is intentional:
- **[CORE-D]**: Defines WHAT objects exist in the building type
- **[FOURTH-D]**: Defines WHEN they're built and dependencies
- **Combined**: One file defines the complete construction checklist

---

## Blender Collection Hierarchy (Automatic from [FIFTH-D])

**The [FIFTH-D] IFC naming layer automatically generates Blender-native collection structure:**

```
Scene Collection
├─ 📁 ARC (Architectural)
│  ├─ 📁 Walls
│  │  ├─ wall_exterior_north
│  │  ├─ wall_exterior_south
│  │  └─ wall_interior_bedroom_1
│  ├─ 📁 Doors
│  │  ├─ door_main_entrance_D1
│  │  ├─ door_bedroom_master_D2
│  │  └─ door_bathroom_D3
│  ├─ 📁 Windows
│  │  └─ window_living_room_W1
│  └─ 📁 Furniture
│     ├─ sofa_living_room
│     └─ bed_master_bedroom
│
├─ 📁 STR (Structural)
│  ├─ 📁 Floor
│  │  └─ floor_slab_main
│  └─ 📁 Roofing
│     └─ roof_slab_main
│
├─ 📁 MEP (Mechanical/Electrical/Plumbing)
│  ├─ 📁 Electrical
│  │  ├─ switch_living_room_S1
│  │  └─ outlet_bedroom_P1
│  └─ 📁 Lighting
│     ├─ ceiling_light_living_room
│     └─ ceiling_fan_bedroom
│
└─ 📁 PLUM (Plumbing)
   ├─ 📁 Fixtures
   │  ├─ toilet_bathroom_master
   │  └─ basin_bathroom_common
   └─ 📁 Drainage
      ├─ floor_drain_bathroom
      └─ discharge_perimeter_1
```

### How This Works (Automatic Pipeline)

```python
# Step 1: [FIFTH-D] provides discipline/group
# (from ifc_naming_layer.json)
obj['discipline'] = 'ARC'
obj['group'] = 'Doors'
obj['blender_name'] = 'ARC_Door_D1'

# Step 2: unified_model.py generates collection hierarchy
outliner = model.outliner_view()
# Returns:
# {
#   "ARC": {
#     "Doors": [door_D1, door_D2, door_D3],
#     "Walls": [wall_north, wall_south],
#   },
#   "STR": {
#     "Roofing": [roof_slab_main]
#   }
# }

# Step 3: Blender import creates collections
for discipline, groups in outliner.items():
    disc_collection = create_collection(discipline)  # "ARC"
    for group, objects in groups.items():
        group_collection = create_collection(group, parent=disc_collection)  # "Doors"
        for obj in objects:
            import_object(obj, collection=group_collection)
```

### Why This Is Smooth for Blender

**1. Native Blender Conventions** ✅
- Collections = natural Blender organizational structure
- Discipline/Group = exactly how architects work in Blender
- Object naming follows Blender conventions (readable, hierarchical)

**2. IFC Standard Compliance** ✅
- Discipline codes (ARC, STR, MEP, PLUM) = ISO 19650 standard
- IFC classes (IfcDoor, IfcWall, IfcSlab) = buildingSMART standard
- Ready for IFC4 export from Blender via BlenderBIM

**3. Multi-Discipline Coordination** ✅
- Same structure as federated BIM models
- Disciplines can be toggled on/off in Blender outliner
- Matches how consultants deliver models (ARC.ifc, STR.ifc, MEP.ifc)

**4. Already Implemented** ✅
- `ifc_naming_layer.json` defines all disciplines/groups
- `unified_model.py` has `outliner_view()` method ready
- `BuildingElement.collection_path` property returns `[discipline, group]`
- No new code needed - just use existing structure!

### Comparison: Our Output vs Manual Blender Organization

**Manual Blender Work (painful):**
```
❌ User manually creates collections
❌ User manually moves objects into collections
❌ User manually renames objects for clarity
❌ Inconsistent naming across projects
```

**Our Pipeline (automatic):**
```
✅ Collections auto-created from [FIFTH-D]
✅ Objects auto-placed in correct collections
✅ Consistent naming: {discipline}_{type}_{identifier}
✅ Same structure every project
```

### The Complete Flow to Blender

```
[CORE-D]     → object_type: "door_900_lod300"
             → Gets LOD300 mesh from library

[THIRD-D]    → position: [3.04, 2.17, 0.0]
             → Spatial placement

[FOURTH-D]   → phase: "2_openings"
             → Construction sequence

[FIFTH-D]    → ifc_class: "IfcDoor"
             → discipline: "ARC"
             → group: "Doors"
             → blender_name: "ARC_Door_MainEntrance"
             → collection_path: ["ARC", "Doors"]

BLENDER      → Scene Collection
             →   └─ ARC
             →       └─ Doors
             →           └─ ARC_Door_MainEntrance
             →               (mesh at [3.04, 2.17, 0.0])
```

**Result:** Clean, organized, IFC-compliant Blender scene with zero manual sorting! 🎯

### Why GridTruth Is "Third D" Not "3D"

**GridTruth alone is just numbers:**
```json
{
  "building_envelope": {
    "x_min": 0.75,
    "y_min": 0.75,
    "x_max": 10.45,
    "y_max": 7.75
  }
}
```

**This is NOT a 3D model yet!** ❌

**Needs [CORE-D] to become [IFC]:**
```python
core_d = get_object("roof_slab_flat_lod300")  # From object library
third_d = gridtruth["building_envelope"]      # From GridTruth

# Combine:
ifc_roof = instantiate(core_d, position=third_d.center, extent=third_d.size)
# NOW it's an IFC object! ✅
```

### Pipeline Flow with BIM5D Tags

```python
# =========================================================================
# STEP 1: Extract from PDF (Input Source - populates dimensions)
# =========================================================================
pdf_labels = extract_from_pdf("TB-LKTN HOUSE.pdf")
# Result: Door labels (D1, D2) and schedules
# Populates: [CORE-D] with object types, [THIRD-D] with PDF positions

# =========================================================================
# STEP 2: Load [THIRD-D] GridTruth (Spatial Geometry - WHERE)
# =========================================================================
gridtruth = load_gridtruth()  # [THIRD-D] [3D]
# Contains: building_envelope, room_bounds, elevations
# ⚠️ INCOMPLETE ALONE - just coordinates!

# =========================================================================
# STEP 3: Load [CORE-D] Object Library (WHAT exists)
# =========================================================================
library = load_object_library()  # [CORE-D] [2D]
# Contains: door_900_lod300 mesh, roof_slab_lod300 properties
# ⚠️ INCOMPLETE ALONE - no positions!

# =========================================================================
# STEP 4: Generate [IFC] = [CORE-D] + [THIRD-D]
# =========================================================================
ifc_objects = []
for label in pdf_labels:
    # [CORE-D]: Get object definition
    template = library.get(label['object_type'])  # WHAT

    # [THIRD-D]: Get spatial position
    position = gridtruth.transform_to_building(label['pdf_pos'])  # WHERE

    # [IFC]: Combine WHAT + WHERE
    instance = instantiate(template, position=position)
    ifc_objects.append(instance)

# For mandatory items missing from PDF:
for item in mandatory_items_missing_from_pdf:
    if can_derive_from_gridtruth(item):
        # Example: Roof has no PDF label, derive from envelope
        template = library.get('roof_slab_lod300')  # [CORE-D] WHAT
        position = gridtruth.building_envelope.center  # [THIRD-D] WHERE
        roof = instantiate(template, position=position)  # [IFC]
        ifc_objects.append(roof)

# Result: [IFC] = [CORE-D] + [THIRD-D] ✅
# Placed 3D model with positioned objects

# =========================================================================
# STEP 5: Load [FOURTH-D] Construction Sequence (WHEN)
# =========================================================================
master_template = load_master_template()  # [FOURTH-D] [4D]
# Contains: phases, sequence, mandatory flags, dependencies

# =========================================================================
# STEP 6: Generate [BIM-4D] = [IFC] + [FOURTH-D]
# =========================================================================
bim4d_objects = []
for obj in ifc_objects:
    # Add [FOURTH-D]: WHEN information
    obj['phase'] = master_template.get_phase(obj['object_type'])
    obj['sequence'] = master_template.get_sequence(obj['object_type'])
    obj['mandatory'] = master_template.is_mandatory(obj['object_type'])
    obj['dependencies'] = master_template.get_dependencies(obj['object_type'])
    bim4d_objects.append(obj)

# Result: [BIM-4D] = [IFC] + [FOURTH-D] ✅
# Time-sequenced construction model

# =========================================================================
# STEP 7: Load [FIFTH-D] Classification/Cost (HOW MUCH)
# =========================================================================
naming_layer = load_ifc_naming_layer()  # [FIFTH-D] [5D]
# Contains: IFC classes, disciplines, materials, costs

# =========================================================================
# STEP 8: Generate [FULL-BIM5D] = [BIM-4D] + [FIFTH-D]
# =========================================================================
full_bim5d = []
for obj in bim4d_objects:
    # Add [FIFTH-D]: HOW MUCH information
    obj['ifc_class'] = naming_layer.get_ifc_class(obj['object_type'])
    obj['discipline'] = naming_layer.get_discipline(obj['object_type'])
    obj['group'] = naming_layer.get_group(obj['object_type'])
    obj['material'] = naming_layer.get_material(obj['object_type'])
    obj['unit_cost'] = naming_layer.get_cost(obj['object_type'])
    full_bim5d.append(obj)

# Result: [FULL-BIM5D] ✅
# Complete model: WHAT + WHERE + WHEN + HOW MUCH

# =========================================================================
# STEP 9: Validate Completeness (GATE 3)
# =========================================================================
# Check: What [FOURTH-D] says MUST exist (mandatory items)
mandatory_items = master_template.get_mandatory_items()

# Check: What actually exists in [IFC]
found_types = {obj['object_type'] for obj in ifc_objects}

# Missing = [FOURTH-D].mandatory - [IFC].placed
missing = set(mandatory_items) - found_types

if missing:
    print(f"❌ GATE 3 FAILED: Missing mandatory [FOURTH-D] items: {missing}")
    print(f"   These must be generated from [CORE-D] + [THIRD-D]")
else:
    print(f"✅ GATE 3 PASSED: [FULL-BIM5D] model complete")
    print(f"   {len(full_bim5d)} objects with WHAT+WHERE+WHEN+HOW MUCH")
```

### Why Roof Was Missing (Now Fixed)

**OLD PIPELINE MISTAKE:**
```
PDF extraction → Objects
[THIRD-D] GridTruth → (ignored, only used for calibration)
[CORE-D] Library → (never consulted for mandatory items)
[FOURTH-D] Template → (not checked for mandatory flags)

Roof has no PDF label → Not extracted → Missing ❌
```

**CORRECT PIPELINE:**
```
[FOURTH-D] template says: "Roof mandatory=true"
[THIRD-D] provides: building_envelope (WHERE)
[CORE-D] provides: roof_slab_flat_lod300 (WHAT)

Pipeline: Generate roof from [CORE-D] + [THIRD-D] → [IFC]
         because [FOURTH-D] says mandatory (even if missing from PDF)

[CORE-D] + [THIRD-D] = Roof exists in [IFC]! ✅
```

**The validator bug:**
```python
# OLD (WRONG):
roof_count = count_objects_with_type(objects, 'roof')
# Counted discharge_perimeter (roof_gutter_100_lod300) as "roof"!

# FIXED:
roof_count = count_objects_with_type(objects, 'roof', exclude=['gutter'])
# Only counts actual roof slabs, not gutters
```

### Documentation Convention

**Use BIM5D tags in all code comments, docstrings, and documentation:**

```python
"""
[CORE-D] Object Library Access Module
Dimension: 2D (WHAT exists)

Interfaces with Ifc_Object_Library.db to retrieve LOD300 mesh definitions
and object properties.

Tags: [CORE-D], [2D]
Dependencies: None (fundamental layer)
Used by: All layers that need object definitions
⚠️ INCOMPLETE ALONE - provides WHAT but not WHERE
"""

"""
[THIRD-D] GridTruth Parser
Dimension: 3D (WHERE it goes)

Parses GridTruth.json to extract spatial geometry (building_envelope,
room_bounds, elevations).

Tags: [THIRD-D], [3D]
Combines with: [CORE-D] → [IFC]
Dependencies: None (fundamental layer)
⚠️ INCOMPLETE ALONE - provides WHERE but not WHAT
Output: Spatial coordinates and boundaries
"""

"""
[IFC] Model Generator
Result: 3D Model (WHAT + WHERE)

Combines [CORE-D] object definitions with [THIRD-D] spatial positions
to generate actual IFC building elements.

Tags: [IFC], [3D-MODEL]
Equation: [CORE-D] + [THIRD-D] = [IFC]
Input:
  - [CORE-D] object library (WHAT)
  - [THIRD-D] gridtruth geometry (WHERE)
Output:
  - [IFC] buildable 3D model
  - Federation.db or Blender scene
"""

"""
[FOURTH-D] Construction Sequence Manager
Dimension: 4D (WHEN it's built)

Manages construction phases, sequences, dependencies, and mandatory flags.

Tags: [FOURTH-D], [4D]
Dependencies: None (fundamental layer)
⚠️ INCOMPLETE ALONE - provides WHEN but needs [IFC] to sequence
Used by: [BIM-4D] model generation
"""

"""
[BIM-4D] Time-Sequenced Model Generator
Result: 4D Model (WHAT + WHERE + WHEN)

Combines [IFC] placed model with [FOURTH-D] construction sequence.

Tags: [BIM-4D], [4D-MODEL]
Equation: [IFC] + [FOURTH-D] = [BIM-4D]
Input:
  - [IFC] placed 3D model
  - [FOURTH-D] master_reference_template (WHEN)
Output:
  - [BIM-4D] time-sequenced construction model
"""

"""
[FIFTH-D] Classification & Cost Layer
Dimension: 5D (HOW MUCH - cost/classification)

Provides IFC classification, disciplines, materials, and cost data.

Tags: [FIFTH-D], [5D]
Dependencies: None (fundamental layer)
Used by: [FULL-BIM5D] model generation for BOQ/costing
"""

"""
[FULL-BIM5D] Unified Building Model
Result: Complete Model (WHAT + WHERE + WHEN + HOW MUCH)

Orchestrates all five dimensions into single coherent model with
multiple views (library, federated, schedule, jigsaw, outliner).

Tags: [FULL-BIM5D]
Equation: [BIM-4D] + [FIFTH-D] = [FULL-BIM5D]
Integrates: [CORE-D], [THIRD-D], [FOURTH-D], [FIFTH-D]
Output: Production-ready BIM5D model with all views
"""
```

**In inline comments:**
```python
# [CORE-D] [2D] Get object definition (WHAT)
door_template = library.get('door_900_lod300')

# [THIRD-D] [3D] Get spatial position (WHERE)
position = gridtruth.room_bounds['RUANG_TAMU'].center

# [IFC] Instantiate: [CORE-D] + [THIRD-D] → [IFC]
door_instance = instantiate(door_template, position=position)
# Result: Placed 3D object (WHAT + WHERE)

# [FOURTH-D] [4D] Add construction phase (WHEN)
door_instance['phase'] = '2_openings'
door_instance['sequence'] = 15
door_instance['mandatory'] = True

# [BIM-4D] Result: Time-sequenced object
# WHAT + WHERE + WHEN

# [FIFTH-D] [5D] Add classification/cost (HOW MUCH)
door_instance['ifc_class'] = 'IfcDoor'
door_instance['discipline'] = 'ARC'
door_instance['unit_cost'] = 450.00

# [FULL-BIM5D] Result: Complete BIM object
# WHAT + WHERE + WHEN + HOW MUCH ✅
```

---

## The Insight

**Object Library, Federated Model, and Master Checklist are the SAME dataset.**

They've been building ONE thing from three directions. This migration reveals the unity.

---

## What The Team Built (All Valid!)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WHAT EXISTS TODAY                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐    │
│  │  OBJECT LIBRARY  │   │ FEDERATED MODEL  │   │ MASTER CHECKLIST │    │
│  │                  │   │                  │   │                  │    │
│  │  - Mesh files    │   │  - Placed objects│   │  - Phase sequence│    │
│  │  - LOD variants  │   │  - Positions     │   │  - Dependencies  │    │
│  │  - Properties    │   │  - Source refs   │   │  - Mandatory flags│   │
│  │  - IFC classes   │   │  - Disciplines   │   │  - Detection IDs │    │
│  │                  │   │                  │   │                  │    │
│  └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘    │
│           │                      │                      │              │
│           └──────────────────────┼──────────────────────┘              │
│                                  │                                      │
│                                  ▼                                      │
│                    ┌─────────────────────────┐                         │
│                    │    SAME DATA MODEL      │                         │
│                    │    Different Views      │                         │
│                    └─────────────────────────┘                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Unified View

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     UNIFIED BUILDING ELEMENT                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  IDENTITY          │  CLASSIFICATION      │  GEOMETRY                   │
│  ─────────         │  ──────────────      │  ────────                   │
│  id                │  ifc_class           │  mesh_path                  │
│  name              │  ifc_predefined_type │  position [x,y,z]           │
│  description       │  discipline          │  rotation [rx,ry,rz]        │
│                    │  group               │  scale [sx,sy,sz]           │
│                    │                      │                             │
│  STATUS            │  SCHEDULE (4D)       │  FEDERATION                 │
│  ──────            │  ────────────        │  ──────────                 │
│  status:           │  phase               │  source_model               │
│   - template       │  sequence            │  source_guid                │
│   - placed         │  dependencies        │  slot_id (jigsaw)           │
│   - missing        │  mandatory           │  confidence                 │
│   - conflict       │                      │                             │
│                    │                      │                             │
│  PROPERTIES        │  DETECTION           │  PROVENANCE                 │
│  ──────────        │  ─────────           │  ──────────                 │
│  properties {}     │  detection_method    │  created_at                 │
│  dimensions {}     │  search_text []      │  updated_at                 │
│  materials {}      │  detection_page      │  created_by                 │
│                    │                      │                             │
└─────────────────────────────────────────────────────────────────────────┘

                              VIEWS
                              
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   LIBRARY   │    │  FEDERATED  │    │  SCHEDULE   │
    │    VIEW     │    │    VIEW     │    │    VIEW     │
    │             │    │             │    │             │
    │ WHERE       │    │ WHERE       │    │ ORDER BY    │
    │ status =    │    │ status =    │    │ phase,      │
    │ 'template'  │    │ 'placed'    │    │ sequence    │
    └─────────────┘    └─────────────┘    └─────────────┘
    
    ┌─────────────┐    ┌─────────────┐
    │   JIGSAW    │    │  OUTLINER   │
    │    VIEW     │    │    VIEW     │
    │             │    │             │
    │ WHERE       │    │ GROUP BY    │
    │ status =    │    │ discipline, │
    │ 'missing'   │    │ group       │
    └─────────────┘    └─────────────┘
```

---

## Migration Phases

### Phase 1: Add Columns (No Breaking Changes)
**Duration: 1 day**
**Risk: Zero**

Add new columns to existing structures. Everything still works.

```
EXISTING                          ADD
────────                          ───
master_reference_template.json    + ifc_class
                                  + ifc_predefined_type
                                  + discipline
                                  + group
                                  + status (default: "template")

federated_model (objects)         + slot_id
                                  + status (default: "placed")
                                  + sequence

object_library                    + status (default: "template")
                                  + phase
```

### Phase 2: Create Unified Views (Non-Destructive)
**Duration: 2 days**
**Risk: Low**

Create SQL views / Python accessors that present unified interface.
Original files still work unchanged.

```python
# unified_model.py - NEW FILE (doesn't touch existing code)

class UnifiedBuildingModel:
    """One model, multiple views."""
    
    def library_view(self):
        """Object Library = elements where status='template'"""
        return [e for e in self.elements if e.status == 'template']
    
    def federated_view(self):
        """Federated Model = elements where status='placed'"""
        return [e for e in self.elements if e.status == 'placed']
    
    def schedule_view(self):
        """4D Schedule = elements ordered by phase, sequence"""
        return sorted(self.elements, key=lambda e: (e.phase, e.sequence))
    
    def jigsaw_view(self):
        """Missing pieces = elements where status='missing'"""
        return [e for e in self.elements if e.status == 'missing']
    
    def outliner_view(self):
        """Blender Outliner = elements grouped by discipline"""
        return group_by(self.elements, ['discipline', 'group'])
```

### Phase 3: Adapter Layer (Backward Compatible)
**Duration: 3 days**
**Risk: Low**

Create adapters that read old formats, write to unified model.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ OLD: template   │     │    ADAPTER      │     │ UNIFIED MODEL   │
│     .json       │────▶│  (reads both)   │────▶│                 │
├─────────────────┤     ├─────────────────┤     │  Single source  │
│ OLD: federated  │────▶│                 │────▶│  of truth       │
│     .blend      │     │                 │     │                 │
├─────────────────┤     │                 │     │                 │
│ OLD: checklist  │────▶│                 │────▶│                 │
│     .json       │     └─────────────────┘     └─────────────────┘
└─────────────────┘
```

### Phase 4: Gradual Consolidation (Optional)
**Duration: Ongoing**
**Risk: Medium (but optional)**

Slowly migrate to single storage. Old code paths remain until deprecated.

---

## File Mapping

### What Stays

| Existing File | Status | Notes |
|---------------|--------|-------|
| `object_library/*.blend` | ✅ KEEP | Mesh source files |
| `GridTruth_*.json` | ✅ KEEP | Ground truth dimensions |
| `*_FINAL.json` | ✅ KEEP | Output format unchanged |

### What Gets Enhanced

| Existing File | Enhancement |
|---------------|-------------|
| `master_reference_template.json` | Add IFC/discipline columns |
| `federated_model.blend` | Add collection hierarchy |
| Output JSON objects | Add `ifc_class`, `discipline`, `group` |

### What Gets Created

| New File | Purpose |
|----------|---------|
| `ifc_naming_layer.json` | IFC class + discipline mapping |
| `unified_model.py` | Single accessor for all views |
| `migration_adapter.py` | Reads old → writes unified |

---

## Team Assignment

| Team Member | Current Work | Migration Task |
|-------------|--------------|----------------|
| **Extraction** | Finds objects in PDF | Add `status='placed'` to output |
| **Object Library** | Manages mesh catalog | Add `status='template'` flag |
| **Federation** | Combines models | Use unified accessor |
| **Blender Output** | Creates scene | Use `discipline/group` for collections |

**Key Message to Team:**
> "Your work is correct. We're not replacing it.
> We're revealing that you built ONE system from THREE angles.
> The migration just makes this explicit."

---

## Code Changes Summary

### Minimal Changes (Do Now)

```python
# In output generation, add these fields to each object:

obj['ifc_class'] = naming.get_ifc_class(obj['object_type'])
obj['discipline'] = naming.get_discipline(obj['object_type'])
obj['group'] = naming.get_group(obj['object_type'])
obj['status'] = 'placed'  # or 'template' for library items
```

### Medium Changes (Phase 2)

```python
# Create unified accessor

from unified_model import UnifiedBuildingModel

model = UnifiedBuildingModel()
model.load_from_template("master_reference_template.json")
model.load_from_gridtruth("GridTruth_TB-LKTN.json")
model.load_from_output("TB-LKTN_FINAL.json")

# Get any view
library = model.library_view()      # For asset browser
schedule = model.schedule_view()    # For 4D timeline
missing = model.jigsaw_view()       # For completion check
```

### Optional Changes (Phase 4)

```python
# Single unified storage (future)

model.save("TB-LKTN_unified.db")  # SQLite with all views
```

---

## Success Criteria

| Phase | Done When |
|-------|-----------|
| 1 | Output JSON has `ifc_class`, `discipline`, `group` |
| 2 | Blender Outliner shows discipline hierarchy |
| 3 | `UnifiedBuildingModel` can load all existing files |
| 4 | Single `.db` file replaces multiple JSONs (optional) |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Team confusion | Clear communication: "You built it right" |
| Breaking changes | Adapter layer preserves old formats |
| Scope creep | Phase 4 is optional, Phase 1-3 are standalone |
| Timeline pressure | Phase 1 is 1 day, delivers immediate value |

---

## Summary

```
TODAY:     3 separate files → 3 separate mental models
           (confusion, duplication, sync issues)

AFTER:     1 unified model → 5 views
           (library, federated, schedule, jigsaw, outliner)
           
BENEFIT:   Same data, many perspectives
           Change once, reflect everywhere
           Team sees the whole picture
```

The team didn't build three things. They built ONE thing, beautifully, from three angles.
This migration just connects the dots.
