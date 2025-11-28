#!/usr/bin/env python3
"""
Gate 3: Structural Completeness Validation

Validates output has minimum required structural elements:
- Walls (minimum 4 exterior)
- Roof (minimum 1)
- Discharge drains (minimum 4)

Based on expert recommendation: 2025-11-28
"""

import json
import sys
from pathlib import Path

# Minimum requirements per expert guidance
MINIMUM_REQUIREMENTS = {
    "walls": 4,        # At minimum, 4 exterior walls
    "roof": 1,         # At least 1 roof element
    "drains": 4,       # Perimeter drainage
    "doors": 1,        # At least entry door
}

# Expected ranges for typical residential
EXPECTED_RANGES = {
    "walls": (10, 150),
    "roof": (1, 5),
    "drains": (4, 20),
    "doors": (5, 20),
    "windows": (5, 30)
}


class StructuralValidator:
    """Gate 3: Validate structural completeness"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.inventory = {}

    def count_by_type(self, objects, type_pattern, exclude_patterns=None):
        """Count objects matching type pattern, optionally excluding certain patterns"""
        exclude_patterns = exclude_patterns or []
        return len([
            o for o in objects
            if type_pattern in o.get('object_type', '').lower()
            and not any(excl in o.get('object_type', '').lower() for excl in exclude_patterns)
        ])

    def validate(self, output_json):
        """
        Run Gate 3 validation

        Returns:
            bool: True if validation passes (critical elements present)
        """
        objects = output_json.get('objects', [])

        # Count structural elements
        self.inventory = {
            'walls': self.count_by_type(objects, 'wall'),
            'roof': self.count_by_type(objects, 'roof', exclude_patterns=['gutter']),  # Exclude roof gutters
            'drains': self.count_by_type(objects, 'gutter') + self.count_by_type(objects, 'drain'),
            'doors': self.count_by_type(objects, 'door'),
            'windows': self.count_by_type(objects, 'window')
        }

        # Check minimum requirements
        for element, min_count in MINIMUM_REQUIREMENTS.items():
            actual = self.inventory.get(element, 0)
            if actual < min_count:
                self.errors.append(
                    f"CRITICAL: {element} count {actual} < minimum {min_count}"
                )

        # Check expected ranges (warnings only)
        for element, (min_expected, max_expected) in EXPECTED_RANGES.items():
            actual = self.inventory.get(element, 0)
            if actual < min_expected:
                self.warnings.append(
                    f"{element} count {actual} below expected range [{min_expected}-{max_expected}]"
                )
            elif actual > max_expected:
                self.warnings.append(
                    f"{element} count {actual} above expected range [{min_expected}-{max_expected}]"
                )

        return len(self.errors) == 0

    def print_report(self):
        """Print validation report"""
        print("\n" + "="*80)
        print("🔍 GATE 3: STRUCTURAL VALIDATION")
        print("="*80)

        print("\n📊 Inventory:")
        for element, count in self.inventory.items():
            min_req = MINIMUM_REQUIREMENTS.get(element, 0)
            status = "✅" if count >= min_req else "❌"
            print(f"   {status} {element.capitalize()}: {count} (min: {min_req})")

        if self.errors:
            print("\n❌ CRITICAL ERRORS:")
            for err in self.errors:
                print(f"   • {err}")
            print("\n⚠️  GATE 3 FAILED - Pipeline cannot continue")
            print("   Fix: Ensure GridTruth has room_bounds and building_envelope")
            return False

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warn in self.warnings:
                print(f"   • {warn}")

        print("\n✅ GATE 3 PASSED - Structural elements complete")
        return True


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 structural_validator.py <output.json>")
        sys.exit(1)

    json_path = sys.argv[1]

    try:
        with open(json_path) as f:
            output_json = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON: {e}")
        sys.exit(1)

    validator = StructuralValidator()
    passed = validator.validate(output_json)
    validator.print_report()

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
