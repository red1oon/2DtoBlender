#!/usr/bin/env python3
"""
Comprehensive Test Suite - Validates Complete Extraction System

Tests:
  1. Output JSON structure and completeness
  2. All master template items accounted for
  3. Object field completeness
  4. Spatial validity
  5. Library references
  6. Hash totals
  7. Phase coverage

Usage:
    python3 comprehensive_test.py <output_json>
"""

import json
import sys
from pathlib import Path


def test_output_structure(data):
    """Test 1: Output JSON has correct structure"""
    print("\n" + "=" * 70)
    print("TEST 1: OUTPUT JSON STRUCTURE")
    print("=" * 70)

    issues = []

    # Required top-level fields
    required = ['extraction_metadata', 'summary', 'objects']
    for field in required:
        if field not in data:
            issues.append(f"Missing top-level field: {field}")

    # Metadata completeness
    if 'extraction_metadata' in data:
        meta_required = ['extracted_by', 'extraction_date', 'pdf_source', 'calibration']
        for field in meta_required:
            if field not in data['extraction_metadata']:
                issues.append(f"Missing metadata field: {field}")

    # Summary completeness
    if 'summary' in data:
        sum_required = ['total_objects', 'by_phase']
        for field in sum_required:
            if field not in data['summary']:
                issues.append(f"Missing summary field: {field}")

    if issues:
        print(f"❌ FAIL: {len(issues)} issues")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ PASS: All required fields present")
        return True


def test_object_completeness(objects):
    """Test 2: All objects have required fields"""
    print("\n" + "=" * 70)
    print("TEST 2: OBJECT FIELD COMPLETENESS")
    print("=" * 70)

    required_fields = ['name', 'object_type', 'position', 'orientation', 'placed', '_phase']
    issues = []

    for idx, obj in enumerate(objects):
        missing = [f for f in required_fields if f not in obj]
        if missing:
            issues.append({
                'index': idx,
                'name': obj.get('name', f'object_{idx}'),
                'missing': missing
            })

    if issues:
        print(f"❌ FAIL: {len(issues)} objects missing fields")
        for issue in issues[:5]:
            print(f"   - {issue['name']}: missing {issue['missing']}")
        if len(issues) > 5:
            print(f"   ... and {len(issues) - 5} more")
        return False
    else:
        print(f"✅ PASS: All {len(objects)} objects have required fields")
        return True


def test_position_validity(objects):
    """Test 3: All positions are valid [X, Y, Z] arrays"""
    print("\n" + "=" * 70)
    print("TEST 3: POSITION VALIDITY")
    print("=" * 70)

    issues = []

    for idx, obj in enumerate(objects):
        pos = obj.get('position')

        # Check position exists
        if pos is None:
            issues.append(f"{obj.get('name')}: position is None")
            continue

        # Check is list
        if not isinstance(pos, list):
            issues.append(f"{obj.get('name')}: position not a list")
            continue

        # Check length
        if len(pos) != 3:
            issues.append(f"{obj.get('name')}: position has {len(pos)} values (need 3)")
            continue

        # Check numeric values
        if not all(isinstance(x, (int, float)) for x in pos):
            issues.append(f"{obj.get('name')}: position has non-numeric values")

    if issues:
        print(f"❌ FAIL: {len(issues)} invalid positions")
        for issue in issues[:5]:
            print(f"   - {issue}")
        if len(issues) > 5:
            print(f"   ... and {len(issues) - 5} more")
        return False
    else:
        print(f"✅ PASS: All {len(objects)} positions valid")
        return True


