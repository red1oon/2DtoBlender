#!/usr/bin/env python3
"""
Wall Combiner - Merge collinear wall segments into single continuous walls

Handles:
1. Detect collinear wall segments (same line, adjacent)
2. Merge into single longer wall
3. Remove internal duplicate segments
4. Preserve wall connectivity for rooms
"""

import json
import math
import sys
from pathlib import Path

# Standard building height for residential construction
BUILDING_HEIGHT = 3.0  # meters


def walls_collinear(wall1, wall2, angle_tolerance=5, dist_tolerance=0.1):
    """Check if two walls are collinear (on same line)"""
    w1_start = wall1['position']
    w1_end = wall1.get('end_point', w1_start)
    w2_start = wall2['position']
    w2_end = wall2.get('end_point', w2_start)

    # Calculate angles
    dx1 = w1_end[0] - w1_start[0]
    dy1 = w1_end[1] - w1_start[1]
    dx2 = w2_end[0] - w2_start[0]
    dy2 = w2_end[1] - w2_start[1]

    if (dx1 == 0 and dy1 == 0) or (dx2 == 0 and dy2 == 0):
        return False

    angle1 = math.atan2(dy1, dx1)
    angle2 = math.atan2(dy2, dx2)

    angle_diff = abs(math.degrees(angle1 - angle2))

    # Normalize angle difference to 0-180
    if angle_diff > 180:
        angle_diff = 360 - angle_diff

    # Check if parallel
    if not (angle_diff < angle_tolerance or abs(angle_diff - 180) < angle_tolerance):
        return False

    # Check if on same line (point from wall2 should be close to wall1's line)
    def point_line_distance(point, line_start, line_end):
        x0, y0 = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        dx = x2 - x1
        dy = y2 - y1
        denom = dx*dx + dy*dy

        if denom == 0:
            return math.sqrt((x0-x1)**2 + (y0-y1)**2)

        t = ((x0 - x1) * dx + (y0 - y1) * dy) / denom
        # Don't clamp t - we want infinite line distance
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        return math.sqrt((x0 - closest_x)**2 + (y0 - closest_y)**2)

    dist1 = point_line_distance(w2_start, w1_start, w1_end)
    dist2 = point_line_distance(w2_end, w1_start, w1_end)

    return (dist1 < dist_tolerance and dist2 < dist_tolerance)


def walls_adjacent(wall1, wall2, gap_tolerance=0.5):
    """Check if two collinear walls are adjacent (endpoints close)

    After grid snapping, walls should align perfectly or have small gaps.
    Increased tolerance to 0.5m to handle grid-snapped coordinates.
    """
    w1_start = wall1['position']
    w1_end = wall1.get('end_point', w1_start)
    w2_start = wall2['position']
    w2_end = wall2.get('end_point', w2_start)

    # Check all endpoint combinations
    endpoints = [
        (w1_end, w2_start),
        (w1_end, w2_end),
        (w1_start, w2_start),
        (w1_start, w2_end)
    ]

    for p1, p2 in endpoints:
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dist = math.sqrt(dx*dx + dy*dy)

        if dist < gap_tolerance:
            return True

    return False


def merge_two_walls(wall1, wall2):
    """Merge two collinear adjacent walls into one"""
    w1_start = wall1['position']
    w1_end = wall1.get('end_point', w1_start)
    w2_start = wall2['position']
    w2_end = wall2.get('end_point', w2_start)

    # Find the extreme points
    all_points = [w1_start, w1_end, w2_start, w2_end]

    # Calculate the line direction from wall1
    dx = w1_end[0] - w1_start[0]
    dy = w1_end[1] - w1_start[1]

    if dx*dx + dy*dy < 0.0001:
        # Use wall2 direction
        dx = w2_end[0] - w2_start[0]
        dy = w2_end[1] - w2_start[1]

    # Project all points onto the line direction
    projections = []
    for p in all_points:
        proj = p[0] * dx + p[1] * dy
        projections.append((proj, p))

    # Sort by projection value
    projections.sort(key=lambda x: x[0])

    # Extreme points are first and last
    new_start = projections[0][1]
    new_end = projections[-1][1]

    # Create merged wall (use properties from wall1)
    merged = wall1.copy()
    merged['name'] = f"{wall1['name']}_merged"
    # Walls are 2D floor plan segments - end_point.z should be 0, not ceiling height
    merged['position'] = [new_start[0], new_start[1], 0.0]
    merged['end_point'] = [new_end[0], new_end[1], 0.0]  # FIXED: was BUILDING_HEIGHT (wrong)

    # Update length
    length = math.sqrt((new_end[0] - new_start[0])**2 + (new_end[1] - new_start[1])**2)
    if 'length' in merged:
        merged['length'] = length

    # DEBUG: Log merge operation
    print(f"    🔗 MERGED: {wall1['name']} + {wall2['name']}")
    print(f"       Start: [{new_start[0]:.2f}, {new_start[1]:.2f}] → End: [{new_end[0]:.2f}, {new_end[1]:.2f}], Length: {length:.2f}m")

    # Validate for degenerate walls
    if length < 0.01:
        print(f"       ⚠️  WARNING: Merged wall has near-zero length ({length:.4f}m) - may be degenerate!")

    return merged


