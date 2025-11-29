# Database Documentation

## Overview

The 2DtoBlender pipeline uses SQLite databases for:

1. **Ifc_Object_Library.db** - LOD300 geometry library (prefab 3D objects)
2. **\*_ANNOTATION_FROM_2D.db** - Extracted PDF primitives (per-project, generated)

---

## Ifc_Object_Library.db

### Location
```
LocalLibrary/Ifc_Object_Library.db
```

### Schema
```
db/schema/ifc_object_library.sql
```

### Tables

| Table | Purpose |
|-------|---------|
| `base_geometries` | 3D mesh data (vertices, faces, normals as BLOBs) |
| `object_catalog` | Object metadata, dimensions, IFC class mapping |

### Key Columns

#### object_catalog
| Column | Type | Description |
|--------|------|-------------|
| `object_type` | TEXT | Unique ID used in pipeline (e.g., `door_single_900_lod300`) |
| `geometry_hash` | TEXT | FK to base_geometries |
| `ifc_class` | TEXT | IFC entity type |
| `width_mm`, `depth_mm`, `height_mm` | INTEGER | Dimensions as modeled |
| `base_rotation_x/y/z` | REAL | Rotation correction (radians) |

#### base_geometries
| Column | Type | Description |
|--------|------|-------------|
| `geometry_hash` | TEXT | MD5 hash (PK) |
| `vertices` | BLOB | Packed float32 (x,y,z per vertex) |
| `faces` | BLOB | Packed uint32 (triangle indices) |
| `normals` | BLOB | Packed float32 (per-face normals) |
| `vertex_count`, `face_count` | INTEGER | Counts for BLOB parsing |

---

## Base Rotation System

### Problem
LOD300 geometry may be modeled with inconsistent orientations:
- Some objects modeled Z-up (correct)
- Some objects modeled Y-up (lying on back)
- Some objects modeled X-up (lying on side)

### Solution
The `base_rotation_x/y/z` columns store rotation corrections (in radians) applied during Blender import to orient geometry correctly.

### How It Works
1. `database_geometry_fetcher.py` queries base_rotation values
2. `blender_lod300_import.py` applies rotation to vertices BEFORE mesh creation
3. Object transform only uses Z rotation from JSON (placement orientation)

### Setting Values

**Automated (Rule 0 Compliant):**
```bash
python3 db/scripts/audit_fix_base_rotation.py LocalLibrary/Ifc_Object_Library.db --apply
```

This script:
- Analyzes vertex spans for each object
- Determines if Z is the tallest axis (correct) or not
- Sets appropriate rotation to make Z tallest

**Values:**
| Orientation | Rotation Needed | Values (radians) |
|-------------|-----------------|------------------|
| Z is tallest | None | (0, 0, 0) |
| Y is tallest | 90° X rotation | (1.5708, 0, 0) |
| X is tallest | 90° Y rotation | (0, 1.5708, 0) |

---

## Migrations

### Location
```
db/schema/migrations/
```

### Applying Migrations

```bash
# Add base_rotation columns
sqlite3 LocalLibrary/Ifc_Object_Library.db < db/schema/migrations/002_add_base_rotation.sql

# Then run audit to set values
python3 src/tools/fix_library_base_rotations.py --database LocalLibrary/Ifc_Object_Library.db
```

---

## Tools

### Database Diagnostics & Repair

#### diagnose_repair_database.py
Location: `db/scripts/diagnose_repair_database.py`

Comprehensive database diagnostic and repair tool. Detects:
- Orphaned catalog entries (no matching geometry)
- Corrupted geometry blobs (size mismatches)
- Unused geometries (no catalog references)

```bash
# Diagnose only (dry run)
python3 db/scripts/diagnose_repair_database.py LocalLibrary/Ifc_Object_Library.db

# Diagnose and repair
python3 db/scripts/diagnose_repair_database.py LocalLibrary/Ifc_Object_Library.db --repair
```

**Output:**
- Orphaned entries: Auto-removed (catalog points to non-existent geometry)
- Corrupted blobs: Reported (requires manual re-extraction)
- Unused geometries: Auto-removed (cleanup)

#### fix_corrupted_lod300.py
Location: `db/scripts/fix_corrupted_lod300.py`

Quick fix for specific LOD300 objects with wrong face_count metadata.

```bash
# Analyze
python3 db/scripts/fix_corrupted_lod300.py LocalLibrary/Ifc_Object_Library.db

# Apply fix
python3 db/scripts/fix_corrupted_lod300.py LocalLibrary/Ifc_Object_Library.db --apply
```

