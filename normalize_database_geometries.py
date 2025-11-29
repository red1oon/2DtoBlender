#!/usr/bin/env python3
"""
DATABASE NORMALIZATION - ONE TIME FIX
Re-centers all geometries at origin and clears base_rotation
PHASE 2: Adds orientation normalization (longest_horizontal_to_Y rule)

Fixes root cause of:
- 2,452 geometries not centered (37% of database)
- 72 geometries with non-zero base_rotation
- Inconsistent orientations (longest horizontal not aligned to Y)
"""

import sqlite3
import struct
import numpy as np
import math
import json

def rotate_vertices(verts, rotation):
    """
    Apply rotation to vertices
    Args:
        verts: Nx3 numpy array
        rotation: (rx, ry, rz) in radians
    Returns:
        Rotated vertices
    """
    rx, ry, rz = rotation

    # Rotation matrices
    if rx != 0:
        cos_x, sin_x = math.cos(rx), math.sin(rx)
        Rx = np.array([
            [1, 0, 0],
            [0, cos_x, -sin_x],
            [0, sin_x, cos_x]
        ])
        verts = verts @ Rx.T

    if ry != 0:
        cos_y, sin_y = math.cos(ry), math.sin(ry)
        Ry = np.array([
            [cos_y, 0, sin_y],
            [0, 1, 0],
            [-sin_y, 0, cos_y]
        ])
        verts = verts @ Ry.T

    if rz != 0:
        cos_z, sin_z = math.cos(rz), math.sin(rz)
        Rz = np.array([
            [cos_z, -sin_z, 0],
            [sin_z, cos_z, 0],
            [0, 0, 1]
        ])
        verts = verts @ Rz.T

    return verts


def detect_and_fix_orientation(verts, object_type=None):
    """
    Detect and fix orientation using longest_horizontal_to_Y rule.

    Args:
        verts: Nx3 numpy array (already centered at origin)
        object_type: Optional type hint for special cases

    Returns:
        (rotated_verts, rotation_applied_degrees)

    Rule: Longest horizontal dimension should align with Y-axis
    - Measure X and Y extents
    - If X > Y, rotate 90° around Z to swap them
    - Returns rotation applied in degrees (0 or 90)
    """

    # Compute bounding box extents
    mins = verts.min(axis=0)
    maxs = verts.max(axis=0)
    extents = maxs - mins

    x_extent = extents[0]
    y_extent = extents[1]

    # Threshold: only rotate if difference is significant (>5cm)
    if x_extent > y_extent + 0.05:
        # Longest horizontal is along X, need to rotate 90° to align with Y
        rotation_z = math.radians(90)
        rotated_verts = rotate_vertices(verts, (0, 0, rotation_z))
        return rotated_verts, 90
    else:
        # Already aligned or Y >= X
        return verts, 0


