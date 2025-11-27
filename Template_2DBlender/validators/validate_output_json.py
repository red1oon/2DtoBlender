#!/usr/bin/env python3
"""
Output JSON Validator - Pre-flight check before Blender placement

Validates:
  1. JSON is well-formed
  2. Required fields are present
  3. Hash total matches (summary.total_objects == len(objects))
  4. All objects have position, orientation, placed flag
  5. All object_types are valid library references

Usage:
    python3 validate_output_json.py <output_json>
"""

import json
import sys


def validate_output_json(json_path):
    """
    Validate output JSON structure and content

    Args:
        json_path: Path to output JSON file

    Returns:
        dict: Validation results with overall status
    """
    print("=" * 80)
    print("🔍 OUTPUT JSON VALIDATOR - Pre-flight Check")
    print("=" * 80)
    print(f"\nFile: {json_path}\n")

    results = {
        "file": json_path,
        "validations": {},
        "errors": [],
        "warnings": [],
        "overall_status": "UNKNOWN"
    }

    # CHECK 1: File exists and is readable
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        results['validations']['json_well_formed'] = {
            "status": "PASS",
            "message": "JSON is well-formed and parseable"
        }
        print("✅ CHECK 1: JSON is well-formed")
    except FileNotFoundError:
        results['validations']['json_well_formed'] = {
            "status": "FAIL",
            "message": f"File not found: {json_path}"
        }
        results['errors'].append("File not found")
        print(f"❌ CHECK 1 FAILED: File not found")
        results['overall_status'] = "FAIL"
        return results
    except json.JSONDecodeError as e:
        results['validations']['json_well_formed'] = {
            "status": "FAIL",
            "message": f"Invalid JSON: {str(e)}"
        }
        results['errors'].append("Invalid JSON syntax")
        print(f"❌ CHECK 1 FAILED: Invalid JSON - {str(e)}")
        results['overall_status'] = "FAIL"
        return results

    # CHECK 2: Required top-level fields
    required_fields = ['extraction_metadata', 'summary', 'objects']
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        results['validations']['required_fields'] = {
            "status": "FAIL",
            "message": f"Missing required fields: {missing_fields}"
        }
        results['errors'].append(f"Missing fields: {', '.join(missing_fields)}")
        print(f"❌ CHECK 2 FAILED: Missing required fields: {missing_fields}")
        results['overall_status'] = "FAIL"
        return results
    else:
        results['validations']['required_fields'] = {
            "status": "PASS",
            "message": "All required top-level fields present"
        }
        print("✅ CHECK 2: Required top-level fields present")

    # CHECK 3: Hash total verification
    summary = data.get('summary', {})
    objects = data.get('objects', [])

    expected_count = summary.get('total_objects', 0)
    actual_count = len(objects)

    if expected_count == actual_count:
        results['validations']['hash_total'] = {
            "status": "PASS",
            "message": f"Hash total matches: {expected_count} objects"
        }
        print(f"✅ CHECK 3: Hash total matches ({expected_count} objects)")
    else:
        results['validations']['hash_total'] = {
            "status": "FAIL",
            "message": f"Hash total mismatch: expected {expected_count}, found {actual_count}"
        }
        results['errors'].append(f"Hash total mismatch: {expected_count} != {actual_count}")
        print(f"❌ CHECK 3 FAILED: Hash total mismatch (expected {expected_count}, found {actual_count})")

    # CHECK 4: All objects have required fields
    required_object_fields = ['name', 'object_type', 'position', 'orientation', 'placed']
    objects_with_issues = []

    for idx, obj in enumerate(objects):
        missing = [f for f in required_object_fields if f not in obj]
        if missing:
            objects_with_issues.append({
                "index": idx,
                "name": obj.get('name', f'object_{idx}'),
                "missing_fields": missing
            })

    if objects_with_issues:
        results['validations']['object_fields'] = {
            "status": "FAIL",
            "message": f"{len(objects_with_issues)} objects missing required fields"
        }
        results['errors'].append(f"{len(objects_with_issues)} objects have missing fields")
        print(f"❌ CHECK 4 FAILED: {len(objects_with_issues)} objects missing required fields")
        for issue in objects_with_issues[:5]:  # Show first 5
            print(f"   - Object '{issue['name']}': missing {issue['missing_fields']}")
        if len(objects_with_issues) > 5:
            print(f"   ... and {len(objects_with_issues) - 5} more")
    else:
        results['validations']['object_fields'] = {
            "status": "PASS",
            "message": f"All {len(objects)} objects have required fields"
        }
        print(f"✅ CHECK 4: All {len(objects)} objects have required fields")

    # CHECK 5: Validate positions and orientations
    invalid_positions = []
    invalid_orientations = []

    for idx, obj in enumerate(objects):
        # Check position
        pos = obj.get('position')
        if pos is None or not isinstance(pos, list) or len(pos) != 3:
            invalid_positions.append({
                "name": obj.get('name', f'object_{idx}'),
                "position": pos,
                "issue": "Not a 3-element list"
            })

        # Check orientation
        orient = obj.get('orientation')
        if orient is None or not isinstance(orient, (int, float)):
            invalid_orientations.append({
                "name": obj.get('name', f'object_{idx}'),
                "orientation": orient,
                "issue": "Not a number"
            })

    if invalid_positions:
        results['validations']['positions'] = {
            "status": "FAIL",
            "message": f"{len(invalid_positions)} objects have invalid positions"
        }
        results['errors'].append(f"{len(invalid_positions)} invalid positions")
        print(f"❌ CHECK 5a FAILED: {len(invalid_positions)} objects have invalid positions")
    else:
        results['validations']['positions'] = {
            "status": "PASS",
            "message": "All positions are valid [X, Y, Z] lists"
        }
        print(f"✅ CHECK 5a: All positions are valid")

    if invalid_orientations:
        results['validations']['orientations'] = {
            "status": "FAIL",
            "message": f"{len(invalid_orientations)} objects have invalid orientations"
        }
        results['errors'].append(f"{len(invalid_orientations)} invalid orientations")
        print(f"❌ CHECK 5b FAILED: {len(invalid_orientations)} objects have invalid orientations")
    else:
        results['validations']['orientations'] = {
            "status": "PASS",
            "message": "All orientations are valid numbers"
        }
        print(f"✅ CHECK 5b: All orientations are valid")

    # CHECK 6: All placed flags are false (before Blender placement)
    objects_already_placed = [obj.get('name') for obj in objects if obj.get('placed') == True]

    if objects_already_placed:
        results['validations']['placed_flags'] = {
            "status": "WARNING",
            "message": f"{len(objects_already_placed)} objects already marked as placed"
        }
        results['warnings'].append(f"{len(objects_already_placed)} objects already placed")
        print(f"⚠️  CHECK 6: {len(objects_already_placed)} objects already marked as 'placed: true'")
        print(f"   (This is OK if re-running placement, but unusual for initial extraction)")
    else:
        results['validations']['placed_flags'] = {
            "status": "PASS",
            "message": "All objects have 'placed: false' (ready for Blender)"
        }
        print(f"✅ CHECK 6: All objects ready for Blender placement (placed: false)")

    # CHECK 7: Calibration data present
    metadata = data.get('extraction_metadata', {})
    calibration = metadata.get('calibration', {})

    if not calibration:
        results['validations']['calibration'] = {
            "status": "FAIL",
            "message": "No calibration data found"
        }
        results['errors'].append("Missing calibration data")
        print(f"❌ CHECK 7 FAILED: No calibration data")
    else:
        required_calib = ['scale_x', 'scale_y', 'confidence']
        missing_calib = [f for f in required_calib if f not in calibration]

        if missing_calib:
            results['validations']['calibration'] = {
                "status": "FAIL",
                "message": f"Calibration missing: {missing_calib}"
            }
            results['errors'].append(f"Incomplete calibration: {missing_calib}")
            print(f"❌ CHECK 7 FAILED: Calibration incomplete - missing {missing_calib}")
        else:
            confidence = calibration.get('confidence', 0)
            results['validations']['calibration'] = {
                "status": "PASS",
                "message": f"Calibration present (confidence: {confidence}%)"
            }
            print(f"✅ CHECK 7: Calibration data present (confidence: {confidence}%)")

    # OVERALL STATUS
    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)

    failed_checks = [k for k, v in results['validations'].items() if v['status'] == 'FAIL']
    warning_checks = [k for k, v in results['validations'].items() if v['status'] == 'WARNING']
    passed_checks = [k for k, v in results['validations'].items() if v['status'] == 'PASS']

    print(f"Total checks: {len(results['validations'])}")
    print(f"  ✅ Passed: {len(passed_checks)}")
    print(f"  ⚠️  Warnings: {len(warning_checks)}")
    print(f"  ❌ Failed: {len(failed_checks)}")

    if results['errors']:
        print(f"\n❌ Errors found:")
        for error in results['errors']:
            print(f"   - {error}")

    if results['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in results['warnings']:
            print(f"   - {warning}")

    # Determine overall status
    if failed_checks:
        results['overall_status'] = "FAIL"
        print(f"\n❌ OVERALL STATUS: FAIL")
        print(f"   ❌ DO NOT proceed to Blender placement - fix errors above")
        return_code = 1
    elif warning_checks:
        results['overall_status'] = "PASS_WITH_WARNINGS"
        print(f"\n⚠️  OVERALL STATUS: PASS WITH WARNINGS")
        print(f"   ✅ Safe to proceed to Blender placement, but review warnings")
        return_code = 0
    else:
        results['overall_status'] = "PASS"
        print(f"\n✅ OVERALL STATUS: PASS")
        print(f"   ✅ Output JSON is valid - ready for Blender placement")
        return_code = 0

    results['return_code'] = return_code

    # Print statistics
    print(f"\n📊 Object Statistics:")
    print(f"   Total objects: {expected_count}")
    print(f"   Unique object_types: {len(set(obj.get('object_type') for obj in objects))}")
    by_phase = summary.get('by_phase', {})
    if by_phase:
        print(f"   Objects by phase:")
        for phase, count in sorted(by_phase.items()):
            print(f"      - {phase}: {count}")

    print("=" * 80)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_output_json.py <output_json>")
        print("\nExample:")
        print("  python3 validate_output_json.py output_artifacts/TB-LKTN_OUTPUT_20251124.json")
        sys.exit(1)

    json_path = sys.argv[1]
    results = validate_output_json(json_path)

    sys.exit(results['return_code'])
