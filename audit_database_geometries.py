#!/usr/bin/env python3
"""
Full Database Geometry Audit
Checks ALL geometries for centering and rotation issues
"""

import sqlite3
import struct
import numpy as np

def audit_database(db_path):
    """Audit all geometries for centering and base_rotation issues"""

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all object types with their geometry and base_rotation
    cur.execute("""
        SELECT DISTINCT
            oc.object_type,
            oc.geometry_hash,
            oc.base_rotation_x,
            oc.base_rotation_y,
            oc.base_rotation_z
        FROM object_catalog oc
        ORDER BY oc.object_type
    """)

    object_types = cur.fetchall()

    print("=" * 80)
    print("DATABASE GEOMETRY AUDIT - FULL SCAN")
    print("=" * 80)
    print(f"Total object types: {len(object_types)}\n")

    centering_issues = []
    rotation_issues = []

    for obj_type, geom_hash, rot_x, rot_y, rot_z in object_types:
        # Get vertices blob
        cur.execute("""
            SELECT vertices FROM base_geometries WHERE geometry_hash = ?
        """, (geom_hash,))

        row = cur.fetchone()
        if not row:
            print(f"⚠️  {obj_type}: No geometry found for hash {geom_hash}")
            continue

        vertices_blob = row[0]

        # Parse vertices
        float_count = len(vertices_blob) // 4
        floats = struct.unpack(f'<{float_count}f', vertices_blob)
        verts = np.array(floats).reshape(-1, 3)

        # Check centering
        center = verts.mean(axis=0)
        offset_magnitude = np.linalg.norm(center)

        if offset_magnitude > 0.01:  # More than 1cm offset
            centering_issues.append({
                'type': obj_type,
                'center': center,
                'magnitude': offset_magnitude
            })

        # Check base_rotation
        if rot_x != 0.0 or rot_y != 0.0 or rot_z != 0.0:
            rotation_issues.append({
                'type': obj_type,
                'rotation': (rot_x, rot_y, rot_z),
                'degrees': (
                    np.degrees(rot_x) if rot_x else 0,
                    np.degrees(rot_y) if rot_y else 0,
                    np.degrees(rot_z) if rot_z else 0
                )
            })

    # Report centering issues
    print("\n" + "=" * 80)
    print(f"CENTERING ISSUES: {len(centering_issues)} objects NOT centered at origin")
    print("=" * 80)

    if centering_issues:
        centering_issues.sort(key=lambda x: x['magnitude'], reverse=True)
        for issue in centering_issues:
            center = issue['center']
            print(f"❌ {issue['type']}")
            print(f"   Center: [{center[0]:8.3f}, {center[1]:8.3f}, {center[2]:8.3f}]")
            print(f"   Offset: {issue['magnitude']:.3f}m")
    else:
        print("✅ All geometries centered at origin")

    # Report rotation issues
    print("\n" + "=" * 80)
    print(f"ROTATION ISSUES: {len(rotation_issues)} objects with non-zero base_rotation")
    print("=" * 80)

    if rotation_issues:
        # Group by rotation type
        x_rotations = [r for r in rotation_issues if r['rotation'][0] != 0]
        y_rotations = [r for r in rotation_issues if r['rotation'][1] != 0]
        z_rotations = [r for r in rotation_issues if r['rotation'][2] != 0]

        if x_rotations:
            print(f"\n❌ X-AXIS ROTATIONS ({len(x_rotations)} objects):")
            for issue in x_rotations:
                deg = issue['degrees']
                print(f"   {issue['type']}: ({deg[0]:.0f}°, {deg[1]:.0f}°, {deg[2]:.0f}°)")

        if y_rotations:
            print(f"\n❌ Y-AXIS ROTATIONS ({len(y_rotations)} objects):")
            for issue in y_rotations:
                deg = issue['degrees']
                print(f"   {issue['type']}: ({deg[0]:.0f}°, {deg[1]:.0f}°, {deg[2]:.0f}°)")

        if z_rotations:
            print(f"\n❌ Z-AXIS ROTATIONS ({len(z_rotations)} objects):")
            for issue in z_rotations:
                deg = issue['degrees']
                print(f"   {issue['type']}: ({deg[0]:.0f}°, {deg[1]:.0f}°, {deg[2]:.0f}°)")
    else:
        print("✅ All geometries have zero base_rotation")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total object types audited: {len(object_types)}")
    print(f"Centering issues: {len(centering_issues)}")
    print(f"Rotation issues: {len(rotation_issues)}")
    print(f"Clean geometries: {len(object_types) - len(centering_issues) - len(rotation_issues)}")

    conn.close()

    return centering_issues, rotation_issues


if __name__ == "__main__":
    db_path = "LocalLibrary/Ifc_Object_Library.db"

    centering_issues, rotation_issues = audit_database(db_path)

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)
