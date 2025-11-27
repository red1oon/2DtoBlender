#!/usr/bin/env python3
"""
Rule 0 compliant: Detect interior partition walls to derive room bounds.
Method: Find all walls, identify enclosed regions, calculate bounding boxes.
"""

import pdf2image
import numpy as np
import cv2
import json
from collections import defaultdict


# Load calibration
def load_calibration():
    with open('output_artifacts/grid_calibration.json', 'r') as f:
        calib = json.load(f)
    return tuple(calib['origin_px']), calib['pixels_per_meter']


# GridTruth
GRID_TRUTH = {
    "horizontal": {"A": 0.0, "B": 1.3, "C": 4.4, "D": 8.1, "E": 11.2},
    "vertical": {"1": 0.0, "2": 2.3, "3": 5.4, "4": 7.0, "5": 8.5}
}


def detect_all_walls(gray, min_length=20):
    """Detect ALL walls including interior partitions."""
    print("\nDetecting all walls...")

    # Use aggressive edge detection for thin partition walls
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 20, 60)  # Lower thresholds for thin lines

    # Morphological closing to connect broken lines
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Detect lines
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=50,  # Lower threshold
        minLineLength=min_length,
        maxLineGap=10
    )

    if lines is None:
        return [], []

    h_walls = []
    v_walls = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        angle = np.abs(np.arctan2(dy, dx) * 180 / np.pi)

        if angle < 15 or angle > 165:  # Horizontal (±15°)
            h_walls.append({
                'x1': min(x1, x2), 'y': (y1 + y2) / 2,
                'x2': max(x1, x2), 'length': length
            })
        elif 75 < angle < 105:  # Vertical (±15°)
            v_walls.append({
                'y1': min(y1, y2), 'x': (x1 + x2) / 2,
                'y2': max(y1, y2), 'length': length
            })

    print(f"  Detected {len(h_walls)} horizontal + {len(v_walls)} vertical wall segments")
    return h_walls, v_walls


def extract_floor_plan_region(gray, origin_px, ppm):
    """Extract just the floor plan area (inside grid)."""
    # Floor plan bounds (grid A-E, 1-5)
    # Grid A starts at origin, grid E is 11.2m away
    x_min = int(origin_px[0] - 0.5 * ppm)  # Start before A (with margin)
    y_min = int(origin_px[1] - 0.5 * ppm)  # Start before 1 (with margin)
    x_max = int(origin_px[0] + (11.2 + 0.5) * ppm)  # End after E
    y_max = int(origin_px[1] + (8.5 + 0.5) * ppm)   # End after 5

    # Bounds check
    x_min = max(0, x_min)
    y_min = max(0, y_min)
    x_max = min(gray.shape[1], x_max)
    y_max = min(gray.shape[0], y_max)

    roi = gray[y_min:y_max, x_min:x_max]

    print(f"\nFloor plan ROI: {roi.shape[1]}x{roi.shape[0]}px")
    print(f"  Position: ({x_min}, {y_min}) to ({x_max}, {y_max})")
    print(f"  Expected size: ~{11.2 * ppm:.0f}x{8.5 * ppm:.0f}px")

    return roi, (x_min, y_min)


def find_rectangular_rooms(h_walls, v_walls, origin_px, offset, ppm):
    """Find rectangular room regions from wall intersections."""
    print("\nFinding rectangular rooms...")

    # Cluster walls by position
    def cluster_positions(walls, key, tolerance=10):
        if not walls:
            return []
        positions = sorted(set(int(w[key]) for w in walls))
        clusters = []
        current = [positions[0]]
        for pos in positions[1:]:
            if pos - current[-1] < tolerance:
                current.append(pos)
            else:
                clusters.append(int(np.mean(current)))
                current = [pos]
        clusters.append(int(np.mean(current)))
        return clusters

    h_positions = cluster_positions(h_walls, 'y', tolerance=5)
    v_positions = cluster_positions(v_walls, 'x', tolerance=5)

    print(f"  Found {len(h_positions)} horizontal wall lines")
    print(f"  Found {len(v_positions)} vertical wall lines")

    # Find rectangular regions bounded by walls
    rooms = []
    for i in range(len(v_positions) - 1):
        for j in range(len(h_positions) - 1):
            x1_px = v_positions[i]
            x2_px = v_positions[i+1]
            y1_px = h_positions[j]
            y2_px = h_positions[j+1]

            # Convert to world coordinates
            x1_m = (x1_px + offset[0] - origin_px[0]) / ppm
            x2_m = (x2_px + offset[0] - origin_px[0]) / ppm
            y1_m = (y1_px + offset[1] - origin_px[1]) / ppm
            y2_m = (y2_px + offset[1] - origin_px[1]) / ppm

            # Calculate area
            width = abs(x2_m - x1_m)
            height = abs(y2_m - y1_m)
            area = width * height

            # Filter out tiny regions (< 1m²) and huge regions (> 40m²)
            if 1.0 < area < 40.0:
                rooms.append({
                    'x': (min(x1_m, x2_m), max(x1_m, x2_m)),
                    'y': (min(y1_m, y2_m), max(y1_m, y2_m)),
                    'width': width,
                    'height': height,
                    'area': area,
                    'px_bounds': (x1_px, y1_px, x2_px, y2_px)
                })

    print(f"  Found {len(rooms)} potential room regions")
    return rooms


