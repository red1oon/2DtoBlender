#!/usr/bin/env python3
"""
Populate context_dimensions table from extracted building dimensions

Reads TB-LKTN HOUSE_BUILDING_DIMENSIONS.json and persists to database
"""

import json
import sqlite3
from pathlib import Path


def populate_context_dimensions(db_path: str, dimensions_json_path: str):
    """
    Populate context_dimensions table from dimension extraction output

    Args:
        db_path: Path to annotation database
        dimensions_json_path: Path to building dimensions JSON
    """
    # Load dimensions
    with open(dimensions_json_path, 'r') as f:
        dims = json.load(f)

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert dimensions
    dimensions_to_insert = [
        ('building_width', dims['building_width'], 'm', dims['method']),
        ('building_length', dims['building_length'], 'm', dims['method']),
        ('grid_spacing_horizontal', dims['grid_spacing_horizontal'], 'pt', dims['method']),
        ('grid_spacing_vertical', dims['grid_spacing_vertical'], 'pt', dims['method']),
        ('scale_factor_meters_per_grid', dims['scale_factor_meters_per_grid'], 'm/grid', dims['method']),
        ('building_height', 3.0, 'm', 'default_residential'),  # Default until elevation extraction works
    ]

    print(f"📐 Populating context_dimensions table...")
    print(f"   Database: {Path(db_path).name}")

    for dim_name, value, unit, source in dimensions_to_insert:
        cursor.execute("""
            INSERT OR REPLACE INTO context_dimensions
            (dimension_name, value, unit, source)
            VALUES (?, ?, ?, ?)
        """, (dim_name, value, unit, source))
        print(f"   ✅ {dim_name}: {value} {unit} (source: {source})")

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM context_dimensions")
    count = cursor.fetchone()[0]

    print(f"\n✅ Populated {count} dimensions to context_dimensions table")

    conn.close()


def main():
    """Main execution"""
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "output_artifacts" / "TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"
    dimensions_json = base_dir / "output_artifacts" / "TB-LKTN HOUSE_BUILDING_DIMENSIONS.json"

    if not dimensions_json.exists():
        print(f"❌ Dimensions file not found: {dimensions_json}")
        return

    populate_context_dimensions(str(db_path), str(dimensions_json))


if __name__ == "__main__":
    main()
