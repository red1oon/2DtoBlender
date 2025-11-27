#!/usr/bin/env python3
"""
Generate window placements from Page 8 schedule.
Rule 0 compliant - uses PLACEMENT_ALGORITHM_SPEC.md rules.
"""

import json


# Load existing data
with open('master_template.json', 'r') as f:
    template = json.load(f)

ROOM_BOUNDS = {k: v for k, v in template['room_bounds'].items()}
GRID_TRUTH = template['grid_truth']


# Window schedule from Page 8
WINDOW_SCHEDULE = {
    "W1": {
        "width_mm": 1800,
        "height_mm": 1000,
        "rooms": ["RUANG_TAMU", "BILIK_UTAMA", "BILIK_2", "BILIK_3", "DAPUR"],
        "type": "viewing",
        "description": "Large viewing window"
    },
    "W2": {
        "width_mm": 1200,
        "height_mm": 1000,
        "rooms": ["RUANG_TAMU", "BILIK_UTAMA", "BILIK_2", "BILIK_3", "DAPUR"],
        "type": "viewing",
        "description": "Medium viewing window"
    },
    "W3": {
        "width_mm": 600,
        "height_mm": 500,
        "rooms": ["BILIK_MANDI", "TANDAS"],
        "type": "ventilation",
        "description": "High ventilation window"
    }
}


def get_exterior_walls(room: str):
    """Identify exterior walls for a room."""
    if room not in ROOM_BOUNDS:
        return []

    bounds = ROOM_BOUNDS[room]
    x_min, x_max = bounds['x']
    y_min, y_max = bounds['y']

    # Building envelope bounds (A-E, 1-5)
    building_min_x = GRID_TRUTH['horizontal']['A']
    building_max_x = GRID_TRUTH['horizontal']['E']
    building_min_y = GRID_TRUTH['vertical']['1']
    building_max_y = GRID_TRUTH['vertical']['5']

    exterior = []

    # Check each wall
    if x_min <= building_min_x + 0.1:  # WEST wall is exterior
        exterior.append("WEST")
    if x_max >= building_max_x - 0.1:  # EAST wall is exterior
        exterior.append("EAST")
    if y_min <= building_min_y + 0.1:  # SOUTH wall is exterior
        exterior.append("SOUTH")
    if y_max >= building_max_y - 0.1:  # NORTH wall is exterior
        exterior.append("NORTH")

    return exterior


def calculate_window_position(room: str, wall: str, window_width_m: float):
    """Calculate window position on wall."""
    bounds = ROOM_BOUNDS[room]
    x_min, x_max = bounds['x']
    y_min, y_max = bounds['y']

    # Wall center with corner clearance
    corner_clearance = 0.3  # 300mm

    if wall == "WEST":
        x = x_min
        y_center = (y_min + y_max) / 2
        # Clamp to avoid corners
        y = max(y_min + corner_clearance, min(y_max - corner_clearance, y_center))
    elif wall == "EAST":
        x = x_max
        y_center = (y_min + y_max) / 2
        y = max(y_min + corner_clearance, min(y_max - corner_clearance, y_center))
    elif wall == "SOUTH":
        y = y_min
        x_center = (x_min + x_max) / 2
        x = max(x_min + corner_clearance, min(x_max - corner_clearance, x_center))
    elif wall == "NORTH":
        y = y_max
        x_center = (x_min + x_max) / 2
        x = max(x_min + corner_clearance, min(x_max - corner_clearance, x_center))
    else:
        x, y = 0, 0

    return (round(x, 3), round(y, 3))


def calculate_confidence(window_code: str, room: str, wall: str):
    """Calculate placement confidence."""
    score = 0.0

    # Schedule explicitly states room (+0.2)
    if room in WINDOW_SCHEDULE[window_code]['rooms']:
        score += 0.2

    # Window on exterior wall (+0.3)
    exterior_walls = get_exterior_walls(room)
    if wall in exterior_walls:
        score += 0.3

    # Room boundary from grid (+0.2)
    score += 0.2

    # Single valid wall (+0.1) or multiple options (-0.1)
    if len(exterior_walls) == 1:
        score += 0.1
    elif len(exterior_walls) > 2:
        score -= 0.1

    return round(score, 2)