def visualize_detected_rooms(img, rooms, origin_px, ppm, output_path):
    """Visualize detected room regions."""
    vis = img.copy()
    if len(vis.shape) == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    # Draw grid
    for label, pos_m in GRID_TRUTH['horizontal'].items():
        x = int(origin_px[0] + pos_m * ppm)
        cv2.line(vis, (x, 0), (x, vis.shape[0]), (200, 200, 200), 1)
        cv2.putText(vis, label, (x+5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    for label, pos_m in GRID_TRUTH['vertical'].items():
        y = int(origin_px[1] + pos_m * ppm)
        cv2.line(vis, (0, y), (vis.shape[1], y), (200, 200, 200), 1)
        cv2.putText(vis, label, (10, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Draw detected rooms
    colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
              (255, 0, 255), (0, 255, 255), (128, 255, 0), (255, 128, 0)]

    for i, room in enumerate(rooms):
        x1 = int(origin_px[0] + room['x'][0] * ppm)
        x2 = int(origin_px[0] + room['x'][1] * ppm)
        y1 = int(origin_px[1] + room['y'][0] * ppm)
        y2 = int(origin_px[1] + room['y'][1] * ppm)

        color = colors[i % len(colors)]
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)

        # Label with area
        label = f"{room['area']:.1f}m²"
        cv2.putText(vis, label, (x1+5, y1+20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    cv2.imwrite(output_path, vis)
    print(f"\n✓ Saved: {output_path}")


def main():
    pdf_path = "TB-LKTN HOUSE.pdf"

    print("=" * 80)
    print("DETECT INTERIOR PARTITIONS (Rule 0 Compliant)")
    print("=" * 80)

    # Load calibration
    origin_px, ppm = load_calibration()
    print(f"\nCalibration:")
    print(f"  Origin: {origin_px}")
    print(f"  Pixels/meter: {ppm:.2f}")

    # Extract page
    print("\nExtracting page 1...")
    pages = pdf2image.convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
    img = np.array(pages[0])
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img

    # Extract floor plan region
    roi, offset = extract_floor_plan_region(gray, origin_px, ppm)

    # Detect walls in ROI
    h_walls, v_walls = detect_all_walls(roi, min_length=20)

    # Find rectangular rooms
    rooms = find_rectangular_rooms(h_walls, v_walls, origin_px, offset, ppm)

    # Sort by area
    rooms_sorted = sorted(rooms, key=lambda r: r['area'], reverse=True)

    print("\n" + "=" * 80)
    print("DETECTED ROOM REGIONS")
    print("=" * 80)
    print(f"{'#':<4} {'Width(m)':<10} {'Height(m)':<11} {'Area(m²)':<10} {'X bounds':<20} {'Y bounds'}")
    print("-" * 80)

    for i, room in enumerate(rooms_sorted):
        print(f"{i+1:<4} {room['width']:<10.2f} {room['height']:<11.2f} {room['area']:<10.2f} "
              f"{str(room['x']):<20} {str(room['y'])}")

    # Visualize
    visualize_detected_rooms(img, rooms_sorted, origin_px, ppm,
                            "output_artifacts/detected_rooms.png")

    # Save results
    output = {
        'rooms': rooms_sorted,
        'calibration': {'origin_px': origin_px, 'pixels_per_meter': ppm},
        'metadata': {
            'method': 'interior_partition_detection',
            'rule_0_compliant': True,
            'total_regions': len(rooms_sorted)
        }
    }

    with open('output_artifacts/detected_rooms.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Saved: output_artifacts/detected_rooms.json")
    print("\n" + "=" * 80)
    print("✓ Rule 0 compliant - Derived from detected wall geometry")
    print("=" * 80)


if __name__ == "__main__":
    main()
