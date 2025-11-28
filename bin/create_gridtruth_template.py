#!/usr/bin/env python3
"""
GridTruth.json Template Generator

Creates a template GridTruth.json for a new PDF project.
User must manually fill in dimensions by reading the PDF.

Usage:
    python create_gridtruth_template.py path/to/MyHouse.pdf

Output:
    path/to/MyHouse/GridTruth.json (template with TODOs)
"""

import json
import os
import sys
from datetime import datetime

def create_gridtruth_template(pdf_path):
    """Create GridTruth.json template for a PDF"""

    # Get PDF directory and name
    pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
    pdf_name = os.path.basename(pdf_path).replace('.pdf', '')

    # GridTruth path
    gridtruth_path = os.path.join(pdf_dir, 'GridTruth.json')

    # Check if already exists
    if os.path.exists(gridtruth_path):
        print(f"⚠️  GridTruth.json already exists at: {gridtruth_path}")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    # Template structure
    template = {
        "_source": "User-created template",
        "_note": "INSTRUCTIONS: Measure dimensions from PDF and replace TODO values below. "
                 "Grid lines are structural grid positions. Room bounds define room boundaries. "
                 "Delete this note when done.",
        "_verification_date": datetime.now().strftime("%Y-%m-%d"),
        "_building": f"{pdf_name} (TODO: Add building description)",

        "grid_horizontal": {
            "_description": "X-axis grid lines (West to East)",
            "_units": "meters",
            "_instructions": "Measure grid line positions from PDF dimension annotations",
            "A": 0.0,
            "B": "TODO: Measure from PDF",
            "C": "TODO: Measure from PDF",
            "D": "TODO: Measure from PDF",
            "E": "TODO: Measure from PDF"
        },

        "grid_vertical": {
            "_description": "Y-axis grid lines (South to North)",
            "_units": "meters",
            "_instructions": "Measure grid line positions from PDF dimension annotations",
            "1": 0.0,
            "2": "TODO: Measure from PDF",
            "3": "TODO: Measure from PDF",
            "4": "TODO: Measure from PDF",
            "5": "TODO: Measure from PDF"
        },

        "grid_spacing": {
            "_description": "Distances between adjacent grid lines (for verification)",
            "_units": "millimeters",
            "A_to_B": "TODO: e.g., 3100",
            "B_to_C": "TODO: e.g., 3700",
            "C_to_D": "TODO: e.g., 3100",
            "1_to_2": "TODO: e.g., 2300",
            "2_to_3": "TODO: e.g., 3100"
        },

        "building_parameters": {
            "wall_setback_from_grid": "TODO: typically 0.75 (750mm)",
            "_setback_note": "Distance from grid line to exterior wall face",
            "wall_thickness": "TODO: typically 0.15 (150mm brick)",
            "_thickness_note": "Standard wall thickness"
        },

        "elevations": {
            "_units": "meters (height from ground)",
            "ground": 0.0,
            "floor_finish_level": "TODO: typically 0.15",
            "window_sill_low": "TODO: typically 0.9",
            "window_sill_high": "TODO: typically 1.5",
            "door_head": "TODO: typically 2.1",
            "ceiling": "TODO: typically 3.0"
        },

        "room_bounds": {
            "_note": "Define room boundaries by grid intersection. Trace from floor plan.",
            "_instructions": "For each room, specify min/max X and Y coordinates",

            "EXAMPLE_LIVING_ROOM": {
                "grid": "A1-C3",
                "x_min": 0.0,
                "x_max": "TODO: Measure from plan",
                "y_min": 0.0,
                "y_max": "TODO: Measure from plan"
            },

            "EXAMPLE_BEDROOM": {
                "grid": "TODO: e.g., D4-E5",
                "x_min": "TODO",
                "x_max": "TODO",
                "y_min": "TODO",
                "y_max": "TODO"
            }
        },

        "building_envelope": {
            "_description": "Exterior wall dimensions (calculated from grid minus setback)",
            "_calculation": "Grid extent minus wall_setback_from_grid on all sides",
            "x_min": "TODO: Auto-calculate: grid_min + setback",
            "y_min": "TODO: Auto-calculate: grid_min + setback",
            "x_max": "TODO: Auto-calculate: grid_max - setback",
            "y_max": "TODO: Auto-calculate: grid_max - setback",
            "width": "TODO: x_max - x_min",
            "depth": "TODO: y_max - y_min",
            "area_m2": "TODO: width × depth",
            "perimeter_m": "TODO: 2 × (width + depth)"
        },

        "validation": {
            "_instructions": "Fill these after completing above sections",
            "grid_extent_x": "TODO: Maximum X grid value (e.g., E value)",
            "grid_extent_y": "TODO: Maximum Y grid value (e.g., 5 value)",
            "expected_building_type": "TODO: e.g., Single-story residential",
            "typical_dimensions": "TODO: e.g., 9m-12m width, 7m-10m depth",
            "matches_typology": "TODO: true/false after verification"
        }
    }

    # Write template
    with open(gridtruth_path, 'w') as f:
        json.dump(template, f, indent=2)

    print()
    print("=" * 80)
    print("✅ GridTruth.json template created!")
    print("=" * 80)
    print()
    print(f"Location: {gridtruth_path}")
    print()
    print("📋 NEXT STEPS:")
    print()
    print("1. Open the PDF in a PDF viewer")
    print("2. Open GridTruth.json in a text editor")
    print("3. Read dimension annotations from PDF")
    print("4. Replace all 'TODO' values with measurements")
    print("5. Trace room boundaries and update room_bounds section")
    print("6. Delete instruction fields (lines starting with '_instructions')")
    print("7. Verify dimensions add up correctly")
    print()
    print("📐 MEASUREMENT TIPS:")
    print()
    print("• Grid lines: Look for dimension annotations like '3100' or '3.1m'")
    print("• Room bounds: Trace room corners on floor plan to get x_min, x_max, y_min, y_max")
    print("• Building envelope: Subtract wall setback (750mm typical) from grid extent")
    print("• Elevations: Standard values listed, but verify from elevation drawings")
    print()
    print("⚠️  IMPORTANT: GridTruth must be ACCURATE - entire pipeline depends on it!")
    print()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_gridtruth_template.py path/to/MyHouse.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF not found: {pdf_path}")
        sys.exit(1)

    if not pdf_path.endswith('.pdf'):
        print(f"❌ Error: File must be a PDF: {pdf_path}")
        sys.exit(1)

    create_gridtruth_template(pdf_path)
