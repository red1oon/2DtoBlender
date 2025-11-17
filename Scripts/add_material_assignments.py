#!/usr/bin/env python3
"""
Add Material Assignments for Discipline Color Coding
====================================================

Adds material_assignments table and populates with discipline-based colors
to enable visual distinction in Blender viewport.

Usage:
    python3 add_material_assignments.py Terminal1_MainBuilding_FILTERED.db

Color Scheme:
- ARC (Architecture): Light blue-gray (0.7, 0.75, 0.85, 1.0)
- STR (Structure): Medium gray (0.6, 0.6, 0.6, 1.0)
- FP (Fire Protection): Red (1.0, 0.2, 0.2, 1.0)
- ELEC (Electrical): Yellow (1.0, 0.8, 0.0, 1.0)
- Default: White (0.9, 0.9, 0.9, 1.0)
"""

import sys
import sqlite3
from pathlib import Path

# Discipline color mapping (RGBA values)
# Maps standardized discipline codes to colors
DISCIPLINE_COLORS = {
    # Standard short codes (2025-11-17: Standardized)
    'ARC': '0.7,0.75,0.85,1.0',     # Light blue-gray (Architecture)
    'STR': '0.6,0.6,0.6,1.0',       # Medium gray (Structure)
    'FP': '1.0,0.2,0.2,1.0',        # Red (Fire Protection)
    'ELEC': '1.0,0.8,0.0,1.0',      # Yellow (Electrical)
    'ACMV': '0.0,0.6,1.0,1.0',      # Blue (HVAC)
    'SP': '0.2,0.8,0.2,1.0',        # Green (Sanitary/Plumbing)
    'CW': '0.0,0.8,0.8,1.0',        # Cyan (Chilled Water)
    'REB': '0.8,0.4,0.0,1.0',       # Orange (Reinforcement)
}

DEFAULT_COLOR = '0.9,0.9,0.9,1.0'  # White

def create_material_assignments_table(conn):
    """Create material_assignments table if it doesn't exist."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS material_assignments (
            guid TEXT NOT NULL,
            material_name TEXT,
            rgba TEXT,
            FOREIGN KEY (guid) REFERENCES elements_meta(guid)
        )
    """)

    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_material_assignments_guid
        ON material_assignments(guid)
    """)

    conn.commit()
    print("✓ Created material_assignments table")

def populate_material_assignments(conn):
    """Populate material assignments based on discipline."""
    cursor = conn.cursor()

    # Get all elements with their disciplines
    cursor.execute("""
        SELECT guid, discipline, ifc_class
        FROM elements_meta
        ORDER BY discipline, ifc_class
    """)
    elements = cursor.fetchall()

    print(f"Found {len(elements)} elements to assign materials")

    stats = {
        'total': len(elements),
        'by_discipline': {},
    }

    # Assign materials
    for guid, discipline, ifc_class in elements:
        # Get color for discipline
        rgba = DISCIPLINE_COLORS.get(discipline, DEFAULT_COLOR)

        # Material name: "{Discipline}_{IFCClass}"
        material_name = f"{discipline}_{ifc_class}" if discipline else ifc_class

        # Insert material assignment
        cursor.execute("""
            INSERT OR REPLACE INTO material_assignments (guid, material_name, rgba)
            VALUES (?, ?, ?)
        """, (guid, material_name, rgba))

        # Track statistics
        if discipline not in stats['by_discipline']:
            stats['by_discipline'][discipline] = 0
        stats['by_discipline'][discipline] += 1

    conn.commit()

    # Print statistics
    print(f"\n✓ Assigned materials to {stats['total']} elements")
    print("\nBreakdown by discipline:")
    for disc, count in sorted(stats['by_discipline'].items(), key=lambda x: -x[1]):
        color_name = get_color_name(disc)
        print(f"  {disc:8s}: {count:4d} elements ({color_name})")

    return stats

def get_color_name(discipline):
    """Get human-readable color name for discipline."""
    color_names = {
        'ARC': 'Light Blue-Gray (Architecture)',
        'STR': 'Medium Gray (Structure)',
        'FP': 'Red (Fire Protection)',
        'ELEC': 'Yellow (Electrical)',
        'ACMV': 'Blue (HVAC)',
        'SP': 'Green (Sanitary/Plumbing)',
        'CW': 'Cyan (Chilled Water)',
        'REB': 'Orange (Reinforcement)',
    }
    return color_names.get(discipline, 'White (Default)')

def verify_assignments(conn):
    """Verify material assignments were created correctly."""
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM material_assignments")
    count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT rgba) as unique_colors
        FROM material_assignments
    """)
    unique_colors = cursor.fetchone()[0]

    print(f"\n✓ Verification:")
    print(f"  Total assignments: {count}")
    print(f"  Unique colors: {unique_colors}")

    # Sample a few entries
    cursor.execute("""
        SELECT em.ifc_class, em.discipline, ma.material_name, ma.rgba
        FROM material_assignments ma
        JOIN elements_meta em ON ma.guid = em.guid
        LIMIT 5
    """)

    print(f"\n  Sample assignments:")
    for ifc_class, discipline, mat_name, rgba in cursor.fetchall():
        print(f"    {ifc_class:25s} ({discipline:4s}) -> {mat_name:30s} RGBA({rgba})")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 add_material_assignments.py <database_file>")
        print("Example: python3 add_material_assignments.py Terminal1_MainBuilding_FILTERED.db")
        sys.exit(1)

    db_path = Path(sys.argv[1])

    if not db_path.exists():
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)

    print(f"Adding material assignments to: {db_path}")
    print(f"Database size: {db_path.stat().st_size / 1024 / 1024:.2f} MB\n")

    # Connect to database
    conn = sqlite3.connect(str(db_path))

    try:
        # Create table
        create_material_assignments_table(conn)

        # Populate assignments
        populate_material_assignments(conn)

        # Verify
        verify_assignments(conn)

        print(f"\n✅ SUCCESS: Material assignments added to {db_path.name}")
        print("\nNext steps:")
        print("  1. Load database in Blender (Full Load mode)")
        print("  2. Verify discipline colors appear correctly")
        print("  3. ARC = Light Blue, STR = Gray, FP = Red, ELEC = Yellow")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
