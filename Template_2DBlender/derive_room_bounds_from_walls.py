#!/usr/bin/env python3
"""
Derive ROOM_BOUNDS by detecting walls between grid lines.
Uses calibrated grid origin + detected wall segments.
"""

import pdf2image
import numpy as np
import cv2
import json
from collections import defaultdict


# GridTruth (meters)
GRID_TRUTH = {
    "horizontal": {"A": 0.0, "B": 1.3, "C": 4.4, "D": 8.1, "E": 11.2},
    "vertical": {"1": 0.0, "2": 2.3, "3": 5.4, "4": 7.0, "5": 8.5}
}


def load_calibration():
    """Load grid calibration from file."""
    with open('output_artifacts/grid_calibration.json', 'r') as f:
        calib = json.load(f)
    return tuple(calib['origin_px']), calib['pixels_per_meter']


def detect_walls(gray, page_name="Page"):
    """Detect wall lines (thick horizontal/vertical segments)."""
    print(f"\n{page_name}: Detecting walls...")

    # Enhance walls (thick black lines)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 30, 100)

    # Detect lines
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=80,
        minLineLength=30,
        maxLineGap=5
    )

    if lines is None:
        print(f"  No lines detected")
        return [], []

    horizontal_walls = []
    vertical_walls = []

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Calculate angle and length
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        angle = np.abs(np.arctan2(dy, dx) * 180 / np.pi)

        # Classify
        if angle < 10 or angle > 170:  # Horizontal
            horizontal_walls.append({
                'x1': min(x1, x2), 'y1': y1,
                'x2': max(x1, x2), 'y2': y2,
                'y_avg': (y1 + y2) / 2,
                'length': length
            })
        elif 80 < angle < 100:  # Vertical
            vertical_walls.append({
                'x1': x1, 'y1': min(y1, y2),
                'x2': x2, 'y2': max(y1, y2),
                'x_avg': (x1 + x2) / 2,
                'length': length
            })

    print(f"  Detected {len(horizontal_walls)} horizontal + {len(vertical_walls)} vertical walls")
    return horizontal_walls, vertical_walls


def cluster_walls(walls, axis_key, tolerance=10):
    """Group walls along same axis."""
    if not walls:
        return []

    sorted_walls = sorted(walls, key=lambda w: w[axis_key])
    clusters = []
    current_cluster = [sorted_walls[0]]

    for wall in sorted_walls[1:]:
        if abs(wall[axis_key] - current_cluster[-1][axis_key]) < tolerance:
            current_cluster.append(wall)
        else:
            clusters.append(current_cluster)
            current_cluster = [wall]

    clusters.append(current_cluster)

    # Merge each cluster into single wall
    merged = []
    for cluster in clusters:
        avg_pos = np.mean([w[axis_key] for w in cluster])
        total_length = sum(w['length'] for w in cluster)

        if axis_key == 'y_avg':  # Horizontal wall
            x_min = min(w['x1'] for w in cluster)
            x_max = max(w['x2'] for w in cluster)
            merged.append({
                'y': avg_pos,
                'x1': x_min,
                'x2': x_max,
                'length': total_length,
                'segments': len(cluster)
            })
        else:  # Vertical wall
            y_min = min(w['y1'] for w in cluster)
            y_max = max(w['y2'] for w in cluster)
            merged.append({
                'x': avg_pos,
                'y1': y_min,
                'y2': y_max,
                'length': total_length,
                'segments': len(cluster)
            })

    return merged


def match_walls_to_grid_cells(h_walls, v_walls, origin_px, ppm):
    """Match walls to grid cell boundaries."""
    print("\nMatching walls to grid cells...")

    # Calculate grid positions in pixels
    grid_x_px = {label: origin_px[0] + pos * ppm for label, pos in GRID_TRUTH['horizontal'].items()}
    grid_y_px = {label: origin_px[1] + pos * ppm for label, pos in GRID_TRUTH['vertical'].items()}

    # Grid cell matrix (tracks which cells are enclosed)
    grid_letters = sorted(GRID_TRUTH['horizontal'].keys())
    grid_numbers = sorted(GRID_TRUTH['vertical'].keys())

    # Find walls on grid boundaries
    grid_h_walls = defaultdict(list)  # grid_number -> walls at that Y
    grid_v_walls = defaultdict(list)  # grid_letter -> walls at that X

    # Match horizontal walls
    for wall in h_walls:
        for label, y_px in grid_y_px.items():
            if abs(wall['y'] - y_px) < 30:  # 30px tolerance
                grid_h_walls[label].append(wall)
                break

    # Match vertical walls
    for wall in v_walls:
        for label, x_px in grid_x_px.items():
            if abs(wall['x'] - x_px) < 30:
                grid_v_walls[label].append(wall)
                break

    print(f"  Matched horizontal walls: {dict((k, len(v)) for k, v in grid_h_walls.items())}")
    print(f"  Matched vertical walls: {dict((k, len(v)) for k, v in grid_v_walls.items())}")

    # Analyze grid cell boundaries
    print("\nGrid cell analysis:")
    for i in range(len(grid_letters) - 1):
        for j in range(len(grid_numbers) - 1):
            letter1, letter2 = grid_letters[i], grid_letters[i+1]
            number1, number2 = grid_numbers[j], grid_numbers[j+1]

            cell_id = f"{letter1}{letter2}{number1}{number2}"

            # Check if cell has walls on boundaries
            has_north = number2 in grid_h_walls
            has_south = number1 in grid_h_walls
            has_east = letter2 in grid_v_walls
            has_west = letter1 in grid_v_walls

            enclosure = sum([has_north, has_south, has_east, has_west])

            if enclosure >= 2:  # At least 2 walls
                print(f"  {cell_id}: {enclosure}/4 walls (N={has_north}, S={has_south}, E={has_east}, W={has_west})")

    return grid_h_walls, grid_v_walls


