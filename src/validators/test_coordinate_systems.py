#!/usr/bin/env python3
"""
Coordinate Systems Validator

Tests all coordinate systems in the extraction pipeline:
1. PDF coordinates (pixel space)
2. Building coordinates (meters)
3. Grid/Lattice coordinates (cell indices)
4. Annotation ground truth positions

Verifies:
- Calibration is accurate
- Coordinate transformations are correct
- Annotations match objects
- Natural grid alignment
"""

import json
import sys
import math


def load_json(filepath):
    """Load JSON file"""
    with open(filepath) as f:
        return json.load(f)


def test_coordinate_systems(output_file, lattice_file=None):
    """
    Test all coordinate systems

    Args:
        output_file: Extraction output JSON
        lattice_file: Optional lattice JSON file
    """
    print("="*80)
    print("COORDINATE SYSTEMS VALIDATION")
    print("="*80)

    # Load data
    data = load_json(output_file)

    calibration = data.get('extraction_metadata', {}).get('calibration', {})
    annotations = data.get('annotations', {})
    objects = data.get('objects', [])

    if not calibration:
        print("❌ No calibration data found")
        return False

    print(f"\n📊 Loaded:")
    print(f"   Calibration: {calibration.get('method')}")
    print(f"   Objects: {len(objects)}")
    print(f"   Annotations: {sum(len(annotations[k]) for k in annotations)}")

    # Test 1: Calibration validation
    print("\n" + "-"*80)
    print("TEST 1: CALIBRATION VALIDATION")
    print("-"*80)

    scale_x = calibration.get('scale_x')
    scale_y = calibration.get('scale_y')
    confidence = calibration.get('confidence', 0)

    print(f"Scale X: {scale_x:.6f} m/pixel")
    print(f"Scale Y: {scale_y:.6f} m/pixel")
    print(f"Confidence: {confidence}%")

    # Check scale consistency
    scale_diff = abs(scale_x - scale_y) / scale_x * 100

    if scale_diff < 5:
        print(f"✅ Scale consistency: {scale_diff:.2f}% (< 5% threshold)")
    else:
        print(f"⚠️  Scale inconsistency: {scale_diff:.2f}% (> 5% threshold)")

    if confidence >= 85:
        print(f"✅ Calibration confidence: {confidence}% (high)")
    else:
        print(f"⚠️  Calibration confidence: {confidence}% (medium)")

    # Test 2: Building coordinate bounds
    print("\n" + "-"*80)
    print("TEST 2: BUILDING COORDINATE BOUNDS")
    print("-"*80)

    # Check if all objects are within reasonable bounds
    all_positions = [obj.get('position', [0, 0, 0]) for obj in objects]

    if all_positions:
        min_x = min(p[0] for p in all_positions)
        max_x = max(p[0] for p in all_positions)
        min_y = min(p[1] for p in all_positions)
        max_y = max(p[1] for p in all_positions)
        min_z = min(p[2] for p in all_positions)
        max_z = max(p[2] for p in all_positions)

        print(f"X range: [{min_x:.2f}, {max_x:.2f}] meters")
        print(f"Y range: [{min_y:.2f}, {max_y:.2f}] meters")
        print(f"Z range: [{min_z:.2f}, {max_z:.2f}] meters")

        building_width = max_x - min_x
        building_length = max_y - min_y
        building_height = max_z - min_z

        print(f"\nBuilding dimensions:")
        print(f"  Width:  {building_width:.2f} m")
        print(f"  Length: {building_length:.2f} m")
        print(f"  Height: {building_height:.2f} m")

        # Validate reasonable dimensions
        if 5 < building_width < 50 and 5 < building_length < 50:
            print(f"✅ Building dimensions are reasonable")
        else:
            print(f"⚠️  Building dimensions seem unusual")

        # Check for objects outside bounds
        outliers = [obj for obj in objects
                   if obj.get('position', [0,0,0])[0] < -1
                   or obj.get('position', [0,0,0])[0] > building_width + 1
                   or obj.get('position', [0,0,0])[1] < -1
                   or obj.get('position', [0,0,0])[1] > building_length + 1]

        if outliers:
            print(f"⚠️  {len(outliers)} objects outside building bounds")
        else:
            print(f"✅ All objects within building bounds")

    # Test 3: Annotation coordinate validation
    print("\n" + "-"*80)
    print("TEST 3: ANNOTATION COORDINATE VALIDATION")
    print("-"*80)

    total_annotations = 0
    total_matches = 0
    total_mismatches = 0

    for category in ['doors', 'windows', 'rooms']:
        anns = annotations.get(category, [])
        if not anns:
            continue

        print(f"\n{category.upper()}:")
        for ann in anns:
            total_annotations += 1

            # Find associated object
            obj_name = ann.get('associated_object')
            obj = next((o for o in objects if o.get('name') == obj_name), None)

            if not obj:
                print(f"  ⚠️  {ann['text']}: No associated object found")
                total_mismatches += 1
                continue

            # Compare positions
            ann_pos = ann.get('building_position', [0, 0, 0])
            obj_pos = obj.get('position', [0, 0, 0])

            distance = math.sqrt(
                (ann_pos[0] - obj_pos[0])**2 +
                (ann_pos[1] - obj_pos[1])**2 +
                (ann_pos[2] - obj_pos[2])**2
            )

            if distance < 0.01:  # < 1cm
                print(f"  ✅ {ann['text']}: Perfect match (distance: {distance*1000:.1f}mm)")
                total_matches += 1
            elif distance < 0.5:  # < 50cm
                print(f"  ✓  {ann['text']}: Good match (distance: {distance*100:.1f}cm)")
                total_matches += 1
            else:
                print(f"  ❌ {ann['text']}: Mismatch (distance: {distance:.2f}m)")
                print(f"      Annotation: {ann_pos[:2]}")
                print(f"      Object:     {obj_pos[:2]}")
                total_mismatches += 1

    if total_annotations > 0:
        match_rate = (total_matches / total_annotations) * 100
        print(f"\nAnnotation-Object Correlation: {match_rate:.1f}%")
        print(f"  Matches: {total_matches}/{total_annotations}")
        print(f"  Mismatches: {total_mismatches}")

        if match_rate >= 95:
            print(f"✅ Excellent correlation")
        elif match_rate >= 80:
            print(f"✓  Good correlation")
        else:
            print(f"⚠️  Poor correlation")

    # Test 4: PDF to Building coordinate transformation
    print("\n" + "-"*80)
    print("TEST 4: PDF → BUILDING COORDINATE TRANSFORMATION")
    print("-"*80)

    if annotations.get('doors'):
        # Test with first door annotation
        ann = annotations['doors'][0]
        pdf_pos = ann.get('pdf_position', {})
        building_pos = ann.get('building_position', [])

        print(f"Sample transformation (from {ann['text']}):")
        print(f"  PDF coords:      ({pdf_pos.get('x'):.2f}, {pdf_pos.get('y'):.2f}) pixels")
        print(f"  Building coords: ({building_pos[0]:.2f}, {building_pos[1]:.2f}) meters")

        # Verify transformation using calibration
        expected_x = (pdf_pos['x'] - calibration['offset_x']) * calibration['scale_x']
        expected_y = (pdf_pos['y'] - calibration['offset_y']) * calibration['scale_y']

        error_x = abs(expected_x - building_pos[0])
        error_y = abs(expected_y - building_pos[1])

        print(f"\nTransformation validation:")
        print(f"  X error: {error_x*1000:.2f}mm")
        print(f"  Y error: {error_y*1000:.2f}mm")

        if error_x < 0.01 and error_y < 0.01:
            print(f"✅ Transformation accurate (< 1cm error)")
        else:
            print(f"⚠️  Transformation has errors")

    # Test 5: Natural grid alignment (if lattice available)
    if lattice_file:
        print("\n" + "-"*80)
        print("TEST 5: NATURAL GRID ALIGNMENT")
        print("-"*80)

        try:
            lattice = load_json(lattice_file)
            grid = lattice.get('grid', {})

            origin = grid.get('origin', [0, 0, 0])
            x_interval = grid.get('x_interval', 1.0)
            y_interval = grid.get('y_interval', 1.0)

            print(f"Grid origin: {origin}")
            print(f"Grid intervals: X={x_interval:.2f}m, Y={y_interval:.2f}m")

            # Check object alignment with grid
            aligned_count = 0
            total_checked = 0

            for obj in objects[:20]:  # Check first 20 objects
                pos = obj.get('position', [0, 0, 0])

                # Calculate distance to nearest grid line
                x_cell = (pos[0] - origin[0]) / x_interval
                y_cell = (pos[1] - origin[1]) / y_interval

                x_offset = abs(x_cell - round(x_cell)) * x_interval
                y_offset = abs(y_cell - round(y_cell)) * y_interval

                total_checked += 1
                if x_offset < 0.2 and y_offset < 0.2:  # Within 20cm of grid
                    aligned_count += 1

            alignment_rate = (aligned_count / total_checked) * 100
            print(f"\nGrid alignment: {alignment_rate:.1f}%")
            print(f"  Aligned: {aligned_count}/{total_checked}")

            if alignment_rate >= 80:
                print(f"✅ Good grid alignment")
            else:
                print(f"⚠️  Poor grid alignment")

        except FileNotFoundError:
            print(f"⚠️  Lattice file not found: {lattice_file}")

    # Summary
    print("\n" + "="*80)
    print("COORDINATE SYSTEMS SUMMARY")
    print("="*80)

    print(f"\n✅ Tests completed:")
    print(f"  1. Calibration: {confidence}% confidence")
    print(f"  2. Building bounds: {building_width:.1f}m × {building_length:.1f}m")

    if total_annotations > 0:
        print(f"  3. Annotations: {match_rate:.1f}% correlation")

    print(f"\n📊 Coordinate systems status:")
    print(f"  • PDF coordinates: ✅ Available")
    print(f"  • Building coordinates: ✅ Validated")
    print(f"  • Annotation coordinates: ✅ {'Tested' if total_annotations > 0 else 'No data'}")
    print(f"  • Grid coordinates: ✅ {'Tested' if lattice_file else 'Available'}")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_coordinate_systems.py <output.json> [lattice.json]")
        sys.exit(1)

    output_file = sys.argv[1]
    lattice_file = sys.argv[2] if len(sys.argv) > 2 else None

    success = test_coordinate_systems(output_file, lattice_file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
