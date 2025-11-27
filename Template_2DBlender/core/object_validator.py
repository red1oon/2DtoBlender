#!/usr/bin/env python3
"""
Object Validator - Validate extracted objects against schedule dimensions

Purpose:
    Cross-reference extracted objects (JSON) with schedule entries (database)
    to validate dimensional accuracy and suggest corrections.

Method:
    1. Load extracted objects from JSON
    2. Query schedule entries from database (context_schedules)
    3. Match objects to schedule by ID (D1, D2, W1, W2, etc.)
    4. Validate object_type matches schedule dimensions
    5. Report mismatches and suggest corrections

Dependencies:
    - Input: extraction output JSON
    - Input: database context_schedules table
    - Master template: object_type naming conventions

Author: Claude Code
Date: 2025-11-25
Status: Priority 2 implementation
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


class ObjectValidator:
    """Validate extracted objects against schedule entries"""

    # Object type mapping based on schedule dimensions
    DOOR_MAPPING = {
        (900, 2100): "door_single_900_lod300",
        (750, 2100): "door_single_900_lod300",  # Use 900 as close match
        (1800, 2100): "door_double_1800_lod300",
    }

    WINDOW_MAPPING = {
        (1800, 1000): "window_aluminum_2panel_1200x1000_lod300",  # Need 1800mm variant
        (1200, 1000): "window_aluminum_2panel_1200x1000_lod300",
        (600, 500): "window_aluminum_2panel_1200x1000_lod300",  # Need 600mm variant
    }

    def __init__(self, db_path: str, json_path: str):
        """Initialize validator with paths"""
        self.db_path = db_path
        self.json_path = json_path
        self.schedules = {}
        self.objects = []
        self.validation_results = []

    def load_schedules(self):
        """Load schedule entries from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT schedule_type, item_id, description, width_mm, height_mm, depth_mm
            FROM context_schedules
            ORDER BY schedule_type, item_id
        """)

        for row in cursor.fetchall():
            key = row['item_id']  # D1, D2, W1, etc.
            self.schedules[key] = {
                'type': row['schedule_type'],
                'id': row['item_id'],
                'description': row['description'],
                'width_mm': row['width_mm'],
                'height_mm': row['height_mm'],
                'depth_mm': row['depth_mm'],
            }

        conn.close()
        print(f"✅ Loaded {len(self.schedules)} schedule entries")

    def load_objects(self):
        """Load extracted objects from JSON"""
        with open(self.json_path, 'r') as f:
            data = json.load(f)
            self.objects = data.get('objects', [])
        print(f"✅ Loaded {len(self.objects)} extracted objects")

    def extract_id_from_name(self, name: str) -> Optional[str]:
        """Extract door/window ID from object name (D1, D2, W1, etc.)"""
        # Match patterns like "D1", "W1", "D1_x20_y30"
        match = re.match(r'^([DW]\d+)', name)
        if match:
            return match.group(1)
        return None

    def get_expected_object_type(self, schedule_entry: Dict) -> Tuple[str, str]:
        """Get expected object_type based on schedule dimensions"""
        sched_type = schedule_entry['type']
        width = schedule_entry['width_mm']
        height = schedule_entry['height_mm']

        if sched_type == 'door':
            mapping = self.DOOR_MAPPING
        elif sched_type == 'window':
            mapping = self.WINDOW_MAPPING
        else:
            return None, "Unknown schedule type"

        expected = mapping.get((width, height))
        if expected:
            return expected, "exact_match"
        else:
            # Find closest match
            for (w, h), obj_type in mapping.items():
                if abs(w - width) < 200 and abs(h - height) < 200:
                    return obj_type, f"close_match (expected {width}×{height}, using {w}×{h})"

            return None, f"no_match_for_{width}x{height}"

    def validate_objects(self):
        """Validate all extracted objects against schedules"""
        door_count = 0
        window_count = 0

        for obj in self.objects:
            name = obj.get('name', '')
            obj_type = obj.get('object_type', '')

            # Extract ID (D1, W1, etc.)
            obj_id = self.extract_id_from_name(name)
            if not obj_id:
                continue  # Skip objects without recognized IDs

            # Look up in schedule
            schedule = self.schedules.get(obj_id)
            if not schedule:
                self.validation_results.append({
                    'status': 'warning',
                    'name': name,
                    'object_type': obj_type,
                    'issue': f"ID '{obj_id}' not found in schedule",
                    'suggestion': "Check if object ID matches schedule table"
                })
                continue

            # Get expected object_type
            expected_type, match_status = self.get_expected_object_type(schedule)

            # Compare
            if obj_type == expected_type:
                self.validation_results.append({
                    'status': 'pass',
                    'name': name,
                    'object_type': obj_type,
                    'schedule_id': obj_id,
                    'dimensions': f"{schedule['width_mm']}×{schedule['height_mm']}mm",
                    'match': match_status
                })
                if schedule['type'] == 'door':
                    door_count += 1
                else:
                    window_count += 1
            else:
                self.validation_results.append({
                    'status': 'fail',
                    'name': name,
                    'object_type': obj_type,
                    'schedule_id': obj_id,
                    'dimensions': f"{schedule['width_mm']}×{schedule['height_mm']}mm",
                    'expected_type': expected_type,
                    'issue': f"Object type mismatch (expected: {expected_type}, got: {obj_type})",
                    'suggestion': f"Update object_type to '{expected_type}'"
                })

        return door_count, window_count

    def generate_report(self):
        """Generate validation report"""
        passes = [r for r in self.validation_results if r['status'] == 'pass']
        fails = [r for r in self.validation_results if r['status'] == 'fail']
        warnings = [r for r in self.validation_results if r['status'] == 'warning']

        print("\n" + "=" * 80)
        print("OBJECT VALIDATION REPORT")
        print("=" * 80)

        print(f"\n📊 Summary:")
        print(f"  ✅ Passed: {len(passes)}")
        print(f"  ❌ Failed: {len(fails)}")
        print(f"  ⚠️  Warnings: {len(warnings)}")
        print(f"  Total validated: {len(self.validation_results)}")

        if passes:
            print(f"\n✅ PASSED ({len(passes)} objects):")
            for r in passes:
                print(f"  {r['name']:30s} → {r['schedule_id']} ({r['dimensions']}) ✓")

        if fails:
            print(f"\n❌ FAILED ({len(fails)} objects):")
            for r in fails:
                print(f"  {r['name']:30s} → {r['schedule_id']} ({r['dimensions']})")
                print(f"     Current:  {r['object_type']}")
                print(f"     Expected: {r['expected_type']}")
                print(f"     Issue:    {r['issue']}")
                print(f"     Fix:      {r['suggestion']}")
                print()

        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)} objects):")
            for r in warnings:
                print(f"  {r['name']:30s} → {r['issue']}")
                print(f"     Suggestion: {r['suggestion']}")
                print()

        print("\n" + "=" * 80)
        print("SCHEDULE COVERAGE")
        print("=" * 80)

        for schedule_id, schedule in sorted(self.schedules.items()):
            validated = any(r.get('schedule_id') == schedule_id for r in self.validation_results)
            status = "✅" if validated else "❌"
            print(f"{status} {schedule_id}: {schedule['description']} ({schedule['width_mm']}×{schedule['height_mm']}mm)")

        return {
            'passed': len(passes),
            'failed': len(fails),
            'warnings': len(warnings),
            'total': len(self.validation_results),
            'schedule_coverage': len([s for s in self.schedules.keys() if any(r.get('schedule_id') == s for r in self.validation_results)]),
            'total_schedules': len(self.schedules)
        }

    def infer_missing_from_legend(self):
        """Suggest objects that should exist based on schedule but not extracted"""
        print("\n" + "=" * 80)
        print("INFERENCE FROM LEGEND/SCHEDULE (GAP 5)")
        print("=" * 80)

        extracted_ids = set()
        for r in self.validation_results:
            if r.get('schedule_id'):
                extracted_ids.add(r['schedule_id'])

        missing = []
        for schedule_id, schedule in self.schedules.items():
            if schedule_id not in extracted_ids:
                missing.append(schedule)

        if missing:
            print(f"\n⚠️  {len(missing)} items in schedule but NOT extracted:")
            for sched in missing:
                print(f"  {sched['id']}: {sched['description']} ({sched['width_mm']}×{sched['height_mm']}mm)")
                print(f"     → Should infer from legend/schedule table")
        else:
            print("\n✅ All schedule items extracted!")

        return missing


def main():
    """Main execution: Validate objects against schedules"""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python3 object_validator.py <database_path> <json_path>")
        print("\nExample:")
        print("  python3 object_validator.py \\")
        print("    'output_artifacts/TB-LKTN HOUSE_ANNOTATION_FROM_2D.db' \\")
        print("    'output_artifacts/TB-LKTN_HOUSE_OUTPUT_20251125_060718.json'")
        sys.exit(1)

    db_path = sys.argv[1]
    json_path = sys.argv[2]

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    if not Path(json_path).exists():
        print(f"❌ JSON not found: {json_path}")
        sys.exit(1)

    print("Object Validator")
    print(f"Database: {db_path}")
    print(f"JSON: {json_path}")
    print()

    validator = ObjectValidator(db_path, json_path)

    # Load data
    validator.load_schedules()
    validator.load_objects()

    # Validate
    door_count, window_count = validator.validate_objects()
    print(f"\n✅ Validated {door_count} doors, {window_count} windows")

    # Generate report
    summary = validator.generate_report()

    # Infer missing
    missing = validator.infer_missing_from_legend()

    print("\n✅ Validation complete!")
    print(f"\n📊 Results: {summary['passed']}/{summary['total']} passed, {summary['failed']} failed, {summary['warnings']} warnings")
    print(f"📋 Schedule coverage: {summary['schedule_coverage']}/{summary['total_schedules']} items")


if __name__ == "__main__":
    main()
