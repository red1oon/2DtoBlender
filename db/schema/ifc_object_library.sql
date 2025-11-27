-- ============================================================================
-- Ifc_Object_Library.db Schema
-- ============================================================================
-- LOD300 Geometry Library for 2DtoBlender Pipeline
-- 
-- Version: 2.0 (2025-11-28)
-- Changes: Added base_rotation columns for geometry orientation correction
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table: base_geometries
-- ----------------------------------------------------------------------------
-- Stores 3D geometry data (vertices, faces, normals) for LOD300 objects.
-- Geometry is stored once and referenced by hash for deduplication.

CREATE TABLE IF NOT EXISTS base_geometries (
    geometry_hash TEXT PRIMARY KEY,
    -- MD5 hash of geometry (vertices + faces) for deduplication

    vertices BLOB NOT NULL,
    -- Vertex coordinates (packed binary float32: x1,y1,z1, x2,y2,z2, ...)

    faces BLOB NOT NULL,
    -- Face indices (packed binary uint32: v1,v2,v3, v4,v5,v6, ...) - triangles

    normals BLOB,
    -- Normal vectors (packed binary float32: nx1,ny1,nz1, nx2,ny2,nz2, ...)
    -- Optional: Blender can auto-calculate if NULL

    vertex_count INTEGER NOT NULL,
    face_count INTEGER NOT NULL,

    -- Bounding Box (calculated from vertices)
    bbox_width REAL,   -- X span in meters
    bbox_depth REAL,   -- Y span in meters  
    bbox_height REAL,  -- Z span in meters

    -- Metrics (optional)
    volume_m3 REAL,
    surface_area_m2 REAL,

    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- Table: object_catalog
-- ----------------------------------------------------------------------------
-- Links geometry to IFC classes, dimensions, and categorization.
-- Each object_type maps to one geometry via geometry_hash.

CREATE TABLE IF NOT EXISTS object_catalog (
    catalog_id INTEGER PRIMARY KEY AUTOINCREMENT,

    geometry_hash TEXT NOT NULL,
    -- Foreign key to base_geometries table

    ifc_class TEXT NOT NULL,
    -- IFC entity type: "IfcDoor", "IfcWindow", "IfcFurnishingElement", etc.

    object_type TEXT NOT NULL UNIQUE,
    -- Unique identifier used in pipeline: "door_single_900_lod300"

    object_name TEXT,
    -- Human-readable name: "Single Door 900mm"

    category TEXT NOT NULL,
    -- Category: "door", "window", "furniture", "mep", "structure"

    sub_category TEXT,
    -- Sub-category: "single_leaf", "sliding", "casement", etc.

    -- Dimensions (in millimeters, as modeled)
    width_mm INTEGER,
    depth_mm INTEGER,
    height_mm INTEGER,

    -- Base Rotation Correction (radians)
    -- Applied to vertices during Blender import to correct modeling orientation
    -- Most geometry should be (0, 0, 0) if modeled correctly (Z-up)
    base_rotation_x REAL DEFAULT 0.0,  -- Rotation around X axis
    base_rotation_y REAL DEFAULT 0.0,  -- Rotation around Y axis
    base_rotation_z REAL DEFAULT 0.0,  -- Rotation around Z axis

    description TEXT,

    -- Source Tracking
    source_file TEXT,
    -- Original file this geometry was extracted from

    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    construction_type TEXT DEFAULT 'universal',
    -- Construction type: "universal", "timber", "steel", "concrete", "masonry"

    FOREIGN KEY (geometry_hash) REFERENCES base_geometries(geometry_hash)
);


-- ----------------------------------------------------------------------------
-- Indexes
-- ----------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_object_type ON object_catalog(object_type);
CREATE INDEX IF NOT EXISTS idx_ifc_class ON object_catalog(ifc_class);
CREATE INDEX IF NOT EXISTS idx_category ON object_catalog(category);
CREATE INDEX IF NOT EXISTS idx_dimensions ON object_catalog(width_mm, depth_mm, height_mm);
CREATE INDEX IF NOT EXISTS idx_geometry_hash ON object_catalog(geometry_hash);


-- ----------------------------------------------------------------------------
-- Views
-- ----------------------------------------------------------------------------

-- View: Objects needing rotation correction
CREATE VIEW IF NOT EXISTS v_objects_with_rotation AS
SELECT 
    object_type,
    object_name,
    category,
    ROUND(base_rotation_x * 180 / 3.14159, 1) AS rot_x_degrees,
    ROUND(base_rotation_y * 180 / 3.14159, 1) AS rot_y_degrees,
    ROUND(base_rotation_z * 180 / 3.14159, 1) AS rot_z_degrees
FROM object_catalog
WHERE base_rotation_x != 0 OR base_rotation_y != 0 OR base_rotation_z != 0;


-- View: Library summary by category
CREATE VIEW IF NOT EXISTS v_library_summary AS
SELECT 
    category,
    COUNT(*) AS object_count,
    COUNT(DISTINCT geometry_hash) AS unique_geometries
FROM object_catalog
GROUP BY category
ORDER BY object_count DESC;


-- ============================================================================
-- Binary Blob Format Reference
-- ============================================================================
--
-- VERTICES (float32 little-endian):
--   Each vertex = 12 bytes (3 × 4-byte floats)
--   Total size = vertex_count × 12 bytes
--   Format: [x1, y1, z1, x2, y2, z2, ...]
--   Units: meters
--
-- FACES (uint32 little-endian):
--   Each face = 12 bytes (3 × 4-byte uints) - triangles only
--   Total size = face_count × 12 bytes
--   Format: [v1, v2, v3, v4, v5, v6, ...] - vertex indices (0-based)
--
-- NORMALS (float32 little-endian):
--   Each normal = 12 bytes (3 × 4-byte floats)
--   Total size = face_count × 12 bytes (one normal per face)
--   Format: [nx1, ny1, nz1, nx2, ny2, nz2, ...]
--   Units: normalized vectors
--
-- ============================================================================
