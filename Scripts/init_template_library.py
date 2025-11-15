#!/usr/bin/env python3
"""
Template Library Initialization Script

Creates a new template_library.db with the complete schema.

Usage:
    python3 init_template_library.py [output_path]

Example:
    python3 init_template_library.py Terminal1_Project/Templates/terminal_base_v1.0/template_library.db
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime


def create_template_library(db_path: str) -> bool:
    """
    Create a new template library database with schema.

    Args:
        db_path: Path where database should be created

    Returns:
        True if successful, False otherwise
    """

    # Ensure parent directory exists
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if database already exists
    if db_path.exists():
        response = input(f"Database already exists at {db_path}. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return False
        db_path.unlink()

    print(f"Creating template library database at: {db_path}")

    try:
        # Connect to database (creates it)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Read schema file
        schema_path = Path(__file__).parent / "create_template_library_schema.sql"

        if not schema_path.exists():
            print(f"ERROR: Schema file not found: {schema_path}")
            return False

        print("Loading schema...")
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # Execute schema
        print("Creating tables...")
        cursor.executescript(schema_sql)

        # Commit changes
        conn.commit()

        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        print(f"\n✅ Database created successfully!")
        print(f"\nTables created ({len(tables)}):")
        for table in tables:
            print(f"  - {table[0]}")

        # Show views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()

        print(f"\nViews created ({len(views)}):")
        for view in views:
            print(f"  - {view[0]}")

        # Get database size
        db_size = db_path.stat().st_size / 1024  # KB
        print(f"\nDatabase size: {db_size:.2f} KB")
        print(f"Location: {db_path.absolute()}")

        conn.close()

        return True

    except sqlite3.Error as e:
        print(f"ERROR: Database error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def verify_schema(db_path: str):
    """
    Verify database schema is correct.

    Args:
        db_path: Path to database
    """

    print(f"\nVerifying schema...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Expected tables
    expected_tables = [
        'element_templates',
        'template_parameters',
        'derivation_rules',
        'spatial_patterns',
        'code_requirements',
        'material_specifications',
        'adaptation_rules',
        'geometry_definitions',
        'validation_history',
        'usage_statistics',
        'template_relationships',
        'template_set_metadata',
        'template_categories',
        'schema_version'
    ]

    # Check each table exists
    missing_tables = []
    for table in expected_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if cursor.fetchone() is None:
            missing_tables.append(table)

    if missing_tables:
        print(f"⚠️  WARNING: Missing tables: {', '.join(missing_tables)}")
    else:
        print(f"✅ All {len(expected_tables)} core tables present")

    # Check schema version
    cursor.execute("SELECT version, applied_date FROM schema_version ORDER BY applied_date DESC LIMIT 1")
    version_info = cursor.fetchone()

    if version_info:
        print(f"✅ Schema version: {version_info[0]} (applied: {version_info[1]})")
    else:
        print("⚠️  WARNING: No schema version found")

    # Check categories
    cursor.execute("SELECT COUNT(*) FROM template_categories")
    cat_count = cursor.fetchone()[0]
    print(f"✅ Template categories: {cat_count} default categories loaded")

    conn.close()


def show_usage():
    """Show usage information."""
    print("""
Template Library Initialization Script
======================================

Creates a new template_library.db with the complete schema.

Usage:
    python3 init_template_library.py [output_path]

Arguments:
    output_path     Path where database should be created (optional)
                    Default: ./template_library.db

Examples:
    # Create in current directory
    python3 init_template_library.py

    # Create in specific location
    python3 init_template_library.py Terminal1_Project/Templates/terminal_base_v1.0/template_library.db

    # Create for new template set
    python3 init_template_library.py Terminal2_Project/Templates/singapore_standard/template_library.db
    """)


def main():
    """Main entry point."""

    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help', 'help']:
            show_usage()
            return
        db_path = sys.argv[1]
    else:
        db_path = "template_library.db"

    print("=" * 70)
    print("Template Library Database Initialization")
    print("=" * 70)
    print()

    # Create database
    success = create_template_library(db_path)

    if success:
        # Verify schema
        verify_schema(db_path)

        print("\n" + "=" * 70)
        print("✅ SUCCESS: Template library ready to use!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Run template extraction script to populate templates")
        print("2. Or manually add templates using Template Studio")
        print()
    else:
        print("\n❌ FAILED: Could not create template library")
        sys.exit(1)


if __name__ == "__main__":
    main()
