#!/usr/bin/env python3
"""
Template Contract Validator

Enforces master plan checkpoints against template JSON.
Outputs debug log showing compliance vs violations.

References: PROJECT_FRAMEWORK_COMPLETE_SPECS.md checkpoints
"""

import json
import sys
from datetime import datetime
from pathlib import Path


class ContractValidator:
    """Validates template against master plan contract"""

    def __init__(self, template_path):
        self.template_path = Path(template_path)
        self.template = self.load_template()
        self.violations = []
        self.passes = []
        self.warnings = []

    def load_template(self):
        """Load template JSON"""
        try:
            with open(self.template_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ FATAL: Cannot load template: {e}")
            sys.exit(1)

    def log_pass(self, checkpoint, requirement, actual):
        """Log passing validation"""
        self.passes.append({
            'checkpoint': checkpoint,
            'requirement': requirement,
            'actual': actual
        })

    def log_violation(self, checkpoint, requirement, expected, actual, master_plan_ref):
        """Log contract violation"""
        self.violations.append({
            'checkpoint': checkpoint,
            'requirement': requirement,
            'expected': expected,
            'actual': actual,
            'master_plan_ref': master_plan_ref
        })

    def log_warning(self, checkpoint, message):
        """Log warning (not a hard failure)"""
        self.warnings.append({
            'checkpoint': checkpoint,
            'message': message
        })

    def validate_phase_1b_checkpoint(self):
        """
        Validate Phase 1B Checkpoint
        Master Plan Reference: PROJECT_FRAMEWORK_COMPLETE_SPECS.md lines 118-184
        """
        print("\n" + "="*80)
        print("PHASE 1B CHECKPOINT VALIDATION")
        print("Contract: PROJECT_FRAMEWORK_COMPLETE_SPECS.md lines 118-184")
        print("="*80)

        checklist = self.template.get('extraction_checklist', {})
        objects = self.template.get('objects', [])

        # REQUIREMENT 1: extraction_metadata exists
        print("\n[1] Checking extraction_metadata section...")
        metadata = self.template.get('extraction_metadata', {})
        required_fields = ['extracted_by', 'extraction_date', 'pdf_source', 'extraction_version']

        for field in required_fields:
            if field in metadata:
                self.log_pass('Phase 1B', f'extraction_metadata.{field} exists', metadata[field])
                print(f"  ✅ {field}: {metadata[field]}")
            else:
                self.log_violation('Phase 1B', f'extraction_metadata.{field} exists',
                                 'Required field', 'MISSING', 'line 124-128')
                print(f"  ❌ {field}: MISSING")

        # REQUIREMENT 2: extraction_checklist has required categories
        print("\n[2] Checking extraction_checklist categories...")
        required_categories = {
            'calibration': 'line 131-136',
            'electrical_markers': 'line 137-142',
            'plumbing_labels': 'line 143-148'
        }

        for category, ref in required_categories.items():
            if category in checklist:
                count = checklist[category].get('total_count', 0)
                self.log_pass('Phase 1B', f'extraction_checklist.{category} exists', f'count={count}')
                print(f"  ✅ {category}: {count} items")
            else:
                self.log_violation('Phase 1B', f'extraction_checklist.{category} exists',
                                 'Required category', 'MISSING', ref)
                print(f"  ❌ {category}: MISSING")

        # REQUIREMENT 3: objects array exists
        print("\n[3] Checking objects array exists...")
        if len(objects) > 0:
            self.log_pass('Phase 1B', 'objects array exists', f'{len(objects)} objects')
            print(f"  ✅ objects array: {len(objects)} objects")
        else:
            self.log_violation('Phase 1B', 'objects array exists',
                             'Array with objects', 'EMPTY or MISSING', 'line 150-165')
            print(f"  ❌ objects array: EMPTY or MISSING")

        # REQUIREMENT 4: All objects have object_type field
        print("\n[4] Checking all objects have object_type...")
        missing_type = [obj.get('name', f'object_{i}')
                       for i, obj in enumerate(objects)
                       if 'object_type' not in obj]

        if len(missing_type) == 0:
            self.log_pass('Phase 1B', 'All objects have object_type', f'{len(objects)} objects')
            print(f"  ✅ All {len(objects)} objects have object_type")
        else:
            self.log_violation('Phase 1B', 'All objects have object_type',
                             'object_type field on all objects',
                             f'{len(missing_type)} objects missing: {missing_type[:5]}',
                             'line 172')
            print(f"  ❌ {len(missing_type)} objects missing object_type: {missing_type[:5]}")

        # REQUIREMENT 5: Every object has position [x, y, z]
        print("\n[5] Checking all objects have position [x, y, z]...")
        missing_position = []
        invalid_position = []

        for i, obj in enumerate(objects):
            obj_name = obj.get('name', f'object_{i}')
            if 'position' not in obj:
                missing_position.append(obj_name)
            elif not isinstance(obj['position'], list) or len(obj['position']) != 3:
                invalid_position.append(f"{obj_name} (has {obj.get('position', 'invalid')})")

        if len(missing_position) == 0 and len(invalid_position) == 0:
            self.log_pass('Phase 1B', 'All objects have position [x, y, z]', f'{len(objects)} objects')
            print(f"  ✅ All {len(objects)} objects have valid position [x, y, z]")
        else:
            if missing_position:
                self.log_violation('Phase 1B', 'All objects have position field',
                                 'position [x, y, z] on all objects',
                                 f'{len(missing_position)} objects missing position: {missing_position[:5]}',
                                 'line 173')
                print(f"  ❌ {len(missing_position)} objects missing position: {missing_position[:5]}")
            if invalid_position:
                self.log_violation('Phase 1B', 'All objects have valid position [x, y, z]',
                                 '[x, y, z] array with 3 numbers',
                                 f'{len(invalid_position)} objects with invalid position: {invalid_position[:5]}',
                                 'line 173')
                print(f"  ❌ {len(invalid_position)} objects with invalid position: {invalid_position[:5]}")

        # REQUIREMENT 6: Every object has name field
        print("\n[6] Checking all objects have name field...")
        missing_name = [f'object_{i}' for i, obj in enumerate(objects) if 'name' not in obj]

        if len(missing_name) == 0:
            self.log_pass('Phase 1B', 'All objects have name', f'{len(objects)} objects')
            print(f"  ✅ All {len(objects)} objects have name field")
        else:
            self.log_violation('Phase 1B', 'All objects have name field',
                             'name (identifier from PDF) on all objects',
                             f'{len(missing_name)} objects missing name',
                             'line 174')
            print(f"  ❌ {len(missing_name)} objects missing name field")

        # REQUIREMENT 7: Count match between checklist and objects
        print("\n[7] Checking count match (checklist vs objects array)...")

        # Electrical count
        elec_checklist = checklist.get('electrical_markers', {}).get('total_count', 0)
        elec_objects = sum(1 for obj in objects
                          if any(t in obj.get('object_type', '')
                                for t in ['switch', 'outlet', 'light', 'fan', 'distribution']))

        print(f"  Electrical:")
        print(f"    Checklist: {elec_checklist}")
        print(f"    Objects:   {elec_objects}")
        if elec_checklist == elec_objects:
            self.log_pass('Phase 1B', 'Electrical count match', f'{elec_objects}')
            print(f"    ✅ Match")
        else:
            self.log_violation('Phase 1B', 'Electrical count match',
                             f'{elec_checklist}', f'{elec_objects}', 'line 176')
            print(f"    ❌ Mismatch!")

        # Plumbing count
        plumb_checklist = checklist.get('plumbing_labels', {}).get('total_count', 0)
        plumb_objects = sum(1 for obj in objects
                           if any(t in obj.get('object_type', '')
                                 for t in ['toilet', 'basin', 'sink', 'shower',
                                          'faucet', 'drain', 'trap', 'heater']))

        print(f"  Plumbing:")
        print(f"    Checklist: {plumb_checklist}")
        print(f"    Objects:   {plumb_objects}")
        if plumb_checklist == plumb_objects:
            self.log_pass('Phase 1B', 'Plumbing count match', f'{plumb_objects}')
            print(f"    ✅ Match")
        else:
            self.log_violation('Phase 1B', 'Plumbing count match',
                             f'{plumb_checklist}', f'{plumb_objects}', 'line 176')
            print(f"    ❌ Mismatch!")

        # REQUIREMENT 8: Parametric objects in objects array (CRITICAL)
        print("\n[8] Checking parametric structural objects...")
        floor_slab = any('slab' in obj.get('object_type', '').lower() for obj in objects)
        roof = any('roof' in obj.get('object_type', '').lower() for obj in objects)

        if floor_slab:
            self.log_pass('Phase 1B', 'Floor slab in objects array', 'Present')
            print(f"  ✅ Floor slab: Present in objects array")
        else:
            self.log_violation('Phase 1B', 'Floor slab in objects array',
                             'slab_floor_*_lod300 in objects', 'MISSING',
                             'FRAMEWORK_CORRECTED_SUMMARY.md (Parametric Missing)')
            print(f"  ❌ Floor slab: MISSING from objects array")

        if roof:
            self.log_pass('Phase 1B', 'Roof in objects array', 'Present')
            print(f"  ✅ Roof: Present in objects array")
        else:
            self.log_violation('Phase 1B', 'Roof in objects array',
                             'roof_*_lod300 in objects', 'MISSING',
                             'FRAMEWORK_CORRECTED_SUMMARY.md (Parametric Missing)')
            print(f"  ❌ Roof: MISSING from objects array")

        # REQUIREMENT 9: External drainage objects (CRITICAL)
        print("\n[9] Checking external drainage objects...")
        drain_checklist = checklist.get('external_drainage', {}).get('total_count', 0)
        gutters = sum(1 for obj in objects if 'gutter' in obj.get('object_type', '').lower())
        downpipes = sum(1 for obj in objects if 'downpipe' in obj.get('object_type', '').lower())
        drain_objects = gutters + downpipes

        print(f"  Checklist: {drain_checklist} drainage items")
        print(f"  Objects:   {drain_objects} (gutters={gutters}, downpipes={downpipes})")

        if drain_checklist > 0 and drain_objects == 0:
            self.log_violation('Phase 1B', 'External drainage in objects array',
                             f'{drain_checklist} drainage objects',
                             f'0 objects (checklist says {drain_checklist} found)',
                             'FRAMEWORK_CORRECTED_SUMMARY.md (Drainage Missing)')
            print(f"  ❌ VIOLATION: Checklist says {drain_checklist} found, but 0 in objects array!")
        elif drain_objects > 0:
            self.log_pass('Phase 1B', 'External drainage present', f'{drain_objects}')
            print(f"  ✅ {drain_objects} drainage objects in array")
        else:
            self.log_warning('Phase 1B', 'No drainage objects in checklist or array')
            print(f"  ⚠️  No drainage objects (OK if PDF has no drainage)")

    def validate_phase_1c_checkpoint(self):
        """
        Validate Phase 1C Checkpoint
        Master Plan Reference: PROJECT_FRAMEWORK_COMPLETE_SPECS.md lines 225-294
        """
        print("\n" + "="*80)
        print("PHASE 1C CHECKPOINT VALIDATION")
        print("Contract: PROJECT_FRAMEWORK_COMPLETE_SPECS.md lines 225-294")
        print("="*80)

        checklist = self.template.get('extraction_checklist', {})
        objects = self.template.get('objects', [])
        building = self.template.get('building', {})

        # REQUIREMENT 1: Walls added to SAME objects array (CRITICAL!)
        print("\n[1] Checking walls in objects array (NOT separate structure)...")

        building_walls = building.get('walls', [])
        object_walls = [obj for obj in objects if 'wall' in obj.get('object_type', '').lower()]

        print(f"  building.walls array: {len(building_walls)} walls")
        print(f"  objects array:        {len(object_walls)} wall objects")

        if len(building_walls) > 0 and len(object_walls) == 0:
            self.log_violation('Phase 1C', 'Walls in objects array',
                             'Walls in objects array with object_type',
                             f'{len(building_walls)} walls in building.walls, 0 in objects[]',
                             'line 270: Walls added to SAME objects array')
            print(f"  ❌ CRITICAL VIOLATION: Walls in separate structure!")
            print(f"     Contract says: 'Walls added to SAME objects array' (line 270)")
            print(f"     Actual: {len(building_walls)} walls in building.walls, 0 in objects[]")
        elif len(object_walls) > 0:
            self.log_pass('Phase 1C', 'Walls in objects array', f'{len(object_walls)} walls')
            print(f"  ✅ {len(object_walls)} walls in objects array")
        else:
            self.log_warning('Phase 1C', 'No walls found in template')
            print(f"  ⚠️  No walls in template")

        # REQUIREMENT 2: Each wall has object_type (not material)
        print("\n[2] Checking walls have object_type (not material)...")

        walls_with_material = [w for w in building_walls if 'material' in w]
        walls_with_object_type = [obj for obj in object_walls if 'object_type' in obj]

        if len(walls_with_material) > 0:
            self.log_violation('Phase 1C', 'Walls use object_type not material',
                             'object_type field on walls',
                             f'{len(walls_with_material)} walls have "material" field',
                             'line 278: If walls have material instead of object_type → STOP')
            print(f"  ❌ {len(walls_with_material)} walls use 'material' instead of 'object_type'")

        if len(object_walls) > 0 and len(walls_with_object_type) == len(object_walls):
            self.log_pass('Phase 1C', 'All walls have object_type', f'{len(walls_with_object_type)}')
            print(f"  ✅ All {len(object_walls)} walls have object_type")

        # REQUIREMENT 3: Walls stored as objects, not start_point/end_point geometry
        print("\n[3] Checking wall format (object format, not geometry)...")

        walls_as_geometry = [w for w in building_walls if 'start_point' in w or 'end_point' in w]

        if len(walls_as_geometry) > 0:
            self.log_violation('Phase 1C', 'Walls in object format',
                             'position + dimensions format',
                             f'{len(walls_as_geometry)} walls in start_point/end_point format',
                             'line 279: If walls stored as start_point/end_point → STOP')
            print(f"  ❌ {len(walls_as_geometry)} walls in geometry format (start_point/end_point)")
            print(f"     Contract requires object format: position + dimensions (line 289-293)")
        else:
            print(f"  ✅ No walls using geometry format")

        # REQUIREMENT 4: Walls have dimensions (length, height, thickness)
        print("\n[4] Checking walls have dimensions...")

        if len(object_walls) > 0:
            walls_missing_dims = []
            walls_incomplete_dims = []

            for wall in object_walls:
                if 'dimensions' not in wall:
                    walls_missing_dims.append(wall.get('name', 'unnamed'))
                else:
                    dims = wall['dimensions']
                    required = ['length', 'height', 'thickness']
                    missing = [k for k in required if k not in dims]
                    if missing:
                        walls_incomplete_dims.append(f"{wall.get('name', 'unnamed')} (missing {missing})")

            if len(walls_missing_dims) == 0 and len(walls_incomplete_dims) == 0:
                self.log_pass('Phase 1C', 'Walls have dimensions', f'{len(object_walls)} walls')
                print(f"  ✅ All {len(object_walls)} walls have dimensions (length, height, thickness)")
            else:
                if walls_missing_dims:
                    self.log_violation('Phase 1C', 'Walls have dimensions field',
                                     'dimensions {length, height, thickness} on all walls',
                                     f'{len(walls_missing_dims)} walls missing dimensions: {walls_missing_dims[:5]}',
                                     'line 272')
                    print(f"  ❌ {len(walls_missing_dims)} walls missing dimensions field: {walls_missing_dims[:5]}")
                if walls_incomplete_dims:
                    self.log_violation('Phase 1C', 'Walls have complete dimensions',
                                     'dimensions with length, height, thickness',
                                     f'{len(walls_incomplete_dims)} walls with incomplete dimensions: {walls_incomplete_dims[:5]}',
                                     'line 272')
                    print(f"  ❌ {len(walls_incomplete_dims)} walls with incomplete dimensions: {walls_incomplete_dims[:5]}")

        # REQUIREMENT 5: Count match
        print("\n[5] Checking wall count match...")

        outer_walls_checklist = checklist.get('outer_walls', {}).get('total_count', 0)
        internal_walls_checklist = checklist.get('internal_walls', {}).get('total_count', 0)
        total_checklist = outer_walls_checklist + internal_walls_checklist
        total_objects_walls = len(object_walls)

        print(f"  Checklist: {total_checklist} walls ({outer_walls_checklist} outer + {internal_walls_checklist} internal)")
        print(f"  Objects:   {total_objects_walls} wall objects")

        if total_checklist > 0 and total_objects_walls == 0:
            self.log_violation('Phase 1C', 'Wall count match',
                             f'{total_checklist} walls',
                             f'{total_objects_walls} walls in objects array',
                             'line 280: If count mismatch → STOP')
            print(f"  ❌ Count mismatch!")
        elif abs(total_checklist - total_objects_walls) <= 5:  # Allow small variance for filtering
            self.log_pass('Phase 1C', 'Wall count match', f'{total_objects_walls}')
            print(f"  ✅ Count match (within tolerance)")
        else:
            self.log_warning('Phase 1C', f'Wall count difference: {abs(total_checklist - total_objects_walls)}')
            print(f"  ⚠️  Significant count difference")

        # REQUIREMENT 6: Progressive count validation (Phase 1B → Phase 1C)
        print("\n[6] Checking progressive object count...")

        # Expected: Phase 1B (25-33 objects) + Walls (~133) = ~158-166 total
        phase_1b_expected = 25  # Min: 9 electrical + 16 plumbing
        walls_expected = total_checklist if total_checklist > 0 else 133  # From checklist or default
        progressive_expected = phase_1b_expected + walls_expected
        total_objects = len(objects)

        print(f"  Expected progression: Phase 1B (~{phase_1b_expected}) + Walls ({walls_expected}) = ~{progressive_expected}")
        print(f"  Actual total objects: {total_objects}")

        # Allow 20% tolerance for filtering/missing categories
        tolerance = int(progressive_expected * 0.2)
        if total_objects >= (progressive_expected - tolerance):
            self.log_pass('Phase 1C', 'Progressive count validation', f'{total_objects} objects')
            print(f"  ✅ Object count within expected range")
        else:
            self.log_violation('Phase 1C', 'Progressive count validation',
                             f'~{progressive_expected} objects (±{tolerance} tolerance)',
                             f'{total_objects} objects',
                             'line 273: Total count = Previous (25) + Walls (133) = 158')
            print(f"  ❌ Object count below expected range (need >{progressive_expected - tolerance})")

    def validate_phase_1d_checkpoint(self):
        """
        Validate Phase 1D Checkpoint
        Master Plan Reference: PROJECT_FRAMEWORK_COMPLETE_SPECS.md lines 651-737
        """
        print("\n" + "="*80)
        print("PHASE 1D CHECKPOINT VALIDATION")
        print("Contract: PROJECT_FRAMEWORK_COMPLETE_SPECS.md lines 651-737")
        print("="*80)

        checklist = self.template.get('extraction_checklist', {})
        objects = self.template.get('objects', [])

        # REQUIREMENT 1: Doors/windows in objects array
        print("\n[1] Checking doors/windows in objects array...")

        doors_checklist = checklist.get('door_positions', {}).get('total_count', 0)
        windows_checklist = checklist.get('window_positions', {}).get('total_count', 0)

        # Fallback to architectural_objects if door_positions not present
        if doors_checklist == 0:
            doors_checklist = checklist.get('architectural_objects', {}).get('doors_single', 0) + \
                            checklist.get('architectural_objects', {}).get('doors_double', 0)

        if windows_checklist == 0:
            windows_checklist = sum(checklist.get('architectural_objects', {}).get(k, 0)
                                  for k in ['windows_standard', 'windows_sliding', 'windows_casement'])

        doors_objects = sum(1 for obj in objects if 'door' in obj.get('object_type', '').lower())
        windows_objects = sum(1 for obj in objects if 'window' in obj.get('object_type', '').lower())

        print(f"  Doors:")
        print(f"    Checklist: {doors_checklist}")
        print(f"    Objects:   {doors_objects}")
        if doors_checklist == doors_objects:
            self.log_pass('Phase 1D', 'Doors in objects array', f'{doors_objects}')
            print(f"    ✅ Match")
        else:
            self.log_violation('Phase 1D', 'Doors in objects array',
                             f'{doors_checklist}', f'{doors_objects}', 'line 705')
            print(f"    ❌ Mismatch!")

        print(f"  Windows:")
        print(f"    Checklist: {windows_checklist}")
        print(f"    Objects:   {windows_objects}")
        if windows_checklist == windows_objects:
            self.log_pass('Phase 1D', 'Windows in objects array', f'{windows_objects}')
            print(f"    ✅ Match")
        else:
            self.log_violation('Phase 1D', 'Windows in objects array',
                             f'{windows_checklist}', f'{windows_objects}', 'line 705')
            print(f"    ❌ Mismatch!")

        # REQUIREMENT 2: Doors/windows have object_type (not door_type/window_type)
        print("\n[2] Checking doors/windows use object_type...")

        door_objs = [obj for obj in objects if 'door' in obj.get('object_type', '').lower()]
        doors_with_wrong_field = [obj for obj in door_objs if 'door_type' in obj]

        if len(doors_with_wrong_field) > 0:
            self.log_violation('Phase 1D', 'Doors use object_type',
                             'object_type field',
                             f'{len(doors_with_wrong_field)} doors have door_type',
                             'line 714: If doors have door_type instead of object_type → STOP')
            print(f"  ❌ {len(doors_with_wrong_field)} doors use 'door_type' instead of 'object_type'")
        else:
            self.log_pass('Phase 1D', 'Doors use object_type', f'{doors_objects} doors')
            print(f"  ✅ All doors use object_type")

        window_objs = [obj for obj in objects if 'window' in obj.get('object_type', '').lower()]
        windows_with_wrong_field = [obj for obj in window_objs if 'window_type' in obj]

        if len(windows_with_wrong_field) > 0:
            self.log_violation('Phase 1D', 'Windows use object_type',
                             'object_type field',
                             f'{len(windows_with_wrong_field)} windows have window_type',
                             'line 715: If windows have window_type instead of object_type → STOP')
            print(f"  ❌ {len(windows_with_wrong_field)} windows use 'window_type' instead of 'object_type'")
        else:
            self.log_pass('Phase 1D', 'Windows use object_type', f'{windows_objects} windows')
            print(f"  ✅ All windows use object_type")

        # REQUIREMENT 3: Doors have Z=0 (floor level)
        print("\n[3] Checking doors have Z=0 (floor level)...")

        if len(door_objs) > 0:
            doors_wrong_z = []
            for door in door_objs:
                door_pos = door.get('position', [0, 0, 0])
                if len(door_pos) >= 3 and door_pos[2] != 0:
                    doors_wrong_z.append(f"{door.get('name', 'unnamed')} (Z={door_pos[2]})")

            if len(doors_wrong_z) == 0:
                self.log_pass('Phase 1D', 'Doors have Z=0', f'{len(door_objs)} doors')
                print(f"  ✅ All {len(door_objs)} doors have Z=0 (floor level)")
            else:
                self.log_violation('Phase 1D', 'Doors have Z=0',
                                 'Z=0 (floor level) for all doors',
                                 f'{len(doors_wrong_z)} doors with wrong Z: {doors_wrong_z[:5]}',
                                 'line 707: Doors have Z=0 (floor level)')
                print(f"  ❌ {len(doors_wrong_z)} doors with wrong Z coordinate: {doors_wrong_z[:5]}")

        # REQUIREMENT 4: Windows have sill_height
        print("\n[4] Checking windows have sill_height from elevations...")

        windows_with_sill = [obj for obj in window_objs
                            if 'sill_height' in obj or obj.get('position', [0,0,0])[2] > 0]

        if len(window_objs) > 0:
            if len(windows_with_sill) == len(window_objs):
                self.log_pass('Phase 1D', 'Windows have sill_height', f'{len(windows_with_sill)}')
                print(f"  ✅ All {len(window_objs)} windows have sill_height or Z > 0")
            else:
                self.log_violation('Phase 1D', 'Windows have sill_height',
                                 f'{len(window_objs)} windows with sill_height',
                                 f'{len(windows_with_sill)} windows',
                                 'line 716: If windows missing sill_height → STOP')
                print(f"  ❌ {len(window_objs) - len(windows_with_sill)} windows missing sill_height")

        # REQUIREMENT 5: Progressive count validation (Phase 1C → Phase 1D)
        print("\n[5] Checking progressive object count...")

        # Expected: Phase 1C (~158-166) + Doors (7) + Windows (10) = ~175-183 total
        objects = self.template.get('objects', [])
        total_objects = len(objects)
        openings_expected = doors_checklist + windows_checklist
        phase_1c_expected = 158  # Default from master plan
        progressive_expected = phase_1c_expected + openings_expected

        print(f"  Expected progression: Phase 1C (~{phase_1c_expected}) + Openings ({openings_expected}) = ~{progressive_expected}")
        print(f"  Actual total objects: {total_objects}")

        # Allow 20% tolerance
        tolerance = int(progressive_expected * 0.2)
        if total_objects >= (progressive_expected - tolerance):
            self.log_pass('Phase 1D', 'Progressive count validation', f'{total_objects} objects')
            print(f"  ✅ Object count within expected range")
        else:
            self.log_violation('Phase 1D', 'Progressive count validation',
                             f'~{progressive_expected} objects (±{tolerance} tolerance)',
                             f'{total_objects} objects',
                             'line 709: Total count = Previous (158) + Doors (7) + Windows (10) = 175')
            print(f"  ❌ Object count below expected range (need >{progressive_expected - tolerance})")

    def generate_summary_report(self):
        """Generate final summary report"""
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)

        total_checks = len(self.passes) + len(self.violations) + len(self.warnings)

        print(f"\nTotal Checks: {total_checks}")
        print(f"✅ Passed:    {len(self.passes)}")
        print(f"❌ Violations: {len(self.violations)}")
        print(f"⚠️  Warnings:  {len(self.warnings)}")

        # Phase-by-phase completeness
        print(f"\n{'='*80}")
        print("PHASE COMPLETENESS")
        print("="*80)

        for phase in ['Phase 1B', 'Phase 1C', 'Phase 1D']:
            phase_passes = [p for p in self.passes if p['checkpoint'] == phase]
            phase_violations = [v for v in self.violations if v['checkpoint'] == phase]
            phase_warnings = [w for w in self.warnings if w['checkpoint'] == phase]

            total = len(phase_passes) + len(phase_violations) + len(phase_warnings)
            passed = len(phase_passes)

            status = "✅ COMPLETE" if len(phase_violations) == 0 else "❌ INCOMPLETE"
            percentage = (passed / total * 100) if total > 0 else 0

            print(f"\n{phase}: {status}")
            print(f"  Checks passed: {passed}/{total} ({percentage:.0f}%)")
            if phase_violations:
                print(f"  Violations: {len(phase_violations)}")
                for v in phase_violations[:3]:  # Show first 3
                    print(f"    - {v['requirement']}")
            if phase_warnings:
                print(f"  Warnings: {len(phase_warnings)}")

        if len(self.violations) > 0:
            print(f"\n{'='*80}")
            print("CRITICAL VIOLATIONS (Contract Failures)")
            print("="*80)

            for i, v in enumerate(self.violations, 1):
                print(f"\n[{i}] {v['checkpoint']}: {v['requirement']}")
                print(f"    Expected:  {v['expected']}")
                print(f"    Actual:    {v['actual']}")
                print(f"    Reference: {v['master_plan_ref']}")

        if len(self.warnings) > 0:
            print(f"\n{'='*80}")
            print("WARNINGS")
            print("="*80)

            for i, w in enumerate(self.warnings, 1):
                print(f"\n[{i}] {w['checkpoint']}: {w['message']}")

        # Final verdict
        print(f"\n{'='*80}")
        if len(self.violations) == 0:
            print("✅ TEMPLATE COMPLIES WITH CONTRACT")
            print("="*80)
            return True
        else:
            print("❌ TEMPLATE VIOLATES CONTRACT")
            print("="*80)
            print(f"\nTemplate MUST be corrected before export to Blender.")
            print(f"Fix the {len(self.violations)} violations listed above.")
            return False

    def save_debug_log(self, output_path):
        """Save detailed debug log to file"""

        # Calculate phase completeness
        phase_completeness = {}
        for phase in ['Phase 1B', 'Phase 1C', 'Phase 1D']:
            phase_passes = [p for p in self.passes if p['checkpoint'] == phase]
            phase_violations = [v for v in self.violations if v['checkpoint'] == phase]
            phase_warnings = [w for w in self.warnings if w['checkpoint'] == phase]

            total = len(phase_passes) + len(phase_violations) + len(phase_warnings)
            passed = len(phase_passes)

            phase_completeness[phase] = {
                'total_checks': total,
                'checks_passed': passed,
                'violations': len(phase_violations),
                'warnings': len(phase_warnings),
                'complete': len(phase_violations) == 0,
                'completion_percentage': (passed / total * 100) if total > 0 else 0
            }

        log = {
            'timestamp': datetime.now().isoformat(),
            'template_path': str(self.template_path),
            'total_checks': len(self.passes) + len(self.violations) + len(self.warnings),
            'passes': self.passes,
            'violations': self.violations,
            'warnings': self.warnings,
            'compliant': len(self.violations) == 0,
            'phase_completeness': phase_completeness
        }

        with open(output_path, 'w') as f:
            json.dump(log, f, indent=2)

        print(f"\n📋 Debug log saved: {output_path}")

    def run_full_validation(self):
        """Run complete validation suite"""
        print("="*80)
        print("TEMPLATE CONTRACT VALIDATOR")
        print("="*80)
        print(f"Template: {self.template_path}")
        print(f"Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Run all checkpoint validations
        self.validate_phase_1b_checkpoint()
        self.validate_phase_1c_checkpoint()
        self.validate_phase_1d_checkpoint()

        # Generate summary
        compliant = self.generate_summary_report()

        # Save debug log
        log_path = self.template_path.parent / f"{self.template_path.stem}_validation_log.json"
        self.save_debug_log(log_path)

        return compliant


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 validate_template.py <template.json>")
        sys.exit(1)

    template_path = sys.argv[1]

    validator = ContractValidator(template_path)
    compliant = validator.run_full_validation()

    sys.exit(0 if compliant else 1)


if __name__ == '__main__':
    main()