def visualize_walls_and_grid(img, h_walls, v_walls, origin_px, ppm, output_path):
    """Visualize detected walls and grid overlay."""
    vis = img.copy()
    if len(vis.shape) == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    # Draw grid lines (thin blue)
    for label, pos_m in GRID_TRUTH['horizontal'].items():
        x = int(origin_px[0] + pos_m * ppm)
        cv2.line(vis, (x, 0), (x, vis.shape[0]), (255, 0, 0), 1)
        cv2.putText(vis, label, (x+5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    for label, pos_m in GRID_TRUTH['vertical'].items():
        y = int(origin_px[1] + pos_m * ppm)
        cv2.line(vis, (0, y), (vis.shape[1], y), (255, 0, 0), 1)
        cv2.putText(vis, label, (10, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # Draw detected walls (thick green)
    for wall in h_walls:
        cv2.line(vis, (int(wall['x1']), int(wall['y'])),
                      (int(wall['x2']), int(wall['y'])), (0, 255, 0), 2)

    for wall in v_walls:
        cv2.line(vis, (int(wall['x']), int(wall['y1'])),
                      (int(wall['x']), int(wall['y2'])), (0, 255, 0), 2)

    # Mark origin
    cv2.circle(vis, origin_px, 10, (0, 0, 255), 2)
    cv2.putText(vis, "Origin (A1)", (origin_px[0]+15, origin_px[1]+5),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    cv2.imwrite(output_path, vis)
    print(f"\n✓ Saved visualization: {output_path}")


def main():
    pdf_path = "TB-LKTN HOUSE.pdf"

    print("=" * 80)
    print("DERIVE ROOM_BOUNDS FROM WALL DETECTION")
    print("=" * 80)

    # Load calibration
    origin_px, ppm = load_calibration()
    print(f"\nUsing calibration:")
    print(f"  Origin: {origin_px}")
    print(f"  Pixels/meter: {ppm:.2f}")

    # Process Page 1 (ARCH)
    print("\n--- PAGE 1 (ARCH) ---")
    pages = pdf2image.convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
    img_p1 = np.array(pages[0])
    gray_p1 = cv2.cvtColor(img_p1, cv2.COLOR_RGB2GRAY) if len(img_p1.shape) == 3 else img_p1

    h_walls_p1, v_walls_p1 = detect_walls(gray_p1, "Page 1")

    print("\nClustering walls...")
    h_clustered_p1 = cluster_walls(h_walls_p1, 'y_avg', tolerance=5)
    v_clustered_p1 = cluster_walls(v_walls_p1, 'x_avg', tolerance=5)
    print(f"  Clustered to {len(h_clustered_p1)} horizontal + {len(v_clustered_p1)} vertical walls")

    # Match to grid
    grid_h, grid_v = match_walls_to_grid_cells(h_clustered_p1, v_clustered_p1, origin_px, ppm)

    # Visualize
    visualize_walls_and_grid(img_p1, h_clustered_p1, v_clustered_p1, origin_px, ppm,
                            "output_artifacts/page1_walls_and_grid.png")

    # Process Page 2 (ELEC)
    print("\n--- PAGE 2 (ELEC) ---")
    pages = pdf2image.convert_from_path(pdf_path, dpi=300, first_page=2, last_page=2)
    img_p2 = np.array(pages[0])
    gray_p2 = cv2.cvtColor(img_p2, cv2.COLOR_RGB2GRAY) if len(img_p2.shape) == 3 else img_p2

    h_walls_p2, v_walls_p2 = detect_walls(gray_p2, "Page 2")

    print("\nClustering walls...")
    h_clustered_p2 = cluster_walls(h_walls_p2, 'y_avg', tolerance=5)
    v_clustered_p2 = cluster_walls(v_walls_p2, 'x_avg', tolerance=5)
    print(f"  Clustered to {len(h_clustered_p2)} horizontal + {len(v_clustered_p2)} vertical walls")

    # Match to grid
    grid_h_p2, grid_v_p2 = match_walls_to_grid_cells(h_clustered_p2, v_clustered_p2, origin_px, ppm)

    # Visualize
    visualize_walls_and_grid(img_p2, h_clustered_p2, v_clustered_p2, origin_px, ppm,
                            "output_artifacts/page2_walls_and_grid.png")

    print("\n" + "=" * 80)
    print("✓ Wall detection complete - check visualizations")
    print("=" * 80)


if __name__ == "__main__":
    main()
