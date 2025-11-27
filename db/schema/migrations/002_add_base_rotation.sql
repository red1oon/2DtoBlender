-- Migration: Add base_rotation columns to object_catalog
-- Date: 2025-11-28
-- Purpose: Store geometry orientation fixes for Rule 0 compliance
--
-- Context:
-- Some LOD300 geometries in library are oriented incorrectly (e.g., doors lying flat).
-- base_rotation stores the correction needed to orient geometry upright in Blender.
-- This is applied programmatically during mesh creation.

ALTER TABLE object_catalog ADD COLUMN base_rotation_x REAL DEFAULT 0.0;
ALTER TABLE object_catalog ADD COLUMN base_rotation_y REAL DEFAULT 0.0;
ALTER TABLE object_catalog ADD COLUMN base_rotation_z REAL DEFAULT 0.0;

-- Update index to include rotation columns
CREATE INDEX IF NOT EXISTS idx_object_rotation
ON object_catalog(object_type, base_rotation_x, base_rotation_y, base_rotation_z);

-- Verify migration
SELECT COUNT(*) as objects_with_rotation
FROM object_catalog
WHERE base_rotation_x != 0.0 OR base_rotation_y != 0.0 OR base_rotation_z != 0.0;
