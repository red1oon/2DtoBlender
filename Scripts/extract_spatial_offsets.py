#!/usr/bin/env python3
"""
Extract Spatial Offsets from Terminal 1 Database
=================================================

This script analyzes the FullExtractionTesellated.db (DB1) to extract typical
z-offsets (heights) for each template type (discipline + IFC class combination).

These offsets are CRITICAL for DWG → BIM conversion because:
- DWG files are 2D (everything at z=0)
- BIM models are 3D (elements at correct heights)
- Templates "remember" the heights from DB1
- When generating DB2: final_z = dwg_z + template_offset

Output:
- Updates template_library.db with z_offset parameters
- Generates OFFSET_ANALYSIS.md with findings
- Logs extraction process

Usage:
    python3 extract_spatial_offsets.py \\
        /path/to/FullExtractionTesellated.db \\
        /path/to/template_library.db
"""

import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


def analyze_spatial_offsets(db1_path: str) -> Dict[str, Dict]:
    """
    Analyze element_transforms table to calculate z-offset statistics.

    Returns dict structure:
    {
        "ARC_IfcFurniture": {
            "count": 176,
            "avg_z": 0.45,
            "min_z": 0.40,
            "max_z": 0.50,
            "std_dev": 0.02,
            "discipline": "ARC",
            "ifc_class": "IfcFurniture"
        },
        ...
    }
    """

    print(f"📊 Analyzing spatial offsets from: {db1_path}")

    conn = sqlite3.connect(db1_path)
    cursor = conn.cursor()

    # Query: Join elements_meta with elements_rtree to get discipline,
    # ifc_class, and z-coordinates from bounding boxes
    # Note: We use (minZ + maxZ) / 2 as the center height
    # Note: We'll calculate std_dev in Python for better performance
    query = """
        SELECT
            em.discipline,
            em.ifc_class,
            COUNT(*) as element_count,
            AVG((rt.minZ + rt.maxZ) / 2.0) as avg_z,
            MIN(rt.minZ) as min_z,
            MAX(rt.maxZ) as max_z
        FROM
            elements_meta em
        JOIN
            elements_rtree rt ON em.id = rt.id
        GROUP BY
            em.discipline, em.ifc_class
        ORDER BY
            em.discipline, element_count DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    # For std_dev calculation, we need to fetch all z values per group
    # This is more efficient than nested subqueries
    print("  → Calculating standard deviations...")
    std_dev_query = """
        SELECT
            em.discipline,
            em.ifc_class,
            (rt.minZ + rt.maxZ) / 2.0 as center_z
        FROM
            elements_meta em
        JOIN
            elements_rtree rt ON em.id = rt.id
        ORDER BY
            em.discipline, em.ifc_class
    """

    cursor.execute(std_dev_query)
    z_values_all = cursor.fetchall()

    # Group z-values by discipline + ifc_class
    from collections import defaultdict
    import statistics

    z_by_template = defaultdict(list)
    for discipline, ifc_class, z_val in z_values_all:
        template_name = f"{discipline}_{ifc_class}"
        z_by_template[template_name].append(z_val)

    offsets = {}

    for row in results:
        discipline, ifc_class, count, avg_z, min_z, max_z = row
        template_name = f"{discipline}_{ifc_class}"

        # Calculate standard deviation from collected z-values
        z_values = z_by_template.get(template_name, [])
        if len(z_values) > 1:
            std_dev = statistics.stdev(z_values)
        else:
            std_dev = 0.0

        offsets[template_name] = {
            "discipline": discipline,
            "ifc_class": ifc_class,
            "count": count,
            "avg_z": round(avg_z, 3) if avg_z else 0.0,
            "min_z": round(min_z, 3) if min_z else 0.0,
            "max_z": round(max_z, 3) if max_z else 0.0,
            "std_dev": round(std_dev, 3) if std_dev else 0.0,
            "z_range": round(max_z - min_z, 3) if (max_z and min_z) else 0.0
        }

        print(f"  ✓ {template_name}: avg_z={offsets[template_name]['avg_z']:.3f}m, "
              f"range={offsets[template_name]['z_range']:.3f}m, count={count}")

    conn.close()

    print(f"\n✅ Analyzed {len(offsets)} template types")
    return offsets


def update_template_library(template_db_path: str, offsets: Dict[str, Dict]):
    """
    Update template_library.db with extracted z-offset parameters.

    For each template, adds parameters:
    - z_offset (avg_z): Primary offset to use
    - z_offset_min: Minimum observed height
    - z_offset_max: Maximum observed height
    - z_offset_std_dev: Standard deviation (variability indicator)
    """

    print(f"\n📝 Updating template library: {template_db_path}")

    conn = sqlite3.connect(template_db_path)
    cursor = conn.cursor()

    # First, get all template_ids from element_templates table
    cursor.execute("SELECT template_id, template_name FROM element_templates")
    templates = cursor.fetchall()

    updated_count = 0
    missing_count = 0

    for template_id, template_name in templates:
        if template_name in offsets:
            offset_data = offsets[template_name]

            # Define parameters to insert
            parameters = [
                {
                    "param_id": f"{template_id}_z_offset",
                    "param_name": "z_offset",
                    "param_type": "float",
                    "param_category": "derived",
                    "default_value": str(offset_data["avg_z"]),
                    "unit": "meters",
                    "editable": 1,
                    "description": f"Average z-coordinate (height) from Terminal 1. "
                                   f"Extracted from {offset_data['count']} elements.",
                    "priority": 1
                },
                {
                    "param_id": f"{template_id}_z_offset_min",
                    "param_name": "z_offset_min",
                    "param_type": "float",
                    "param_category": "derived",
                    "default_value": str(offset_data["min_z"]),
                    "unit": "meters",
                    "editable": 0,
                    "description": "Minimum z-coordinate observed in Terminal 1",
                    "priority": 2
                },
                {
                    "param_id": f"{template_id}_z_offset_max",
                    "param_name": "z_offset_max",
                    "param_type": "float",
                    "param_category": "derived",
                    "default_value": str(offset_data["max_z"]),
                    "unit": "meters",
                    "editable": 0,
                    "description": "Maximum z-coordinate observed in Terminal 1",
                    "priority": 3
                },
                {
                    "param_id": f"{template_id}_z_offset_std_dev",
                    "param_name": "z_offset_std_dev",
                    "param_type": "float",
                    "param_category": "derived",
                    "default_value": str(offset_data["std_dev"]),
                    "unit": "meters",
                    "editable": 0,
                    "description": "Standard deviation of z-coordinates (height variability)",
                    "priority": 4
                },
                {
                    "param_id": f"{template_id}_z_range",
                    "param_name": "z_range",
                    "param_type": "float",
                    "param_category": "derived",
                    "default_value": str(offset_data["z_range"]),
                    "unit": "meters",
                    "editable": 0,
                    "description": f"Range of z-coordinates (max - min = {offset_data['z_range']:.3f}m)",
                    "priority": 5
                }
            ]

            # Insert parameters (or replace if they exist)
            for param in parameters:
                cursor.execute("""
                    INSERT OR REPLACE INTO template_parameters (
                        param_id, template_id, param_name, param_type, param_category,
                        default_value, unit, editable, description, priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    param["param_id"],
                    template_id,
                    param["param_name"],
                    param["param_type"],
                    param["param_category"],
                    param["default_value"],
                    param["unit"],
                    param["editable"],
                    param["description"],
                    param["priority"]
                ))

            updated_count += 1
            print(f"  ✓ {template_name}: z_offset={offset_data['avg_z']:.3f}m")
        else:
            missing_count += 1
            print(f"  ⚠ {template_name}: No spatial data found in DB1")

    conn.commit()
    conn.close()

    print(f"\n✅ Updated {updated_count} templates with spatial offsets")
    if missing_count > 0:
        print(f"⚠️  {missing_count} templates had no spatial data (may be non-geometric)")


