#!/usr/bin/env python3
"""
Template Set Metadata Creator and Validator

Creates and validates metadata.json files for template sets.

Usage:
    python3 create_template_metadata.py create [template_dir] [--interactive]
    python3 create_template_metadata.py validate [template_dir]

Examples:
    # Interactive creation
    python3 create_template_metadata.py create Terminal1_Project/Templates/terminal_base_v1.0/ --interactive

    # Validate existing metadata
    python3 create_template_metadata.py validate Terminal1_Project/Templates/terminal_base_v1.0/
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


METADATA_SCHEMA = {
    "required_fields": [
        "template_set_name",
        "version",
        "created_date",
        "author",
        "description"
    ],
    "optional_fields": [
        "source",
        "statistics",
        "validation",
        "compatibility",
        "changelog",
        "notes"
    ]
}


def count_templates_in_db(db_path: Path) -> Dict:
    """
    Count templates by category in database.

    Args:
        db_path: Path to template_library.db

    Returns:
        Dictionary with statistics
    """

    if not db_path.exists():
        return {"total_templates": 0, "by_category": {}}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Total templates
    cursor.execute("SELECT COUNT(*) FROM element_templates WHERE status='active'")
    total = cursor.fetchone()[0]

    # By category
    cursor.execute("""
        SELECT category, COUNT(*)
        FROM element_templates
        WHERE status='active'
        GROUP BY category
        ORDER BY category
    """)

    by_category = {}
    for row in cursor.fetchall():
        by_category[row[0]] = row[1]

    conn.close()

    return {
        "total_templates": total,
        "by_category": by_category
    }


def create_metadata_interactive(template_dir: Path) -> Dict:
    """
    Interactively create metadata.json

    Args:
        template_dir: Template set directory

    Returns:
        Metadata dictionary
    """

    print("\n" + "=" * 70)
    print("Interactive Template Set Metadata Creation")
    print("=" * 70)
    print()

    metadata = {}

    # Basic information
    print("Basic Information:")
    print("-" * 70)

    default_name = template_dir.name
    metadata["template_set_name"] = input(f"Template set name [{default_name}]: ") or default_name

    default_version = "1.0.0"
    metadata["version"] = input(f"Version [{default_version}]: ") or default_version

    metadata["created_date"] = datetime.now().strftime("%Y-%m-%d")
    print(f"Created date: {metadata['created_date']}")

    metadata["author"] = input("Author: ") or "BIM Team"

    metadata["description"] = input("Description: ") or "Template set for BIM generation"

    # Source information
    print("\nSource Information (optional, press Enter to skip):")
    print("-" * 70)

    extracted_from = input("Extracted from project: ")
    if extracted_from:
        metadata["source"] = {
            "extracted_from": extracted_from,
            "reference_database": input("Reference database path: ") or "",
            "extraction_date": input(f"Extraction date [{metadata['created_date']}]: ") or metadata['created_date']
        }

    # Statistics (auto-detect from database)
    db_path = template_dir / "template_library.db"
    if db_path.exists():
        print("\nStatistics (auto-detected from database):")
        print("-" * 70)

        stats = count_templates_in_db(db_path)
        metadata["statistics"] = stats

        print(f"Total templates: {stats['total_templates']}")
        if stats['by_category']:
            print("By category:")
            for cat, count in stats['by_category'].items():
                print(f"  - {cat}: {count}")
    else:
        print("\n⚠️  No database found, skipping statistics")

    # Validation info
    print("\nValidation Information (optional):")
    print("-" * 70)

    tested_on = input("Tested on project: ")
    if tested_on:
        metadata["validation"] = {
            "tested_on": tested_on,
            "accuracy": {
                "element_count": input("Element count accuracy (e.g., 94.7%): ") or "N/A",
                "spatial_position": input("Spatial position delta (e.g., 0.18m avg): ") or "N/A",
                "property_match": input("Property match (e.g., 96.2%): ") or "N/A"
            },
            "test_date": datetime.now().strftime("%Y-%m-%d")
        }

    # Compatibility
    print("\nCompatibility:")
    print("-" * 70)

    metadata["compatibility"] = {
        "bonsai_addon_version": input("Bonsai addon version [>=1.0.0]: ") or ">=1.0.0",
        "ifc_version": input("IFC version [IFC4]: ") or "IFC4",
        "region": input("Region [Singapore]: ") or "Singapore",
        "building_codes": []
    }

    codes = input("Building codes (comma-separated): ")
    if codes:
        metadata["compatibility"]["building_codes"] = [c.strip() for c in codes.split(",")]

    # Notes
    notes_input = input("\nNotes (comma-separated, optional): ")
    if notes_input:
        metadata["notes"] = [n.strip() for n in notes_input.split(",")]

    # Changelog
    metadata["changelog"] = {
        metadata["version"]: [
            input("Changelog entry (describe what's in this version): ") or "Initial version"
        ]
    }

    return metadata


def create_metadata_default(template_dir: Path) -> Dict:
    """
    Create default metadata.json

    Args:
        template_dir: Template set directory

    Returns:
        Metadata dictionary
    """

    # Auto-detect from database
    db_path = template_dir / "template_library.db"
    stats = count_templates_in_db(db_path) if db_path.exists() else {"total_templates": 0, "by_category": {}}

    metadata = {
        "template_set_name": template_dir.name,
        "version": "1.0.0",
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "author": "BIM Team",
        "description": "Template set for BIM generation",

        "source": {
            "extracted_from": "Terminal 1",
            "reference_database": "",
            "extraction_date": datetime.now().strftime("%Y-%m-%d")
        },

        "statistics": stats,

        "compatibility": {
            "bonsai_addon_version": ">=1.0.0",
            "ifc_version": "IFC4",
            "region": "Singapore",
            "building_codes": []
        },

        "changelog": {
            "1.0.0": [
                "Initial template set creation"
            ]
        },

        "notes": []
    }

    return metadata


def validate_metadata(metadata: Dict) -> List[str]:
    """
    Validate metadata structure.

    Args:
        metadata: Metadata dictionary

    Returns:
        List of validation errors (empty if valid)
    """

    errors = []

    # Check required fields
    for field in METADATA_SCHEMA["required_fields"]:
        if field not in metadata:
            errors.append(f"Missing required field: {field}")
        elif not metadata[field]:
            errors.append(f"Required field is empty: {field}")

    # Validate version format (should be semver-like)
    if "version" in metadata:
        version = metadata["version"]
        if not version.count('.') >= 1:
            errors.append(f"Version should be in format X.Y.Z, got: {version}")

    # Validate date format
    if "created_date" in metadata:
        try:
            datetime.strptime(metadata["created_date"], "%Y-%m-%d")
        except ValueError:
            errors.append(f"Invalid date format, should be YYYY-MM-DD: {metadata['created_date']}")

    # Validate statistics if present
    if "statistics" in metadata:
        if "total_templates" not in metadata["statistics"]:
            errors.append("Missing total_templates in statistics")

    return errors


def save_metadata(metadata: Dict, template_dir: Path) -> bool:
    """
    Save metadata.json to template directory.

    Args:
        metadata: Metadata dictionary
        template_dir: Template set directory

    Returns:
        True if successful
    """

    metadata_path = template_dir / "metadata.json"

    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\n✅ Metadata saved to: {metadata_path}")
        return True

    except Exception as e:
        print(f"\n❌ ERROR saving metadata: {e}")
        return False


def load_metadata(template_dir: Path) -> Optional[Dict]:
    """
    Load metadata.json from template directory.

    Args:
        template_dir: Template set directory

    Returns:
        Metadata dictionary or None if not found
    """

    metadata_path = template_dir / "metadata.json"

    if not metadata_path.exists():
        print(f"❌ Metadata file not found: {metadata_path}")
        return None

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        return metadata

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in metadata file: {e}")
        return None
    except Exception as e:
        print(f"❌ ERROR loading metadata: {e}")
        return None


def cmd_create(template_dir: Path, interactive: bool = False):
    """Create metadata.json"""

    print(f"\nCreating metadata for: {template_dir}")

    # Check if directory exists
    if not template_dir.exists():
        print(f"❌ Directory does not exist: {template_dir}")
        print("Create it first, or specify correct path.")
        return False

    # Check if metadata already exists
    metadata_path = template_dir / "metadata.json"
    if metadata_path.exists():
        response = input(f"\n⚠️  metadata.json already exists. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return False

    # Create metadata
    if interactive:
        metadata = create_metadata_interactive(template_dir)
    else:
        print("Creating default metadata (use --interactive for guided creation)")
        metadata = create_metadata_default(template_dir)

    # Validate
    print("\nValidating metadata...")
    errors = validate_metadata(metadata)

    if errors:
        print("\n⚠️  Validation warnings:")
        for error in errors:
            print(f"  - {error}")

        response = input("\nSave anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return False

    # Save
    success = save_metadata(metadata, template_dir)

    if success:
        print("\n" + "=" * 70)
        print("✅ SUCCESS: Metadata created!")
        print("=" * 70)
        print(f"\nTemplate Set: {metadata['template_set_name']}")
        print(f"Version: {metadata['version']}")
        print(f"Templates: {metadata.get('statistics', {}).get('total_templates', 0)}")
        print()

    return success


def cmd_validate(template_dir: Path):
    """Validate existing metadata.json"""

    print(f"\nValidating metadata in: {template_dir}")

    metadata = load_metadata(template_dir)
    if not metadata:
        return False

    print("\n" + "=" * 70)
    print("Metadata Validation Report")
    print("=" * 70)

    # Validate structure
    errors = validate_metadata(metadata)

    if errors:
        print("\n❌ Validation FAILED:")
        for error in errors:
            print(f"  - {error}")
        return False

    else:
        print("\n✅ Validation PASSED")

    # Display metadata summary
    print("\n" + "-" * 70)
    print("Metadata Summary:")
    print("-" * 70)

    print(f"Template Set: {metadata.get('template_set_name')}")
    print(f"Version: {metadata.get('version')}")
    print(f"Author: {metadata.get('author')}")
    print(f"Created: {metadata.get('created_date')}")
    print(f"Description: {metadata.get('description')}")

    if "statistics" in metadata:
        stats = metadata["statistics"]
        print(f"\nTemplates: {stats.get('total_templates', 0)}")

        if "by_category" in stats and stats["by_category"]:
            print("By category:")
            for cat, count in stats["by_category"].items():
                print(f"  - {cat}: {count}")

    if "validation" in metadata:
        val = metadata["validation"]
        print(f"\nValidation:")
        print(f"  Tested on: {val.get('tested_on')}")
        if "accuracy" in val:
            print(f"  Accuracy: {val['accuracy'].get('element_count')}")

    if "compatibility" in metadata:
        comp = metadata["compatibility"]
        print(f"\nCompatibility:")
        print(f"  Bonsai: {comp.get('bonsai_addon_version')}")
        print(f"  IFC: {comp.get('ifc_version')}")
        print(f"  Region: {comp.get('region')}")

    print("\n" + "=" * 70)

    return True


def show_usage():
    """Show usage information."""
    print("""
