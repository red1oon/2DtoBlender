#!/usr/bin/env python3
"""
Template Extraction Script

Extracts templates from Terminal 1 database (FullExtractionTesellated.db)
and populates template_library.db.

Since positions are at origin, we focus on:
- Element type patterns (counts, IFC classes)
- Relationships and groupings
- Material properties
- Discipline-specific rules

Usage:
    python3 extract_templates.py [source_db] [template_lib_db] [--discipline DISC]

Example:
    python3 extract_templates.py FullExtractionTesellated.db terminal_base_v1.0/template_library.db --discipline FP
"""

import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class TemplateExtractor:
    """Extract templates from source database."""

    def __init__(self, source_db: str, target_db: str):
        """
        Initialize extractor.

        Args:
            source_db: Path to FullExtractionTesellated.db
            target_db: Path to template_library.db
        """
        self.source_db = Path(source_db)
        self.target_db = Path(target_db)

        if not self.source_db.exists():
            raise FileNotFoundError(f"Source database not found: {source_db}")

        if not self.target_db.exists():
            raise FileNotFoundError(f"Target database not found: {target_db}")

        self.source_conn = None
        self.target_conn = None

    def connect(self):
        """Open database connections."""
        self.source_conn = sqlite3.connect(self.source_db)
        self.target_conn = sqlite3.connect(self.target_db)

        # Enable foreign keys
        self.target_conn.execute("PRAGMA foreign_keys = ON")

        print(f"✅ Connected to source: {self.source_db}")
        print(f"✅ Connected to target: {self.target_db}")

    def close(self):
        """Close database connections."""
        if self.source_conn:
            self.source_conn.close()
        if self.target_conn:
            self.target_conn.close()

    def analyze_discipline(self, discipline: str) -> Dict:
        """
        Analyze a discipline to find patterns.

        Args:
            discipline: Discipline code (ARC, FP, ELEC, etc.)

        Returns:
            Dictionary with analysis results
        """

        cursor = self.source_conn.cursor()

        # Count by IFC class
        cursor.execute("""
            SELECT ifc_class, COUNT(*) as count
            FROM elements_meta
            WHERE discipline = ?
            GROUP BY ifc_class
            ORDER BY count DESC
        """, (discipline,))

        ifc_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Count by element type
        cursor.execute("""
            SELECT element_type, COUNT(*) as count
            FROM elements_meta
            WHERE discipline = ? AND element_type IS NOT NULL AND element_type != ''
            GROUP BY element_type
            ORDER BY count DESC
            LIMIT 20
        """, (discipline,))

        type_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Get materials used
        cursor.execute("""
            SELECT DISTINCT material_name
            FROM elements_meta
            WHERE discipline = ? AND material_name IS NOT NULL AND material_name != ''
            LIMIT 10
        """, (discipline,))

        materials = [row[0] for row in cursor.fetchall()]

        return {
            "discipline": discipline,
            "ifc_counts": ifc_counts,
            "type_counts": type_counts,
            "materials": materials,
            "total_elements": sum(ifc_counts.values())
        }

    def extract_simple_template(self, discipline: str, ifc_class: str, element_type: str = None) -> Dict:
        """
        Extract a simple template based on IFC class.

        Args:
            discipline: Discipline code
            ifc_class: IFC class name
            element_type: Optional specific element type

        Returns:
            Template dictionary
        """

        cursor = self.source_conn.cursor()

        # Count instances
        if element_type:
            cursor.execute("""
                SELECT COUNT(*), element_type, material_name
                FROM elements_meta
                WHERE discipline = ? AND ifc_class = ? AND element_type = ?
                GROUP BY element_type, material_name
            """, (discipline, ifc_class, element_type))
        else:
            cursor.execute("""
                SELECT COUNT(*), element_type, material_name
                FROM elements_meta
                WHERE discipline = ? AND ifc_class = ?
                GROUP BY element_type, material_name
                ORDER BY COUNT(*) DESC
                LIMIT 1
            """, (discipline, ifc_class))

        result = cursor.fetchone()

        if not result:
            return None

        count, elem_type, material = result

        # Create template ID
        template_id = f"{discipline.lower()}_{ifc_class.lower()}_{datetime.now().strftime('%Y%m%d')}"

        template = {
            "template_id": template_id,
            "template_name": f"{discipline}_{ifc_class}",
            "version": "1.0.0",
            "category": self._get_category(discipline),
            "subcategory": elem_type or "General",
            "ifc_class": ifc_class,
            "object_type": elem_type,
            "description": f"Extracted from Terminal 1: {count} instances",
            "confidence_score": 0.9 if count > 10 else 0.7,
            "instance_count": count,
            "material": material,
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "extracted_from": "Terminal 1",
            "status": "active"
        }

        return template

    def _get_category(self, discipline: str) -> str:
        """Map discipline to template category."""
        mapping = {
            "ARC": "Seating",
            "FP": "Fire_Protection",
            "ELEC": "Electrical",
            "ACMV": "ACMV",
            "SP": "Plumbing",
            "STR": "Structure",
            "CW": "Chilled_Water",
            "LPG": "LPG"
        }
        return mapping.get(discipline, "Other")

    def save_template(self, template: Dict) -> bool:
        """
        Save template to target database.

        Args:
            template: Template dictionary

        Returns:
            True if successful
        """

        cursor = self.target_conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO element_templates (
                    template_id, template_name, version, category, subcategory,
                    ifc_class, object_type, description, confidence_score,
                    instance_count, created_date, extracted_from, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template["template_id"],
                template["template_name"],
                template["version"],
                template["category"],
                template["subcategory"],
                template["ifc_class"],
                template.get("object_type"),
                template["description"],
                template["confidence_score"],
                template["instance_count"],
                template["created_date"],
                template["extracted_from"],
                template["status"]
            ))

            self.target_conn.commit()
            return True

        except sqlite3.IntegrityError as e:
            print(f"⚠️  Template already exists: {template['template_id']}")
            return False
        except Exception as e:
            print(f"❌ Error saving template: {e}")
            return False

    def extract_discipline_templates(self, discipline: str) -> int:
        """
        Extract all templates for a discipline.

        Args:
            discipline: Discipline code

        Returns:
            Number of templates extracted
        """

        print(f"\n{'='*70}")
        print(f"Extracting templates for: {discipline}")
        print(f"{'='*70}\n")

        # Analyze discipline
        analysis = self.analyze_discipline(discipline)

        print(f"Total elements: {analysis['total_elements']}")
        print(f"IFC classes: {len(analysis['ifc_counts'])}")
        print(f"Element types: {len(analysis['type_counts'])}\n")

        print("IFC Class breakdown:")
        for ifc_class, count in analysis['ifc_counts'].items():
            print(f"  - {ifc_class}: {count}")

        print(f"\nExtracting templates...")

        templates_created = 0

        # Extract template for each significant IFC class
        for ifc_class, count in analysis['ifc_counts'].items():
            if count < 5:  # Skip rare elements
                print(f"  ⊘ Skipping {ifc_class} (only {count} instances)")
                continue

            template = self.extract_simple_template(discipline, ifc_class)

            if template:
                success = self.save_template(template)
                if success:
                    print(f"  ✓ Created: {template['template_name']} ({count} instances, confidence: {template['confidence_score']})")
                    templates_created += 1
                else:
                    print(f"  ⊘ Skipped: {template['template_name']} (already exists)")

        print(f"\n✅ Created {templates_created} templates for {discipline}")

        return templates_created

    def extract_all(self) -> Dict:
        """
        Extract templates for all disciplines.

        Returns:
            Summary dictionary
        """

        disciplines = ["ARC", "FP", "ELEC", "ACMV", "SP", "STR", "CW", "LPG"]

        summary = {}
        total_templates = 0

        for discipline in disciplines:
            count = self.extract_discipline_templates(discipline)
            summary[discipline] = count
            total_templates += count

        return {
            "total_templates": total_templates,
            "by_discipline": summary
        }


