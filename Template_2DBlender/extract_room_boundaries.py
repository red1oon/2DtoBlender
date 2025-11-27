#!/usr/bin/env python3
"""
Extract room boundaries from Page 2 (ELEC) blocky outlines.
Use grid lines + wall detection to derive ROOM_BOUNDS.
"""

import pdf2image
import numpy as np
import cv2
import json
from pathlib import Path


# GridTruth coordinates (meters)
GRID_TRUTH = {
    "horizontal": {"A": 0.0, "B": 1.3, "C": 4.4, "D": 8.1, "E": 11.2},
    "vertical": {"1": 0.0, "2": 2.3, "3": 5.4, "4": 7.0, "5": 8.5}
}


def extract_page_image(pdf_path: str, page: int, dpi: int = 300):
    """Extract page as image."""
    print(f"Converting page {page} at {dpi} DPI...")
    pages = pdf2image.convert_from_path(pdf_path, dpi=dpi, first_page=page, last_page=page)
    img = np.array(pages[0])

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img

    return img, gray


def detect_lines(gray, min_length=100):
    """Detect horizontal and vertical lines using HoughLinesP."""
    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detect lines
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi/180,
        threshold=100,
        minLineLength=min_length,
        maxLineGap=10
    )

    if lines is None:
        return [], []

    horizontal_lines = []
    vertical_lines = []

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Calculate angle
        dx = x2 - x1
        dy = y2 - y1
        angle = np.abs(np.arctan2(dy, dx) * 180 / np.pi)

        # Classify as horizontal or vertical (within 10 degrees)
        if angle < 10 or angle > 170:
            horizontal_lines.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'y': (y1 + y2) / 2})
        elif 80 < angle < 100:
            vertical_lines.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'x': (x1 + x2) / 2})

    print(f"  Detected {len(horizontal_lines)} horizontal lines")
    print(f"  Detected {len(vertical_lines)} vertical lines")

    return horizontal_lines, vertical_lines


def cluster_lines(lines, axis_key, tolerance=10):
    """Cluster parallel lines that are close together."""
    if not lines:
        return []

    # Sort by position along axis
    sorted_lines = sorted(lines, key=lambda l: l[axis_key])

    clusters = []
    current_cluster = [sorted_lines[0]]

    for line in sorted_lines[1:]:
        if abs(line[axis_key] - current_cluster[-1][axis_key]) < tolerance:
            current_cluster.append(line)
        else:
            clusters.append(current_cluster)
            current_cluster = [line]

    clusters.append(current_cluster)

    # Average each cluster
    averaged = []
    for cluster in clusters:
        avg_pos = np.mean([line[axis_key] for line in cluster])
        # Keep first line as template, update position
        line = cluster[0].copy()
        line[axis_key] = avg_pos
        if axis_key == 'y':
            line['y1'] = line['y2'] = avg_pos
        else:
            line['x1'] = line['x2'] = avg_pos
        averaged.append(line)

    return averaged


def match_lines_to_grid(lines, axis_key, grid_coords_m, pixels_per_meter, origin_px):
    """Match detected lines to grid coordinates."""
    matched = {}

    for grid_label, grid_pos_m in grid_coords_m.items():
        # Convert grid position to pixels
        if axis_key == 'x':
            expected_px = origin_px[0] + grid_pos_m * pixels_per_meter
        else:  # y
            expected_px = origin_px[1] - grid_pos_m * pixels_per_meter  # Invert Y

        # Find closest line
        closest_line = None
        min_dist = float('inf')

        for line in lines:
            dist = abs(line[axis_key] - expected_px)
            if dist < min_dist:
                min_dist = dist
                closest_line = line

        # Match if within 20px tolerance
        if closest_line and min_dist < 20:
            matched[grid_label] = {
                'grid_pos_m': grid_pos_m,
                'detected_px': closest_line[axis_key],
                'expected_px': expected_px,
                'error_px': min_dist,
                'line': closest_line
            }
            print(f"    {grid_label}: expected={expected_px:.0f}px, detected={closest_line[axis_key]:.0f}px, error={min_dist:.1f}px")

    return matched


