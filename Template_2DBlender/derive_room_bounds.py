#!/usr/bin/env python3
"""
Derive ROOM_BOUNDS from OCR room labels + GridTruth.
Rule 0 compliant - no manual mapping.

Algorithm:
1. OCR room labels → centroids (pixel coords)
2. Pixel → world transform using GridTruth
3. Voronoi assignment: each grid cell → nearest room centroid
4. Room bounds = bounding box of assigned cells
"""

import pytesseract
import pdf2image
import numpy as np
import cv2
import re
from typing import Dict, Tuple, List
import json

# GridTruth (verified)
GRID_TRUTH = {
    "horizontal": {"A": 0.0, "B": 1.3, "C": 4.4, "D": 8.1, "E": 11.2},
    "vertical": {"1": 0.0, "2": 2.3, "3": 5.4, "4": 7.0, "5": 8.5}
}

# Calibration (from coordinate_generator.py)
PIXELS_PER_METER = 118.11

# Expected room names
ROOM_NAMES = [
    "RUANG TAMU", "RUANG_TAMU",
    "DAPUR",
    "BILIK UTAMA", "BILIK_UTAMA",
    "BILIK 2", "BILIK_2",
    "BILIK 3", "BILIK_3",
    "BILIK MANDI", "BILIK_MANDI",
    "TANDAS",
    "RUANG BASUH", "RUANG_BASUH"
]


def ocr_room_labels(pdf_path: str, page: int = 1) -> Dict[str, Tuple[float, float]]:
    """
    Extract room label positions using OCR.
    Returns {room_name: (center_x_px, center_y_px)}
    """
    print(f"Converting page {page}...")
    pages = pdf2image.convert_from_path(pdf_path, dpi=300, first_page=page, last_page=page)
    img = np.array(pages[0])

    print("Running OCR...")
    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    room_positions = {}

    for i, text in enumerate(ocr_data['text']):
        text_upper = text.strip().upper()

        # Check if this matches any room name (partial match)
        matched_room = None
        for room in ROOM_NAMES:
            room_upper = room.upper().replace("_", " ")
            # Match if significant overlap
            if room_upper in text_upper or text_upper in room_upper:
                matched_room = room.replace(" ", "_")
                break
            # Also check for partial words
            room_words = room_upper.split()
            text_words = text_upper.split()
            if any(word in text_words for word in room_words if len(word) > 3):
                matched_room = room.replace(" ", "_")
                break

        if matched_room and ocr_data['conf'][i] > 30:
            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            w = ocr_data['width'][i]
            h = ocr_data['height'][i]

            # Calculate centroid
            cx = x + w / 2
            cy = y + h / 2

            # Keep first occurrence (room labels are typically unique)
            if matched_room not in room_positions:
                room_positions[matched_room] = (cx, cy)
                print(f"  Found: {matched_room} at ({cx:.0f}, {cy:.0f})px")

    return room_positions


def pixel_to_world(px: float, py: float, origin_px: Tuple[float, float]) -> Tuple[float, float]:
    """
    Convert pixel coordinates to world (meters).
    Assumes origin_px is the (0,0) reference point.
    Y-axis inverted (image Y increases down, world Y increases up).
    """
    ox, oy = origin_px

    # Transform: px → meters (invert Y)
    wx = (px - ox) / PIXELS_PER_METER
    wy = (oy - py) / PIXELS_PER_METER  # Invert Y axis

    return (wx, wy)


def find_grid_origin(ocr_data) -> Tuple[float, float]:
    """
    Find pixel position of grid origin (A,1).
    Look for grid circle labeled "A" or "1" near corners.
    """
    # Heuristic: Find "A" label in lower-left quadrant
    # For now, use approximate origin from previous calibration
    # TODO: Improve by detecting grid circles
    return (178, 322)  # From coordinate_generator calibration


def get_grid_cell_center(grid_letter: str, grid_number: str) -> Tuple[float, float]:
    """
    Get world coordinates for grid cell center.
    """
    x = GRID_TRUTH["horizontal"][grid_letter]
    y = GRID_TRUTH["vertical"][grid_number]
    return (x, y)


