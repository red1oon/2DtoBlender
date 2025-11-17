#!/usr/bin/env python3
"""
Test Complete Placement Workflow: Generate → Insert to Database

Demonstrates end-to-end integration:
1. Generate code-compliant placements using PlacementGenerator
2. Insert into database using insert_generated_elements_to_db()
3. Verify elements appear in database
"""

import sys
import sqlite3
from pathlib import Path

# Import our placement framework
from code_compliance import PlacementGenerator, get_placement_standards

def test_placement_to_db(db_path: str):
    """
    Test complete workflow: generate sprinklers → insert to DB → verify.

    Args:
        db_path: Path to existing database (will add generated elements)
    """
    print("\n" + "="*80)
    print("TEST: PLACEMENT GENERATION → DATABASE INSERTION")
    print("="*80)

    # Get building bounds from existing database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # First check if there are any elements
    cursor.execute("SELECT COUNT(*) FROM element_transforms")
    element_count = cursor.fetchone()[0]

    if element_count == 0:
        print("❌ ERROR: No existing elements in database")
        conn.close()
        return False

    print(f"\nExisting elements in database: {element_count}")

    cursor.execute("""
        SELECT MIN(center_x), MAX(center_x), MIN(center_y), MAX(center_y)
        FROM element_transforms
        WHERE center_x IS NOT NULL AND center_y IS NOT NULL
    """)
    result = cursor.fetchone()
    conn.close()

    if not result or any(x is None for x in result):
        print("❌ ERROR: Unable to get building bounds (NULL coordinates)")
        return False

    min_x, max_x, min_y, max_y = result

    print(f"\nBuilding Bounds (from existing elements):")
    print(f"  X: {min_x:.1f} to {max_x:.1f} ({max_x - min_x:.1f}m)")
    print(f"  Y: {min_y:.1f} to {max_y:.1f} ({max_y - min_y:.1f}m)")

    # Define a test room (subset of building)
    room_bounds = {
        'min_x': min_x,
        'max_x': min(min_x + 20.0, max_x),  # 20m wide
        'min_y': min_y,
        'max_y': min(min_y + 15.0, max_y),  # 15m long
    }

    print(f"\nTest Room:")
    print(f"  X: {room_bounds['min_x']:.1f} to {room_bounds['max_x']:.1f}")
    print(f"  Y: {room_bounds['min_y']:.1f} to {room_bounds['max_y']:.1f}")

    # STEP 1: Generate sprinkler placements
    print("\n" + "="*80)
    print("STEP 1: GENERATE SPRINKLER PLACEMENTS")
    print("="*80)

    placements = PlacementGenerator.generate_grid_placement(
        room_bounds=room_bounds,
        element_type='sprinkler',
        discipline='FP',
        z_height=4.0
    )

    print(f"✅ Generated {len(placements)} sprinkler positions")
    print(f"   Sample positions:")
    for i, (x, y, z) in enumerate(placements[:5]):
        print(f"   [{i+1}] ({x:.2f}, {y:.2f}, {z:.2f})")

    # STEP 2: Insert into database
    print("\n" + "="*80)
    print("STEP 2: INSERT INTO DATABASE")
    print("="*80)

    inserted = PlacementGenerator.insert_generated_elements_to_db(
        db_path=db_path,
        placements=placements,
        element_type='sprinkler',
        discipline='FP',
        element_name='Generated_Sprinkler'
    )

    # STEP 3: Verify in database
    print("\n" + "="*80)
    print("STEP 3: VERIFY IN DATABASE")
    print("="*80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count generated sprinklers
    cursor.execute("""
        SELECT COUNT(*) FROM elements_meta
        WHERE element_name = 'Generated_Sprinkler' AND discipline = 'FP'
    """)
    count = cursor.fetchone()[0]

    print(f"Database verification:")
    print(f"  Generated sprinklers in elements_meta: {count}")

    # Check a sample position
    cursor.execute("""
        SELECT em.guid, et.center_x, et.center_y, et.center_z
        FROM elements_meta em
        JOIN element_transforms et ON em.guid = et.guid
        WHERE em.element_name = 'Generated_Sprinkler'
        LIMIT 5
    """)

    print(f"\n  Sample entries from database:")
    for row in cursor.fetchall():
        guid, x, y, z = row
        print(f"    GUID: {guid[:13]}... Position: ({x:.2f}, {y:.2f}, {z:.2f})")

    # Check spatial index
    cursor.execute("""
        SELECT COUNT(*) FROM elements_rtree r
        JOIN element_transforms et ON r.id = et.rowid
        JOIN elements_meta em ON et.guid = em.guid
        WHERE em.element_name = 'Generated_Sprinkler'
    """)
    rtree_count = cursor.fetchone()[0]

    print(f"\n  Entries in spatial index (elements_rtree): {rtree_count}")

    conn.close()

    # STEP 4: Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    success = (count == len(placements) == inserted == rtree_count)

    if success:
        print(f"✅ SUCCESS: Complete workflow verified!")
        print(f"   - Generated: {len(placements)} placements")
        print(f"   - Inserted: {inserted} to database")
        print(f"   - Verified: {count} in elements_meta")
        print(f"   - Indexed: {rtree_count} in spatial index")
        print(f"\n✅ All counts match - integration complete!")
    else:
        print(f"⚠️  WARNING: Count mismatch detected")
        print(f"   - Generated: {len(placements)}")
        print(f"   - Inserted: {inserted}")
        print(f"   - Verified: {count}")
        print(f"   - Indexed: {rtree_count}")

    print("="*80 + "\n")

    return success


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_placement_to_db.py <database.db>")
        print("\nExample:")
        print("  python3 test_placement_to_db.py Terminal1_MainBuilding_FILTERED.db")
        sys.exit(1)

    db_path = sys.argv[1]

    if not Path(db_path).exists():
        print(f"❌ ERROR: Database not found: {db_path}")
        sys.exit(1)

    # Run test
    success = test_placement_to_db(db_path)

    sys.exit(0 if success else 1)