def combine_collinear_walls(walls):
    """Combine collinear adjacent walls into single continuous walls

    Uses iterative merging until no more merges possible (handles 3+ segment chains)
    """
    if not walls:
        return []

    print(f"   Analyzing {len(walls)} walls for merging...")

    # Iterative merging until no more merges possible
    iteration = 0
    prev_count = len(walls)

    while True:
        iteration += 1
        combined = []
        merged_indices = set()
        merge_found = False

        for i in range(len(walls)):
            if i in merged_indices:
                continue

            current_wall = walls[i]

            # Try to merge with ALL other walls in one pass
            for j in range(len(walls)):
                if i == j or j in merged_indices:
                    continue

                other_wall = walls[j]

                # Check if collinear and adjacent (with more generous tolerance after grid snap)
                if walls_collinear(current_wall, other_wall, angle_tolerance=5, dist_tolerance=0.15):
                    if walls_adjacent(current_wall, other_wall, gap_tolerance=0.6):
                        # Merge them
                        current_wall = merge_two_walls(current_wall, other_wall)
                        merged_indices.add(j)
                        merge_found = True

            # Add the (possibly merged) wall
            combined.append(current_wall)
            merged_indices.add(i)

        walls = combined

        if not merge_found or len(walls) == prev_count:
            # No more merges possible
            break

        prev_count = len(walls)

        if iteration > 10:
            # Safety limit
            print(f"   ⚠️  Stopped after {iteration} iterations")
            break

    merged_count = prev_count - len(walls)
    print(f"   ✅ Merged in {iteration} iterations → {len(walls)} walls")

    # CRITICAL: Filter out zero-length (degenerate) walls
    valid_walls = []
    degenerate_walls = []
    for wall in walls:
        # Skip walls without end_point (not proper wall segments)
        if 'end_point' not in wall:
            valid_walls.append(wall)
            continue

        pos = wall['position']
        end = wall['end_point']
        length = math.sqrt((end[0]-pos[0])**2 + (end[1]-pos[1])**2)

        if length < 0.01:  # Less than 1cm - degenerate
            degenerate_walls.append(wall)
            print(f"   ⚠️  FILTERED DEGENERATE WALL: {wall['name']}")
            print(f"       Position: [{pos[0]:.2f}, {pos[1]:.2f}] → End: [{end[0]:.2f}, {end[1]:.2f}]")
            print(f"       Length: {length:.6f}m (near-zero)")
        else:
            valid_walls.append(wall)

    if degenerate_walls:
        print(f"   🧹 Removed {len(degenerate_walls)} degenerate walls (length < 0.01m)")

    return valid_walls


def remove_overlapping_walls(walls, tolerance=0.2):
    """Remove walls that completely overlap each other"""
    if not walls:
        return []

    keep = []
    skip_indices = set()

    for i in range(len(walls)):
        if i in skip_indices:
            continue

        w1 = walls[i]
        w1_start = w1['position']
        w1_end = w1.get('end_point', w1_start)
        w1_len = math.sqrt((w1_end[0] - w1_start[0])**2 + (w1_end[1] - w1_start[1])**2)

        keep_this = True

        for j in range(i + 1, len(walls)):
            if j in skip_indices:
                continue

            w2 = walls[j]
            w2_start = w2['position']
            w2_end = w2.get('end_point', w2_start)
            w2_len = math.sqrt((w2_end[0] - w2_start[0])**2 + (w2_end[1] - w2_start[1])**2)

            # Check if collinear
            if not walls_collinear(w1, w2, angle_tolerance=5, dist_tolerance=tolerance):
                continue

            # Check if one wall contains the other
            # Project all points onto w1's direction
            dx = w1_end[0] - w1_start[0]
            dy = w1_end[1] - w1_start[1]
            if dx*dx + dy*dy < 0.0001:
                continue

            # Project endpoints
            projs = []
            for p in [w1_start, w1_end, w2_start, w2_end]:
                proj = (p[0] - w1_start[0]) * dx + (p[1] - w1_start[1]) * dy
                projs.append(proj)

            w1_min, w1_max = min(projs[0], projs[1]), max(projs[0], projs[1])
            w2_min, w2_max = min(projs[2], projs[3]), max(projs[2], projs[3])

            # Check overlap percentage
            overlap_start = max(w1_min, w2_min)
            overlap_end = min(w1_max, w2_max)
            overlap_len = max(0, overlap_end - overlap_start)

            # If overlap is > 80% of shorter wall, consider duplicate
            shorter_len = min(w1_len, w2_len)
            if shorter_len > 0 and overlap_len / shorter_len > 0.8:
                # Keep the longer wall
                if w1_len < w2_len:
                    skip_indices.add(i)
                    keep_this = False
                    break
                else:
                    skip_indices.add(j)

        if keep_this:
            keep.append(w1)

    removed_count = len(walls) - len(keep)
    if removed_count > 0:
        print(f"   ✅ Removed {removed_count} overlapping walls ({len(walls)} → {len(keep)} walls)")

    return keep


