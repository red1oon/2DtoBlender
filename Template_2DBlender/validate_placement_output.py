#!/usr/bin/env python3
"""
Placement Output Validator
=========================

Validates that placement_results.json matches the extraction_checklist contract.

Usage:
    python3 validate_placement_output.py \
        --template input_templates/TB_LKTN_COMPLETE_template.json \
        --placement output_artifacts/TB_LKTN_placement_results.json

Purpose:
    - Loads template's extraction_checklist (THE CONTRACT)
    - Loads placement_results.json (THE OUTPUT)
    - Validates: contract == output
    - Shows ✅ or ❌ for each category

Output:
    - Console report with visual indicators
    - JSON log file with detailed breakdown
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class PlacementValidator:
    def __init__(self, template_path, placement_path):
        self.template_path = Path(template_path)
        self.placement_path = Path(placement_path)
        self.template_data = None
        self.placement_data = None
        self.contract = None
        self.output_counts = None
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'template_file': str(template_path),
            'placement_file': str(placement_path),
            'checks': [],
            'compliant': True,
            'summary': {}
        }

    def load_files(self):
        """Load template and placement files"""
        try:
            with open(self.template_path, 'r') as f:
                self.template_data = json.load(f)
            print(f"✅ Loaded template: {self.template_path.name}")
        except Exception as e:
            print(f"❌ Failed to load template: {e}")
            sys.exit(1)

        try:
            with open(self.placement_path, 'r') as f:
                self.placement_data = json.load(f)
            print(f"✅ Loaded placement results: {self.placement_path.name}")
        except Exception as e:
            print(f"❌ Failed to load placement results: {e}")
            sys.exit(1)

        # Extract contract
        self.contract = self.template_data.get('extraction_checklist', {})
        if not self.contract:
            print("❌ No extraction_checklist found in template")
            sys.exit(1)

    def count_placed_objects(self):
        """Count objects by type in placement_results"""
        counts = defaultdict(int)

        for obj in self.placement_data:
            object_type = obj.get('object_type', '').lower()

            # Map object types to checklist categories
            # ELECTRICAL
            if 'switch' in object_type:
                if '1gang' in object_type:
                    counts['electrical.switches_1gang'] += 1
                elif '2gang' in object_type:
                    counts['electrical.switches_2gang'] += 1
                elif '3gang' in object_type:
                    counts['electrical.switches_3gang'] += 1
            elif 'outlet' in object_type or 'power' in object_type:
                counts['electrical.outlets_3pin'] += 1
            elif 'ceiling_light' in object_type or 'light_ceiling' in object_type:
                counts['electrical.lights_ceiling'] += 1
            elif 'wall_light' in object_type or 'light_wall' in object_type:
                counts['electrical.lights_wall'] += 1
            elif 'pendant' in object_type:
                counts['electrical.lights_pendant'] += 1
            elif 'ceiling_fan' in object_type or 'fan_ceiling' in object_type:
                counts['electrical.fans_ceiling'] += 1
            elif 'exhaust_fan' in object_type or 'fan_exhaust' in object_type:
                counts['electrical.fans_exhaust'] += 1
            elif 'distribution_board' in object_type or 'db' in object_type:
                counts['electrical.distribution_board'] += 1

            # PLUMBING
            elif 'toilet' in object_type:
                if 'floor' in object_type or 'floor_mounted' in object_type:
                    counts['plumbing.toilets_floor_mounted'] += 1
                elif 'wall' in object_type or 'wall_mounted' in object_type:
                    counts['plumbing.toilets_wall_mounted'] += 1
                elif 'asian' in object_type:
                    counts['plumbing.toilets_asian'] += 1
            elif 'basin' in object_type:
                if 'wall' in object_type or 'wall_mounted' in object_type:
                    counts['plumbing.basins_wall_mounted'] += 1
                else:
                    counts['plumbing.basins_residential'] += 1
            elif 'kitchen_sink' in object_type or 'sink' in object_type:
                counts['plumbing.kitchen_sink'] += 1
            elif 'shower' in object_type:
                counts['plumbing.showerheads'] += 1
            elif 'faucet' in object_type:
                if 'basin' in object_type:
                    counts['plumbing.faucets_basin'] += 1
                elif 'kitchen' in object_type:
                    counts['plumbing.faucets_kitchen'] += 1
            elif 'floor_drain' in object_type or 'drain' in object_type:
                counts['plumbing.floor_drains'] += 1
            elif 'water_heater' in object_type:
                counts['plumbing.water_heaters'] += 1
            elif 'washing_machine' in object_type:
                counts['plumbing.washing_machine_point'] += 1

            # ARCHITECTURAL
            elif 'door' in object_type:
                if 'double' in object_type:
                    counts['architectural.doors_double'] += 1
                else:
                    counts['architectural.doors_single'] += 1
            elif 'window' in object_type:
                if 'sliding' in object_type:
                    counts['architectural.windows_sliding'] += 1
                elif 'casement' in object_type:
                    counts['architectural.windows_casement'] += 1
                else:
                    counts['architectural.windows_standard'] += 1
            elif 'stair' in object_type:
                counts['architectural.stairs'] += 1
            elif 'railing' in object_type:
                counts['architectural.railings'] += 1

            # WALLS (special handling)
            elif 'wall' in object_type:
                counts['walls'] += 1

            # HVAC
            elif 'air_conditioner' in object_type or 'ac_' in object_type:
                counts['hvac.air_conditioners'] += 1
            elif 'diffuser' in object_type:
                if 'supply' in object_type:
                    counts['hvac.diffusers_supply'] += 1
                elif 'return' in object_type:
                    counts['hvac.diffusers_return'] += 1

            # KITCHEN APPLIANCES
            elif 'stove' in object_type:
                if 'gas' in object_type:
                    counts['kitchen.stove_gas'] += 1
                elif 'electric' in object_type:
                    counts['kitchen.stove_electric'] += 1
            elif 'refrigerator' in object_type or 'fridge' in object_type:
                counts['kitchen.refrigerator'] += 1
            elif 'oven' in object_type:
                counts['kitchen.oven'] += 1
            elif 'dishwasher' in object_type:
                counts['kitchen.dishwasher'] += 1
            elif 'range_hood' in object_type or 'hood' in object_type:
                counts['kitchen.range_hood'] += 1
            elif 'cabinet' in object_type:
                if 'upper' in object_type or 'wall' in object_type:
                    counts['kitchen.cabinets_upper'] += 1
                elif 'lower' in object_type or 'base' in object_type:
                    counts['kitchen.cabinets_lower'] += 1

            # FURNITURE
            elif 'bed' in object_type:
                counts['furniture.beds'] += 1
            elif 'wardrobe' in object_type:
                counts['furniture.wardrobes'] += 1
            elif 'table' in object_type and 'dining' in object_type:
                counts['furniture.tables_dining'] += 1
            elif 'chair' in object_type:
                counts['furniture.chairs'] += 1
            elif 'sofa' in object_type:
                counts['furniture.sofas'] += 1
            elif 'shelf' in object_type or 'shelves' in object_type:
                counts['furniture.shelves'] += 1

        self.output_counts = counts
        return counts

    def validate_category(self, category_name, category_data, category_key):
        """Validate a checklist category against placement output"""
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category_name}")
        print(f"{'='*80}")

        category_compliant = True
        checks = []

        for item_key, required_count in category_data.items():
            if item_key.startswith('_'):
                continue

            # Build lookup key
            if category_key == 'architectural_objects':
                lookup_key = f'architectural.{item_key}'
            elif category_key == 'electrical_objects':
                lookup_key = f'electrical.{item_key}'
            elif category_key == 'plumbing_fixtures':
                lookup_key = f'plumbing.{item_key}'
            elif category_key == 'hvac_objects':
                lookup_key = f'hvac.{item_key}'
            elif category_key == 'kitchen_appliances':
                lookup_key = f'kitchen.{item_key}'
            elif category_key == 'furniture_residential':
                lookup_key = f'furniture.{item_key}'
            else:
                lookup_key = item_key

            actual_count = self.output_counts.get(lookup_key, 0)

            # Check compliance
            if required_count == actual_count:
                status = "✅"
                compliant = True
            else:
                status = "❌"
                compliant = False
                category_compliant = False
                self.validation_results['compliant'] = False

            # Display result
            print(f"{status} {item_key}: Required={required_count}, Placed={actual_count}")

            # Record check
            checks.append({
                'item': item_key,
                'required': required_count,
                'actual': actual_count,
                'compliant': compliant,
                'status': status
            })

        # Summary
        passed = sum(1 for c in checks if c['compliant'])
        total = len(checks)
        print(f"\n{category_name}: {passed}/{total} items match ({int(passed/total*100)}%)")

        return category_compliant, checks

    def run_validation(self):
        """Run complete validation"""
        print("\n" + "="*80)
        print("PLACEMENT OUTPUT VALIDATOR")
        print("Checking: CONTRACT (extraction_checklist) == OUTPUT (placement_results)")
        print("="*80)

        # Count placed objects
        print("\n📊 Analyzing placement_results.json...")
        self.count_placed_objects()
        print(f"✅ Found {len(self.placement_data)} placed objects")

        # Validate each category
        categories = [
            ('Architectural Objects', 'architectural_objects'),
            ('Electrical Objects', 'electrical_objects'),
            ('Plumbing Fixtures', 'plumbing_fixtures'),
            ('HVAC Objects', 'hvac_objects'),
            ('Kitchen Appliances', 'kitchen_appliances'),
            ('Furniture', 'furniture_residential')
        ]

        all_checks = []
        for category_name, category_key in categories:
            if category_key in self.contract:
                category_data = self.contract[category_key]
                compliant, checks = self.validate_category(
                    category_name, category_data, category_key
                )
                all_checks.extend(checks)

        # Calculate totals
        electrical_required = sum(
            v for k, v in self.contract.get('electrical_objects', {}).items()
            if not k.startswith('_')
        )
        electrical_placed = sum(
            v for k, v in self.output_counts.items()
            if k.startswith('electrical.')
        )

        plumbing_required = sum(
            v for k, v in self.contract.get('plumbing_fixtures', {}).items()
            if not k.startswith('_')
        )
        plumbing_placed = sum(
            v for k, v in self.output_counts.items()
            if k.startswith('plumbing.')
        )

        # Wall special case (from screenshot)
        walls_placed = self.output_counts.get('walls', 0)

        # Doors and windows
        doors_required = sum(
            v for k, v in self.contract.get('architectural_objects', {}).items()
            if 'door' in k and not k.startswith('_')
        )
        doors_placed = sum(
            v for k, v in self.output_counts.items()
            if 'door' in k
        )

        windows_required = sum(
            v for k, v in self.contract.get('architectural_objects', {}).items()
            if 'window' in k and not k.startswith('_')
        )
        windows_placed = sum(
            v for k, v in self.output_counts.items()
            if 'window' in k
        )

        # Final Summary (like screenshot)
        print("\n" + "="*80)
        print("FINAL VALIDATION SUMMARY")
        print("="*80)
        print(f"\n{'✅' if electrical_placed == electrical_required else '❌'} {electrical_placed} electrical objects placed (required: {electrical_required})")
        print(f"{'✅' if plumbing_placed == plumbing_required else '❌'} {plumbing_placed} plumbing objects placed (required: {plumbing_required})")
        print(f"{'✅' if walls_placed > 0 else '❌'} {walls_placed} walls placed")
        print(f"{'✅' if doors_placed == doors_required else '❌'} {doors_placed} doors placed (required: {doors_required})")
        print(f"{'✅' if windows_placed == windows_required else '❌'} {windows_placed} windows placed (required: {windows_required})")

        # Overall compliance
        print("\n" + "="*80)
        if self.validation_results['compliant']:
            print("✅ CONTRACT FULFILLED: All placement requirements met!")
            print("The Validator Confirms: placement_results == extraction_checklist")
        else:
            print("❌ CONTRACT VIOLATED: Some placement requirements not met")
            print("Review the failures above and regenerate placement_results")
        print("="*80)

        # Save detailed log
        self.validation_results['checks'] = all_checks
        self.validation_results['summary'] = {
            'total_objects_placed': len(self.placement_data),
            'electrical': {'required': electrical_required, 'placed': electrical_placed},
            'plumbing': {'required': plumbing_required, 'placed': plumbing_placed},
            'walls': {'placed': walls_placed},
            'doors': {'required': doors_required, 'placed': doors_placed},
            'windows': {'required': windows_required, 'placed': windows_placed}
        }

        log_path = self.placement_path.parent / f"{self.placement_path.stem}_validation_log.json"
        with open(log_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        print(f"\n📄 Detailed log: {log_path}")

        return self.validation_results['compliant']


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Validate placement output against extraction checklist contract'
    )
    parser.add_argument(
        '--template',
        default='input_templates/TB_LKTN_COMPLETE_template.json',
        help='Path to template JSON (contains extraction_checklist)'
    )
    parser.add_argument(
        '--placement',
        default='TB_LKTN_placement_results.json',
        help='Path to placement_results JSON'
    )

    args = parser.parse_args()

    validator = PlacementValidator(args.template, args.placement)
    validator.load_files()
    compliant = validator.run_validation()

    sys.exit(0 if compliant else 1)


if __name__ == '__main__':
    main()
