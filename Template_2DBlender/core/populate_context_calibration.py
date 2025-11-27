#!/usr/bin/env python3
"""
Populate context_calibration table from grid-based calibration

Uses grid spacing from context_dimensions to establish coordinate transform
"""

import sqlite3
from pathlib import Path


def populate_context_calibration(db_path: str):
    """
    Populate context_calibration table using grid-based method

    Derives scale and offset from grid spacing and building dimensions
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"📏 Populating context_calibration table...")
    print(f"   Database: {Path(db_path).name}")

    # Get dimensions from context_dimensions table
    cursor.execute("""
        SELECT dimension_name, value
        FROM context_dimensions
        WHERE dimension_name IN (
            'grid_spacing_horizontal',
            'grid_spacing_vertical',
            'building_width',
            'building_length'
        )
    """)

    dims = {row[0]: row[1] for row in cursor.fetchall()}

    # Calculate scale factors (meters per PDF point)
    # Grid spacing in PDF points, building dimensions in meters
    # Assuming 4 grids horizontally for 8m width: scale = 8.0 / (4 * 96.83)
    scale_x = dims['building_width'] / (4 * dims['grid_spacing_horizontal'])
    scale_y = dims['building_length'] / (6 * dims['grid_spacing_vertical'])

    # Offset to origin (will be refined by actual drain perimeter detection)
    offset_x = 0.0
    offset_y = 0.0

    # Calibration data to insert
    calibrations = [
        ('scale_x', scale_x, 0.70, 'grid_based_estimate'),
        ('scale_y', scale_y, 0.70, 'grid_based_estimate'),
        ('offset_x', offset_x, 0.50, 'default_origin'),
        ('offset_y', offset_y, 0.50, 'default_origin'),
    ]

    for key, value, confidence, source in calibrations:
        cursor.execute("""
            INSERT OR REPLACE INTO context_calibration
            (key, value, confidence, source)
            VALUES (?, ?, ?, ?)
        """, (key, value, confidence, source))
        print(f"   ✅ {key}: {value:.6f} (confidence: {confidence}, source: {source})")

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM context_calibration")
    count = cursor.fetchone()[0]

    print(f"\n✅ Populated {count} calibration parameters")
    print(f"   Note: Grid-based calibration (confidence: 0.70)")
    print(f"   TODO: Implement drain perimeter detection for higher confidence")

    conn.close()


def main():
    """Main execution"""
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "output_artifacts" / "TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"

    populate_context_calibration(str(db_path))


if __name__ == "__main__":
    main()
