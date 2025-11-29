#!/usr/bin/env python3
"""
Database Diagnostic and Repair Tool

Diagnoses and optionally repairs Ifc_Object_Library.db issues:
  - Orphaned catalog entries (no matching geometry)
  - Corrupted geometry blobs (size mismatches)
  - Missing geometry hashes

Usage:
    python3 diagnose_repair_database.py <database_path> [--repair]

Examples:
    # Diagnose only
    python3 diagnose_repair_database.py LocalLibrary/Ifc_Object_Library.db

    # Diagnose and repair
    python3 diagnose_repair_database.py LocalLibrary/Ifc_Object_Library.db --repair
"""

import sqlite3
import sys
from pathlib import Path


def diagnose_database(db_path):
    """
    Run comprehensive database diagnostics

    Returns:
        dict: Diagnostic results
    """
    print("=" * 80)
    print("DATABASE DIAGNOSTICS")
    print("=" * 80)
    print(f"Database: {db_path}\n")

    if not Path(db_path).exists():
        print(f"❌ ERROR: Database not found: {db_path}")
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    results = {}

    # Check table counts
    print("TABLE COUNTS:")
    cursor.execute("SELECT COUNT(*) FROM object_catalog")
    catalog_count = cursor.fetchone()[0]
    print(f"  object_catalog: {catalog_count} entries")

    cursor.execute("SELECT COUNT(*) FROM base_geometries")
    geometry_count = cursor.fetchone()[0]
    print(f"  base_geometries: {geometry_count} entries")

    results['catalog_count'] = catalog_count
    results['geometry_count'] = geometry_count

    # Find orphaned catalog entries
    print("\nORPHANED CATALOG ENTRIES:")
    cursor.execute('''
        SELECT oc.object_type, oc.geometry_hash
        FROM object_catalog oc
        LEFT JOIN base_geometries bg ON oc.geometry_hash = bg.geometry_hash
        WHERE bg.geometry_hash IS NULL
    ''')
    orphaned = cursor.fetchall()

    if orphaned:
        print(f"  ❌ Found {len(orphaned)} orphaned entries (catalog points to non-existent geometry)")
        for obj_type, hash in orphaned[:5]:
            print(f"     - {obj_type} → {hash[:16]}...")
        if len(orphaned) > 5:
            print(f"     ... and {len(orphaned) - 5} more")
    else:
        print(f"  ✅ No orphaned entries")

    results['orphaned'] = orphaned

    # Find corrupted geometry blobs
    print("\nCORRUPTED GEOMETRY BLOBS:")
    cursor.execute('''
        SELECT
            geometry_hash,
            vertex_count,
            face_count,
            LENGTH(vertices) as v_size,
            LENGTH(faces) as f_size,
            LENGTH(normals) as n_size
        FROM base_geometries
        WHERE
            LENGTH(vertices) != vertex_count * 3 * 4
            OR LENGTH(faces) != face_count * 3 * 4
    ''')
    corrupted = cursor.fetchall()

    if corrupted:
        print(f"  ❌ Found {len(corrupted)} corrupted geometry blobs (size mismatch)")
        for hash, v_count, f_count, v_size, f_size, n_size in corrupted[:5]:
            expected_v = v_count * 3 * 4
            expected_f = f_count * 3 * 4
            print(f"     - {hash[:16]}...")
            print(f"       vertices: {v_size}/{expected_v} bytes")
            print(f"       faces: {f_size}/{expected_f} bytes")
        if len(corrupted) > 5:
            print(f"     ... and {len(corrupted) - 5} more")
    else:
        print(f"  ✅ No corrupted blobs")

    results['corrupted'] = corrupted

    # Find unused geometries
    print("\nUNUSED GEOMETRIES:")
    cursor.execute('''
        SELECT bg.geometry_hash
        FROM base_geometries bg
        LEFT JOIN object_catalog oc ON bg.geometry_hash = oc.geometry_hash
        WHERE oc.geometry_hash IS NULL
    ''')
    unused = cursor.fetchall()

    if unused:
        print(f"  ⚠️  Found {len(unused)} unused geometries (no catalog entry references them)")
    else:
        print(f"  ✅ All geometries are referenced")

    results['unused'] = unused

    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"  Total catalog entries: {catalog_count}")
    print(f"  Total geometries: {geometry_count}")
    print(f"  Orphaned entries: {len(orphaned)}")
    print(f"  Corrupted blobs: {len(corrupted)}")
    print(f"  Unused geometries: {len(unused)}")
    print()

    conn.close()
    return results


def repair_database(db_path, results, dry_run=False):
    """
    Repair database issues

    Args:
        db_path: Path to database
        results: Diagnostic results
        dry_run: If True, only show what would be done
    """
    print("=" * 80)
    print("DATABASE REPAIR" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 80)

    if dry_run:
        print("ℹ️  Showing what would be repaired (use --repair to apply changes)\n")
    else:
        print("⚠️  APPLYING REPAIRS - Database will be modified!\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    repairs_made = 0

    # Remove orphaned catalog entries
    orphaned = results.get('orphaned', [])
    if orphaned:
        print(f"REMOVING ORPHANED CATALOG ENTRIES: {len(orphaned)}")
        for obj_type, hash in orphaned[:3]:
            print(f"  Would remove: {obj_type}")
        if len(orphaned) > 3:
            print(f"  ... and {len(orphaned) - 3} more")

        if not dry_run:
            for obj_type, hash in orphaned:
                cursor.execute("DELETE FROM object_catalog WHERE object_type = ? AND geometry_hash = ?",
                             (obj_type, hash))
            conn.commit()
            print(f"  ✅ Removed {len(orphaned)} orphaned entries")
            repairs_made += len(orphaned)
        print()

    # Mark corrupted geometries (can't auto-fix, need re-extraction)
    corrupted = results.get('corrupted', [])
    if corrupted:
        print(f"CORRUPTED GEOMETRIES: {len(corrupted)}")
        print("  ⚠️  Cannot auto-repair corrupted blobs - requires re-extraction from source IFC")
        print("  Affected object_types:")

        corrupted_hashes = [c[0] for c in corrupted]
        for hash in corrupted_hashes[:5]:
            cursor.execute("SELECT object_type FROM object_catalog WHERE geometry_hash = ?", (hash,))
            obj_types = cursor.fetchall()
            for (obj_type,) in obj_types:
                print(f"     - {obj_type}")
        if len(corrupted_hashes) > 5:
            print(f"     ... and {len(corrupted_hashes) - 5} more")
        print()

    # Remove unused geometries (cleanup)
    unused = results.get('unused', [])
    if unused:
        print(f"REMOVING UNUSED GEOMETRIES: {len(unused)}")
        if not dry_run:
            for (hash,) in unused:
                cursor.execute("DELETE FROM base_geometries WHERE geometry_hash = ?", (hash,))
            conn.commit()
            print(f"  ✅ Removed {len(unused)} unused geometries")
            repairs_made += len(unused)
        else:
            print(f"  Would remove {len(unused)} unused geometries")
        print()

    conn.close()

    # Summary
    print("=" * 80)
    if dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print(f"Run with --repair to apply {repairs_made} changes")
    else:
        print(f"REPAIR COMPLETE - {repairs_made} changes applied")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    db_path = sys.argv[1]
    apply_repair = "--repair" in sys.argv

    # Diagnose
    results = diagnose_database(db_path)

    if results is None:
        sys.exit(1)

    # Repair if requested
    if apply_repair:
        print()
        repair_database(db_path, results, dry_run=False)
    else:
        print()
        repair_database(db_path, results, dry_run=True)
        print("\nTo apply repairs, run with --repair flag")
