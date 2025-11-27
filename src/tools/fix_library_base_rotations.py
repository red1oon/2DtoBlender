#!/usr/bin/env python3
"""
Systematic Base Rotation Fixer for LOD300/LOD200 Library

RULE 0 COMPLIANCE:
- Analyzes ALL geometry in database programmatically
- Determines required base_rotation based on geometry orientation
- Updates database systematically (not manual per-object fixes)
- Idempotent: can be re-run safely anytime

PRINCIPLE:
Objects should be modeled Z-up (tallest axis = Z).
If geometry is flat (X or Y tallest), apply base_rotation to fix at import time.

USAGE:
    python3 tools/fix_library_base_rotations.py [--dry-run] [--database PATH]

OUTPUTS:
    - Audit report of all objects
    - SQL updates for base_rotation
    - Summary statistics
"""

import sqlite3
import struct
import numpy as np
import argparse
import sys
from pathlib import Path


def analyze_geometry(verts_blob):
    """
    Analyze geometry orientation.

    Returns:
        dict: {
            'x_span': float,
            'y_span': float,
            'z_span': float,
            'tallest_axis': str,  # 'X', 'Y', or 'Z'
            'needs_rotation': bool,
            'suggested_rotation': tuple  # (rx, ry, rz) in radians
        }
    """
    # Parse vertices
    n_floats = len(verts_blob) // 4
    floats = struct.unpack(f'<{n_floats}f', verts_blob)
    verts = np.array(floats).reshape(-1, 3)

    # Calculate spans
    x_span = verts[:,0].max() - verts[:,0].min()
    y_span = verts[:,1].max() - verts[:,1].min()
    z_span = verts[:,2].max() - verts[:,2].min()

    # Determine tallest axis
    spans = {'X': x_span, 'Y': y_span, 'Z': z_span}
    tallest_axis = max(spans, key=spans.get)
    tallest_value = spans[tallest_axis]

    # Check if needs rotation
    # Object is considered "upright" if Z is tallest or within 20% of tallest
    upright = (tallest_axis == 'Z' or z_span > tallest_value * 0.8)

    # Determine required rotation
    if upright:
        suggested = (0.0, 0.0, 0.0)
    elif tallest_axis == 'Y':
        # Lying on back (Y is up) → rotate 90° around X-axis
        suggested = (1.5708, 0.0, 0.0)  # π/2 radians
    elif tallest_axis == 'X':
        # Lying on side (X is up) → rotate 90° around Y-axis
        suggested = (0.0, 1.5708, 0.0)
    else:
        suggested = (0.0, 0.0, 0.0)

    return {
        'x_span': x_span,
        'y_span': y_span,
        'z_span': z_span,
        'tallest_axis': tallest_axis,
        'needs_rotation': not upright,
        'suggested_rotation': suggested
    }


