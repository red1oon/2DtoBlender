#!/usr/bin/env python3
"""
Stage 5: Generate Window Placements

Reads:  output_artifacts/page8_schedules.json (from Stage 1)
        output_artifacts/room_bounds.json (from Stage 3)
Writes: output_artifacts/window_placements.json

Rule 0 Compliant: Derives window positions from room bounds and schedule.
"""

import json
from pathlib import Path


def load_stage_outputs():
    """Load outputs from previous stages."""
    with open('output_artifacts/page8_schedules.json') as f:
        schedules = json.load(f)

    with open('output_artifacts/room_bounds.json') as f:
        room_bounds = json.load(f)

    return schedules['window_schedule'], room_bounds


def get_exterior_walls(room_name, room_bounds, building_envelope=None):
    """Identify which walls are exterior for this room."""
    if room_name not in room_bounds:
        return []

    bounds = room_bounds[room_name]
    x_min, x_max = bounds['x']
    y_min, y_max = bounds['y']

    # Building envelope (TB-LKTN standard)
    WEST_WALL = 0.0
    EAST_WALL = 11.2
    SOUTH_WALL = 0.0
    NORTH_WALL = 8.5

    exterior_walls = []

    if abs(x_min - WEST_WALL) < 0.1:
        exterior_walls.append("WEST")
    if abs(x_max - EAST_WALL) < 0.1:
        exterior_walls.append("EAST")
    if abs(y_min - SOUTH_WALL) < 0.1:
        exterior_walls.append("SOUTH")
    if abs(y_max - NORTH_WALL) < 0.1:
        exterior_walls.append("NORTH")

    return exterior_walls


def place_window(element_id, code, room_name, wall, window_spec, room_bounds):
    """Calculate window placement."""
    bounds = room_bounds[room_name]
    x_min, x_max = bounds['x']
    y_min, y_max = bounds['y']

    width_mm = window_spec['width_mm']
    height_mm = window_spec['height_mm']
    sill_height_mm = window_spec['sill_height_mm']

    # Calculate center position on wall
    if wall == "SOUTH":
        x = (x_min + x_max) / 2
        y = y_min
    elif wall == "NORTH":
        x = (x_min + x_max) / 2
        y = y_max
    elif wall == "WEST":
        x = x_min
        y = (y_min + y_max) / 2
    elif wall == "EAST":
        x = x_max
        y = (y_min + y_max) / 2
    else:
        x, y = 0, 0

    # Z position is sill height
    z = sill_height_mm / 1000.0  # Convert mm to meters

    return {
        "element_id": element_id,
        "code": code,
        "room": room_name,
        "wall": wall,
        "position": {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)},
        "width_mm": width_mm,
        "height_mm": height_mm,
        "sill_height_mm": sill_height_mm,
        "window_type": window_spec['type']
    }


def main():
    print("=" * 80)
    print("STAGE 5: GENERATE WINDOW PLACEMENTS")
    print("=" * 80)

    # Load stage outputs
    print("\n📖 Loading stage outputs...")
    window_schedule, room_bounds = load_stage_outputs()

    print(f"   ✓ Window types: {len(window_schedule)}")
    print(f"   ✓ Rooms: {len(room_bounds)}")

    # Generate window placements
    print("\n🪟 Placing windows...")
    placements = []
    counters = {code: 1 for code in window_schedule.keys()}

    for code, spec in window_schedule.items():
        locations = spec['locations'].split(', ')

        print(f"\n{code}: {spec['width_mm']}×{spec['height_mm']}mm (sill {spec['sill_height_mm']}mm)")

        for room_name in locations:
            room_name = room_name.strip().upper().replace(' ', '_')

            # Normalize room names to match room_bounds keys
            # Schedule uses "Bilik 2", room_bounds uses "BILIK_2"

            if room_name not in room_bounds:
                print(f"   ⚠️  {room_name}: Room not found, skipping")
                continue

            # Get exterior walls
            exterior_walls = get_exterior_walls(room_name, room_bounds)

            if not exterior_walls:
                print(f"   ⚠️  {room_name}: No exterior walls, skipping")
                continue

            # Place window on first exterior wall
            wall = exterior_walls[0]
            element_id = f"{code}_{counters[code]}"
            counters[code] += 1

            placement = place_window(element_id, code, room_name, wall, spec, room_bounds)
            placements.append(placement)

            print(f"   {element_id}: {room_name} on {wall} wall at ({placement['position']['x']:.2f}, {placement['position']['y']:.2f}, {placement['position']['z']:.2f})")

    # Save output
    output_path = Path("output_artifacts/window_placements.json")
    with open(output_path, 'w') as f:
        json.dump(placements, f, indent=2)

    print("\n" + "=" * 80)
    print("WINDOW PLACEMENT COMPLETE")
    print("=" * 80)
    print(f"\nTotal windows placed: {len(placements)}")
    print(f"✓ Saved: {output_path}")

    print("\n📊 Next step:")
    print("   Stage 6: python3 consolidate_master_template.py")
    print("=" * 80)


if __name__ == "__main__":
    main()