def show_usage():
    """Show usage information."""
    print("""
Template Extraction Script
==========================

Extracts templates from Terminal 1 database and populates template library.

Usage:
    python3 extract_templates.py [source_db] [template_lib_db] [options]

Arguments:
    source_db         Path to FullExtractionTesellated.db
    template_lib_db   Path to template_library.db

Options:
    --discipline DISC Extract only specified discipline (ARC, FP, ELEC, etc.)
    --all            Extract all disciplines (default)

Examples:
    # Extract all disciplines
    python3 extract_templates.py \\
        DatabaseFiles/FullExtractionTesellated.db \\
        Terminal1_Project/Templates/terminal_base_v1.0/template_library.db

    # Extract only Fire Protection
    python3 extract_templates.py \\
        DatabaseFiles/FullExtractionTesellated.db \\
        Terminal1_Project/Templates/terminal_base_v1.0/template_library.db \\
        --discipline FP
    """)


def main():
    """Main entry point."""

    if len(sys.argv) < 3:
        show_usage()
        sys.exit(1)

    source_db = sys.argv[1]
    target_db = sys.argv[2]

    # Parse options
    extract_discipline = None
    if "--discipline" in sys.argv:
        idx = sys.argv.index("--discipline")
        if idx + 1 < len(sys.argv):
            extract_discipline = sys.argv[idx + 1]

    print("="*70)
    print("Template Extraction from Terminal 1")
    print("="*70)
    print(f"\nSource: {source_db}")
    print(f"Target: {target_db}")
    if extract_discipline:
        print(f"Discipline: {extract_discipline}")
    else:
        print(f"Discipline: ALL")
    print()

    try:
        extractor = TemplateExtractor(source_db, target_db)
        extractor.connect()

        if extract_discipline:
            count = extractor.extract_discipline_templates(extract_discipline)
            summary = {
                "total_templates": count,
                "by_discipline": {extract_discipline: count}
            }
        else:
            summary = extractor.extract_all()

        extractor.close()

        # Print summary
        print("\n" + "="*70)
        print("Extraction Complete!")
        print("="*70)
        print(f"\nTotal templates created: {summary['total_templates']}")
        print("\nBy discipline:")
        for disc, count in summary['by_discipline'].items():
            print(f"  - {disc}: {count}")

        print("\nNext steps:")
        print("1. Review templates: sqlite3 template_library.db 'SELECT * FROM element_templates;'")
        print("2. Update metadata: python3 create_template_metadata.py create [template_dir]")
        print("3. Validate: python3 create_template_metadata.py validate [template_dir]")
        print()

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