def audit_database(db_path, dry_run=False):
    """
    Audit entire database and fix base_rotations.

    Args:
        db_path: Path to Ifc_Object_Library.db
        dry_run: If True, only report without updating

    Returns:
        dict: Statistics
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all LOD300/LOD200 objects with geometry
    cur.execute("""
        SELECT oc.object_type,
               oc.base_rotation_x, oc.base_rotation_y, oc.base_rotation_z,
               bg.vertices
        FROM object_catalog oc
        JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
        WHERE oc.object_type LIKE '%lod300%' OR oc.object_type LIKE '%lod200%'
        ORDER BY oc.object_type
    """)

    results = cur.fetchall()

    stats = {
        'total': 0,
        'upright': 0,
        'needs_x_rotation': 0,
        'needs_y_rotation': 0,
        'already_correct': 0,
        'will_update': 0
    }

    updates_needed = []

    print("=" * 80)
    print("SYSTEMATIC BASE ROTATION AUDIT")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'UPDATE MODE'}")
    print(f"Total objects: {len(results)}")
    print()

    for obj_type, cur_rx, cur_ry, cur_rz, verts_blob in results:
        stats['total'] += 1

        try:
            analysis = analyze_geometry(verts_blob)
            suggested_rx, suggested_ry, suggested_rz = analysis['suggested_rotation']

            # Check if current rotation matches suggested
            current_matches = (
                abs(cur_rx - suggested_rx) < 0.01 and
                abs(cur_ry - suggested_ry) < 0.01 and
                abs(cur_rz - suggested_rz) < 0.01
            )

            if not analysis['needs_rotation']:
                stats['upright'] += 1
                if current_matches:
                    stats['already_correct'] += 1
            else:
                if suggested_rx != 0:
                    stats['needs_x_rotation'] += 1
                if suggested_ry != 0:
                    stats['needs_y_rotation'] += 1

                if not current_matches:
                    stats['will_update'] += 1
                    updates_needed.append({
                        'object_type': obj_type,
                        'current': (cur_rx, cur_ry, cur_rz),
                        'suggested': (suggested_rx, suggested_ry, suggested_rz),
                        'analysis': analysis
                    })
                else:
                    stats['already_correct'] += 1

        except Exception as e:
            print(f"⚠️  Error analyzing {obj_type}: {e}")

    # Report objects needing updates
    if updates_needed:
        print("\n❌ OBJECTS NEEDING BASE_ROTATION UPDATE:")
        print("-" * 80)
        for item in updates_needed:
            obj = item['object_type']
            cur = item['current']
            sug = item['suggested']
            ana = item['analysis']

            print(f"  {obj}")
            print(f"    Geometry: X={ana['x_span']:.3f}, Y={ana['y_span']:.3f}, Z={ana['z_span']:.3f}")
            print(f"    Tallest axis: {ana['tallest_axis']}")
            print(f"    Current:   ({cur[0]:.4f}, {cur[1]:.4f}, {cur[2]:.4f})")
            print(f"    Suggested: ({sug[0]:.4f}, {sug[1]:.4f}, {sug[2]:.4f})")
            print()

    # Apply updates if not dry run
    if not dry_run and updates_needed:
        print(f"\n🔧 APPLYING {len(updates_needed)} UPDATES...")
        for item in updates_needed:
            obj_type = item['object_type']
            rx, ry, rz = item['suggested']

            cur.execute("""
                UPDATE object_catalog
                SET base_rotation_x = ?, base_rotation_y = ?, base_rotation_z = ?
                WHERE object_type = ?
            """, (rx, ry, rz, obj_type))

        conn.commit()
        print(f"✅ Updated {len(updates_needed)} objects")
    elif dry_run and updates_needed:
        print(f"\n💡 DRY RUN: Would update {len(updates_needed)} objects")
        print("    Run without --dry-run to apply changes")

    conn.close()

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("-" * 80)
    print(f"  Total objects:           {stats['total']}")
    print(f"  ✅ Already upright:      {stats['upright']}")
    print(f"  ✅ Already correct:      {stats['already_correct']}")
    print(f"  🔧 Need X-rotation:      {stats['needs_x_rotation']}")
    print(f"  🔧 Need Y-rotation:      {stats['needs_y_rotation']}")
    if not dry_run:
        print(f"  ✅ Updated:              {stats['will_update']}")
    else:
        print(f"  💡 Would update:         {stats['will_update']}")
    print("=" * 80)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Systematically analyze and fix base_rotation for all LOD geometry"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Analyze only, don't update database"
    )
    parser.add_argument(
        '--database',
        default='LocalLibrary/Ifc_Object_Library.db',
        help="Path to database (default: LocalLibrary/Ifc_Object_Library.db)"
    )

    args = parser.parse_args()

    # Check database exists
    db_path = Path(args.database)
    if not db_path.exists():
        print(f"❌ Error: Database not found: {db_path}")
        sys.exit(1)

    # Run audit
    try:
        stats = audit_database(db_path, dry_run=args.dry_run)

        if args.dry_run:
            print("\n💡 This was a dry run. Run without --dry-run to apply changes.")
            return 0
        else:
            print("\n✅ Database updated successfully!")
            return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