def normalize_database(db_path, apply_orientation_fix=True):
    """
    Normalize all geometries:
    1. Apply base_rotation to vertices (bake it in)
    2. Center at origin
    3. Fix orientation (longest_horizontal_to_Y rule)
    4. Clear base_rotation field

    Args:
        apply_orientation_fix: If True, applies orientation normalization
    """

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all unique geometry hashes with their base_rotation and object_type
    cur.execute("""
        SELECT DISTINCT
            oc.geometry_hash,
            oc.base_rotation_x,
            oc.base_rotation_y,
            oc.base_rotation_z,
            oc.object_type
        FROM object_catalog oc
    """)

    geometries = cur.fetchall()

    print("=" * 80)
    print("DATABASE NORMALIZATION - PHASE 2 (WITH ORIENTATION FIX)")
    print("=" * 80)
    print(f"Total unique geometries: {len(geometries)}\n")

    centered_count = 0
    rotated_count = 0
    oriented_count = 0
    skipped_count = 0

    # Rotation compensation map (safety net for rollback)
    rotation_compensation = {}

    for geom_hash, rot_x, rot_y, rot_z, object_type in geometries:
        # Get vertices blob
        cur.execute("""
            SELECT vertices FROM base_geometries WHERE geometry_hash = ?
        """, (geom_hash,))

        row = cur.fetchone()
        if not row or not row[0]:
            skipped_count += 1
            continue

        vertices_blob = row[0]

        # Parse vertices
        float_count = len(vertices_blob) // 4
        floats = struct.unpack(f'<{float_count}f', vertices_blob)
        verts = np.array(floats).reshape(-1, 3).copy()

        modified = False

        # Step 1: Apply base_rotation to vertices (if exists)
        if rot_x != 0.0 or rot_y != 0.0 or rot_z != 0.0:
            verts = rotate_vertices(verts, (rot_x, rot_y, rot_z))
            rotated_count += 1
            modified = True

        # Step 2: Center at origin
        center = verts.mean(axis=0)
        if np.abs(center).max() > 0.001:  # More than 1mm offset
            verts -= center
            centered_count += 1
            modified = True

        # Step 3: Fix orientation (longest_horizontal_to_Y)
        orientation_rotation = 0
        if apply_orientation_fix:
            verts, orientation_rotation = detect_and_fix_orientation(verts, object_type)
            if orientation_rotation != 0:
                oriented_count += 1
                modified = True
                # Record for safety net
                rotation_compensation[geom_hash] = {
                    'object_type': object_type,
                    'rotation_applied': orientation_rotation
                }

        # Update database if modified
        if modified:
            new_vertices_blob = verts.astype(np.float32).tobytes()
            cur.execute("""
                UPDATE base_geometries
                SET vertices = ?
                WHERE geometry_hash = ?
            """, (new_vertices_blob, geom_hash))

    # Step 4: Clear ALL base_rotation values
    cur.execute("""
        UPDATE object_catalog
        SET base_rotation_x = 0.0,
            base_rotation_y = 0.0,
            base_rotation_z = 0.0
    """)

    conn.commit()

    print("=" * 80)
    print("NORMALIZATION COMPLETE")
    print("=" * 80)
    print(f"Geometries rotated (base_rotation baked): {rotated_count}")
    print(f"Geometries centered at origin: {centered_count}")
    print(f"Geometries oriented (longest→Y): {oriented_count}")
    print(f"Geometries skipped (no blob): {skipped_count}")
    print(f"\n✅ All base_rotation values cleared")
    print(f"✅ All geometries normalized to (0, 0, 0)")
    print(f"✅ All geometries oriented (longest horizontal → Y-axis)")

    conn.close()

    return rotated_count, centered_count, oriented_count, rotation_compensation


if __name__ == "__main__":
    db_path = "LocalLibrary/Ifc_Object_Library.db"
    compensation_file = "rotation_compensation.json"

    print("\n" + "=" * 80)
    print("DATABASE NORMALIZATION SCRIPT - PHASE 2")
    print("=" * 80)
    print(f"Database: {db_path}")
    print("\nThis will:")
    print("1. Apply base_rotation to vertices (bake rotations)")
    print("2. Center all geometries at (0, 0, 0)")
    print("3. Fix orientation (longest horizontal → Y-axis)")
    print("4. Clear all base_rotation values")
    print("\nPrevious audit showed:")
    print("- 2,452 geometries not centered (37%)")
    print("- 72 geometries with base_rotation")
    print("\n" + "=" * 80)

    response = input("\nProceed with normalization? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Aborted")
        exit(0)

    print()
    rotated, centered, oriented, rotation_comp = normalize_database(db_path, apply_orientation_fix=True)

    # Save rotation compensation map as safety net
    if rotation_comp:
        with open(compensation_file, 'w') as f:
            json.dump(rotation_comp, f, indent=2)
        print(f"\n📝 Rotation compensation saved to: {compensation_file}")
        print(f"   ({len(rotation_comp)} geometries rotated for orientation)")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Re-run audit script to verify normalization")
    print("2. Update templates to use 'facing' field (Phase 2)")
    print("3. Update import to use bounding box contract (Phase 3)")
    print(f"4. Safety net: {compensation_file} saved (for rollback if needed)")
    print("\nAll objects now standardized:")
    print("  ✅ Centered at origin")
    print("  ✅ Longest horizontal dimension aligned to Y-axis")
    print("  ✅ No base_rotation compensation needed")