Template Set Metadata Creator and Validator
============================================

Creates and validates metadata.json files for template sets.

Usage:
    python3 create_template_metadata.py create [template_dir] [--interactive]
    python3 create_template_metadata.py validate [template_dir]

Commands:
    create      Create new metadata.json
    validate    Validate existing metadata.json

Arguments:
    template_dir    Path to template set directory
    --interactive   Use interactive mode for creation

Examples:
    # Create default metadata
    python3 create_template_metadata.py create Terminal1_Project/Templates/terminal_base_v1.0/

    # Create with interactive prompts
    python3 create_template_metadata.py create Terminal1_Project/Templates/terminal_base_v1.0/ --interactive

    # Validate existing metadata
    python3 create_template_metadata.py validate Terminal1_Project/Templates/terminal_base_v1.0/
    """)


def main():
    """Main entry point."""

    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command in ['-h', '--help', 'help']:
        show_usage()
        return

    if command not in ['create', 'validate']:
        print(f"❌ Unknown command: {command}")
        show_usage()
        sys.exit(1)

    if len(sys.argv) < 3:
        print(f"❌ Missing template directory argument")
        show_usage()
        sys.exit(1)

    template_dir = Path(sys.argv[2])
    interactive = '--interactive' in sys.argv or '-i' in sys.argv

    if command == 'create':
        success = cmd_create(template_dir, interactive)
    elif command == 'validate':
        success = cmd_validate(template_dir)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
