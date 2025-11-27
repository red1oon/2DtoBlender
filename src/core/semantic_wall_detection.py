#!/usr/bin/env python3
"""
Stage 2.1: Structural Semantic Layer - Wall Detection from Primitives

Converts disconnected line primitives into semantic wall entities using
DISCHARGE perimeter (contractor workflow).

INPUT: primitives_lines table + context_calibration (DISCHARGE perimeter)
OUTPUT: semantic_walls table (wall_id, primitive_line_ids[], bbox, orientation, length, wall_type)

Algorithm (DETERMINISTIC - TEXT-ONLY, no AI):
  Step 1A: Extract 4 exterior walls from DISCHARGE perimeter (ground truth)
    - Read DISCHARGE perimeter from context_calibration
    - Calculate exterior wall bounding box (perimeter - overhang)
    - Find line clusters aligned with 4 sides
    - WALL_ALIGNMENT_TOLERANCE = 0.3m

  Step 1B: Cluster interior walls (DBSCAN)
    - Exclude lines used in exterior walls
    - Filter by line width (structural walls are thicker)
    - PROXIMITY_EPS = 0.15m
    - MIN_SAMPLES = 2
    - MIN_LINE_WIDTH = 0.15pt

  Step 2: Collinear merging
    - ALIGNMENT_TOLERANCE = 5°
    - GAP_TOLERANCE = 0.05m

  Step 3: Wall validation
    - MIN_WALL_LENGTH = 0.5m

Compliance: Rule 0 (First Law) - if walls wrong → edit constants below, re-run
"""

import sqlite3
import numpy as np
import json
from pathlib import Path
from typing import List, Tuple, Dict
import math


# ============================================================================
# Manual DBSCAN Implementation (no sklearn dependency)
# ============================================================================

def manual_dbscan(points: np.ndarray, eps: float, min_samples: int) -> np.ndarray:
    """
    Simple DBSCAN implementation without sklearn dependency

    Args:
        points: Nx2 array of (x, y) coordinates
        eps: Maximum distance for neighborhood
        min_samples: Minimum points in neighborhood to form cluster

    Returns:
        Array of cluster labels (-1 for noise)
    """
    n_points = len(points)
    labels = np.full(n_points, -1, dtype=int)
    cluster_id = 0

    for i in range(n_points):
        if labels[i] != -1:
            continue

        # Find neighbors
        distances = np.sqrt(np.sum((points - points[i])**2, axis=1))
        neighbors = np.where(distances <= eps)[0]

        if len(neighbors) < min_samples:
            continue  # Noise point

        # Start new cluster
        labels[i] = cluster_id
        seed_set = list(neighbors)

        # Expand cluster
        while seed_set:
            current = seed_set.pop(0)

            if labels[current] == -1:
                labels[current] = cluster_id

                # Find neighbors of current point
                distances = np.sqrt(np.sum((points - points[current])**2, axis=1))
                current_neighbors = np.where(distances <= eps)[0]

                if len(current_neighbors) >= min_samples:
                    for neighbor in current_neighbors:
                        if labels[neighbor] == -1:
                            seed_set.append(neighbor)

        cluster_id += 1

    return labels


# ============================================================================
# HARDCODED PARAMETERS (Rule 0: Edit these if results incorrect)
# ============================================================================

# Step 1A: Exterior wall extraction
WALL_ALIGNMENT_TOLERANCE = 0.3    # meters (lines near DISCHARGE boundary)

# Step 1B: Interior wall clustering
PROXIMITY_EPS = 0.40              # meters (perpendicular distance threshold for clustering)
MIN_SAMPLES = 2                   # minimum lines to form cluster
MIN_LINE_WIDTH = 3.5              # PDF points (structural walls 4pt+, exclude fixtures 1-3pt)

# Step 2: Collinear merging
ALIGNMENT_TOLERANCE = 5           # degrees (angle difference threshold)
PERPENDICULAR_TOLERANCE = 0.15    # meters (perpendicular distance for collinear check)
GAP_TOLERANCE = 2.5               # meters (max endpoint gap to bridge - for door openings)

# Step 3: Validation
MIN_WALL_LENGTH = 1.2             # meters (reject short segments - door frames, cabinets)


# ============================================================================
# Helper Functions
# ============================================================================

