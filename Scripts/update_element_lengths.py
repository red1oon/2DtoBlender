#!/usr/bin/env python3
"""
Update element_transforms.length from elements_meta.dimensions JSON
Applies validation to filter out corrupt/invalid dimension data.
"""

import sys
import sqlite3
import json
from pathlib import Path


def validate_dimension(value, min_val=0.05, max_val=20.0):
    """Validate and clamp dimension to reasonable range."""
    if value is None or value <= 0:
        return None

    # Filter extreme outliers (corrupt data)
    if value < 0.001:  # Less than 1mm
        return None
    if value > 100:  # Greater than 100m
        return None

    # Clamp to reasonable range
    if value < min_val:
        value = min_val
    if value > max_val:
        value = max_val

    return value


def get_primary_dimension(dimensions_json, ifc_class):
    """Extract primary dimension from JSON with validation."""
    if not dimensions_json:
        return 1.0

    try:
        dims = json.loads(dimensions_json)
    except:
        return 1.0

    # For columns, prefer diameter
    if ifc_class == "IfcColumn":
        value = dims.get('diameter') or dims.get('length') or dims.get('width')
        validated = validate_dimension(value, min_val=0.2, max_val=3.0)
        return validated if validated else 1.0

    # For walls, prefer length
    elif ifc_class == "IfcWall":
        value = dims.get('length')
        validated = validate_dimension(value, min_val=0.1, max_val=50.0)
        return validated if validated else 1.0

    # For doors/windows
    elif ifc_class in ("IfcDoor", "IfcWindow"):
        value = dims.get('width') or dims.get('length')
        validated = validate_dimension(value, min_val=0.3, max_val=5.0)
        return validated if validated else 1.0

    # For equipment/proxy
    elif ifc_class == "IfcBuildingElementProxy":
        value = dims.get('length') or dims.get('width') or dims.get('diameter')
        validated = validate_dimension(value, min_val=0.05, max_val=10.0)
        return validated if validated else 1.0

    # Default: prefer length
    value = dims.get('length') or dims.get('width') or dims.get('diameter')
    validated = validate_dimension(value, min_val=0.05, max_val=20.0)
    return validated if validated else 1.0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 update_element_lengths.py <database_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)

    print("="*70)
    print("UPDATING ELEMENT_TRANSFORMS.LENGTH FROM DIMENSIONS JSON")
    print("="*70)
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all elements with dimensions
    cursor.execute("""
        SELECT em.guid, em.ifc_class, em.dimensions
        FROM elements_meta em
        WHERE em.guid IN (SELECT guid FROM element_transforms)
    """)

    elements = cursor.fetchall()
    print(f"Found {len(elements)} elements to process\n")

    stats = {
        'total': len(elements),
        'updated': 0,
        'no_change': 0,
        'validated': 0,
        'by_class': {}
    }

    # Update each element
    for guid, ifc_class, dimensions_json in elements:
        if ifc_class not in stats['by_class']:
            stats['by_class'][ifc_class] = {'updated': 0, 'validated': 0}

        # Extract and validate primary dimension
        new_length = get_primary_dimension(dimensions_json, ifc_class)

        # Get current length
        cursor.execute("SELECT length FROM element_transforms WHERE guid = ?", (guid,))
        row = cursor.fetchone()
        current_length = row[0] if row else 1.0

        # Update if different
        if abs(new_length - current_length) > 0.001:
            cursor.execute("""
                UPDATE element_transforms
                SET length = ?
                WHERE guid = ?
            """, (new_length, guid))
            stats['updated'] += 1
            stats['by_class'][ifc_class]['updated'] += 1

            # Track if validation changed value
            if dimensions_json:
                try:
                    dims = json.loads(dimensions_json)
                    original_value = dims.get('length') or dims.get('diameter') or dims.get('width')
                    if original_value and abs(new_length - original_value) > 0.001:
                        stats['validated'] += 1
                        stats['by_class'][ifc_class]['validated'] += 1
                except:
                    pass
        else:
            stats['no_change'] += 1

    conn.commit()

    # Print statistics
    print("="*70)
    print("UPDATE COMPLETE")
    print("="*70)
    print(f"Total elements:     {stats['total']}")
    print(f"Updated:            {stats['updated']}")
    print(f"No change:          {stats['no_change']}")
    print(f"Validated/fixed:    {stats['validated']}\n")

    print("By IFC Class:")
    for ifc_class, class_stats in sorted(stats['by_class'].items(), key=lambda x: -x[1]['updated']):
        if class_stats['updated'] > 0:
            validated_str = f" ({class_stats['validated']} validated)" if class_stats['validated'] > 0 else ""
            print(f"  {ifc_class:30} {class_stats['updated']:5} updated{validated_str}")

    # Verify with queries
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70)

    cursor.execute("""
        SELECT ifc_class,
               COUNT(*) as count,
               ROUND(MIN(length), 3) as min_len,
               ROUND(MAX(length), 3) as max_len,
               ROUND(AVG(length), 3) as avg_len
        FROM element_transforms et
        JOIN elements_meta em ON et.guid = em.guid
        WHERE ifc_class IN ('IfcColumn', 'IfcBuildingElementProxy', 'IfcWall', 'IfcDoor')
        GROUP BY ifc_class
        ORDER BY ifc_class
    """)

    print(f"\n{'IFC Class':<30} {'Count':>6} {'Min':>8} {'Max':>8} {'Avg':>8}")
    print("-"*70)
    for row in cursor.fetchall():
        print(f"{row[0]:<30} {row[1]:>6} {row[2]:>8.3f} {row[3]:>8.3f} {row[4]:>8.3f}")

    # Check for near-zero or extreme values
    cursor.execute("""
        SELECT COUNT(*)
        FROM element_transforms
        WHERE length < 0.01 OR length > 50
    """)
    outliers = cursor.fetchone()[0]

    if outliers > 0:
        print(f"\n⚠️  Warning: {outliers} elements with extreme dimensions (< 0.01m or > 50m)")
    else:
        print(f"\n✅ No extreme dimension outliers detected")

    conn.close()

    print("\n" + "="*70)
    print("✅ SUCCESS: Element lengths updated with validation")
    print("="*70)


if __name__ == "__main__":
    main()
