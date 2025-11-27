#!/usr/bin/env python3
"""
Detect grid circles and labels to calibrate origin accurately.
Look for grid labels A-E and 1-5 with their circle markers.
"""

import pdf2image
import numpy as np
import cv2
import pytesseract
import json


def detect_grid_circles(gray, min_radius=15, max_radius=30):
    """Detect grid circle markers."""
    # Use medium blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=30,
        param1=50,
        param2=20,
        minRadius=min_radius,
        maxRadius=max_radius
    )

    if circles is None:
        return []

    circles = np.round(circles[0, :]).astype("int")
    print(f"  Detected {len(circles)} grid circles (r={min_radius}-{max_radius}px)")

    return [{'x': int(x), 'y': int(y), 'radius': int(r)} for x, y, r in circles]


def detect_grid_labels(img_rgb, circles):
    """OCR text near circles to find grid labels."""
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY) if len(img_rgb.shape) == 3 else img_rgb

    labeled_circles = []

    for circle in circles:
        cx, cy, r = circle['x'], circle['y'], circle['radius']

        # Extract ROI around circle (larger for label detection)
        margin = r * 3
        x1 = max(0, cx - margin)
        y1 = max(0, cy - margin)
        x2 = min(gray.shape[1], cx + margin)
        y2 = min(gray.shape[0], cy + margin)

        roi = gray[y1:y2, x1:x2]

        # OCR
        text = pytesseract.image_to_string(roi, config='--psm 10').strip().upper()

        # Check if it's a grid label
        if text in ['A', 'B', 'C', 'D', 'E', '1', '2', '3', '4', '5']:
            labeled_circles.append({
                'label': text,
                'x': cx,
                'y': cy,
                'radius': r
            })
            print(f"    Found grid label '{text}' at ({cx}, {cy})px")

    return labeled_circles


def find_origin(labeled_circles):
    """Find origin (grid A1) from labeled circles."""
    # Look for A and 1
    a_circle = None
    one_circle = None

    for circle in labeled_circles:
        if circle['label'] == 'A':
            a_circle = circle
        elif circle['label'] == '1':
            one_circle = circle

    if a_circle and one_circle:
        # Origin is at intersection of A (vertical) and 1 (horizontal)
        origin_x = a_circle['x']
        origin_y = one_circle['y']
        print(f"\n✓ Found origin from A and 1 circles: ({origin_x}, {origin_y})px")
        return (origin_x, origin_y), True

    # Fallback: estimate from detected labels
    if a_circle:
        print(f"\n⚠ Only found A circle at ({a_circle['x']}, {a_circle['y']})px")
        return (a_circle['x'], a_circle['y']), False
    if one_circle:
        print(f"\n⚠ Only found 1 circle at ({one_circle['x']}, {one_circle['y']})px")
        return (one_circle['x'], one_circle['y']), False

    print("\n✗ Could not find origin - no A or 1 labels detected")
    return None, False


def calibrate_pixels_per_meter(labeled_circles):
    """Calibrate pixels/meter from known grid spacing."""
    # Expected spacing in meters
    GRID_SPACING = {
        'A': 0.0, 'B': 1.3, 'C': 4.4, 'D': 8.1, 'E': 11.2,
        '1': 0.0, '2': 2.3, '3': 5.4, '4': 7.0, '5': 8.5
    }

    # Find pairs with known spacing
    horizontal_pairs = []
    vertical_pairs = []

    for i, c1 in enumerate(labeled_circles):
        for c2 in labeled_circles[i+1:]:
            label1, label2 = c1['label'], c2['label']

            # Horizontal (A-E)
            if label1 in GRID_SPACING and label2 in GRID_SPACING and label1.isalpha() and label2.isalpha():
                dist_px = abs(c2['x'] - c1['x'])
                dist_m = abs(GRID_SPACING[label2] - GRID_SPACING[label1])
                if dist_m > 0:
                    ppm = dist_px / dist_m
                    horizontal_pairs.append((label1, label2, dist_px, dist_m, ppm))

            # Vertical (1-5)
            elif label1 in GRID_SPACING and label2 in GRID_SPACING and label1.isdigit() and label2.isdigit():
                dist_px = abs(c2['y'] - c1['y'])
                dist_m = abs(GRID_SPACING[label2] - GRID_SPACING[label1])
                if dist_m > 0:
                    ppm = dist_px / dist_m
                    vertical_pairs.append((label1, label2, dist_px, dist_m, ppm))

    # Average calibration
    all_ppm = [p[4] for p in horizontal_pairs + vertical_pairs]
    if all_ppm:
        avg_ppm = np.mean(all_ppm)
        print(f"\nCalibrated pixels/meter from {len(all_ppm)} grid pairs:")
        for label1, label2, dist_px, dist_m, ppm in horizontal_pairs + vertical_pairs:
            print(f"  {label1}-{label2}: {dist_px:.0f}px / {dist_m:.1f}m = {ppm:.2f} px/m")
        print(f"  Average: {avg_ppm:.2f} px/m")
        return avg_ppm
    else:
        print("\n⚠ Could not calibrate - insufficient grid labels")
        return 118.11  # Use default


def main():
    pdf_path = "TB-LKTN HOUSE.pdf"

    print("=" * 80)
    print("CALIBRATE GRID ORIGIN FROM DETECTED CIRCLES")
    print("=" * 80)

    # Try Page 1
    print("\n--- PAGE 1 ---")
    pages = pdf2image.convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
    img = np.array(pages[0])
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img

    print("\nDetecting grid circles...")
    circles = detect_grid_circles(gray, min_radius=10, max_radius=25)

    if circles:
        print(f"\nOCR labels near circles...")
        labeled = detect_grid_labels(img, circles)
        print(f"  Found {len(labeled)} labeled grid circles")

        # Find origin
        origin, exact = find_origin(labeled)

        # Calibrate
        ppm = calibrate_pixels_per_meter(labeled)

        # Save
        result = {
            'origin_px': list(origin) if origin else None,
            'origin_exact': exact,
            'pixels_per_meter': ppm,
            'labeled_circles': labeled
        }

        with open('output_artifacts/grid_calibration.json', 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n✓ Saved: output_artifacts/grid_calibration.json")

        if origin:
            print("\n" + "=" * 80)
            print("CALIBRATION COMPLETE")
            print("=" * 80)
            print(f"Origin: ({origin[0]}, {origin[1]})px")
            print(f"Pixels/meter: {ppm:.2f}")
            print("=" * 80)
    else:
        print("\n✗ No grid circles detected")


if __name__ == "__main__":
    main()