def close_envelope_gaps(walls, envelope):
    """Add wall segments to ensure complete building envelope coverage

    Always adds 4 perimeter walls at envelope boundaries. Duplicate removal
    will handle any overlaps with existing walls.

    Args:
        walls: List of wall objects
        envelope: Building envelope dict with x_min, x_max, y_min, y_max

    Returns:
        List of walls with envelope perimeter segments added
    """
    if not envelope:
        return walls

    # Extract envelope boundaries
    x_min = envelope.get('x_min', 0)
    x_max = envelope.get('x_max', 10)
    y_min = envelope.get('y_min', 0)
    y_max = envelope.get('y_max', 10)

    print(f"   📐 Envelope bounds: x=[{x_min:.2f}, {x_max:.2f}], y=[{y_min:.2f}, {y_max:.2f}]")

    # Define 4 perimeter walls (always add these for complete closure)
    perimeter_walls = [
        ((x_min, y_min), (x_max, y_min), 'SOUTH'),  # South wall (SW to SE)
        ((x_max, y_min), (x_max, y_max), 'EAST'),   # East wall (SE to NE)
        ((x_max, y_max), (x_min, y_max), 'NORTH'),  # North wall (NE to NW)
        ((x_min, y_max), (x_min, y_min), 'WEST'),   # West wall (NW to SW)
    ]

    closure_walls = []

    for (start_pt, end_pt, wall_name) in perimeter_walls:
        # Always add perimeter wall (use "exterior" in name for validator compatibility)
        closure_wall = {
            'name': f'wall_exterior_envelope_{wall_name.lower()}',
            'object_type': 'wall_brick_3m_lod300',
            'position': [start_pt[0], start_pt[1], 0.0],
            'end_point': [end_pt[0], end_pt[1], 0.0],
            'orientation': 0.0,
            'room': 'structure',
            'placed': True,
            '_phase': '1C_structure',
            'ifc_class': 'IfcWall',
            'ifc_predefined_type': 'SOLIDWALL',
            'discipline': 'ARC',
            'group': 'Structure',
            'blender_name': f'ARC_Wall_Envelope_{wall_name}'
        }
        closure_walls.append(closure_wall)
        print(f"      {wall_name}: ({start_pt[0]:.2f}, {start_pt[1]:.2f}) → ({end_pt[0]:.2f}, {end_pt[1]:.2f})")

    print(f"   🔒 Added {len(closure_walls)} envelope perimeter walls")
    print(f"      (duplicates will be removed in next step)")

    return walls + closure_walls


def process_walls(objects, envelope=None):
    """Main wall combining process

    Args:
        objects: List of all objects
        envelope: Optional building envelope dict for closure
    """
    walls = [o for o in objects if 'wall' in (o.get('object_type') or '').lower()]
    other_objects = [o for o in objects if 'wall' not in (o.get('object_type') or '').lower()]

    if not walls:
        return objects

    print(f"\n🧱 Processing {len(walls)} wall segments...")

    # Step 0: Add envelope closure segments if gaps exist
    if envelope:
        walls = close_envelope_gaps(walls, envelope)

    # Step 1: Combine collinear adjacent walls
    walls = combine_collinear_walls(walls)

    # Step 2: Remove overlapping duplicates
    walls = remove_overlapping_walls(walls)

    return walls + other_objects


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 wall_combiner.py <output.json>")
        sys.exit(1)

    input_path = sys.argv[1]

    # Load data
    with open(input_path) as f:
        data = json.load(f)

    # Process walls
    print("="*80)
    print("🧱 WALL COMBINER - Merge collinear segments into single walls")
    print("="*80)

    original_count = len(data.get('objects', []))
    data['objects'] = process_walls(data.get('objects', []))
    final_count = len(data.get('objects', []))

    print(f"\n✅ Complete: {original_count} → {final_count} objects")

    # Update summary
    if 'summary' in data:
        data['summary']['total_objects'] = final_count

    # Save
    output_path = input_path.replace('.json', '_COMBINED.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"💾 Saved: {output_path}")
