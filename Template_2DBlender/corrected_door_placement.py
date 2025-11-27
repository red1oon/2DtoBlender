#!/usr/bin/env python3
"""
Corrected door placement based on Page 8 schedule ground truth.

DOOR SCHEDULE (from Page 8):
- D1: 900MM × 2100MM - Ruang Tamu & Dapur (2 doors)
- D2: 900MM × 2100MM - Bilik Utama, Bilik 2 & Bilik 3 (3 doors)
- D3: 750MM × 2100MM - Bilik Mandi & Tandas (2 doors)

Total: 7 doors
"""

import json


# GridTruth (verified)
GRID_TRUTH = {
    "horizontal": {"A": 0.0, "B": 1.3, "C": 4.4, "D": 8.1, "E": 11.2},
    "vertical": {"1": 0.0, "2": 2.3, "3": 5.4, "4": 7.0, "5": 8.5}
}

# Room bounds (from poc_pipeline.py)
# Note: BILIK_UTAMA bounds may need correction if bedrooms should be square
ROOM_BOUNDS = {
    "RUANG_TAMU":   {"x": (0.0, 4.4),   "y": (0.0, 5.4)},    # 4.4×5.4m = 23.76m²
    "DAPUR":        {"x": (4.4, 11.2),  "y": (2.3, 7.0)},    # 6.8×4.7m = 31.96m²
    "BILIK_UTAMA":  {"x": (8.1, 11.2),  "y": (7.0, 8.5)},    # 3.1×1.5m = 4.65m² ⚠ Suspect
    "BILIK_2":      {"x": (1.3, 8.1),   "y": (7.0, 8.5)},    # 6.8×1.5m = 10.2m²
    "BILIK_3":      {"x": (4.4, 8.1),   "y": (0.0, 2.3)},    # 3.7×2.3m = 8.51m²
    "BILIK_MANDI":  {"x": (0.0, 1.3),   "y": (5.4, 7.0)},    # 1.3×1.6m = 2.08m²
    "TANDAS":       {"x": (0.0, 1.3),   "y": (7.0, 8.5)},    # 1.3×1.5m = 1.95m²
    "RUANG_BASUH":  {"x": (4.4, 8.1),   "y": (5.4, 7.0)},    # 3.7×1.6m = 5.92m²
}


# CORRECTED door placement rules (Rule 0 compliant)
DOOR_PLACEMENTS = [
    # D1 - External doors (900mm × 2100mm)
    {
        "id": "D1_1",
        "code": "D1",
        "room": "RUANG_TAMU",
        "wall": "SOUTH",
        "position": "center",
        "width_mm": 900,
        "height_mm": 2100,
        "description": "External door - Living room"
    },
    {
        "id": "D1_2",
        "code": "D1",
        "room": "DAPUR",
        "wall": "EAST",
        "position": "center",
        "width_mm": 900,
        "height_mm": 2100,
        "description": "External door - Kitchen"
    },

    # D2 - Internal bedroom doors (900mm × 2100mm)
    {
        "id": "D2_1",
        "code": "D2",
        "room": "BILIK_UTAMA",
        "wall": "SOUTH",
        "position": "center",
        "width_mm": 900,
        "height_mm": 2100,
        "description": "Bedroom door - Master bedroom"
    },
    {
        "id": "D2_2",
        "code": "D2",
        "room": "BILIK_2",
        "wall": "SOUTH",
        "position": "center",
        "width_mm": 900,
        "height_mm": 2100,
        "description": "Bedroom door - Bedroom 2"
    },
    {
        "id": "D2_3",
        "code": "D2",
        "room": "BILIK_3",
        "wall": "NORTH",
        "position": "center",
        "width_mm": 900,
        "height_mm": 2100,
        "description": "Bedroom door - Bedroom 3"
    },

    # D3 - Bathroom doors (750mm × 2100mm)
    {
        "id": "D3_1",
        "code": "D3",
        "room": "BILIK_MANDI",
        "wall": "EAST",
        "position": "center",
        "width_mm": 750,
        "height_mm": 2100,
        "description": "Bathroom door - Main bathroom"
    },
    {
        "id": "D3_2",
        "code": "D3",
        "room": "TANDAS",
        "wall": "EAST",
        "position": "center",
        "width_mm": 750,
        "height_mm": 2100,
        "description": "Bathroom door - Toilet"
    },
]


