#!/usr/bin/env python3
"""
Validate Library References - Verify all object_types exist in Ifc_Object_Library.db

This script MUST be run once on the master template to confirm all library object IDs
are valid references to objects in the Ifc_Object_Library.db database.

Usage:
    python3 validate_library_references.py <template.json> <database_path>

Example:
    python3 validate_library_references.py \
        output_artifacts/TB-LKTN_HOUSE_complete_template_20251124_121310.json \
        LocalLibrary/Ifc_Object_Library.db
"""

import json
import sqlite3
import sys
from datetime import datetime


def validate_library_references(template_path, database_path):
    """
    Validate that all object_types in template exist in the library database

    Args:
        template_path: Path to template JSON file
        database_path: Path to Ifc_Object_Library.db

    Returns:
        dict: Validation results
    """
    print("=" * 80)
    print("LIBRARY REFERENCE VALIDATION")
    print("=" * 80)
    print(f"Template: {template_path}")
    print(f"Database: {database_path}")
    print()

    # Load template
    with open(template_path, 'r') as f:
        template = json.load(f)

    # Support both formats: 'objects' (placement template) and 'extraction_sequence' (master template)
    objects = template.get('objects', [])
    extraction_sequence = template.get('extraction_sequence', [])

    if extraction_sequence:
        # Master reference template format
        objects = extraction_sequence
        print(f"✅ Loaded master reference template with {len(objects)} items")
    else:
        # Placement template format
        print(f"✅ Loaded template with {len(objects)} objects")

    # Extract unique object_types
    object_types = set()
    for obj in objects:
        obj_type = obj.get('object_type')
        if obj_type:
            object_types.add(obj_type)

    print(f"✅ Found {len(object_types)} unique object_types (library IDs)")
    print()

    # Connect to database
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        print(f"✅ Connected to database: {database_path}")
    except sqlite3.Error as e:
        print(f"❌ ERROR: Cannot connect to database: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'database_path': database_path
        }

    # Query database schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"✅ Database has {len(tables)} tables")
    print()

    # Check for objects table (support both 'objects' and 'object_catalog')
    objects_table = None
    if 'objects' in tables:
        objects_table = 'objects'
    elif 'object_catalog' in tables:
        objects_table = 'object_catalog'

    if not objects_table:
        print(f"❌ ERROR: Database does not have 'objects' or 'object_catalog' table")
        print(f"Available tables: {tables}")
        conn.close()
        return {
            'status': 'error',
            'error': 'objects/object_catalog table not found',
            'available_tables': tables
        }

    # Get database schema for objects table
    cursor.execute(f"PRAGMA table_info({objects_table})")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"✅ '{objects_table}' table columns: {columns}")
    print()

    # Determine which column to use for object_type lookup
    # Common column names: object_type, ifc_type, type, name
    lookup_column = None
    for col in ['object_type', 'ifc_type', 'type', 'name']:
        if col in columns:
            lookup_column = col
            break

    if not lookup_column:
        print(f"❌ ERROR: Cannot determine object_type column in database")
        print(f"Available columns: {columns}")
        conn.close()
        return {
            'status': 'error',
            'error': 'object_type column not found',
            'available_columns': columns
        }

    print(f"✅ Using column '{lookup_column}' for object_type lookup")
    print()

    # Validate each object_type
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print()

    found = []
    missing = []
    errors = []

    for obj_type in sorted(object_types):
        try:
            # Query database for this object_type (use dynamic table name)
            query = f"SELECT COUNT(*) FROM {objects_table} WHERE {lookup_column} = ?"
            cursor.execute(query, (obj_type,))
            count = cursor.fetchone()[0]

            if count > 0:
                found.append(obj_type)
                print(f"✅ {obj_type:<60} FOUND ({count} instances)")
            else:
                missing.append(obj_type)
                print(f"❌ {obj_type:<60} MISSING")

        except sqlite3.Error as e:
            errors.append({'object_type': obj_type, 'error': str(e)})
            print(f"⚠️  {obj_type:<60} ERROR: {e}")

    conn.close()

    # Summary
    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total object_types checked: {len(object_types)}")
    print(f"✅ Found in database:       {len(found)}")
    print(f"❌ Missing from database:   {len(missing)}")
    print(f"⚠️  Errors:                 {len(errors)}")
    print()

    if missing:
        print("MISSING OBJECT_TYPES:")
        for obj_type in missing:
            print(f"  - {obj_type}")
        print()

    if errors:
        print("ERRORS:")
        for err in errors:
            print(f"  - {err['object_type']}: {err['error']}")
        print()

    # Generate validation report
    validation_report = {
        'validation_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'template_path': template_path,
        'database_path': database_path,
        'total_objects': len(objects),
        'unique_object_types': len(object_types),
        'found': len(found),
        'missing': len(missing),
        'errors': len(errors),
        'found_object_types': sorted(found),
        'missing_object_types': sorted(missing),
        'error_details': errors,
        'status': 'valid' if len(missing) == 0 and len(errors) == 0 else 'invalid',
        'lookup_column': lookup_column
    }

    # Save validation report
    report_path = template_path.replace('.json', '_library_validation.json')
    with open(report_path, 'w') as f:
        json.dump(validation_report, f, indent=2)

    print(f"📄 Validation report saved: {report_path}")
    print()

    if validation_report['status'] == 'valid':
        print("✅ VALIDATION PASSED: All object_types exist in database")
        print()
        return validation_report
    else:
        print("❌ VALIDATION FAILED: Some object_types missing from database")
        print()
        return validation_report


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 validate_library_references.py <template.json> <database_path>")
        print()
        print("Example:")
        print("  python3 validate_library_references.py \\")
        print("      output_artifacts/TB-LKTN_HOUSE_complete_template_20251124_121310.json \\")
        print("      LocalLibrary/Ifc_Object_Library.db")
        sys.exit(1)

    template_path = sys.argv[1]
    database_path = sys.argv[2]

    result = validate_library_references(template_path, database_path)

    # Exit with appropriate code
    sys.exit(0 if result['status'] == 'valid' else 1)
