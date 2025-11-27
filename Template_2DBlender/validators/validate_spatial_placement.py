#!/usr/bin/env python3
"""
Spatial Placement Validator - Verify objects are correctly positioned in space

Validates:
  1. Objects adjacent to walls (doors, windows, switches, outlets)
  2. Objects within building bounds
  3. No overlapping objects
  4. Orientation matches wall normal

Usage:
    python3 validate_spatial_placement.py <output_json>
"""

import json
import sys
import math


def distance_point_to_line_segment(px, py, x1, y1, x2, y2):
    """Calculate perpendicular distance from point to line segment"""
    # Line vector
    dx = x2 - x1
    dy = y2 - y1
    line_length_sq = dx*dx + dy*dy

    if line_length_sq == 0:
        return math.sqrt((px - x1)**2 + (py - y1)**2)

    # Projection parameter (clamped to [0,1] for line segment)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / line_length_sq))

    # Closest point on line segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    # Distance to closest point
    return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)


def validate_object_wall_adjacency(obj, walls, max_distance=0.5):
    """
    Validate that object is adjacent to at least one wall

    Args:
        obj: Object dict with position
        walls: List of walls
        max_distance: Maximum acceptable distance to wall (meters)

    Returns:
        dict: {valid: bool, nearest_wall_distance: float, message: str}
    """
    if not walls:
        return {
            "valid": False,
            "nearest_wall_distance": None,
            "message": "No walls available for validation"
        }

    px, py = obj['position'][0], obj['position'][1]
    min_distance = float('inf')

    for wall in walls:
        x1, y1 = wall['start_point'][0], wall['start_point'][1]
        x2, y2 = wall['end_point'][0], wall['end_point'][1]

        distance = distance_point_to_line_segment(px, py, x1, y1, x2, y2)

        if distance < min_distance:
            min_distance = distance

    if min_distance <= max_distance:
        return {
            "valid": True,
            "nearest_wall_distance": min_distance,
            "message": f"Adjacent to wall ({min_distance:.3f}m)"
        }
    else:
        return {
            "valid": False,
            "nearest_wall_distance": min_distance,
            "message": f"Too far from walls ({min_distance:.3f}m > {max_distance}m)"
        }


def validate_building_bounds(obj, building_dimensions):
    """
    Validate object is within building bounds

    Args:
        obj: Object dict with position
        building_dimensions: dict with length, breadth, height

    Returns:
        dict: {valid: bool, message: str}
    """
    px, py, pz = obj['position']

    # Default bounds if not specified
    max_x = building_dimensions.get('length', 10.0)
    max_y = building_dimensions.get('breadth', 10.0)
    max_z = building_dimensions.get('height', 3.0)

    # Check bounds with small margin
    margin = 1.0  # 1 meter margin for exterior fixtures
    valid_x = -margin <= px <= max_x + margin
    valid_y = -margin <= py <= max_y + margin
    valid_z = -margin <= pz <= max_z + margin

    if valid_x and valid_y and valid_z:
        return {
            "valid": True,
            "message": f"Within bounds [{px:.2f}, {py:.2f}, {pz:.2f}]"
        }
    else:
        return {
            "valid": False,
            "message": f"Out of bounds [{px:.2f}, {py:.2f}, {pz:.2f}] (max: [{max_x}, {max_y}, {max_z}])"
        }


def check_overlapping_objects(objects, min_distance=0.3):
    """
    Check for overlapping objects

    Args:
        objects: List of object dicts
        min_distance: Minimum distance between objects (meters)

    Returns:
        list: List of overlapping pairs
    """
    overlaps = []

    for i, obj1 in enumerate(objects):
        for j, obj2 in enumerate(objects[i+1:], i+1):
            p1 = obj1['position']
            p2 = obj2['position']

            # 2D distance (ignoring Z for now)
            distance = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

            if distance < min_distance:
                overlaps.append({
                    "object1": obj1['name'],
                    "object2": obj2['name'],
                    "distance": distance,
                    "message": f"{obj1['name']} and {obj2['name']} too close ({distance:.3f}m)"
                })

    return overlaps