#### fix_missing_5_objects.py
Location: `db/scripts/fix_missing_5_objects.py`

Copies valid geometries from similar objects to fix 5 specific missing LOD300 entries.

```bash
# Dry run
python3 db/scripts/fix_missing_5_objects.py LocalLibrary/Ifc_Object_Library.db

# Apply
python3 db/scripts/fix_missing_5_objects.py LocalLibrary/Ifc_Object_Library.db --apply
```

### Base Rotation Tools

#### fix_library_base_rotations.py
Location: `src/tools/fix_library_base_rotations.py`

Analyzes geometry orientation and sets base_rotation values systematically (Rule 0 compliant).

```bash
# Dry run (show what would change)
python3 src/tools/fix_library_base_rotations.py --database LocalLibrary/Ifc_Object_Library.db --dry-run

# Apply changes
python3 src/tools/fix_library_base_rotations.py --database LocalLibrary/Ifc_Object_Library.db
```

**Or use the convenience script:**
```bash
./bin/setup_library.sh          # Apply fixes
./bin/setup_library.sh --dry-run  # Show what would change
```

---

## Binary BLOB Format

### Vertices
- Format: Little-endian float32
- Structure: `[x1, y1, z1, x2, y2, z2, ...]`
- Size: `vertex_count × 12 bytes`
- Units: meters

### Faces
- Format: Little-endian uint32
- Structure: `[v1, v2, v3, v4, v5, v6, ...]` (triangles)
- Size: `face_count × 12 bytes`
- Indices: 0-based

### Normals
- Format: Little-endian float32
- Structure: `[nx1, ny1, nz1, nx2, ny2, nz2, ...]`
- Size: `face_count × 12 bytes`
- Values: Normalized vectors

### Parsing Example (Python)
```python
import struct
import numpy as np

# Parse vertices
float_count = len(vertices_blob) // 4
floats = struct.unpack(f'<{float_count}f', vertices_blob)
vertices = np.array(floats).reshape(-1, 3)

# Parse faces
uint_count = len(faces_blob) // 4
indices = struct.unpack(f'<{uint_count}I', faces_blob)
faces = np.array(indices).reshape(-1, 3)
```

---

## Queries

### Check objects with rotation corrections
```sql
SELECT object_type, 
       ROUND(base_rotation_x * 180 / 3.14159, 1) AS rot_x_deg,
       ROUND(base_rotation_y * 180 / 3.14159, 1) AS rot_y_deg
FROM object_catalog 
WHERE base_rotation_x != 0 OR base_rotation_y != 0;
```

### Library summary
```sql
SELECT category, COUNT(*) AS count 
FROM object_catalog 
GROUP BY category 
ORDER BY count DESC;
```

### Verify geometry completeness
```sql
SELECT oc.object_type, 
       bg.vertex_count,
       bg.face_count,
       CASE WHEN bg.normals IS NULL THEN 'MISSING' ELSE 'OK' END AS normals
FROM object_catalog oc
JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash;
```

---

## Pipeline Integration

### Library Validation (GATE 4)

The complete pipeline (`bin/RUN_COMPLETE_PIPELINE.sh`) now includes **mandatory library validation** before claiming success:

```bash
🔍 GATE 4: Validating library geometry availability...
   Checking 31 unique object_types in library...
   ✅ All 31 object_types have valid geometry
```

**Validation checks:**
1. All `object_type` values from JSON exist in `object_catalog`
2. Each catalog entry has valid `geometry_hash` in `base_geometries`
3. Geometry blobs match expected sizes:
   - `LENGTH(vertices) = vertex_count × 3 × 4`
   - `LENGTH(faces) = face_count × 3 × 4`

**Failure behavior:**
- Pipeline **HARD STOPS** if any geometries missing/corrupted
- Provides diagnostic commands to fix issues
- Prevents false "100% LOD300" claims

### Comprehensive Test Integration

Library validation is also part of `src/validators/comprehensive_test.py`:

```bash
python3 src/validators/comprehensive_test.py <json_file> <database_path>
```

**Test 11: Library Geometry Validation**
- Validates all unique object_types
- Reports missing/corrupted geometries
- Outputs validation JSON for CI/CD integration

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11 | Initial schema |
| 2.0 | 2025-11-28 | Added base_rotation columns |
| 2.1 | 2025-11-29 | Added diagnostic/repair tools, pipeline GATE 4 validation |