def get_line_angle(x0: float, y0: float, x1: float, y1: float) -> float:
    """Calculate line orientation in degrees (0-180)"""
    angle_rad = math.atan2(y1 - y0, x1 - x0)
    angle_deg = math.degrees(angle_rad)
    # Normalize to 0-180 (walls don't have direction)
    if angle_deg < 0:
        angle_deg += 180
    return angle_deg


def lines_collinear(line1: Tuple, line2: Tuple) -> bool:
    """Check if two lines are collinear"""
    x0_1, y0_1, x1_1, y1_1 = line1
    x0_2, y0_2, x1_2, y1_2 = line2

    angle1 = get_line_angle(x0_1, y0_1, x1_1, y1_1)
    angle2 = get_line_angle(x0_2, y0_2, x1_2, y1_2)

    # Check angle alignment
    angle_diff = abs(angle1 - angle2)
    if angle_diff > 90:
        angle_diff = 180 - angle_diff

    if angle_diff > ALIGNMENT_TOLERANCE:
        return False

    # Check perpendicular distance
    def perp_dist(px, py, x0, y0, x1, y1):
        dx = x1 - x0
        dy = y1 - y0
        denom = dx*dx + dy*dy
        if denom == 0:
            return math.sqrt((px - x0)**2 + (py - y0)**2)
        t = ((px - x0) * dx + (py - y0) * dy) / denom
        closest_x = x0 + t * dx
        closest_y = y0 + t * dy
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

    dist1 = perp_dist(x0_2, y0_2, x0_1, y0_1, x1_1, y1_1)
    dist2 = perp_dist(x1_2, y1_2, x0_1, y0_1, x1_1, y1_1)

    return (dist1 < PERPENDICULAR_TOLERANCE and dist2 < PERPENDICULAR_TOLERANCE)


def lines_adjacent(line1: Tuple, line2: Tuple) -> bool:
    """Check if two collinear lines have endpoints within GAP_TOLERANCE"""
    x0_1, y0_1, x1_1, y1_1 = line1
    x0_2, y0_2, x1_2, y1_2 = line2

    endpoints = [
        (x0_1, y0_1, x0_2, y0_2),
        (x0_1, y0_1, x1_2, y1_2),
        (x1_1, y1_1, x0_2, y0_2),
        (x1_1, y1_1, x1_2, y1_2),
    ]

    for x1, y1, x2, y2 in endpoints:
        dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if dist < GAP_TOLERANCE:
            return True

    return False


def merge_collinear_lines(lines: List[Tuple]) -> Tuple:
    """Merge list of collinear lines into single line segment"""
    if not lines:
        return None
    if len(lines) == 1:
        return lines[0]

    points = []
    for x0, y0, x1, y1 in lines:
        points.append((x0, y0))
        points.append((x1, y1))

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    first_line = lines[0]
    angle = get_line_angle(*first_line)

    if abs(angle - 0) < 45 or abs(angle - 180) < 45:
        # Horizontal
        min_idx = xs.index(min(xs))
        max_idx = xs.index(max(xs))
        return (points[min_idx][0], points[min_idx][1],
                points[max_idx][0], points[max_idx][1])
    else:
        # Vertical
        min_idx = ys.index(min(ys))
        max_idx = ys.index(max(ys))
        return (points[min_idx][0], points[min_idx][1],
                points[max_idx][0], points[max_idx][1])


# ============================================================================
# Main Wall Detection Pipeline
# ============================================================================

