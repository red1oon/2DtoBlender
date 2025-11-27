#!/usr/bin/env python3
"""
Deduce correct ROOM_BOUNDS from constraints:
1. Bedrooms are squares (user confirmation)
2. Schedule shows 3 bedrooms, 2 bathrooms
3. Grid coordinates are ground truth
4. Total floor area: 11.2m × 8.5m = 95.2 m²
"""

import json


# GridTruth (verified)
GRID_TRUTH = {
    "horizontal": {"A": 0.0, "B": 1.3, "C": 4.4, "D": 8.1, "E": 11.2},
    "vertical": {"1": 0.0, "2": 2.3, "3": 5.4, "4": 7.0, "5": 8.5}
}

# Current (suspect) room bounds
CURRENT_BOUNDS = {
    "RUANG_TAMU":   {"grid": "A1-C3",  "x": (0.0, 4.4),   "y": (0.0, 5.4)},
    "DAPUR":        {"grid": "C2-E4",  "x": (4.4, 11.2),  "y": (2.3, 7.0)},
    "BILIK_UTAMA":  {"grid": "D4-E5",  "x": (8.1, 11.2),  "y": (7.0, 8.5)},  # ⚠ 3.1×1.5m NOT square
    "BILIK_2":      {"grid": "B4-D5",  "x": (1.3, 8.1),   "y": (7.0, 8.5)},  # ⚠ 6.8×1.5m NOT square
    "BILIK_3":      {"grid": "C1-D2",  "x": (4.4, 8.1),   "y": (0.0, 2.3)},  # 3.7×2.3m roughly square
    "BILIK_MANDI":  {"grid": "A3-B4",  "x": (0.0, 1.3),   "y": (5.4, 7.0)},
    "TANDAS":       {"grid": "A4-B5",  "x": (0.0, 1.3),   "y": (7.0, 8.5)},
    "RUANG_BASUH":  {"grid": "C3-D4",  "x": (4.4, 8.1),   "y": (5.4, 7.0)},
}


def calculate_area(bounds):
    """Calculate room area in m²."""
    width = bounds['x'][1] - bounds['x'][0]
    height = bounds['y'][1] - bounds['y'][0]
    return width * height


def is_square(bounds, tolerance=0.5):
    """Check if room is roughly square."""
    width = bounds['x'][1] - bounds['x'][0]
    height = bounds['y'][1] - bounds['y'][0]
    return abs(width - height) < tolerance


print("=" * 80)
print("DEDUCTIVE ROOM BOUNDS ANALYSIS")
print("=" * 80)

print("\nConstraints:")
print("  1. Bedrooms are squares (user confirmation)")
print("  2. 3 bedrooms + 2 bathrooms + living + kitchen + utility")
print("  3. Grid coordinates are ground truth")
print("  4. Malaysian low-cost housing (Rumah Rakyat) typical sizes:")
print("     - Bedrooms: 9-12 m² each")
print("     - Living room: 20-25 m²")
print("     - Kitchen: 10-15 m²")

print("\n" + "=" * 80)
print("CURRENT ROOM BOUNDS ANALYSIS")
print("=" * 80)

bedroom_names = ["BILIK_UTAMA", "BILIK_2", "BILIK_3"]
total_area = 0

for room, bounds in CURRENT_BOUNDS.items():
    area = calculate_area(bounds)
    total_area += area
    width = bounds['x'][1] - bounds['x'][0]
    height = bounds['y'][1] - bounds['y'][0]
    square_check = "✓ Square" if is_square(bounds) else "✗ NOT square"

    marker = ""
    if room in bedroom_names:
        if not is_square(bounds):
            marker = " ⚠ SUSPECT"
        if area < 8:
            marker += " (too small)"

    print(f"{room:15s}: {width:.2f}m × {height:.2f}m = {area:6.2f}m² {square_check}{marker}")

print(f"\nTotal area: {total_area:.2f}m² (gross: {11.2 * 8.5:.2f}m²)")