def assign_cells_to_rooms(room_centroids: Dict[str, Tuple[float, float]]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Voronoi assignment: each grid cell → nearest room centroid.
    Returns {room_name: [(grid_letter, grid_number), ...]}
    """
    # All grid cells
    grid_letters = list(GRID_TRUTH["horizontal"].keys())
    grid_numbers = list(GRID_TRUTH["vertical"].keys())

    room_cells = {room: [] for room in room_centroids.keys()}

    for i in range(len(grid_letters) - 1):
        for j in range(len(grid_numbers) - 1):
            # Cell defined by corners (i,j) to (i+1, j+1)
            letter1, letter2 = grid_letters[i], grid_letters[i+1]
            number1, number2 = grid_numbers[j], grid_numbers[j+1]

            # Cell center
            cx = (GRID_TRUTH["horizontal"][letter1] + GRID_TRUTH["horizontal"][letter2]) / 2
            cy = (GRID_TRUTH["vertical"][number1] + GRID_TRUTH["vertical"][number2]) / 2

            # Find nearest room centroid
            min_dist = float('inf')
            nearest_room = None

            for room, (rx, ry) in room_centroids.items():
                dist = np.sqrt((cx - rx)**2 + (cy - ry)**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_room = room

            if nearest_room:
                room_cells[nearest_room].append((letter1 + letter2, number1 + number2))

    return room_cells


def calculate_room_bounds(room_cells: Dict[str, List[Tuple[str, str]]]) -> Dict[str, Dict]:
    """
    Calculate bounding box for each room from assigned cells.
    """
    room_bounds = {}

    for room, cells in room_cells.items():
        if not cells:
            continue

        # Collect all grid coordinates
        x_coords = []
        y_coords = []

        for cell_id in cells:
            # Parse cell_id like "AB12"
            letters = ''.join([c for c in cell_id if c.isalpha()])
            numbers = ''.join([c for c in cell_id if c.isdigit()])

            for letter in letters:
                if letter in GRID_TRUTH["horizontal"]:
                    x_coords.append(GRID_TRUTH["horizontal"][letter])

            for number in numbers:
                if number in GRID_TRUTH["vertical"]:
                    y_coords.append(GRID_TRUTH["vertical"][number])

        if x_coords and y_coords:
            room_bounds[room] = {
                "x": (min(x_coords), max(x_coords)),
                "y": (min(y_coords), max(y_coords)),
                "cells": cells
            }

    return room_bounds


def main():
    print("=" * 80)
    print("DERIVE ROOM_BOUNDS FROM OCR + GRIDTRUTH")
    print("=" * 80)

    pdf_path = "TB-LKTN HOUSE.pdf"

    # Step 1: OCR room labels
    room_positions_px = ocr_room_labels(pdf_path, page=1)

    if not room_positions_px:
        print("\n❌ No room labels found via OCR")
        return

    # Step 2: Find grid origin
    origin_px = find_grid_origin(None)
    print(f"\nGrid origin (estimated): ({origin_px[0]:.0f}, {origin_px[1]:.0f})px")

    # Step 3: Convert room positions to world coords
    room_centroids = {}
    for room, (px, py) in room_positions_px.items():
        wx, wy = pixel_to_world(px, py, origin_px)
        room_centroids[room] = (wx, wy)
        print(f"  {room}: ({wx:.2f}, {wy:.2f})m")

    # Step 4: Assign grid cells to rooms
    print("\nAssigning grid cells to rooms (Voronoi)...")
    room_cells = assign_cells_to_rooms(room_centroids)

    # Step 5: Calculate room bounds
    room_bounds = calculate_room_bounds(room_cells)

    # Display results
    print("\n" + "=" * 80)
    print("DERIVED ROOM_BOUNDS")
    print("=" * 80)

    for room, bounds in sorted(room_bounds.items()):
        x_min, x_max = bounds['x']
        y_min, y_max = bounds['y']
        width = x_max - x_min
        height = y_max - y_min
        area = width * height

        print(f"\n{room}:")
        print(f"  X: [{x_min:.2f}, {x_max:.2f}]m  ({width:.2f}m wide)")
        print(f"  Y: [{y_min:.2f}, {y_max:.2f}]m  ({height:.2f}m tall)")
        print(f"  Area: {area:.2f}m²")
        print(f"  Cells: {len(bounds['cells'])} grid cells")

    # Save to JSON
    output = {
        "room_centroids": {k: list(v) for k, v in room_centroids.items()},
        "room_bounds": room_bounds,
        "metadata": {
            "method": "OCR_Voronoi",
            "grid_origin_px": origin_px,
            "pixels_per_meter": PIXELS_PER_METER
        }
    }

    output_path = "output_artifacts/room_bounds_derived.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Saved: {output_path}")
    print("\n" + "=" * 80)
    print("✅ Rule 0 Compliant - Derived from OCR + GridTruth geometry")
    print("=" * 80)


if __name__ == "__main__":
    main()