def generate_offset_report(offsets: Dict[str, Dict], output_path: str):
    """
    Generate OFFSET_ANALYSIS.md report with findings.
    """

    print(f"\n📄 Generating offset analysis report: {output_path}")

    # Group by discipline
    by_discipline = {}
    for template_name, data in offsets.items():
        discipline = data["discipline"]
        if discipline not in by_discipline:
            by_discipline[discipline] = []
        by_discipline[discipline].append((template_name, data))

    # Sort each discipline by avg_z
    for discipline in by_discipline:
        by_discipline[discipline].sort(key=lambda x: x[1]["avg_z"])

    # Generate markdown report
    report_lines = [
        "=" * 77,
        "SPATIAL OFFSET ANALYSIS - TERMINAL 1",
        "=" * 77,
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Templates Analyzed: {len(offsets)}",
        "",
        "=" * 77,
        "OVERVIEW",
        "=" * 77,
        "",
        "This report shows the z-coordinates (heights) extracted from Terminal 1",
        "3D model. These offsets are used to convert 2D DWG files (z=0) to 3D BIM.",
        "",
        "Key Metrics:",
        "- avg_z: Average height (PRIMARY offset to use)",
        "- min_z / max_z: Range of heights observed",
        "- std_dev: Height variability (low = consistent, high = varies)",
        "- z_range: Total height span (max - min)",
        "",
    ]

    for discipline in sorted(by_discipline.keys()):
        templates = by_discipline[discipline]

        report_lines.extend([
            "=" * 77,
            f"DISCIPLINE: {discipline} ({len(templates)} templates)",
            "=" * 77,
            ""
        ])

        for template_name, data in templates:
            report_lines.extend([
                f"{template_name}",
                "-" * len(template_name),
                f"IFC Class:     {data['ifc_class']}",
                f"Element Count: {data['count']}",
                f"Average Z:     {data['avg_z']:.3f} m  ← PRIMARY OFFSET",
                f"Min Z:         {data['min_z']:.3f} m",
                f"Max Z:         {data['max_z']:.3f} m",
                f"Std Dev:       {data['std_dev']:.3f} m",
                f"Z Range:       {data['z_range']:.3f} m",
                ""
            ])

            # Add interpretation
            if data['z_range'] < 0.1:
                report_lines.append("✓ Very consistent height (all elements at same level)")
            elif data['z_range'] < 0.5:
                report_lines.append("✓ Fairly consistent height (minor variations)")
            elif data['z_range'] < 2.0:
                report_lines.append("⚠ Moderate height variation (elements span multiple levels)")
            else:
                report_lines.append("⚠ High height variation (elements distributed across building)")

            report_lines.append("")

    # Summary section
    report_lines.extend([
        "=" * 77,
        "SUMMARY BY HEIGHT",
        "=" * 77,
        "",
        "Templates sorted by average height (ground to ceiling):",
        ""
    ])

    all_templates = sorted(offsets.items(), key=lambda x: x[1]["avg_z"])

    for template_name, data in all_templates:
        report_lines.append(
            f"{data['avg_z']:6.3f}m  {template_name:40s}  ({data['count']:5d} elements)"
        )

    report_lines.extend([
        "",
        "=" * 77,
        "KEY OBSERVATIONS",
        "=" * 77,
        ""
    ])

    # Find interesting patterns
    floor_level = [t for t in all_templates if t[1]['avg_z'] < 1.0]
    mid_level = [t for t in all_templates if 1.0 <= t[1]['avg_z'] < 2.5]
    ceiling_level = [t for t in all_templates if t[1]['avg_z'] >= 2.5]

    report_lines.extend([
        f"Floor Level (< 1m):     {len(floor_level)} templates",
        f"Mid Level (1-2.5m):     {len(mid_level)} templates",
        f"Ceiling Level (> 2.5m): {len(ceiling_level)} templates",
        "",
        "Lowest Element:  " + (f"{all_templates[0][0]} at {all_templates[0][1]['avg_z']:.3f}m" if all_templates else "N/A"),
        "Highest Element: " + (f"{all_templates[-1][0]} at {all_templates[-1][1]['avg_z']:.3f}m" if all_templates else "N/A"),
        "",
        "=" * 77,
        f"END OF REPORT - {datetime.now().strftime('%Y-%m-%d')}",
        "=" * 77,
    ])

    # Write report
    with open(output_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"✅ Report generated successfully")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 extract_spatial_offsets.py <db1_path> <template_library_path>")
        print("\nExample:")
        print("  python3 extract_spatial_offsets.py \\")
        print("      /home/red1/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db \\")
        print("      Terminal1_Project/Templates/terminal_base_v1.0/template_library.db")
        sys.exit(1)

    db1_path = sys.argv[1]
    template_db_path = sys.argv[2]

    # Validate paths
    if not Path(db1_path).exists():
        print(f"❌ Error: DB1 not found: {db1_path}")
        sys.exit(1)

    if not Path(template_db_path).exists():
        print(f"❌ Error: Template library not found: {template_db_path}")
        sys.exit(1)

    print("=" * 77)
    print("SPATIAL OFFSET EXTRACTION")
    print("=" * 77)
    print(f"Source DB1:       {db1_path}")
    print(f"Template Library: {template_db_path}")
    print(f"Started:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 77)
    print()

    # Step 1: Analyze offsets from DB1
    offsets = analyze_spatial_offsets(db1_path)

    # Step 2: Update template library
    update_template_library(template_db_path, offsets)

    # Step 3: Generate report
    report_path = Path(template_db_path).parent / "OFFSET_ANALYSIS.md"
    generate_offset_report(offsets, str(report_path))

    print("\n" + "=" * 77)
    print("✅ SPATIAL OFFSET EXTRACTION COMPLETE")
    print("=" * 77)
    print(f"\nNext steps:")
    print(f"1. Review report: {report_path}")
    print(f"2. Check updated template library: {template_db_path}")
    print(f"3. Proceed to DWG → DXF conversion (Priority 2)")
    print()


if __name__ == "__main__":
    main()