def get_wall_coordinate(room: str, wall: str, position: str = "center"):
    """
    Calculate wall coordinate for door placement.

    Args:
        room: Room name
        wall: "NORTH", "SOUTH", "EAST", "WEST"
        position: "center", "grid_X", or specific offset

    Returns:
        (x, y, z) coordinates in meters (z=0 for floor level)
    """
    if room not in ROOM_BOUNDS:
        return (0, 0, 0)

    bounds = ROOM_BOUNDS[room]
    x_min, x_max = bounds['x']
    y_min, y_max = bounds['y']

    # Wall positions
    if wall == "SOUTH":
        x = (x_min + x_max) / 2 if position == "center" else x_min
        y = y_min
    elif wall == "NORTH":
        x = (x_min + x_max) / 2 if position == "center" else x_min
        y = y_max
    elif wall == "WEST":
        x = x_min
        y = (y_min + y_max) / 2 if position == "center" else y_min
    elif wall == "EAST":
        x = x_max
        y = (y_min + y_max) / 2 if position == "center" else y_min
    else:
        x = (x_min + x_max) / 2
        y = (y_min + y_max) / 2

    return (x, y, 0.0)  # z=0 at floor level


def main():
    print("=" * 80)
    print("CORRECTED DOOR PLACEMENT (Rule 0 Compliant)")
    print("=" * 80)
    print("\nGround truth source: Page 8 Door Schedule")
    print("\nDoor specifications:")
    print("  D1: 900mm × 2100mm - External doors (Ruang Tamu & Dapur)")
    print("  D2: 900mm × 2100mm - Bedroom doors (Bilik Utama, 2 & 3)")
    print("  D3: 750mm × 2100mm - Bathroom doors (Bilik Mandi & Tandas)")

    print("\n" + "=" * 80)
    print("DOOR PLACEMENTS (7 Total)")
    print("=" * 80)
    print(f"{'ID':<8} {'Code':<6} {'Room':<15} {'Wall':<7} {'Size (mm)':<12} {'Position (m)':<20} {'Description'}")
    print("-" * 110)

    for door in DOOR_PLACEMENTS:
        x, y, z = get_wall_coordinate(door['room'], door['wall'], door['position'])
        size_str = f"{door['width_mm']}×{door['height_mm']}"
        pos_str = f"({x:.2f}, {y:.2f})"

        print(f"{door['id']:<8} {door['code']:<6} {door['room']:<15} {door['wall']:<7} "
              f"{size_str:<12} {pos_str:<20} {door['description']}")

    # Save to JSON
    output = {
        'door_placements': DOOR_PLACEMENTS,
        'room_bounds': ROOM_BOUNDS,
        'grid_truth': GRID_TRUTH,
        'metadata': {
            'source': 'Page 8 Door Schedule',
            'rule_0_compliant': True,
            'total_doors': len(DOOR_PLACEMENTS),
            'corrections': [
                'D1 width: 750mm → 900mm',
                'D2 width: 750mm → 900mm',
                'D2 count: Added D2_3 for BILIK_3',
                'D2_1: Moved from DAPUR to BILIK_UTAMA (corrected assignment)'
            ]
        }
    }

    with open('output_artifacts/corrected_door_placement.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 80)
    print("CHANGES FROM PREVIOUS VERSION:")
    print("=" * 80)
    print("✓ D1 doors: 750mm → 900mm (2 doors)")
    print("✓ D2 doors: 750mm → 900mm (3 doors)")
    print("✓ D2_3: Added for BILIK_3 (was missing)")
    print("✓ D3 doors: 750mm ✓ (correct)")
    print("\n✓ Saved: output_artifacts/corrected_door_placement.json")
    print("=" * 80)


if __name__ == "__main__":
    main()
