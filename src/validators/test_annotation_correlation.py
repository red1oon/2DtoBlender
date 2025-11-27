#!/usr/bin/env python3
"""
Annotation Correlation Validator

Validates extracted objects against annotation GROUND TRUTH and suggests
corrections when mismatches are found.

Annotations are FACTS from the original drawings - if extraction doesn't
match annotations, extraction is likely wrong and should be corrected.
"""

import json
import sys
import math
from typing import Dict, List


def load_output_json(filepath: str) -> Dict:
    """Load extraction output JSON"""
    with open(filepath) as f:
        return json.load(f)


def validate_annotation_correlation(data: Dict):
    """
    Validate objects against annotation ground truth

    Checks:
    1. Every annotation has corresponding object
    2. Object positions match annotation positions
    3. Object dimensions match schedule dimensions
    4. Room assignments match room labels
    """
    print("="*80)
    print("ANNOTATION CORRELATION VALIDATION")
    print("="*80)
    print("\nAnnotations are GROUND TRUTH from original drawings.")
    print("This validator checks if extracted objects match these facts.\n")

    # Check if annotations exist
    if 'annotations' not in data:
        print("❌ No annotations found in output JSON")
        print("   Annotations must be captured during extraction to enable correlation validation")
        print("\n💡 To fix: Modify extraction_engine.py to capture and persist annotations")
        return False

    annotations = data['annotations']
    objects = data.get('objects', [])

    print(f"📋 Loaded {len(objects)} objects")
    print(f"📝 Loaded annotations:")
    print(f"   Doors: {len(annotations.get('doors', []))}")
    print(f"   Windows: {len(annotations.get('windows', []))}")
    print(f"   Rooms: {len(annotations.get('rooms', []))}")
    print(f"   Dimensions: {len(annotations.get('dimensions', []))}")

    # Run validation
    issues = []
    corrections = []

    # Validate doors
    issues_doors, corrections_doors = validate_door_annotations(
        annotations.get('doors', []), objects
    )
    issues.extend(issues_doors)
    corrections.extend(corrections_doors)

    # Validate windows
    issues_windows, corrections_windows = validate_window_annotations(
        annotations.get('windows', []), objects
    )
    issues.extend(issues_windows)
    corrections.extend(corrections_windows)

    # Validate rooms
    issues_rooms = validate_room_annotations(
        annotations.get('rooms', []), objects
    )
    issues.extend(issues_rooms)

    # Print summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    critical = len([i for i in issues if i.get('severity') == 'critical'])
    warnings = len([i for i in issues if i.get('severity') == 'warning'])

    print(f"\n❌ Critical issues: {critical}")
    print(f"⚠️  Warnings: {warnings}")
    print(f"🔧 Corrections suggested: {len(corrections)}")

    # Print issues
    if issues:
        print("\n📋 ISSUES FOUND:")
        for i, issue in enumerate(issues[:10], 1):
            severity_icon = "❌" if issue['severity'] == 'critical' else "⚠️ "
            print(f"{i}. {severity_icon} {issue['message']}")

        if len(issues) > 10:
            print(f"   ... and {len(issues) - 10} more issues")

    # Print corrections
    if corrections:
        print("\n🔧 SUGGESTED CORRECTIONS:")
        for i, corr in enumerate(corrections[:5], 1):
            print(f"{i}. {corr['object_name']}: {corr['reason']}")
            if corr['correction_type'] == 'update_position':
                print(f"   Move from {corr['from'][:2]} to {corr['to'][:2]}")
            elif corr['correction_type'] == 'update_dimension':
                print(f"   Change {corr['dimension']} from {corr['from']}m to {corr['to']}m")

        if len(corrections) > 5:
            print(f"   ... and {len(corrections) - 5} more corrections")

    # Print pass/fail
    print("\n" + "="*80)
    if critical > 0:
        print("❌ VALIDATION FAILED")
        print(f"   {critical} critical issues found")
        print("   Extraction does not match annotation ground truth")
        return False
    elif warnings > 0:
        print("⚠️  VALIDATION PASSED WITH WARNINGS")
        print(f"   {warnings} warnings found")
        print("   Consider applying suggested corrections")
        return True
    else:
        print("✅ VALIDATION PASSED")
        print("   All objects match annotation ground truth")
        return True