def step1a_extract_exterior_walls(cursor: sqlite3.Cursor) -> Tuple[List[Dict], List[int]]:
    """
    Step 1A: Extract 4 exterior walls from DISCHARGE perimeter

    Returns: (exterior_walls, used_line_ids)
    """
    print(f"\n📦 STEP 1A: Extracting 4 exterior walls from DISCHARGE perimeter")
    print(f"   Parameter: WALL_ALIGNMENT_TOLERANCE={WALL_ALIGNMENT_TOLERANCE}m")

    # Get calibration data
    cursor.execute("SELECT key, value FROM context_calibration")
    calibration = {row[0]: row[1] for row in cursor.fetchall()}

    scale_m_per_pt = calibration.get('scale_m_per_pt', 0.03528)
    offset_x = calibration.get('offset_x', 0.0)
    offset_y = calibration.get('offset_y', 0.0)

    # Master doc lines 213-216: DISCHARGE perimeter (outer) vs building footprint (walls)
    # Exterior walls align with building_footprint (8m×8m)
    # DISCHARGE perimeter (11.78m×10.05m) used as outer boundary constraint only
    building_width = calibration.get('building_width_m', 8.0)
    building_length = calibration.get('building_length_m', 8.0)

    west_x = 0.0
    east_x = building_width
    south_y = 0.0
    north_y = building_length

    print(f"   Building footprint (exterior walls): {building_width}m × {building_length}m")
    print(f"   Boundary: X=[{west_x:.2f}, {east_x:.2f}], Y=[{south_y:.2f}, {north_y:.2f}]")

    # Get all structural lines (page 1 only - floor plan)
    cursor.execute("""
        SELECT id, x0, y0, x1, y1, linewidth
        FROM primitives_lines
        WHERE length > 10 AND linewidth >= ?
        AND page = 1
    """, (MIN_LINE_WIDTH,))

    lines_raw = cursor.fetchall()
    print(f"   Loaded {len(lines_raw)} structural lines (width >= {MIN_LINE_WIDTH}pt)")

    # Convert to meters
    lines = []
    for line_id, x0, y0, x1, y1, linewidth in lines_raw:
        x0_m = (x0 - offset_x) * scale_m_per_pt
        y0_m = (y0 - offset_y) * scale_m_per_pt
        x1_m = (x1 - offset_x) * scale_m_per_pt
        y1_m = (y1 - offset_y) * scale_m_per_pt

        lines.append({
            'id': line_id,
            'coords': (x0_m, y0_m, x1_m, y1_m),
            'angle': get_line_angle(x0_m, y0_m, x1_m, y1_m)
        })

    # Find lines aligned with each boundary
    exterior_walls = []
    used_line_ids = set()

    # North wall (top, Y ~ north_y)
    north_lines = [l for l in lines if abs(min(l['coords'][1], l['coords'][3]) - north_y) < WALL_ALIGNMENT_TOLERANCE and
                   abs(l['angle'] - 0) < 20 or abs(l['angle'] - 180) < 20]
    if north_lines:
        coords_list = [l['coords'] for l in north_lines]
        merged = merge_collinear_lines(coords_list)
        if merged:
            exterior_walls.append({
                'primitive_line_ids': [l['id'] for l in north_lines],
                'coords': merged,
                'length': math.sqrt((merged[2] - merged[0])**2 + (merged[3] - merged[1])**2),
                'wall_type': 'exterior',
                'side': 'north'
            })
            used_line_ids.update([l['id'] for l in north_lines])

    # South wall (bottom, Y ~ south_y)
    south_lines = [l for l in lines if abs(max(l['coords'][1], l['coords'][3]) - south_y) < WALL_ALIGNMENT_TOLERANCE and
                   abs(l['angle'] - 0) < 20 or abs(l['angle'] - 180) < 20]
    if south_lines:
        coords_list = [l['coords'] for l in south_lines]
        merged = merge_collinear_lines(coords_list)
        if merged:
            exterior_walls.append({
                'primitive_line_ids': [l['id'] for l in south_lines],
                'coords': merged,
                'length': math.sqrt((merged[2] - merged[0])**2 + (merged[3] - merged[1])**2),
                'wall_type': 'exterior',
                'side': 'south'
            })
            used_line_ids.update([l['id'] for l in south_lines])

    # East wall (right, X ~ east_x)
    east_lines = [l for l in lines if abs(min(l['coords'][0], l['coords'][2]) - east_x) < WALL_ALIGNMENT_TOLERANCE and
                  abs(l['angle'] - 90) < 20]
    if east_lines:
        coords_list = [l['coords'] for l in east_lines]
        merged = merge_collinear_lines(coords_list)
        if merged:
            exterior_walls.append({
                'primitive_line_ids': [l['id'] for l in east_lines],
                'coords': merged,
                'length': math.sqrt((merged[2] - merged[0])**2 + (merged[3] - merged[1])**2),
                'wall_type': 'exterior',
                'side': 'east'
            })
            used_line_ids.update([l['id'] for l in east_lines])

    # West wall (left, X ~ west_x)
    west_lines = [l for l in lines if abs(max(l['coords'][0], l['coords'][2]) - west_x) < WALL_ALIGNMENT_TOLERANCE and
                  abs(l['angle'] - 90) < 20]
    if west_lines:
        coords_list = [l['coords'] for l in west_lines]
        merged = merge_collinear_lines(coords_list)
        if merged:
            exterior_walls.append({
                'primitive_line_ids': [l['id'] for l in west_lines],
                'coords': merged,
                'length': math.sqrt((merged[2] - merged[0])**2 + (merged[3] - merged[1])**2),
                'wall_type': 'exterior',
                'side': 'west'
            })
            used_line_ids.update([l['id'] for l in west_lines])

    print(f"   ✅ Extracted {len(exterior_walls)} exterior walls ({', '.join([w['side'] for w in exterior_walls])})")
    print(f"   Used {len(used_line_ids)} line primitives")

    return exterior_walls, list(used_line_ids)


