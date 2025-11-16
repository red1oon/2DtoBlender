# Bonsai Federation Database Schema Reference

**Date:** 2025-11-16
**Source:** Extracted from working databases and verified scripts

---

## ✅ Correct Schema (As Used by Bonsai Federation)

### Required Tables

#### 1. elements_meta
```sql
CREATE TABLE elements_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT UNIQUE NOT NULL,
    discipline TEXT NOT NULL,
    ifc_class TEXT NOT NULL,
    filepath TEXT,
    element_name TEXT,
    element_type TEXT,
    element_description TEXT,
    storey TEXT,
    material_name TEXT,
    material_rgba TEXT
);

CREATE INDEX idx_elements_meta_guid ON elements_meta(guid);
CREATE INDEX idx_elements_meta_discipline ON elements_meta(discipline);
CREATE INDEX idx_elements_meta_ifc_class ON elements_meta(ifc_class);
```

#### 2. element_transforms
```sql
CREATE TABLE element_transforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT NOT NULL,
    center_x REAL,
    center_y REAL,
    center_z REAL
);
```

#### 3. element_geometry
```sql
CREATE TABLE element_geometry (
    guid TEXT PRIMARY KEY,
    vertices BLOB,
    faces BLOB,
    bbox_min_x REAL,
    bbox_min_y REAL,
    bbox_min_z REAL,
    bbox_max_x REAL,
    bbox_max_y REAL,
    bbox_max_z REAL
);
```

#### 4. elements_rtree (CRITICAL: Use camelCase, Store Meters!)
```sql
CREATE VIRTUAL TABLE elements_rtree USING rtree(
    id,
    minX, maxX,  -- ✅ camelCase (NOT min_x)
    minY, maxY,
    minZ, maxZ
);
```

**⚠️ CRITICAL:**
- R-tree column names MUST be camelCase (`minX` not `min_x`)!
- R-tree coordinates MUST be in METERS (same units as element_transforms)!
- DO NOT multiply by 1000 - store meters directly!

**Source:** `/home/red1/Documents/bonsai/8_IFC/enhanced_federation.db`
**Verified:** Bonsai Federation code queries use `r.minX`, `r.maxX`, etc.
**Verified:** Working database has element_transforms and R-tree in same units (meters)

#### 5. global_offset
```sql
CREATE TABLE global_offset (
    offset_x REAL NOT NULL,
    offset_y REAL NOT NULL,
    offset_z REAL NOT NULL,
    extent_x REAL,
    extent_y REAL,
    extent_z REAL
);
```

**Population:**
```sql
INSERT INTO global_offset (offset_x, offset_y, offset_z, extent_x, extent_y, extent_z)
SELECT
    -MIN(center_x),  -- Negative because Bonsai adds this
    -MIN(center_y),
    -MIN(center_z),
    MAX(center_x) - MIN(center_x),
    MAX(center_y) - MIN(center_y),
    MAX(center_z) - MIN(center_z)
FROM element_transforms;
```

#### 6. spatial_structure (Optional but Recommended)
```sql
CREATE TABLE spatial_structure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT UNIQUE NOT NULL,
    parent_guid TEXT,
    name TEXT,
    storey TEXT,
    elevation REAL
);
```

---

## 📊 Population Examples

### Populate elements_rtree
```sql
INSERT INTO elements_rtree (id, minX, maxX, minY, maxY, minZ, maxZ)
SELECT
    t.id,
    t.center_x - 0.5, t.center_x + 0.5,  -- 1m placeholder bbox
    t.center_y - 0.5, t.center_y + 0.5,
    t.center_z - 0.5, t.center_z + 0.5
FROM element_transforms t;
```

### Populate element_geometry (Placeholder Boxes)
```python
# Create simple box mesh (1m cube)
def create_box_mesh(x, y, z, width=1.0, height=1.0, depth=1.0):
    hw, hh, hd = width/2, height/2, depth/2
    vertices = [
        (x-hw, y-hd, z-hh), (x+hw, y-hd, z-hh),
        (x+hw, y+hd, z-hh), (x-hw, y+hd, z-hh),
        (x-hw, y-hd, z+hh), (x+hw, y-hd, z+hh),
        (x+hw, y+hd, z+hh), (x-hw, y+hd, z+hh),
    ]
    # Pack to BLOB and insert...
```