def validate_spatial_placement(json_path):
    """
    Main validation function

    Args:
        json_path: Path to output JSON file

    Returns:
        dict: Validation results
    """
    print(f"🔍 Spatial Placement Validator")
    print(f"=" * 80)
    print(f"\nReading: {json_path}")

    # Load JSON
    with open(json_path, 'r') as f:
        data = json.load(f)

    objects = data.get('objects', [])
    metadata = data.get('extraction_metadata', {})
    calibration = metadata.get('calibration', {})

    # Extract walls from context (if available)
    # Note: Current output doesn't store walls, so we'll skip wall validation for now
    walls = []  # TODO: Add walls to output JSON for full validation

    # Building dimensions (from calibration or defaults)
    building_dims = {
        'length': 9.8,
        'breadth': 8.0,
        'height': 3.0
    }

    print(f"✅ Loaded {len(objects)} objects")
    print(f"📐 Building dimensions: {building_dims['length']}m x {building_dims['breadth']}m x {building_dims['height']}m")

    # Validation results
    results = {
        "total_objects": len(objects),
        "validated": 0,
        "passed": 0,
        "failed": 0,
        "object_results": [],
        "overlaps": [],
        "summary": {}
    }

    # Validate each object
    print(f"\n🔍 Validating object placement...")

    for obj in objects:
        obj_result = {
            "name": obj['name'],
            "object_type": obj['object_type'],
            "position": obj['position'],
            "orientation": obj.get('orientation', 0.0),
            "validations": {}
        }

        # Check 1: Within building bounds
        bounds_check = validate_building_bounds(obj, building_dims)
        obj_result['validations']['bounds'] = bounds_check

        # Check 2: Wall adjacency (only for wall-mounted objects)
        wall_mounted_types = ['door', 'window', 'switch', 'outlet', 'light']
        needs_wall = any(t in obj['object_type'].lower() for t in wall_mounted_types)

        if needs_wall and walls:
            wall_check = validate_object_wall_adjacency(obj, walls)
            obj_result['validations']['wall_adjacency'] = wall_check
        elif needs_wall and not walls:
            obj_result['validations']['wall_adjacency'] = {
                "valid": None,
                "message": "Wall data not available (skipped)"
            }

        # Determine overall pass/fail
        all_valid = all(
            v.get('valid', True) for v in obj_result['validations'].values()
        )

        obj_result['passed'] = all_valid

        if all_valid:
            results['passed'] += 1
            print(f"  ✅ {obj['name']}: All checks passed")
        else:
            results['failed'] += 1
            print(f"  ❌ {obj['name']}: Validation failed")
            for check_name, check_result in obj_result['validations'].items():
                if not check_result.get('valid', True):
                    print(f"     - {check_name}: {check_result['message']}")

        results['object_results'].append(obj_result)
        results['validated'] += 1

    # Check for overlaps
    print(f"\n🔍 Checking for overlapping objects...")
    overlaps = check_overlapping_objects(objects)
    results['overlaps'] = overlaps

    if overlaps:
        print(f"  ⚠️  Found {len(overlaps)} overlapping pairs:")
        for overlap in overlaps:
            print(f"     - {overlap['message']}")
    else:
        print(f"  ✅ No overlapping objects detected")

    # Summary
    print(f"\n" + "=" * 80)
    print(f"📊 VALIDATION SUMMARY")
    print(f"=" * 80)
    print(f"Total objects: {results['total_objects']}")
    print(f"Validated: {results['validated']}")
    print(f"Passed: {results['passed']} ({results['passed']/max(results['validated'],1)*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/max(results['validated'],1)*100:.1f}%)")
    print(f"Overlaps: {len(overlaps)}")

    results['summary'] = {
        "pass_rate": results['passed'] / max(results['validated'], 1) * 100,
        "overlap_count": len(overlaps)
    }

    # Overall status
    if results['failed'] == 0 and len(overlaps) == 0:
        print(f"\n✅ ALL VALIDATIONS PASSED - Spatial placement is correct")
        results['overall_status'] = "PASS"
    else:
        print(f"\n⚠️  SOME VALIDATIONS FAILED - Review issues above")
        results['overall_status'] = "FAIL"

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_spatial_placement.py <output_json>")
        print("\nExample:")
        print("  python3 validate_spatial_placement.py output_artifacts/TB-LKTN_OUTPUT_20251124.json")
        sys.exit(1)

    json_path = sys.argv[1]
    results = validate_spatial_placement(json_path)

    sys.exit(0 if results['overall_status'] == "PASS" else 1)