def step1b_cluster_interior_walls(cursor: sqlite3.Cursor, excluded_line_ids: List[int]) -> List[List[int]]:
    """
    Step 1B: Cluster interior walls from remaining lines

    Returns: List of clusters (each cluster is list of line IDs)
    """
    print(f"\n🏠 STEP 1B: Clustering interior walls (DBSCAN)")
    print(f"   Parameters: eps={PROXIMITY_EPS}m, min_samples={MIN_SAMPLES}, min_linewidth={MIN_LINE_WIDTH}pt")

    # Get calibration
    cursor.execute("SELECT key, value FROM context_calibration WHERE key IN ('scale_m_per_pt', 'offset_x', 'offset_y', 'building_width_m', 'building_length_m')")
    calibration = {row[0]: row[1] for row in cursor.fetchall()}

    scale_m_per_pt = calibration['scale_m_per_pt']
    offset_x = calibration.get('offset_x', 0.0)
    offset_y = calibration.get('offset_y', 0.0)

    # Get building footprint for boundary constraint (8m×8m building walls)
    # Note: DISCHARGE perimeter (11.78m×10.05m) is outer property, not building boundary
    building_width = calibration.get('building_width_m', 8.0)
    building_length = calibration.get('building_length_m', 8.0)

    boundary_x_min, boundary_x_max = 0.0, building_width
    boundary_y_min, boundary_y_max = 0.0, building_length

    print(f"   Boundary constraint (building footprint): X=[{boundary_x_min:.2f}, {boundary_x_max:.2f}], Y=[{boundary_y_min:.2f}, {boundary_y_max:.2f}]")

    # Get text annotation positions to exclude nearby lines (dimension lines filter)
    cursor.execute("SELECT x, y FROM primitives_text WHERE page = 1")
    text_positions = [(x, y) for x, y in cursor.fetchall()]
    print(f"   Text annotations: {len(text_positions)} markers (will exclude lines within 0.3m)")

    # Get remaining structural lines
    placeholders = ','.join('?' * len(excluded_line_ids)) if excluded_line_ids else '?'
    params = list(excluded_line_ids) if excluded_line_ids else [-1]
    params.insert(0, MIN_LINE_WIDTH)

    cursor.execute(f"""
        SELECT id, x0, y0, x1, y1
        FROM primitives_lines
        WHERE length > 10
          AND linewidth >= ?
          AND page = 1
          AND id NOT IN ({placeholders})
    """, params)

    lines_raw = cursor.fetchall()
    print(f"   Loaded {len(lines_raw)} remaining structural lines")

    if len(lines_raw) == 0:
        return []

    # Convert to meters and apply filters
    lines = []
    filtered_count = {'boundary': 0, 'text_proximity': 0}

    for line_id, x0, y0, x1, y1 in lines_raw:
        x0_m = (x0 - offset_x) * scale_m_per_pt
        y0_m = (y0 - offset_y) * scale_m_per_pt
        x1_m = (x1 - offset_x) * scale_m_per_pt
        y1_m = (y1 - offset_y) * scale_m_per_pt

        # Filter 1: Boundary constraint (exclude lines outside DISCHARGE perimeter)
        if not (boundary_x_min <= x0_m <= boundary_x_max and boundary_x_min <= x1_m <= boundary_x_max and
                boundary_y_min <= y0_m <= boundary_y_max and boundary_y_min <= y1_m <= boundary_y_max):
            filtered_count['boundary'] += 1
            continue

        # Filter 2: Exclude lines near text annotations (dimension lines)
        line_midpoint_x = (x0_m + x1_m) / 2
        line_midpoint_y = (y0_m + y1_m) / 2
        too_close_to_text = False

        for text_x, text_y in text_positions:
            text_x_m = (text_x - offset_x) * scale_m_per_pt
            text_y_m = (text_y - offset_y) * scale_m_per_pt
            dist = math.sqrt((text_x_m - line_midpoint_x)**2 + (text_y_m - line_midpoint_y)**2)
            if dist < WALL_ALIGNMENT_TOLERANCE:  # 0.3m threshold
                too_close_to_text = True
                break

        if too_close_to_text:
            filtered_count['text_proximity'] += 1
            continue

        lines.append({
            'id': line_id,
            'coords': (x0_m, y0_m, x1_m, y1_m),
            'angle': get_line_angle(x0_m, y0_m, x1_m, y1_m)
        })

    print(f"   Filtered out: {filtered_count['boundary']} outside boundary, {filtered_count['text_proximity']} near text")
    print(f"   Remaining for clustering: {len(lines)} lines")

    if len(lines) == 0:
        return []

    # Group by angle
    angle_groups = {}
    for line in lines:
        bucket = int(line['angle'] / 15) * 15
        if bucket not in angle_groups:
            angle_groups[bucket] = []
        angle_groups[bucket].append(line)

    print(f"   Grouped into {len(angle_groups)} angle buckets")

    # Cluster within angle groups using perpendicular distance
    all_clusters = []

    for angle_bucket, group_lines in angle_groups.items():
        if len(group_lines) < MIN_SAMPLES:
            continue

        # Use midpoint for clustering but check perpendicular distance in collinear merging
        # PROXIMITY_EPS applies to perpendicular distance during collinear check (line 159)
        # For DBSCAN, use 2D midpoint clustering to ensure contiguous walls
        midpoints = []
        for line in group_lines:
            x0, y0, x1, y1 = line['coords']
            mid_x = (x0 + x1) / 2
            mid_y = (y0 + y1) / 2
            midpoints.append((mid_x, mid_y))

        midpoints_array = np.array(midpoints)

        # DBSCAN clustering on midpoints (creates contiguous wall segments)
        labels = manual_dbscan(midpoints_array, eps=PROXIMITY_EPS, min_samples=MIN_SAMPLES)

        # Group by cluster
        unique_labels = set(labels)
        for label in unique_labels:
            if label == -1:
                continue

            cluster_line_ids = [group_lines[i]['id'] for i in range(len(labels)) if labels[i] == label]
            all_clusters.append(cluster_line_ids)

    print(f"   ✅ Found {len(all_clusters)} interior wall clusters")
    return all_clusters