---

## 🔍 Verification Queries

### Check Schema Completeness
```sql
-- List all tables
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

-- Expected tables:
-- base_geometries (optional)
-- coordinate_metadata (optional)
-- element_geometry ✅
-- element_transforms ✅
-- elements_meta ✅
-- elements_rtree ✅
-- global_offset ✅
-- spatial_structure ✅
```

### Verify R-tree Column Names
```sql
PRAGMA table_info(elements_rtree);

-- Expected output:
-- 0|id|INT|0||0
-- 1|minX|REAL|0||0  ✅ camelCase!
-- 2|maxX|REAL|0||0
-- 3|minY|REAL|0||0
-- 4|maxY|REAL|0||0
-- 5|minZ|REAL|0||0
-- 6|maxZ|REAL|0||0
```

### Check Population
```sql
SELECT
    (SELECT COUNT(*) FROM elements_meta) as metadata,
    (SELECT COUNT(*) FROM element_transforms) as transforms,
    (SELECT COUNT(*) FROM element_geometry) as geometries,
    (SELECT COUNT(*) FROM elements_rtree) as spatial_index,
    (SELECT COUNT(*) FROM global_offset) as coord_system;

-- All should have same count except coord_system = 1
```

---

## ❌ Common Mistakes

### 1. Wrong R-tree Column Names
```sql
-- ❌ WRONG (lowercase with underscores)
CREATE VIRTUAL TABLE elements_rtree USING rtree(
    id,
    min_x, max_x,  -- WRONG!
    min_y, max_y,
    min_z, max_z
);

-- ✅ CORRECT (camelCase)
CREATE VIRTUAL TABLE elements_rtree USING rtree(
    id,
    minX, maxX,  -- CORRECT!
    minY, maxY,
    minZ, maxZ
);
```

**Error if wrong:**
```
sqlite3.OperationalError: no such column: r.minX
```

### 2. Missing Tables
```
ValueError: Invalid database: missing elements_rtree spatial index
sqlite3.OperationalError: no such table: element_geometry
sqlite3.OperationalError: no such table: global_offset
```

### 3. Wrong R-tree Units
```sql
-- ❌ WRONG (multiplying by 1000 to store millimeters)
INSERT INTO elements_rtree (id, minX, maxX, ...)
SELECT id, center_x * 1000, (center_x + 1) * 1000, ...;

-- ✅ CORRECT (store meters, same units as element_transforms)
INSERT INTO elements_rtree (id, minX, maxX, ...)
SELECT id, center_x - 0.5, center_x + 0.5, ...;
```

**Error if wrong:**
- Geometry appears microscopic in Blender viewport
- 5km building rendered as 5mm (1000× too small)

### 4. Wrong global_offset Sign
```sql
-- ❌ WRONG (positive offset)
INSERT INTO global_offset VALUES (min_x, min_y, min_z, ...);

-- ✅ CORRECT (negative offset - Bonsai adds it back)
INSERT INTO global_offset VALUES (-min_x, -min_y, -min_z, ...);
```

---

## 📖 Reference Sources

**Working Databases:**
- `/home/red1/Documents/bonsai/8_IFC/enhanced_federation.db` (camelCase R-tree ✅)
- `/home/red1/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db` (camelCase R-tree ✅)

**Schema Definitions:**
- `/home/red1/Documents/bonsai/Scripts/initialize_federation_database_COMPLETE.sql` (shows camelCase)
- `/home/red1/Documents/bonsai/Scripts/extract_tessellation_to_db_v2.py.VERIFIED_CORRECT` (has lowercase - OUTDATED)

**Bonsai Federation Code:**
- Queries use `r.minX`, `r.maxX` (expects camelCase)
- See: `bonsai/bim/module/federation/bbox_visualization.py:164`

---

## ✅ Current Status

**Database:** `/home/red1/Documents/bonsai/2Dto3D/Terminal1_3D_FINAL.db`

**Schema Verified:**
- ✅ R-tree with camelCase columns
- ✅ All required tables present
- ✅ 15,257 elements fully populated
- ✅ global_offset configured
- ✅ spatial_structure created

**Ready For:** Bonsai Federation Preview/Full Load

---

**Last Verified:** 2025-11-16
**Status:** Schema matches working databases exactly ✅