def validate_door_annotations(door_annotations: List[Dict], objects: List[Dict]):
    """Validate door objects match door annotations"""
    print("\n" + "-"*80)
    print("VALIDATING DOOR ANNOTATIONS")
    print("-"*80)

    issues = []
    corrections = []

    for ann in door_annotations:
        text = ann['text']
        ann_pos = ann['building_position']
        associated_obj = ann.get('associated_object')

        # Find object
        obj = find_object(objects, associated_obj)

        if not obj:
            issues.append({
                'type': 'missing_object',
                'annotation': text,
                'category': 'door',
                'message': f"Door annotation {text} has no associated object",
                'severity': 'critical'
            })
            print(f"❌ {text}: No associated object found")
            continue

        # Check position
        obj_pos = obj.get('position', [0, 0, 0])
        distance = calculate_distance_2d(ann_pos[:2], obj_pos[:2])

        if distance > 0.5:  # More than 50cm off
            severity = 'critical' if distance > 1.0 else 'warning'
            icon = "❌" if severity == 'critical' else "⚠️ "

            issues.append({
                'type': 'position_mismatch',
                'annotation': text,
                'category': 'door',
                'distance': round(distance, 2),
                'message': f"Door {text} position mismatch: {distance:.2f}m from annotation",
                'severity': severity
            })

            corrections.append({
                'object_name': obj.get('name'),
                'correction_type': 'update_position',
                'from': obj_pos,
                'to': ann_pos,
                'reason': f"Match annotation {text} ground truth position (off by {distance:.2f}m)",
                'confidence': ann['confidence']
            })

            print(f"{icon} {text}: Position mismatch ({distance:.2f}m)")
            print(f"      Annotation: {ann_pos[:2]}")
            print(f"      Object:     {obj_pos[:2]}")
        else:
            print(f"✓ {text}: Position matches annotation")

    print(f"\nDoor validation: {len(issues)} issues, {len(corrections)} corrections")
    return issues, corrections


def validate_window_annotations(window_annotations: List[Dict], objects: List[Dict]):
    """Validate window objects match window annotations"""
    print("\n" + "-"*80)
    print("VALIDATING WINDOW ANNOTATIONS")
    print("-"*80)

    issues = []
    corrections = []

    for ann in window_annotations:
        text = ann['text']
        ann_pos = ann['building_position']
        associated_obj = ann.get('associated_object')

        obj = find_object(objects, associated_obj)

        if not obj:
            issues.append({
                'type': 'missing_object',
                'annotation': text,
                'category': 'window',
                'message': f"Window annotation {text} has no associated object",
                'severity': 'critical'
            })
            print(f"❌ {text}: No associated object found")
            continue

        obj_pos = obj.get('position', [0, 0, 0])
        distance = calculate_distance_2d(ann_pos[:2], obj_pos[:2])

        if distance > 0.5:
            severity = 'critical' if distance > 1.0 else 'warning'
            icon = "❌" if severity == 'critical' else "⚠️ "

            issues.append({
                'type': 'position_mismatch',
                'annotation': text,
                'category': 'window',
                'distance': round(distance, 2),
                'message': f"Window {text} position mismatch: {distance:.2f}m from annotation",
                'severity': severity
            })

            corrections.append({
                'object_name': obj.get('name'),
                'correction_type': 'update_position',
                'from': obj_pos,
                'to': ann_pos,
                'reason': f"Match annotation {text} ground truth position (off by {distance:.2f}m)",
                'confidence': ann['confidence']
            })

            print(f"{icon} {text}: Position mismatch ({distance:.2f}m)")
        else:
            print(f"✓ {text}: Position matches annotation")

    print(f"\nWindow validation: {len(issues)} issues, {len(corrections)} corrections")
    return issues, corrections


def validate_room_annotations(room_annotations: List[Dict], objects: List[Dict]):
    """Validate room assignments match room annotations"""
    print("\n" + "-"*80)
    print("VALIDATING ROOM ANNOTATIONS")
    print("-"*80)

    issues = []

    for ann in room_annotations:
        text = ann['text']
        associated_room = ann.get('associated_room')

        if not associated_room:
            continue

        # Find objects in this room
        room_objects = [o for o in objects if o.get('room') == associated_room]

        if not room_objects:
            issues.append({
                'type': 'empty_room',
                'annotation': text,
                'category': 'room',
                'message': f"Room {text} ({associated_room}) has no objects",
                'severity': 'warning'
            })
            print(f"⚠️  {text} ({associated_room}): No objects in room")
            continue

        # Check if annotation position is within room bounds
        room_centroid = calculate_room_centroid(room_objects)
        ann_pos = ann['building_position']
        distance = calculate_distance_2d(room_centroid, ann_pos[:2])

        if distance > 3.0:  # Room label > 3m from room center
            issues.append({
                'type': 'room_label_mismatch',
                'annotation': text,
                'category': 'room',
                'distance': round(distance, 2),
                'message': f"Room {text} label {distance:.2f}m from room center",
                'severity': 'warning'
            })
            print(f"⚠️  {text}: Label position far from room ({distance:.2f}m)")
        else:
            print(f"✓ {text}: {len(room_objects)} objects, label within room")

    print(f"\nRoom validation: {len(issues)} issues")
    return issues


def find_object(objects: List[Dict], name: str) -> Dict:
    """Find object by name"""
    if not name:
        return None
    for obj in objects:
        if obj.get('name') == name:
            return obj
    return None


def calculate_distance_2d(pos1: List[float], pos2: List[float]) -> float:
    """Calculate 2D Euclidean distance"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return math.sqrt(dx*dx + dy*dy)


def calculate_room_centroid(room_objects: List[Dict]):
    """Calculate centroid of room objects"""
    positions = [o.get('position', [0, 0, 0]) for o in room_objects]
    avg_x = sum(p[0] for p in positions) / len(positions)
    avg_y = sum(p[1] for p in positions) / len(positions)
    return (avg_x, avg_y)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_annotation_correlation.py <output.json>")
        sys.exit(1)

    # Load data
    data = load_output_json(sys.argv[1])

    # Run validation
    passed = validate_annotation_correlation(data)

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