def step2_merge_and_persist(cursor: sqlite3.Cursor, exterior_walls: List[Dict], interior_clusters: List[List[int]]):
    """
    Step 2: Merge interior wall clusters and persist all walls
    """
    print(f"\n💾 STEP 2: Merging interior walls and persisting")

    # Get calibration
    cursor.execute("SELECT key, value FROM context_calibration WHERE key IN ('scale_m_per_pt', 'offset_x', 'offset_y', 'building_width_m', 'building_length_m')")
    calibration = {row[0]: row[1] for row in cursor.fetchall()}

    scale_m_per_pt = calibration['scale_m_per_pt']
    offset_x = calibration.get('offset_x', 0.0)
    offset_y = calibration.get('offset_y', 0.0)

    interior_walls = []

    for cluster_ids in interior_clusters:
        placeholders = ','.join('?' * len(cluster_ids))
        cursor.execute(f"""
            SELECT id, x0, y0, x1, y1
            FROM primitives_lines
            WHERE id IN ({placeholders})
        """, cluster_ids)

        lines_data = cursor.fetchall()

        # Convert to meters
        lines_coords = {}
        for line_id, x0, y0, x1, y1 in lines_data:
            x0_m = (x0 - offset_x) * scale_m_per_pt
            y0_m = (y0 - offset_y) * scale_m_per_pt
            x1_m = (x1 - offset_x) * scale_m_per_pt
            y1_m = (y1 - offset_y) * scale_m_per_pt
            lines_coords[line_id] = (x0_m, y0_m, x1_m, y1_m)

        # Merge collinear adjacent lines
        merged_groups = []
        used = set()

        for line_id in cluster_ids:
            if line_id in used:
                continue

            group = [line_id]
            used.add(line_id)

            # Find adjacent collinear lines
            changed = True
            while changed:
                changed = False
                for other_id in cluster_ids:
                    if other_id in used:
                        continue

                    for group_line_id in group:
                        if lines_collinear(lines_coords[group_line_id], lines_coords[other_id]) and \
                           lines_adjacent(lines_coords[group_line_id], lines_coords[other_id]):
                            group.append(other_id)
                            used.add(other_id)
                            changed = True
                            break

            merged_groups.append(group)

        # Create wall segments
        for group in merged_groups:
            group_lines = [lines_coords[lid] for lid in group]
            merged_line = merge_collinear_lines(group_lines)

            if merged_line:
                x0, y0, x1, y1 = merged_line
                length = math.sqrt((x1 - x0)**2 + (y1 - y0)**2)

                if length >= MIN_WALL_LENGTH:
                    interior_walls.append({
                        'primitive_line_ids': group,
                        'coords': merged_line,
                        'length': length,
                        'wall_type': 'interior'
                    })

    print(f"   Created {len(interior_walls)} interior walls (min_length={MIN_WALL_LENGTH}m)")

    # Create table (drop old version if exists)
    cursor.execute("DROP TABLE IF EXISTS semantic_walls")
    cursor.execute("""
        CREATE TABLE semantic_walls (
            wall_id INTEGER PRIMARY KEY AUTOINCREMENT,
            primitive_line_ids TEXT NOT NULL,
            bbox_x0 REAL NOT NULL,
            bbox_y0 REAL NOT NULL,
            bbox_x1 REAL NOT NULL,
            bbox_y1 REAL NOT NULL,
            orientation TEXT NOT NULL,
            length REAL NOT NULL,
            wall_type TEXT NOT NULL
        )
    """)

    # Insert all walls
    all_walls = exterior_walls + interior_walls

    for wall in all_walls:
        x0, y0, x1, y1 = wall['coords']
        angle = get_line_angle(x0, y0, x1, y1)

        if abs(angle - 0) < 45 or abs(angle - 180) < 45:
            orientation = 'H'
        else:
            orientation = 'V'

        primitive_ids_json = json.dumps(wall['primitive_line_ids'])

        cursor.execute("""
            INSERT INTO semantic_walls
            (primitive_line_ids, bbox_x0, bbox_y0, bbox_x1, bbox_y1, orientation, length, wall_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (primitive_ids_json, x0, y0, x1, y1, orientation, wall['length'], wall['wall_type']))

    print(f"   ✅ Persisted {len(all_walls)} total walls ({len(exterior_walls)} exterior + {len(interior_walls)} interior)")


def main():
    """Main execution - Stage 2.1 pipeline"""
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "output_artifacts" / "TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"

    print("=" * 80)
    print("STAGE 2.1: STRUCTURAL SEMANTIC LAYER - WALL DETECTION")
    print("=" * 80)
    print(f"Database: {db_path.name}")
    print(f"Algorithm: DISCHARGE perimeter + DBSCAN (DETERMINISTIC - Contractor Workflow)")
    print()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Execute pipeline
        exterior_walls, used_line_ids = step1a_extract_exterior_walls(cursor)
        interior_clusters = step1b_cluster_interior_walls(cursor, used_line_ids)
        step2_merge_and_persist(cursor, exterior_walls, interior_clusters)

        conn.commit()

        # Verification summary
        cursor.execute("SELECT COUNT(*), wall_type, AVG(length) FROM semantic_walls GROUP BY wall_type")
        summary = cursor.fetchall()

        print("\n" + "=" * 80)
        print("✅ STAGE 2.1 COMPLETE - Semantic Walls Created")
        print("=" * 80)
        for count, wall_type, avg_len in summary:
            print(f"   {wall_type.capitalize()}: {count} walls (avg length: {avg_len:.2f}m)")

        total_walls = sum(s[0] for s in summary)
        if 15 <= total_walls <= 25:
            print(f"\n✅ Wall count ({total_walls}) within expected range (15-25 for typical house)")
        else:
            print(f"\n⚠️  Wall count ({total_walls}) outside expected range (15-25)")
            print(f"   If incorrect → edit constants in {__file__} and re-run")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