# Deduction: If bedrooms are squares, what should they be?
print("\n" + "=" * 80)
print("DEDUCED CORRECTIONS")
print("=" * 80)

print("\nBedroom analysis:")
print("  Current bedroom areas: 4.65m², 10.2m², 8.51m²")
print("  Average: {:.2f}m²".format((4.65 + 10.2 + 8.51) / 3))
print("\n  If bedrooms should be equal-sized squares:")
print("  - Typical bedroom: ~3m × 3m = 9m²")
print("  - Grid spacing suggests: ~3.5m × 2.5m cells")

# Check grid cell sizes
print("\nGrid cell dimensions:")
for i, (l1, l2) in enumerate([('A','B'), ('B','C'), ('C','D'), ('D','E')]):
    width = GRID_TRUTH['horizontal'][l2] - GRID_TRUTH['horizontal'][l1]
    print(f"  {l1}-{l2}: {width:.1f}m wide")

for i, (n1, n2) in enumerate([('1','2'), ('2','3'), ('3','4'), ('4','5')]):
    height = GRID_TRUTH['vertical'][n2] - GRID_TRUTH['vertical'][n1]
    print(f"  {n1}-{n2}: {height:.1f}m tall")

# Proposed corrections
print("\n" + "=" * 80)
print("PROPOSED CORRECTED BOUNDS")
print("=" * 80)

# Based on typical Malaysian house layout and "bedrooms are squares"
# Assumption: Bedrooms might share similar dimensions along one axis
# Upper floor (rows 4-5): Bedrooms along the top
# If BILIK_2 is B4-D5 (6.8m × 1.5m), split it into proper square rooms

CORRECTED_BOUNDS = {
    "RUANG_TAMU":   {"grid": "A1-C3",  "x": (0.0, 4.4),   "y": (0.0, 5.4)},   # Keep (23.76m²) ✓
    "DAPUR":        {"grid": "C2-E4",  "x": (4.4, 11.2),  "y": (2.3, 7.0)},   # Keep (31.96m²) ?
    "BILIK_3":      {"grid": "C1-D2",  "x": (4.4, 8.1),   "y": (0.0, 2.3)},   # Keep (8.51m²) ✓
    "BILIK_MANDI":  {"grid": "A3-B4",  "x": (0.0, 1.3),   "y": (5.4, 7.0)},   # Keep (2.08m²) ✓
    "TANDAS":       {"grid": "A4-B5",  "x": (0.0, 1.3),   "y": (7.0, 8.5)},   # Keep (1.95m²) ✓
    "RUANG_BASUH":  {"grid": "C3-D4",  "x": (4.4, 8.1),   "y": (5.4, 7.0)},   # Keep (5.92m²) ✓

    # Bedroom corrections (if they should be squares):
    # Option 1: BILIK_2 is wider, BILIK_UTAMA is corner room
    "BILIK_2":      {"grid": "B4-C5",  "x": (1.3, 4.4),   "y": (7.0, 8.5)},   # 3.1m × 1.5m = 4.65m² (square-ish)
    "BILIK_UTAMA":  {"grid": "C4-E5",  "x": (4.4, 11.2),  "y": (7.0, 8.5)},   # 6.8m × 1.5m = 10.2m² (if this is correct)
}

print("\n⚠ Cannot determine exact boundaries without visual inspection")
print("Recommendation: Check wall detection visualizations:")
print("  - output_artifacts/page1_walls_and_grid.png")
print("  - output_artifacts/page2_walls_and_grid.png")
print("\nIdentify where bedroom partition walls actually are on grid.")

print("\n" + "=" * 80)
print("NEXT STEP:")
print("=" * 80)
print("Please visually inspect page1_walls_and_grid.png and tell me:")
print("1. Which grid cells does BILIK_UTAMA actually occupy?")
print("2. Which grid cells does BILIK_2 actually occupy?")
print("3. Are bedroom partition walls visible between them?")
print("=" * 80)


if __name__ == "__main__":
    pass