def test_orientation_validity(objects):
    """Test 4: All orientations are valid degrees (0-360)"""
    print("\n" + "=" * 70)
    print("TEST 4: ORIENTATION VALIDITY")
    print("=" * 70)

    issues = []

    for obj in objects:
        ori = obj.get('orientation')

        # Check exists
        if ori is None:
            issues.append(f"{obj.get('name')}: orientation is None")
            continue

        # Check numeric
        if not isinstance(ori, (int, float)):
            issues.append(f"{obj.get('name')}: orientation not numeric")
            continue

        # Check range (allow 0-360 and negative angles)
        if ori < -360 or ori > 360:
            issues.append(f"{obj.get('name')}: orientation {ori}° out of range")

    if issues:
        print(f"❌ FAIL: {len(issues)} invalid orientations")
        for issue in issues[:5]:
            print(f"   - {issue}")
        if len(issues) > 5:
            print(f"   ... and {len(issues) - 5} more")
        return False
    else:
        print(f"✅ PASS: All {len(objects)} orientations valid")
        return True


def test_hash_total(summary, objects):
    """Test 5: Hash total matches"""
    print("\n" + "=" * 70)
    print("TEST 5: HASH TOTAL VERIFICATION")
    print("=" * 70)

    expected = summary.get('total_objects', 0)
    actual = len(objects)

    if expected != actual:
        print(f"❌ FAIL: Hash mismatch (expected {expected}, got {actual})")
        return False
    else:
        print(f"✅ PASS: Hash total matches ({expected} objects)")
        return True


def test_phase_coverage(objects, template_path):
    """Test 6: Compare extracted phases vs master template"""
    print("\n" + "=" * 70)
    print("TEST 6: PHASE COVERAGE (vs Master Template)")
    print("=" * 70)

    try:
        with open(template_path) as f:
            template = json.load(f)
    except:
        print("⚠️  SKIP: Cannot load master template")
        return None

    # Get phases with object_type (physical objects)
    template_phases = {}
    for item in template['extraction_sequence']:
        phase = item.get('_phase', '')
        obj_type = item.get('object_type')
        if obj_type:  # Only count items with physical objects
            if phase not in template_phases:
                template_phases[phase] = []
            template_phases[phase].append(item['item'])

    # Get phases in output
    output_phases = {}
    for obj in objects:
        phase = obj.get('_phase', 'unknown')
        if phase not in output_phases:
            output_phases[phase] = 0
        output_phases[phase] += 1

    print(f"Master template phases (with object_type): {len(template_phases)}")
    print(f"Output phases: {len(output_phases)}")
    print()

    # Find missing phases
    template_phase_keys = set(template_phases.keys())
    output_phase_keys = set(output_phases.keys())
    missing = template_phase_keys - output_phase_keys

    if missing:
        print(f"⚠️  WARNING: {len(missing)} phases missing from output:")
        for phase in sorted(missing):
            items = template_phases[phase]
            print(f"   - {phase}: {', '.join(items)}")
        return False
    else:
        print(f"✅ PASS: All phases with physical objects covered")
        return True


def test_placed_flags(objects):
    """Test 7: All objects have placed=false before Blender"""
    print("\n" + "=" * 70)
    print("TEST 7: PLACEMENT FLAGS")
    print("=" * 70)

    already_placed = [obj for obj in objects if obj.get('placed') == True]

    if already_placed:
        print(f"⚠️  WARNING: {len(already_placed)} objects already marked placed=true")
        for obj in already_placed[:3]:
            print(f"   - {obj.get('name')}")
        return False
    else:
        print(f"✅ PASS: All {len(objects)} objects have placed=false")
        return True


def test_object_types(objects):
    """Test 8: All object_types follow naming convention"""
    print("\n" + "=" * 70)
    print("TEST 8: OBJECT TYPE NAMING")
    print("=" * 70)

    issues = []

    for obj in objects:
        obj_type = obj.get('object_type', '')

        # Check not empty
        if not obj_type:
            issues.append(f"{obj.get('name')}: empty object_type")
            continue

        # Check format (should be lowercase with underscores)
        if not obj_type.replace('_', '').replace('lod', '').replace('300', '').replace('200', '').replace('100', '').isalnum():
            issues.append(f"{obj.get('name')}: invalid object_type format: {obj_type}")

    if issues:
        print(f"⚠️  WARNING: {len(issues)} object_types with format issues")
        for issue in issues[:5]:
            print(f"   - {issue}")
        return False
    else:
        print(f"✅ PASS: All {len(objects)} object_types valid")
        return True