def visualize_detection(img, h_lines, v_lines, matched_h, matched_v, output_path):
    """Visualize detected lines and grid matches."""
    vis = img.copy()
    if len(vis.shape) == 2:
        vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

    # Draw all detected lines (gray)
    for line in h_lines:
        cv2.line(vis, (int(line['x1']), int(line['y1'])),
                      (int(line['x2']), int(line['y2'])), (128, 128, 128), 1)

    for line in v_lines:
        cv2.line(vis, (int(line['x1']), int(line['y1'])),
                      (int(line['x2']), int(line['y2'])), (128, 128, 128), 1)

    # Draw matched grid lines (green for horizontal, blue for vertical)
    for label, match in matched_h.items():
        line = match['line']
        cv2.line(vis, (int(line['x1']), int(line['y1'])),
                      (int(line['x2']), int(line['y2'])), (0, 255, 0), 2)
        cv2.putText(vis, label, (10, int(line['y'])),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    for label, match in matched_v.items():
        line = match['line']
        cv2.line(vis, (int(line['x1']), int(line['y1'])),
                      (int(line['x2']), int(line['y2'])), (255, 0, 0), 2)
        cv2.putText(vis, label, (int(line['x']), 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # Save
    cv2.imwrite(output_path, vis)
    print(f"  Saved visualization: {output_path}")


def main():
    pdf_path = "TB-LKTN HOUSE.pdf"

    print("=" * 80)
    print("EXTRACT ROOM BOUNDARIES FROM BLOCKY OUTLINES")
    print("=" * 80)

    # Try Page 2 (ELEC - user said it's cleaner)
    print("\n--- PAGE 2 (ELEC) ---")
    img_p2, gray_p2 = extract_page_image(pdf_path, page=2, dpi=300)

    print("\nDetecting lines...")
    h_lines_p2, v_lines_p2 = detect_lines(gray_p2, min_length=50)

    print("\nClustering parallel lines...")
    h_clustered = cluster_lines(h_lines_p2, 'y', tolerance=5)
    v_clustered = cluster_lines(v_lines_p2, 'x', tolerance=5)
    print(f"  Clustered to {len(h_clustered)} horizontal lines")
    print(f"  Clustered to {len(v_clustered)} vertical lines")

    # Calibration (from coordinate_generator.py)
    PIXELS_PER_METER = 118.11
    ORIGIN_PX = (178, 322)  # Estimated from previous calibration

    print("\nMatching to grid coordinates...")
    print("  Horizontal grid (1-5):")
    matched_h = match_lines_to_grid(
        h_clustered, 'y',
        GRID_TRUTH['vertical'],
        PIXELS_PER_METER,
        ORIGIN_PX
    )

    print("  Vertical grid (A-E):")
    matched_v = match_lines_to_grid(
        v_clustered, 'x',
        GRID_TRUTH['horizontal'],
        PIXELS_PER_METER,
        ORIGIN_PX
    )

    # Visualize
    print("\nGenerating visualization...")
    visualize_detection(
        img_p2, h_clustered, v_clustered, matched_h, matched_v,
        "output_artifacts/page2_grid_detection.png"
    )

    # Try Page 1 as well
    print("\n--- PAGE 1 (ARCH) ---")
    img_p1, gray_p1 = extract_page_image(pdf_path, page=1, dpi=300)

    print("\nDetecting lines...")
    h_lines_p1, v_lines_p1 = detect_lines(gray_p1, min_length=50)

    print("\nClustering parallel lines...")
    h_clustered_p1 = cluster_lines(h_lines_p1, 'y', tolerance=5)
    v_clustered_p1 = cluster_lines(v_lines_p1, 'x', tolerance=5)
    print(f"  Clustered to {len(h_clustered_p1)} horizontal lines")
    print(f"  Clustered to {len(v_clustered_p1)} vertical lines")

    print("\nMatching to grid coordinates...")
    print("  Horizontal grid (1-5):")
    matched_h_p1 = match_lines_to_grid(
        h_clustered_p1, 'y',
        GRID_TRUTH['vertical'],
        PIXELS_PER_METER,
        ORIGIN_PX
    )

    print("  Vertical grid (A-E):")
    matched_v_p1 = match_lines_to_grid(
        v_clustered_p1, 'x',
        GRID_TRUTH['horizontal'],
        PIXELS_PER_METER,
        ORIGIN_PX
    )

    # Visualize
    print("\nGenerating visualization...")
    visualize_detection(
        img_p1, h_clustered_p1, v_clustered_p1, matched_h_p1, matched_v_p1,
        "output_artifacts/page1_grid_detection.png"
    )

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Page 1: Matched {len(matched_h_p1)}/5 horizontal + {len(matched_v_p1)}/5 vertical grid lines")
    print(f"Page 2: Matched {len(matched_h)}/5 horizontal + {len(matched_v)}/5 vertical grid lines")

    # Save results
    results = {
        'page1': {
            'horizontal_matches': {k: {'grid_pos_m': v['grid_pos_m'], 'detected_px': v['detected_px'], 'error_px': v['error_px']}
                                  for k, v in matched_h_p1.items()},
            'vertical_matches': {k: {'grid_pos_m': v['grid_pos_m'], 'detected_px': v['detected_px'], 'error_px': v['error_px']}
                                for k, v in matched_v_p1.items()}
        },
        'page2': {
            'horizontal_matches': {k: {'grid_pos_m': v['grid_pos_m'], 'detected_px': v['detected_px'], 'error_px': v['error_px']}
                                  for k, v in matched_h.items()},
            'vertical_matches': {k: {'grid_pos_m': v['grid_pos_m'], 'detected_px': v['detected_px'], 'error_px': v['error_px']}
                                for k, v in matched_v.items()}
        },
        'calibration': {
            'pixels_per_meter': PIXELS_PER_METER,
            'origin_px': ORIGIN_PX
        }
    }

    with open('output_artifacts/grid_line_detection.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n✓ Saved: output_artifacts/grid_line_detection.json")
    print("✓ Next: Use matched grid lines to trace room boundaries")
    print("=" * 80)


if __name__ == "__main__":
    main()
