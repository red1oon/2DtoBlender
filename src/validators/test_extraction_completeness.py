#!/usr/bin/env python3
"""
Extraction Completeness Validator

Cross-references output JSON against master_reference_template.json to ensure:
1. All expected items from template were extracted
2. All phases completed
3. All dependencies satisfied
4. No items forgotten

"Such testing must already be corelated from the master template to the output
json and refer back to master doc in case something is forgotten" - User
"""

import json
import sys
from typing import Dict, List, Set, Tuple


class CompletenessValidator:
    """Validate extraction output against master reference template"""

    def __init__(self, output_file: str, template_file: str):
        """
        Args:
            output_file: Extraction output JSON
            template_file: Master reference template JSON
        """
        with open(output_file) as f:
            self.output = json.load(f)

        with open(template_file) as f:
            self.template = json.load(f)

        self.extraction_sequence = self.template.get('extraction_sequence', [])
        self.objects = self.output.get('objects', [])
        self.extraction_metadata = self.output.get('extraction_metadata', {})

        self.missing_items = []
        self.present_items = []
        self.partial_items = []

    def validate(self) -> Dict:
        """
        Validate extraction completeness

        Returns:
            Dict with validation results
        """
        print("=" * 80)
        print("EXTRACTION COMPLETENESS VALIDATION")
        print("=" * 80)
        print(f"\nMaster Template: {len(self.extraction_sequence)} items defined")
        print(f"Output JSON: {len(self.objects)} objects extracted")
        print()

        # Group template items by phase
        phases = self._group_by_phase()

        # Validate each phase
        for phase_name in sorted(phases.keys()):
            self._validate_phase(phase_name, phases[phase_name])

        # Summary
        self._print_summary()

        return {
            'total_items': len(self.extraction_sequence),
            'present': len(self.present_items),
            'missing': len(self.missing_items),
            'partial': len(self.partial_items),
            'missing_items': self.missing_items,
            'partial_items': self.partial_items
        }

    def _group_by_phase(self) -> Dict[str, List[Dict]]:
        """Group extraction items by phase"""
        phases = {}
        for item in self.extraction_sequence:
            phase = item.get('_phase', 'unknown')
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(item)
        return phases

    def _validate_phase(self, phase_name: str, items: List[Dict]):
        """Validate all items in a phase"""
        print("-" * 80)
        print(f"PHASE: {phase_name}")
        print("-" * 80)

        # Check dependency
        if items and items[0].get('_dependency'):
            print(f"Dependency: {items[0]['_dependency']}")

        for item in items:
            self._validate_item(item)

        print()

    def _validate_item(self, item: Dict):
        """Validate a single extraction item"""
        item_name = item.get('item', 'Unknown')
        object_type = item.get('object_type')
        detection_id = item.get('detection_id')
        outputs = item.get('outputs', [])

        # Check if item was extracted
        status = self._check_item_status(item)

        if status == 'present':
            count = self._count_objects_of_type(object_type)
            print(f"  ✅ {item_name:30s} - {count} objects extracted")
            self.present_items.append({
                'item': item_name,
                'count': count,
                'type': object_type
            })

        elif status == 'partial':
            issues = self._get_partial_issues(item)
            print(f"  ⚠️  {item_name:30s} - Partially extracted")
            for issue in issues:
                print(f"       {issue}")
            self.partial_items.append({
                'item': item_name,
                'issues': issues
            })

        else:  # missing
            print(f"  ❌ {item_name:30s} - NOT FOUND")
            self.missing_items.append({
                'item': item_name,
                'expected_type': object_type,
                'detection_method': detection_id
            })

    def _check_item_status(self, item: Dict) -> str:
        """
        Check if item is present, missing, or partial

        Returns:
            'present', 'missing', or 'partial'
        """
        object_type = item.get('object_type')
        detection_id = item.get('detection_id')
        outputs = item.get('outputs', [])

        # Special handling for calibration
        if detection_id == 'CALIBRATION_DRAIN_PERIMETER':
            if self.extraction_metadata.get('calibration'):
                return 'present'
            else:
                return 'missing'

        # Special handling for elevations
        if detection_id == 'ELEVATION_TEXT_REGEX':
            # Check if any elevation data exists
            if self.extraction_metadata.get('elevations'):
                return 'present'
            return 'missing'

        # Special handling for schedules
        if detection_id == 'SCHEDULE_TABLE_EXTRACTION':
            if 'door' in item.get('item', '').lower():
                if self.extraction_metadata.get('door_schedule'):
                    return 'present'
                return 'missing'
            elif 'window' in item.get('item', '').lower():
                if self.extraction_metadata.get('window_schedule'):
                    return 'present'
                return 'missing'

        # For regular objects with object_type
        if object_type:
            matching_objects = self._count_objects_of_type(object_type)

            if matching_objects > 0:
                # Check if schedule dimensions match (if applicable)
                if 'door' in item.get('item', '').lower() or 'window' in item.get('item', '').lower():
                    if not self._check_dimension_annotations(object_type):
                        return 'partial'  # Objects exist but no dimension validation

                return 'present'
            else:
                return 'missing'

        # For items without object_type (metadata items)
        return 'missing'

    def _count_objects_of_type(self, object_type: str) -> int:
        """Count how many objects of a given type were extracted"""
        if not object_type:
            return 0

        count = 0
        for obj in self.objects:
            if obj.get('object_type') == object_type:
                count += 1

        return count

    def _check_dimension_annotations(self, object_type: str) -> bool:
        """Check if dimension annotations exist for door/window objects"""
        annotations = self.output.get('annotations', {})
        dimensions = annotations.get('dimensions', [])

        # If no dimensions captured, return False
        if not dimensions:
            return False

        # Check if any dimension annotations exist for this object type
        for dim in dimensions:
            associated = dim.get('associated_object', '')
            if object_type in associated:
                return True

        return False

    def _get_partial_issues(self, item: Dict) -> List[str]:
        """Get list of issues for partially extracted items"""
        issues = []

        object_type = item.get('object_type')

        # Check for missing dimension annotations
        if 'door' in item.get('item', '').lower() or 'window' in item.get('item', '').lower():
            if not self._check_dimension_annotations(object_type):
                issues.append("Missing dimension annotations from schedule")

        # Check for missing ground truth validation
        annotations = self.output.get('annotations', {})
        if 'door' in item.get('item', '').lower():
            if not annotations.get('doors'):
                issues.append("Missing door label annotations (D1, D2, D3)")

        if 'window' in item.get('item', '').lower():
            if not annotations.get('windows'):
                issues.append("Missing window label annotations (W1, W2, W3)")

        return issues

    def _print_summary(self):
        """Print validation summary"""
        print("=" * 80)
        print("COMPLETENESS SUMMARY")
        print("=" * 80)

        total = len(self.extraction_sequence)
        present = len(self.present_items)
        partial = len(self.partial_items)
        missing = len(self.missing_items)

        completeness = (present / total) * 100 if total > 0 else 0

        print(f"\n✅ Fully extracted: {present}/{total} ({completeness:.1f}%)")
        print(f"⚠️  Partially extracted: {partial}/{total}")
        print(f"❌ Missing: {missing}/{total}")
        print()

        if missing > 0:
            print("MISSING ITEMS (refer to master_reference_template.json):")
            for item in self.missing_items:
                print(f"  ❌ {item['item']}")
                print(f"     Expected type: {item['expected_type']}")
                print(f"     Detection method: {item['detection_method']}")
            print()

        if partial > 0:
            print("PARTIALLY EXTRACTED (needs completion):")
            for item in self.partial_items:
                print(f"  ⚠️  {item['item']}")
                for issue in item['issues']:
                    print(f"     - {issue}")
            print()

        # Overall status
        if completeness == 100 and partial == 0:
            print("🎉 EXTRACTION 100% COMPLETE")
        elif completeness >= 80:
            print("⚠️  EXTRACTION MOSTLY COMPLETE (review partial/missing items)")
        else:
            print("❌ EXTRACTION INCOMPLETE (many items missing)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_extraction_completeness.py <output.json> [template.json]")
        print()
        print("Validates extraction output against master reference template")
        print("Identifies missing or forgotten items")
        sys.exit(1)

    output_file = sys.argv[1]
    template_file = sys.argv[2] if len(sys.argv) > 2 else 'master_reference_template.json'

    validator = CompletenessValidator(output_file, template_file)
    result = validator.validate()

    # Exit code: 0 if complete, 1 if incomplete
    sys.exit(0 if result['missing'] == 0 and result['partial'] == 0 else 1)


if __name__ == "__main__":
    main()