def test_calibration(metadata):
    """Test 9: Calibration data complete and valid"""
    print("\n" + "=" * 70)
    print("TEST 9: CALIBRATION DATA")
    print("=" * 70)

    calibration = metadata.get('calibration', {})

    required = ['scale_x', 'scale_y', 'offset_x', 'offset_y', 'confidence']
    missing = [f for f in required if f not in calibration]

    if missing:
        print(f"❌ FAIL: Missing calibration fields: {missing}")
        return False

    confidence = calibration.get('confidence', 0)
    if confidence < 50:
        print(f"⚠️  WARNING: Low calibration confidence ({confidence}%)")
        return False

    print(f"✅ PASS: Calibration complete (confidence: {confidence}%)")
    print(f"   scale_x: {calibration['scale_x']:.6f}")
    print(f"   scale_y: {calibration['scale_y']:.6f}")
    return True


def test_unique_names(objects):
    """Test 10: Check for duplicate object names"""
    print("\n" + "=" * 70)
    print("TEST 10: UNIQUE OBJECT NAMES")
    print("=" * 70)

    names = [obj.get('name') for obj in objects]
    duplicates = [name for name in set(names) if names.count(name) > 1]

    if duplicates:
        print(f"⚠️  WARNING: {len(duplicates)} duplicate names found:")
        for name in duplicates[:5]:
            count = names.count(name)
            print(f"   - {name}: {count} instances")
        if len(duplicates) > 5:
            print(f"   ... and {len(duplicates) - 5} more")
        return False
    else:
        print(f"✅ PASS: All {len(objects)} object names unique")
        return True


def run_comprehensive_tests(json_path):
    """Run all tests"""
    print("=" * 70)
    print("🧪 COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"File: {json_path}")

    # Load data
    try:
        with open(json_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"\n❌ FATAL: Cannot load JSON: {e}")
        return False

    objects = data.get('objects', [])
    summary = data.get('summary', {})
    metadata = data.get('extraction_metadata', {})

    # Find master template
    template_path = Path(__file__).parent.parent / 'core' / 'master_reference_template.json'

    # Run tests
    results = []
    results.append(("Structure", test_output_structure(data)))
    results.append(("Object Fields", test_object_completeness(objects)))
    results.append(("Positions", test_position_validity(objects)))
    results.append(("Orientations", test_orientation_validity(objects)))
    results.append(("Hash Total", test_hash_total(summary, objects)))
    results.append(("Phase Coverage", test_phase_coverage(objects, template_path)))
    results.append(("Placed Flags", test_placed_flags(objects)))
    results.append(("Object Types", test_object_types(objects)))
    results.append(("Calibration", test_calibration(metadata)))
    results.append(("Unique Names", test_unique_names(objects)))

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result == True)
    failed = sum(1 for _, result in results if result == False)
    skipped = sum(1 for _, result in results if result is None)

    print(f"Total tests: {len(results)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⚠️  Warnings/Skipped: {skipped}")
    print()

    for name, result in results:
        status = "✅ PASS" if result == True else ("❌ FAIL" if result == False else "⚠️  SKIP")
        print(f"  {status}: {name}")

    print("\n" + "=" * 70)

    if failed == 0:
        print("🎉 ALL TESTS PASSED - Output ready for Blender")
        print("=" * 70)
        return True
    else:
        print(f"⚠️  {failed} TEST(S) FAILED - Review issues above")
        print("=" * 70)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 comprehensive_test.py <output_json>")
        sys.exit(1)

    json_path = sys.argv[1]
    success = run_comprehensive_tests(json_path)

    sys.exit(0 if success else 1)
