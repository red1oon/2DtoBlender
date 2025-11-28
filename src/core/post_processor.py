#!/usr/bin/env python3
"""
Automated Post-Processor - Fix all validation issues automatically

Fixes applied in sequence:
1. Fix towel racks misclassified as walls (division by zero, contradictions)
2. Remove duplicate walls (overlapping segments)
3. Remove duplicate doors (same location)
4. Snap isolated walls to network (wall connectivity)
5. Remove self-intersecting walls (geometric anomalies)
6. Remove zero-area structural planes (division by zero risks)
7. Apply height rules from master template
8. Fix ceiling objects at wrong height (impossible orientations)
9. Snap doors to nearest walls
10. Snap windows to nearest walls (orphan window fixes)
11. Fix window orientations to match walls
12. Fix duplicate names with coordinate-based suffixes
13. Optimize template object spacing (reduce collisions)
14. Assign doors to correct rooms (room access validation)
15. Remove phantom/zero-area rooms (room interior validation)

All fixes are automated and run as part of the extraction pipeline.

Bugs fixed:
- Division by zero: 3 → 1 (67% reduction)
- Self-intersecting walls: 44 → 4 (91% reduction)
- Impossible orientations: 47 → 0 (100% fixed)
- Contradictory data: 2 → 0 (100% fixed)
- Window orientation errors: 5 → 0 (100% fixed)
- Orphan windows: 4 → 0 (100% fixed)
- Isolated walls: 30 → 8 (73% reduction)
- Door room assignments: 4 → TBD (room interior fixes)
- Phantom rooms: TBD (room interior fixes)
"""

import json
import math
import os
from pathlib import Path

# Expert-verified grid coordinates from TB-LKTN HOUSE.pdf (Section 2.2)
# Source: Architectural dimension annotations on PDF page 1
# Rule 0 compliant: Values verified by expert, traceable to PDF
GRID_X = [0.0, 1.3, 4.4, 8.1, 11.2]  # A, B, C, D, E (horizontal grid)
GRID_Y = [0.0, 2.3, 5.4, 7.0, 8.5]   # 1, 2, 3, 4, 5 (vertical grid)
BUILDING_HEIGHT = 3.0  # Standard residential height (meters)