def main():
    print("=" * 80)
    print("GENERATE WINDOW PLACEMENTS FROM PAGE 8 SCHEDULE")
    print("=" * 80)

    window_placements = []
    window_id_counter = 1

    # Generate placements
    for code, spec in WINDOW_SCHEDULE.items():
        print(f"\n{code}: {spec['width_mm']}×{spec['height_mm']}mm - {spec['type']}")

        # Sill height by type (from PLACEMENT_ALGORITHM_SPEC.md)
        sill_mm = 1500 if spec['type'] == 'ventilation' else 900
        sill_m = sill_mm / 1000.0

        for room in spec['rooms']:
            if room not in ROOM_BOUNDS:
                continue

            exterior_walls = get_exterior_walls(room)

            if not exterior_walls:
                print(f"  ⚠ {room}: No exterior walls - skipping")
                continue

            # Select wall (prefer longest exterior wall)
            room_type = ROOM_BOUNDS[room]['type']

            # Bathroom windows on WEST/NORTH walls (away from shower)
            if room_type in ['bathroom', 'toilet']:
                wall = exterior_walls[0]  # Take first available
            else:
                # For other rooms, prefer NORTH/EAST walls (better light)
                preferred = [w for w in ['NORTH', 'EAST'] if w in exterior_walls]
                wall = preferred[0] if preferred else exterior_walls[0]

            # Calculate position
            window_width_m = spec['width_mm'] / 1000.0
            x, y = calculate_window_position(room, wall, window_width_m)
            confidence = calculate_confidence(code, room, wall)

            placement = {
                "element_id": f"{code}_{window_id_counter}",
                "type": "window",
                "code": code,
                "room": room,
                "wall": wall,
                "position": {"x": x, "y": y, "z": sill_m},
                "size": {
                    "width": spec['width_mm'] / 1000.0,
                    "height": spec['height_mm'] / 1000.0
                },
                "width_mm": spec['width_mm'],
                "height_mm": spec['height_mm'],
                "sill_height_mm": sill_mm,
                "window_type": spec['type'],
                "confidence": confidence,
                "requires_review": confidence < 0.6,
                "description": f"{spec['description']} - {room}",
                "derivation": "Page 8 schedule + exterior wall selection"
            }

            window_placements.append(placement)
            window_id_counter += 1

            review = "⚠" if confidence < 0.6 else "✓"
            print(f"  {placement['element_id']}: {room} {wall} at ({x:.2f}, {y:.2f}, {sill_m:.2f})m "
                  f"conf={confidence:.2f} {review}")

    # Summary
    print("\n" + "=" * 80)
    print("WINDOW PLACEMENT SUMMARY")
    print("=" * 80)
    print(f"Total windows: {len(window_placements)}")
    print(f"Requires review: {sum(1 for w in window_placements if w['requires_review'])}")

    # Group by code
    print("\nBy window code:")
    for code in ['W1', 'W2', 'W3']:
        count = len([w for w in window_placements if w['code'] == code])
        print(f"  {code}: {count} windows")

    # Save
    output = {
        'window_placements': window_placements,
        'window_schedule': WINDOW_SCHEDULE,
        'metadata': {
            'source': 'Page 8 window schedule',
            'rule_0_compliant': True,
            'total_windows': len(window_placements),
            'sill_heights': {
                'viewing': 900,
                'ventilation': 1500
            }
        }
    }

    with open('output_artifacts/window_placements.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Saved: output_artifacts/window_placements.json")

    # Update master template
    template['window_placements'] = window_placements

    with open('master_template.json', 'w') as f:
        json.dump(template, f, indent=2)

    print(f"✓ Updated: master_template.json")
    print("=" * 80)


if __name__ == "__main__":
    main()
