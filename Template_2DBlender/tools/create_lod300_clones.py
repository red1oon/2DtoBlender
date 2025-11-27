#!/usr/bin/env python3
"""
Create LOD300 clones of base objects by duplicating catalog entries.

Strategy:
- Keep same geometry (same geometry_hash)
- Create new catalog entry with _lod300 suffix
- Preserves all dimensions and metadata
"""

import sqlite3
from pathlib import Path

# Objects to clone
OBJECTS_TO_CLONE = [
    'nightstand',
    'dresser_6drawer',
    'armchair',
    'bookshelf_5tier',
    'toilet_paper_holder',
    'towel_rack_wall',
    'bathroom_vanity_1000',
    'office_chair_ergonomic',
    'dining_chair',
    'table_study',
    'floor_drain',
    'refrigerator_residential_lod200',
    'stove_residential_lod200',
]

def create_lod300_clones(db_path: Path):
    """Clone base objects as LOD300 variants"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 80)
    print("CREATING LOD300 CLONES")
    print("=" * 80)
    print()

    created = []
    skipped = []
    errors = []

    for base_name in OBJECTS_TO_CLONE:
        # Determine LOD300 name
        if base_name.endswith('_lod200'):
            lod300_name = base_name.replace('_lod200', '_lod300')
        else:
            lod300_name = f"{base_name}_lod300"

        # Check if LOD300 already exists
        cursor.execute("SELECT COUNT(*) FROM object_catalog WHERE object_type = ?", (lod300_name,))
        if cursor.fetchone()[0] > 0:
            skipped.append(f"{lod300_name} (already exists)")
            continue

        # Get base object data
        cursor.execute("""
            SELECT geometry_hash, ifc_class, object_name, category, sub_category,
                   width_mm, depth_mm, height_mm, description, construction_type
            FROM object_catalog
            WHERE object_type = ?
            LIMIT 1
        """, (base_name,))

        row = cursor.fetchone()
        if not row:
            errors.append(f"{base_name} (not found in catalog)")
            continue

        (geometry_hash, ifc_class, object_name, category, sub_category,
         width_mm, depth_mm, height_mm, description, construction_type) = row

        # Create LOD300 clone
        try:
            cursor.execute("""
                INSERT INTO object_catalog
                (geometry_hash, ifc_class, object_type, object_name, category, sub_category,
                 width_mm, depth_mm, height_mm, description, construction_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                geometry_hash,
                ifc_class,
                lod300_name,
                object_name,  # Keep same object_name (display name)
                category,
                sub_category,
                width_mm,
                depth_mm,
                height_mm,
                f"{description} (LOD300 variant)" if description else "LOD300 variant",
                construction_type
            ))

            created.append(f"{base_name} → {lod300_name}")

        except sqlite3.Error as e:
            errors.append(f"{base_name} (SQL error: {e})")

    conn.commit()
    conn.close()

    # Report
    print(f"✅ Created: {len(created)} LOD300 objects")
    for item in created:
        print(f"   ✓ {item}")

    if skipped:
        print(f"\n⏭️  Skipped: {len(skipped)} (already exist)")
        for item in skipped:
            print(f"   - {item}")

    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for item in errors:
            print(f"   ✗ {item}")

    print()
    print("=" * 80)
    print(f"SUMMARY: {len(created)} created, {len(skipped)} skipped, {len(errors)} errors")
    print("=" * 80)


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "LocalLibrary/Ifc_Object_Library.db"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        exit(1)

    create_lod300_clones(db_path)