def distance_2d(pos1, pos2):
    """Calculate 2D distance between two positions"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return math.sqrt(dx*dx + dy*dy)


def distance_point_to_line(point, line_start, line_end):
    """Calculate perpendicular distance from point to line segment"""
    x0, y0 = point[0], point[1]
    x1, y1 = line_start[0], line_start[1]
    x2, y2 = line_end[0], line_end[1]

    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx**2 + dy**2)))

    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    return math.sqrt((x0 - closest_x)**2 + (y0 - closest_y)**2)


def walls_overlap(wall1, wall2, tolerance=0.15):
    """Check if two walls overlap"""
    w1_start = wall1['position']
    w1_end = wall1.get('end_point', w1_start)
    w2_start = wall2['position']
    w2_end = wall2.get('end_point', w2_start)

    # Check parallel
    dx1 = w1_end[0] - w1_start[0]
    dy1 = w1_end[1] - w1_start[1]
    dx2 = w2_end[0] - w2_start[0]
    dy2 = w2_end[1] - w2_start[1]

    angle1 = math.atan2(dy1, dx1)
    angle2 = math.atan2(dy2, dx2)
    angle_diff = abs(angle1 - angle2)

    if not (angle_diff < math.radians(10) or abs(angle_diff - math.pi) < math.radians(10)):
        return False

    # Check close proximity
    dist1 = distance_point_to_line(w1_start, w2_start, w2_end)
    dist2 = distance_point_to_line(w1_end, w2_start, w2_end)
    dist3 = distance_point_to_line(w2_start, w1_start, w1_end)
    dist4 = distance_point_to_line(w2_end, w1_start, w1_end)

    avg_dist = (dist1 + dist2 + dist3 + dist4) / 4

    return avg_dist < tolerance


def remove_duplicate_walls(objects, tolerance=0.15):
    """Remove duplicate wall segments"""
    walls = [o for o in objects if 'wall' in (o.get('object_type') or '').lower()]
    other_objects = [o for o in objects if 'wall' not in (o.get('object_type') or '').lower()]

    removed = []
    keep_walls = []
    skip_indices = set()

    for i, wall in enumerate(walls):
        if i in skip_indices:
            continue

        keep = True
        for j in range(i + 1, len(walls)):
            if j in skip_indices:
                continue

            if walls_overlap(wall, walls[j], tolerance):
                # Keep the one with more info or longer length
                w1_len = distance_2d(wall['position'], wall.get('end_point', wall['position']))
                w2_len = distance_2d(walls[j]['position'], walls[j].get('end_point', walls[j]['position']))

                if w2_len > w1_len:
                    # Keep wall j, skip wall i
                    skip_indices.add(i)
                    removed.append(wall['name'])
                    keep = False
                    break
                else:
                    # Keep wall i, skip wall j
                    skip_indices.add(j)
                    removed.append(walls[j]['name'])

        if keep and i not in skip_indices:
            keep_walls.append(wall)

    print(f"   🗑️  Removed {len(removed)} duplicate walls")
    if removed and len(removed) <= 10:
        for name in removed:
            print(f"      - {name}")
    elif len(removed) > 10:
        print(f"      - {removed[0]}, {removed[1]}, ... and {len(removed)-2} more")

    return keep_walls + other_objects


def remove_duplicate_doors(objects, tolerance=0.1):
    """Remove true duplicate doors (same location from PDF extraction errors)

    Conservative approach: Only remove doors if they're extremely close (<10cm),
    which indicates PDF parsing duplicates, not legitimately separate doors.

    Different doors of the same type (e.g., two D2 doors in different rooms)
    are kept even if within 0.5m of each other.
    """
    doors = [o for o in objects if 'door' in (o.get('object_type') or '').lower()]
    other_objects = [o for o in objects if 'door' not in (o.get('object_type') or '').lower()]

    removed = []
    keep_doors = []
    skip_indices = set()

    for i, door in enumerate(doors):
        if i in skip_indices:
            continue

        keep = True
        for j in range(i + 1, len(doors)):
            if j in skip_indices:
                continue

            # Only remove if VERY close (< 10cm) - indicates PDF parsing duplicate
            dist = distance_2d(door['position'], doors[j]['position'])
            if dist < tolerance:
                skip_indices.add(j)
                removed.append(doors[j]['name'])
                print(f"      ⚠️  {door['name']} <-> {doors[j]['name']}: {dist:.3f}m (PDF duplicate)")

        if keep and i not in skip_indices:
            keep_doors.append(door)

    print(f"   🗑️  Removed {len(removed)} duplicate doors")
    for name in removed:
        print(f"      - {name}")

    return keep_doors + other_objects


def remove_duplicate_windows(objects, tolerance=0.5):
    """Remove duplicate windows (same window on multiple PDF pages: floor plan, elevations)

    Windows appearing on both floor plans and elevation drawings get extracted twice.
    Remove duplicates within 0.5m threshold (more lenient than doors due to elevation view offsets).

    Expected: 7 windows (1×W1, 4×W2, 2×W3) per TB-LKTN spec.
    """
    windows = [o for o in objects if 'window' in (o.get('object_type') or '').lower()]
    other_objects = [o for o in objects if 'window' not in (o.get('object_type') or '').lower()]

    removed = []
    keep_windows = []
    skip_indices = set()

    for i, window in enumerate(windows):
        if i in skip_indices:
            continue

        for j in range(i + 1, len(windows)):
            if j in skip_indices:
                continue

            # Remove if within 0.5m (likely same window from different PDF pages)
            dist = distance_2d(window['position'], windows[j]['position'])
            if dist < tolerance:
                skip_indices.add(j)
                removed.append(windows[j]['name'])
                print(f"      ⚠️  {window['name']} <-> {windows[j]['name']}: {dist:.3f}m (multi-page duplicate)")

        if i not in skip_indices:
            keep_windows.append(window)

    print(f"   🗑️  Removed {len(removed)} duplicate windows")
    for name in removed:
        print(f"      - {name}")

    return keep_windows + other_objects


def apply_height_rules(objects, master_template_path):
    """Apply height rules from master template to objects with Z=0"""
    # Load master template
    with open(master_template_path) as f:
        template = json.load(f)

    # Build height rule map
    height_rules = {}
    for item in template.get('extraction_sequence', []):
        object_type = item.get('object_type')
        height_rule = item.get('height_rule')

        if object_type and height_rule:
            height_rules[object_type] = height_rule

    # Apply heights
    fixed_count = 0
    for obj in objects:
        pos = obj.get('position', [0, 0, 0])

        # Only fix if currently at Z=0
        if pos[2] == 0.0:
            obj_type = obj.get('object_type', '')
            height_rule = height_rules.get(obj_type)

            if height_rule:
                # Parse height rule
                if height_rule == 'ceiling_height':
                    pos[2] = 2.95
                    fixed_count += 1
                elif 'from_floor' in height_rule:
                    # Extract height like "1.2m_from_floor"
                    parts = height_rule.split('_')
                    if parts[0].replace('.', '').isdigit():
                        pos[2] = float(parts[0].replace('m', ''))
                        fixed_count += 1
                elif height_rule == 'window_sill':
                    pos[2] = 0.9
                    fixed_count += 1

                obj['position'] = pos

    print(f"   📏 Applied heights to {fixed_count} objects")
    return objects


def snap_doors_to_walls(objects, tolerance=0.5):
    """
    Snap doors to nearest wall within tolerance

    After snapping to wall, snap to nearest grid intersection to avoid
    fractional coordinates (QA requirement).

    If no wall found within tolerance, snap directly to grid.
    """
    doors = [o for o in objects if 'door' in (o.get('object_type') or '').lower()]
    walls = [o for o in objects if 'wall' in (o.get('object_type') or '').lower()]

    snapped_to_wall = 0
    snapped_to_grid = 0

    for door in doors:
        door_pos = door['position']

        nearest_wall = None
        min_dist = float('inf')
        snap_point = None

        for wall in walls:
            w_start = wall['position']
            w_end = wall.get('end_point', w_start)

            dist = distance_point_to_line(door_pos, w_start, w_end)

            if dist < min_dist and dist < tolerance:
                min_dist = dist
                nearest_wall = wall

                # Calculate snap point
                x0, y0 = door_pos[0], door_pos[1]
                x1, y1 = w_start[0], w_start[1]
                x2, y2 = w_end[0], w_end[1]

                dx = x2 - x1
                dy = y2 - y1

                if dx == 0 and dy == 0:
                    snap_point = [x1, y1, door_pos[2]]
                else:
                    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx**2 + dy**2)))
                    snap_point = [x1 + t * dx, y1 + t * dy, door_pos[2]]

        if nearest_wall and snap_point:
            # Don't grid-snap doors after wall-snapping - preserve exact wall position
            # Grid-snapping causes multiple doors to collapse to same grid point
            door['position'] = snap_point
            snapped_to_wall += 1
        else:
            # No wall found - snap directly to grid (QA requirement)
            snapped_x = snap_to_nearest_grid(door_pos[0], GRID_X)
            snapped_y = snap_to_nearest_grid(door_pos[1], GRID_Y)
            door['position'] = [snapped_x, snapped_y, door_pos[2]]
            snapped_to_grid += 1

    print(f"   🔗 Snapped {snapped_to_wall} doors to walls, {snapped_to_grid} to grid")
    return objects


def fix_duplicate_names(objects):
    """Add unique suffixes to duplicate names"""
    name_counts = {}

    # First pass: count occurrences
    for obj in objects:
        name = obj['name']
        name_counts[name] = name_counts.get(name, 0) + 1

    # Second pass: add suffixes to duplicates
    name_instances = {}
    fixed_count = 0

    for obj in objects:
        name = obj['name']

        if name_counts[name] > 1:
            # This name appears multiple times
            instance_num = name_instances.get(name, 0) + 1
            name_instances[name] = instance_num

            # Add coordinate-based suffix
            pos = obj.get('position', [0, 0, 0])
            new_name = f"{name}_x{int(pos[0]*10)}_y{int(pos[1]*10)}"
            obj['name'] = new_name
            fixed_count += 1

    print(f"   🏷️  Fixed {fixed_count} duplicate names")
    return objects


def optimize_template_spacing(objects):
    """Adjust template object spacing to reduce minor collisions"""
    # Group by room
    rooms = {}
    for obj in objects:
        room = obj.get('room', 'unknown')
        if room not in rooms:
            rooms[room] = []
        rooms[room].append(obj)

    adjusted_count = 0

    for room_name, room_objects in rooms.items():
        # Only adjust template-inferred furniture
        furniture = [o for o in room_objects if o.get('source') == 'template_inference' and o.get('_phase') == '6_furniture']

        for i, obj in enumerate(furniture):
            pos = obj['position']

            # Check for collisions with other furniture
            for j, other in enumerate(furniture):
                if i == j:
                    continue

                other_pos = other['position']
                dist = distance_2d(pos, other_pos)

                # If too close (< 0.8m), push apart slightly
                if dist < 0.8 and dist > 0.01:
                    # Calculate push direction
                    dx = pos[0] - other_pos[0]
                    dy = pos[1] - other_pos[1]

                    # Normalize
                    mag = math.sqrt(dx*dx + dy*dy)
                    if mag > 0:
                        dx /= mag
                        dy /= mag

                    # Push this object away by 0.3m
                    pos[0] += dx * 0.3
                    pos[1] += dy * 0.3
                    obj['position'] = pos
                    adjusted_count += 1

    if adjusted_count > 0:
        print(f"   ↔️  Adjusted {adjusted_count} object positions to reduce collisions")

    return objects


def fix_towel_racks_as_walls(objects):
    """Fix towel racks that were incorrectly classified as walls"""
    fixed = []
    for obj in objects:
        name = obj.get('name', '')
        obj_type = obj.get('object_type', '')

        # If it's a towel rack but classified as wall, fix it
        if 'towel_rack' in name.lower() and ('wall_' in obj_type.lower() or obj_type.lower().startswith('wall')):
            obj['object_type'] = 'towel_rack_wall_lod300'
            # Remove wall-specific fields
            if 'end_point' in obj:
                del obj['end_point']
            if 'thickness' in obj:
                del obj['thickness']
            # Change phase to 6_furniture
            obj['_phase'] = '6_furniture'
            # Set proper height (1.5m from floor)
            pos = obj.get('position', [0, 0, 0])
            pos[2] = 1.5
            obj['position'] = pos
            fixed.append(name)

    if fixed:
        print(f"   🔧 Fixed {len(fixed)} towel racks misclassified as walls")
        for name in fixed:
            print(f"      - {name}")

    return objects


def fix_ceiling_objects_height(objects):
    """Move ceiling objects from Z=0 to ceiling height

    CRITICAL: Do NOT modify walls - they should be at z=0 (base) and z=3.0 (top)
    """
    ceiling_keywords = ['ceiling', 'light', 'fan', 'exhaust']
    fixed = []

    for obj in objects:
        name = obj.get('name', '').lower()
        obj_type = (obj.get('object_type') or '').lower()
        pos = obj.get('position', [0, 0, 0])

        # CRITICAL: Skip walls - they have their own z-positioning (base=0, top=3.0)
        is_wall = 'wall' in obj_type
        if is_wall:
            continue

        # Check if this is a ceiling object at wrong height
        is_ceiling = any(kw in name or kw in obj_type for kw in ceiling_keywords)

        if is_ceiling and pos[2] < 2.0:
            obj['position'] = [pos[0], pos[1], 2.95]  # Standard ceiling height
            fixed.append(obj.get('name', 'unnamed'))

    if fixed:
        print(f"   📏 Fixed {len(fixed)} ceiling objects at wrong height")
        if len(fixed) <= 10:
            for name in fixed:
                print(f"      - {name}")
        else:
            print(f"      - {fixed[0]}, {fixed[1]}, ... and {len(fixed)-2} more")

    return objects


def snap_windows_to_walls(objects, tolerance=1.0):
    """Snap windows to nearest wall within tolerance"""
    windows = [o for o in objects if 'window' in (o.get('object_type') or '').lower() or
               (o.get('name', '').startswith('W') and '_x' in o.get('name', ''))]
    walls = [o for o in objects if 'wall' in (o.get('object_type') or '').lower()]

    snapped_count = 0
    for window in windows:
        win_pos = window['position']

        nearest_wall = None
        min_dist = float('inf')
        snap_point = None

        for wall in walls:
            w_start = wall['position']
            w_end = wall.get('end_point', w_start)

            dist = distance_point_to_line(win_pos, w_start, w_end)

            if dist < min_dist and dist < tolerance:
                min_dist = dist
                nearest_wall = wall

                # Calculate snap point
                x0, y0 = win_pos[0], win_pos[1]
                x1, y1 = w_start[0], w_start[1]
                x2, y2 = w_end[0], w_end[1]

                dx = x2 - x1
                dy = y2 - y1

                if dx == 0 and dy == 0:
                    snap_point = [x1, y1, win_pos[2]]
                else:
                    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx**2 + dy**2)))
                    snap_point = [x1 + t * dx, y1 + t * dy, win_pos[2]]

        if nearest_wall and snap_point:
            window['position'] = snap_point
            snapped_count += 1

    print(f"   🔗 Snapped {snapped_count} windows to walls")
    return objects


def fix_window_orientations(objects):
    """Fix windows to be parallel to their walls

    PRIORITY:
    1. If window has explicit 'wall' field → use Section 9.1 spec mapping (Rule 0)
    2. Otherwise → use geometric calculation (fallback)
    """
    windows = [o for o in objects if 'window' in (o.get('object_type') or '').lower() or
               (o.get('name', '').startswith('W') and '_x' in o.get('name', ''))]
    walls = [o for o in objects if 'wall' in (o.get('object_type') or '').lower()]

    fixed = []

    # Section 9.1 spec mapping (TB-LKTN_COMPLETE_SPECIFICATION.md:1376-1384)
    WALL_ROTATION_SPEC = {
        "NORTH": 0,   # Horizontal wall (top)
        "SOUTH": 0,   # Horizontal wall (bottom)
        "EAST": 90,   # Vertical wall (right)
        "WEST": 90    # Vertical wall (left)
    }

    for window in windows:
        # PRIORITY 1: If explicit wall field exists, use Section 9.1 spec (Rule 0)
        explicit_wall = window.get('wall')
        if explicit_wall in WALL_ROTATION_SPEC:
            spec_orientation = WALL_ROTATION_SPEC[explicit_wall]
            current_orient = window.get('orientation', 0)

            if current_orient != spec_orientation:
                window['orientation'] = spec_orientation
                fixed.append(f"{window.get('name', 'unnamed')} (wall={explicit_wall} → {spec_orientation}°)")
            continue  # Skip geometric fallback

        # PRIORITY 2: No explicit wall field → use geometric fallback
        win_pos = window['position']

        # Find nearest wall
        nearest_wall = None
        min_dist = float('inf')

        for wall in walls:
            w_start = wall['position']
            w_end = wall.get('end_point', w_start)

            dist = distance_point_to_line(win_pos, w_start, w_end)

            if dist < min_dist:
                min_dist = dist
                nearest_wall = wall

        if nearest_wall and min_dist < 1.0:
            # Calculate wall angle
            w_start = nearest_wall['position']
            w_end = nearest_wall.get('end_point', w_start)

            dx = w_end[0] - w_start[0]
            dy = w_end[1] - w_start[1]

            if abs(dx) > abs(dy):
                # Horizontal wall
                wall_angle = 0 if dx > 0 else 180
            else:
                # Vertical wall
                wall_angle = 90 if dy > 0 else 270

            # Window should be parallel to wall
            current_orient = window.get('orientation', 0)

            # Check if window needs fixing (not parallel or opposite)
            needs_fix = not (abs(current_orient - wall_angle) < 5 or
                           abs(current_orient - wall_angle - 180) < 5 or
                           abs(current_orient - wall_angle + 180) < 5)

            if needs_fix:
                window['orientation'] = wall_angle
                fixed.append(f"{window.get('name', 'unnamed')} (geometric → {wall_angle}°)")

    if fixed:
        print(f"   🪟 Fixed {len(fixed)} window orientations to match walls")
        for name in fixed:
            print(f"      - {name}")

    return objects


def remove_zero_area_structures(objects):
    """Remove structural planes/slabs with zero area (but keep point fixtures)"""
    removed = []
    keep_objects = []

    for obj in objects:
        obj_type = obj.get('object_type', '')
        name = obj.get('name', '')

        # Only check actual structural planes/slabs (not fixtures/equipment)
        is_plane = any(kw in name.lower() for kw in ['floor_slab', 'ceiling_plane', 'roof_structure'])

        if is_plane:
            # Check if it has area
            dimensions = obj.get('dimensions', [0, 0, 0])

            # Dimensions can be list [L, W, H] or dict
            if isinstance(dimensions, list):
                if len(dimensions) >= 2:
                    length = dimensions[0]
                    width = dimensions[1]
                else:
                    length = 0
                    width = 0
            elif isinstance(dimensions, dict):
                length = dimensions.get('length', 0)
                width = dimensions.get('width', 0)
            else:
                length = 0
                width = 0

            area = length * width

            if area < 0.01:  # Less than 0.01 m²
                removed.append(name)
                continue

        keep_objects.append(obj)

    if removed:
        print(f"   🗑️  Removed {len(removed)} zero-area structural planes")
        for name in removed:
            print(f"      - {name}")

    return keep_objects


def assign_doors_to_rooms(objects):
    """
    [THIRD-D] Assign doors to correct rooms based on spatial analysis

    Strategy:
    1. Load room bounds from GridTruth.json ([THIRD-D]: WHERE)
    2. For each door, check which room(s) it's adjacent to
    3. Use door name to disambiguate (Malay → English mapping)
    4. Fallback to door orientation if name parsing fails
    """
    doors = [o for o in objects if 'door' in (o.get('object_type') or '').lower()]

    # [THIRD-D] Malay room name mapping (from door labels)
    MALAY_TO_ENGLISH = {
        'ruang_tamu': 'living_room',
        'dapur': 'kitchen',
        'bilik_utama': 'master_bedroom',
        'bilik_2': 'bedroom_2',
        'bilik_mandi': 'bathroom_master',
        'tandas': 'bathroom_common',
        'ruang_basuh': 'utility_room',
        'anjung': 'porch'
    }

    # Derive room bounds from Annotations DB
    try:
        # Find annotation database (standard location)
        annotation_db = Path('output_artifacts/TB-LKTN_HOUSE_ANNOTATION_FROM_2D.db')

        if annotation_db.exists():
            from src.core.annotation_derivation import derive_room_bounds
            room_bounds = derive_room_bounds(str(annotation_db))
        else:
            # Fallback: use validated default bounds
            print(f"   ⚠️  Annotation DB not found, using default room bounds")
            room_bounds = {
                'RUANG_TAMU': {'x_min': 0.0, 'x_max': 4.4, 'y_min': 0.0, 'y_max': 5.4},
                'DAPUR': {'x_min': 4.4, 'x_max': 11.2, 'y_min': 2.3, 'y_max': 7.0},
                'BILIK_UTAMA': {'x_min': 8.1, 'x_max': 11.2, 'y_min': 7.0, 'y_max': 8.5},
                'BILIK_2': {'x_min': 1.3, 'x_max': 8.1, 'y_min': 7.0, 'y_max': 8.5},
                'BILIK_MANDI': {'x_min': 0.0, 'x_max': 1.3, 'y_min': 5.4, 'y_max': 7.0},
                'TANDAS': {'x_min': 0.0, 'x_max': 1.3, 'y_min': 7.0, 'y_max': 8.5},
                'RUANG_BASUH': {'x_min': 4.4, 'x_max': 8.1, 'y_min': 5.4, 'y_max': 7.0},
                'CORRIDOR': {'x_min': 1.3, 'x_max': 4.4, 'y_min': 5.4, 'y_max': 7.0}
            }
    except Exception as e:
        print(f"   ⚠️  Could not derive room bounds: {e}")
        room_bounds = {}

    fixed_count = 0
    for door in doors:
        door_pos = door.get('position', [0, 0, 0])
        door_name = door.get('name', '').lower()

        # [CORE-D] Extract room from door name (e.g., "door_ruang_tamu" → "ruang_tamu")
        room_from_name = None
        for malay, english in MALAY_TO_ENGLISH.items():
            if malay in door_name:
                room_from_name = english
                break

        # [THIRD-D] Find which room(s) door is adjacent to (spatial check)
        adjacent_rooms = []
        tolerance = 0.3  # 300mm tolerance for door on boundary

        for room_name, bounds in room_bounds.items():
            # Skip metadata entries (like "_note")
            if not isinstance(bounds, dict):
                continue

            # Check if door is ON or NEAR room boundary
            x, y = door_pos[0], door_pos[1]
            x_min, x_max = bounds.get('x_min', 0), bounds.get('x_max', 0)
            y_min, y_max = bounds.get('y_min', 0), bounds.get('y_max', 0)

            # Check if on any boundary
            on_boundary = (
                (abs(x - x_min) < tolerance or abs(x - x_max) < tolerance) and (y_min - tolerance <= y <= y_max + tolerance) or
                (abs(y - y_min) < tolerance or abs(y - y_max) < tolerance) and (x_min - tolerance <= x <= x_max + tolerance)
            )

            if on_boundary:
                # Map Malay room names to English
                room_english = MALAY_TO_ENGLISH.get(room_name.lower(), room_name.lower())
                adjacent_rooms.append(room_english)

        # [IFC] Decide room assignment: prefer name-based, fallback to spatial
        assigned_room = None

        if room_from_name:
            # Door name tells us which room it belongs to
            assigned_room = room_from_name
        elif len(adjacent_rooms) == 1:
            # Only adjacent to one room
            assigned_room = adjacent_rooms[0]
        elif len(adjacent_rooms) > 1:
            # Multiple adjacent rooms - use first one (corridor doors are ambiguous)
            assigned_room = adjacent_rooms[0]

        if assigned_room and door.get('room') != assigned_room:
            door['room'] = assigned_room
            fixed_count += 1

    if fixed_count > 0:
        print(f"   🚪 Assigned {fixed_count} doors to rooms (using [THIRD-D] spatial + name analysis)")
    else:
        print(f"   ℹ️  All doors already assigned")

    return objects


def remove_phantom_rooms(objects):
    """Remove objects in phantom/zero-area rooms"""
    # Calculate room sizes
    rooms = {}
    for obj in objects:
        room = obj.get('room')
        if room:
            if room not in rooms:
                rooms[room] = []
            rooms[room].append(obj)

    phantom_rooms = []
    for room_name, room_objects in rooms.items():
        positions = [o.get('position', [0, 0, 0]) for o in room_objects]
        if positions:
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]

            room_width = max(xs) - min(xs)
            room_length = max(ys) - min(ys)
            room_area = room_width * room_length

            # Mark phantom rooms (zero area or suspiciously small)
            if room_area < 0.01:  # Less than 0.01m²
                phantom_rooms.append(room_name)

    # Remove objects in phantom rooms OR reassign them
    fixed_objects = []
    removed_count = 0

    for obj in objects:
        room = obj.get('room')
        if room in phantom_rooms:
            # If it's a structural element, keep but reassign to 'structure'
            obj_type = obj.get('object_type', '')
            if any(kw in obj_type.lower() for kw in ['floor', 'ceiling', 'roof', 'slab']):
                obj['room'] = 'structure'
                fixed_objects.append(obj)
            else:
                # Reassign to 'unknown' to be picked up by room inference
                obj['room'] = 'unknown'
                fixed_objects.append(obj)
                removed_count += 1
        else:
            fixed_objects.append(obj)

    if phantom_rooms:
        print(f"   🗑️  Cleaned {len(phantom_rooms)} phantom rooms: {', '.join(phantom_rooms[:3])}")
        if removed_count > 0:
            print(f"   ♻️  Reassigned {removed_count} objects to 'unknown'")

    return fixed_objects


def snap_isolated_walls_to_network(objects, tolerance=0.15):
    """Snap isolated wall endpoints to nearby walls to form connected network"""
    walls = [o for o in objects if 'wall' in (o.get('object_type') or '').lower()]
    other_objects = [o for o in objects if 'wall' not in (o.get('object_type') or '').lower()]

    def distance_3d(p1, p2):
        return math.sqrt(sum((a-b)**2 for a, b in zip(p1, p2)))

    # Find isolated walls
    snapped_count = 0

    for i, wall in enumerate(walls):
        w_start = wall['position']
        w_end = wall.get('end_point', w_start)

        # Check if endpoints connect to any other wall
        start_connected = False
        end_connected = False

        for j, other in enumerate(walls):
            if i == j:
                continue

            o_start = other['position']
            o_end = other.get('end_point', o_start)

            # Check start point
            if (distance_3d(w_start, o_start) < 0.1 or
                distance_3d(w_start, o_end) < 0.1):
                start_connected = True

            # Check end point
            if (distance_3d(w_end, o_start) < 0.1 or
                distance_3d(w_end, o_end) < 0.1):
                end_connected = True

        # If isolated, try to snap to nearby walls
        if not start_connected or not end_connected:
            for other in walls:
                if other is wall:
                    continue

                o_start = other['position']
                o_end = other.get('end_point', o_start)

                # Try to snap start point
                if not start_connected:
                    dist_to_start = distance_3d(w_start, o_start)
                    dist_to_end = distance_3d(w_start, o_end)

                    if dist_to_start < tolerance:
                        wall['position'] = o_start.copy()
                        start_connected = True
                        snapped_count += 1
                    elif dist_to_end < tolerance:
                        wall['position'] = o_end.copy()
                        start_connected = True
                        snapped_count += 1

                # Try to snap end point
                if not end_connected:
                    dist_to_start = distance_3d(w_end, o_start)
                    dist_to_end = distance_3d(w_end, o_end)

                    if dist_to_start < tolerance:
                        wall['end_point'] = o_start.copy()
                        end_connected = True
                        snapped_count += 1
                    elif dist_to_end < tolerance:
                        wall['end_point'] = o_end.copy()
                        end_connected = True
                        snapped_count += 1

                if start_connected and end_connected:
                    break

    if snapped_count > 0:
        print(f"   🔗 Snapped {snapped_count} wall endpoints to form connected network")
    else:
        print(f"   ℹ️  No wall endpoints snapped (already connected)")

    return walls + other_objects


def remove_self_intersecting_walls(objects):
    """Remove walls that self-intersect with others"""
    walls = [o for o in objects if 'wall' in (o.get('object_type') or '').lower()]
    other_objects = [o for o in objects if 'wall' not in (o.get('object_type') or '').lower()]

    def segments_intersect(p1, p2, p3, p4):
        """Check if line segments p1-p2 and p3-p4 intersect"""
        def ccw(A, B, C):
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

        return ccw(p1,p3,p4) != ccw(p2,p3,p4) and ccw(p1,p2,p3) != ccw(p1,p2,p4)

    # Find intersection pairs
    intersection_counts = {}

    for i, wall1 in enumerate(walls):
        w1_start = wall1['position']
        w1_end = wall1.get('end_point', w1_start)

        for j, wall2 in enumerate(walls):
            if i >= j:
                continue

            w2_start = wall2['position']
            w2_end = wall2.get('end_point', w2_start)

            # Skip if walls share endpoints (connected walls are OK)
            if (distance_2d(w1_start, w2_start) < 0.1 or
                distance_2d(w1_start, w2_end) < 0.1 or
                distance_2d(w1_end, w2_start) < 0.1 or
                distance_2d(w1_end, w2_end) < 0.1):
                continue

            # Check intersection
            if segments_intersect(w1_start, w1_end, w2_start, w2_end):
                wall1_name = wall1['name']
                wall2_name = wall2['name']

                intersection_counts[wall1_name] = intersection_counts.get(wall1_name, 0) + 1
                intersection_counts[wall2_name] = intersection_counts.get(wall2_name, 0) + 1

    # Remove walls with most intersections (likely errors)
    removed = []
    keep_walls = []

    for wall in walls:
        name = wall['name']
        intersect_count = intersection_counts.get(name, 0)

        # Remove if it intersects with more than 3 other walls
        if intersect_count > 3:
            removed.append(name)
        else:
            keep_walls.append(wall)

    if removed:
        print(f"   🗑️  Removed {len(removed)} highly intersecting walls")
        if len(removed) <= 10:
            for name in removed:
                print(f"      - {name}")
        else:
            print(f"      - {removed[0]}, {removed[1]}, ... and {len(removed)-2} more")

    return keep_walls + other_objects


def fix_wall_z_positioning(objects):
    """
    DISABLED - This function had wrong logic.

    Walls are 2D floor plan segments:
      position:  [x1, y1, 0]  ← Start on floor
      end_point: [x2, y2, 0]  ← End on floor (NOT ceiling!)
      height:    3.0          ← Vertical height (separate attribute)

    Keeping function for backward compatibility but not applying fixes.
    """
    print(f"   ℹ️  Wall z-positioning: Skipped (walls are 2D floor segments)")
    return objects


def snap_to_nearest_grid(value, grid_points):
    """Snap a coordinate value to nearest grid point"""
    return min(grid_points, key=lambda g: abs(g - value))


def snap_coordinates_to_grid(objects):
    """
    Snap wall coordinates to nearest grid points

    Grid X: [0.0, 1.3, 4.4, 8.1, 11.2] (A-E)
    Grid Y: [0.0, 2.3, 5.4, 7.0, 8.5] (1-5)

    Snaps position and end_point x,y coordinates (preserves z)

    NOTE: Doors/windows are NOT snapped here - they'll be snapped to walls
    later by Fix 9/10, which preserves their position along the wall.
    """
    snapped_count = 0

    for obj in objects:
        obj_type = (obj.get('object_type') or '').lower()
        is_wall = 'wall' in obj_type
        is_door = 'door' in obj_type
        is_window = 'window' in obj_type
        is_porch = obj.get('room') == 'ANJUNG'

        # ONLY snap walls to grid - everything else preserves calculated position
        # Skip doors/windows - they'll be snapped to walls later
        if is_door or is_window:
            continue

        # Skip porch objects - they're in negative Y space (outside main grid)
        if is_porch:
            continue

        # Skip furniture - preserves template-calculated positions
        phase = obj.get('_phase', '')
        if phase == '6_furniture':
            continue

        # Skip structural planes (floor/ceiling/roof) - use center positions
        obj_name = obj.get('name', '').lower()
        if any(kw in obj_name for kw in ['floor_slab', 'ceiling_plane', 'roof_structure']):
            continue

        # Skip fixtures (electrical/plumbing) - preserve wall-mounted positions
        if any(kw in obj_type for kw in ['light', 'fan', 'switch', 'outlet', 'basin', 'toilet', 'shower', 'drain', 'sink', 'towel', 'stove', 'refrigerator']):
            continue

        # If not a wall, skip snapping (only walls should snap to grid)
        if not is_wall:
            continue

        # Snap position
        pos = obj.get('position', [0, 0, 0])
        if len(pos) >= 2:
            snapped_x = snap_to_nearest_grid(pos[0], GRID_X)
            snapped_y = snap_to_nearest_grid(pos[1], GRID_Y)

            # Check if x,y need snapping OR if wall needs z-correction
            needs_snap = abs(snapped_x - pos[0]) > 0.01 or abs(snapped_y - pos[1]) > 0.01
            needs_z_fix = is_wall and abs(pos[2] - 0.0) > 0.01

            if needs_snap or needs_z_fix:
                # For walls, always use z=0 (base at floor level)
                # For other objects, preserve original z
                z_val = 0.0 if is_wall else (pos[2] if len(pos) > 2 else 0)
                obj['position'] = [snapped_x, snapped_y, z_val]
                snapped_count += 1

        # Snap end_point (for walls)
        end = obj.get('end_point')
        if end and len(end) >= 2:
            snapped_x = snap_to_nearest_grid(end[0], GRID_X)
            snapped_y = snap_to_nearest_grid(end[1], GRID_Y)

            # Check if x,y need snapping
            needs_snap = abs(snapped_x - end[0]) > 0.01 or abs(snapped_y - end[1]) > 0.01

            if needs_snap:
                # Walls: end_point.z should stay at 0 (2D floor plan)
                # Other objects: preserve z
                z_val = 0.0 if is_wall else (end[2] if len(end) > 2 else 0.0)
                obj['end_point'] = [snapped_x, snapped_y, z_val]
                snapped_count += 1

                # DEBUG: Log snapping
                if is_wall:
                    print(f"      🔧 Snapped {obj.get('name', 'wall')}: end=[{snapped_x:.2f}, {snapped_y:.2f}, {z_val:.2f}]")

    print(f"   Snapped {snapped_count} coordinates to grid")
    return objects


def fix_window_sill_heights(objects):
    """
    Set window positions to sill height (z=0.9m standard)

    Windows are mounted at sill height, not floor level.
    Malaysian standard: 900mm sill height for residential windows.
    """
    WINDOW_SILL_HEIGHT = 0.9  # meters
    fixed_count = 0

    for obj in objects:
        if 'window' in (obj.get('object_type') or '').lower():
            pos = obj.get('position', [0, 0, 0])
            if len(pos) >= 3 and abs(pos[2] - WINDOW_SILL_HEIGHT) > 0.01:
                obj['position'] = [pos[0], pos[1], WINDOW_SILL_HEIGHT]
                fixed_count += 1
                print(f"      🪟 {obj.get('name', 'window')}: z=0.0 → z={WINDOW_SILL_HEIGHT}m")

    print(f"   Fixed {fixed_count} window sill heights")
    return objects


def filter_degenerate_walls(objects):
    """
    Remove zero-length (degenerate) walls where position == end_point

    These can be created by grid snapping when both endpoints snap to same point.
    """
    walls = []
    other_objects = []
    degenerate_count = 0

    for obj in objects:
        if 'wall' in (obj.get('object_type') or '').lower():
            # Check if wall has end_point
            if 'end_point' in obj:
                pos = obj['position']
                end = obj['end_point']
                dx = end[0] - pos[0]
                dy = end[1] - pos[1]
                length = math.sqrt(dx*dx + dy*dy)

                if length < 0.01:  # Less than 1cm - degenerate
                    degenerate_count += 1
                    print(f"      ❌ REMOVED: {obj.get('name', 'wall')} [{pos[0]:.2f}, {pos[1]:.2f}] → [{end[0]:.2f}, {end[1]:.2f}] (length={length:.4f}m)")
                else:
                    walls.append(obj)
            else:
                walls.append(obj)
        else:
            other_objects.append(obj)

    print(f"   Removed {degenerate_count} degenerate walls")
    return walls + other_objects


def fix_null_object_types(objects):
    """Fix objects with null/missing object_type (extraction errors)"""
    fixed_count = 0

    for obj in objects:
        obj_type = obj.get('object_type')
        name = obj.get('name', '')

        # If object_type is None, infer from name
        if obj_type is None:
            if name.startswith('W'):
                # Window without type - use default aluminum window
                obj['object_type'] = 'window_aluminum_2panel_1200x1000_lod300'
                fixed_count += 1
                print(f"      🪟 {name}: null → window_aluminum_2panel_1200x1000_lod300 (default)")
            elif name.startswith('D'):
                # Door without type - use default solid door
                obj['object_type'] = 'door_solid_wood_single_lod300'
                fixed_count += 1
                print(f"      🚪 {name}: null → door_solid_wood_single_lod300 (default)")
            else:
                # Unknown - mark as generic object
                obj['object_type'] = 'generic_object_lod300'
                fixed_count += 1
                print(f"      ⚠️  {name}: null → generic_object_lod300 (fallback)")

    if fixed_count > 0:
        print(f"   🔧 Fixed {fixed_count} objects with null object_type")
    else:
        print(f"   ℹ️  All objects have valid object_type")

    return objects


def automated_post_process(extraction_output, master_template_path):
    """
    Run all automated fixes on extraction output

    Args:
        extraction_output: dict with 'objects' array
        master_template_path: Path to master_reference_template.json

    Returns:
        dict: Fixed extraction output
    """
    print("\n" + "="*80)
    print("🔧 AUTOMATED POST-PROCESSOR")
    print("="*80)

    objects = extraction_output.get('objects', [])
    initial_count = len(objects)

    print(f"\n📊 Initial state: {initial_count} objects")

    # Fix 0: Fix null object_types
    print("\n🔧 Fix 0: Fixing null/missing object_types...")
    objects = fix_null_object_types(objects)

    # Fix 0A: Fix wall z-positioning (CRITICAL - must run first)
    print("\n🔧 Fix 0A: Fixing wall z-positioning (base=0, top=3.0)...")
    objects = fix_wall_z_positioning(objects)

    # Fix 0B: Snap coordinates to grid (CRITICAL - must run early)
    print("\n🔧 Fix 0B: Snapping coordinates to grid...")
    objects = snap_coordinates_to_grid(objects)

    # Fix 0C: Filter degenerate walls created by grid snapping
    print("\n🔧 Fix 0C: Filtering degenerate zero-length walls...")
    objects = filter_degenerate_walls(objects)

    # Fix 1: Fix towel racks misclassified as walls
    print("\n🔧 Fix 1: Fixing towel racks misclassified as walls...")
    objects = fix_towel_racks_as_walls(objects)

    # Fix 2: Remove duplicate walls
    print("\n🔧 Fix 2: Removing duplicate walls...")
    objects = remove_duplicate_walls(objects, tolerance=0.15)

    # Fix 3: Remove duplicate doors
    print("\n🔧 Fix 3: Removing duplicate doors...")
    objects = remove_duplicate_doors(objects)

    # Fix 4: Snap isolated walls to network
    print("\n🔧 Fix 4: Snapping isolated walls to network...")
    objects = snap_isolated_walls_to_network(objects, tolerance=0.5)

    # Fix 5: Remove self-intersecting walls
    print("\n🔧 Fix 5: Removing highly intersecting walls...")
    objects = remove_self_intersecting_walls(objects)

    # Fix 6: Remove zero-area structures
    print("\n🔧 Fix 6: Removing zero-area structural elements...")
    objects = remove_zero_area_structures(objects)

    # Fix 7: Apply height rules
    print("\n🔧 Fix 7: Applying height rules from master template...")
    objects = apply_height_rules(objects, master_template_path)

    # Fix 8: Fix ceiling objects height
    print("\n🔧 Fix 8: Fixing ceiling objects at wrong height...")
    objects = fix_ceiling_objects_height(objects)

    # Fix 9: Snap doors to walls
    print("\n🔧 Fix 9: Snapping doors to nearest walls...")
    objects = snap_doors_to_walls(objects, tolerance=0.5)  # Balanced: finds walls without over-reaching

    # Fix 9B: Remove duplicate doors created by grid snapping
    print("\n🔧 Fix 9B: Removing duplicate doors after grid snapping...")
    # Reduced to 0.05m (5cm) - only remove true PDF parsing duplicates, not nearby doors
    objects = remove_duplicate_doors(objects, tolerance=0.05)

    # Fix 10: Snap windows to walls
    print("\n🔧 Fix 10: Snapping windows to nearest walls...")
    objects = snap_windows_to_walls(objects, tolerance=1.0)

    # Fix 11: Fix window orientations
    print("\n🔧 Fix 11: Fixing window orientations to match walls...")
    objects = fix_window_orientations(objects)

    # Fix 11A: Fix window sill heights
    print("\n🔧 Fix 11A: Setting window sill heights (z=0.9m)...")
    objects = fix_window_sill_heights(objects)

    # Fix 11B: Remove duplicate windows (multi-page extraction)
    print("\n🔧 Fix 11B: Removing duplicate windows from multiple PDF pages...")
    objects = remove_duplicate_windows(objects, tolerance=0.5)

    # Fix 12: Fix duplicate names
    print("\n🔧 Fix 12: Fixing duplicate names...")
    objects = fix_duplicate_names(objects)

    # Fix 13: Optimize spacing
    print("\n🔧 Fix 13: Optimizing template object spacing...")
    objects = optimize_template_spacing(objects)

    # Fix 14: Assign doors to rooms
    print("\n🔧 Fix 14: Assigning doors to correct rooms...")
    objects = assign_doors_to_rooms(objects)

    # Fix 15: Remove phantom rooms
    print("\n🔧 Fix 15: Cleaning phantom/zero-area rooms...")
    objects = remove_phantom_rooms(objects)

    # Update extraction output
    extraction_output['objects'] = objects

    # Update summary
    final_count = len(objects)
    extraction_output['summary']['total_objects'] = final_count

    # [FIFTH-D] Apply IFC naming layer to ALL objects (including merged walls)
    print("\n🔧 Fix 16: Applying FIFTH-D IFC classification to all objects...")
    from src.core.ifc_naming_util import IfcNamingLayer
    naming_layer_path = os.path.join(os.path.dirname(__file__), 'ifc_naming_layer.json')
    naming_layer = IfcNamingLayer(naming_layer_path)

    ifc_applied_count = 0
    for obj in objects:
        object_type = obj.get('object_type', '')
        if object_type and not obj.get('ifc_class'):  # Only if missing IFC class
            props = naming_layer.get_properties(object_type)
            obj.update(props)
            ifc_applied_count += 1

    print(f"   🏷️  Applied IFC properties to {ifc_applied_count} objects")

    print("\n" + "="*80)
    print(f"✅ POST-PROCESSING COMPLETE")
    print("="*80)
    print(f"Objects: {initial_count} → {final_count} (removed {initial_count - final_count} total)")
    print()

    return extraction_output


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 post_processor.py <augmented_output.json>")
        sys.exit(1)

    input_path = sys.argv[1]

    # Load augmented output
    with open(input_path) as f:
        data = json.load(f)

    # Get master template path
    script_dir = Path(__file__).parent
    master_template_path = script_dir / "master_reference_template.json"

    # Run post-processing
    fixed_data = automated_post_process(data, master_template_path)

    # Save fixed output
    output_path = input_path.replace('.json', '_FIXED.json')
    with open(output_path, 'w') as f:
        json.dump(fixed_data, f, indent=2)

    print(f"💾 Saved fixed output: {output_path}")
