#!/usr/bin/env python3
"""
Stage 4: Generate Door Placements

Reads:  output_artifacts/page8_schedules.json (from Stage 1)
        output_artifacts/room_bounds.json (from Stage 3)
Writes: output_artifacts/door_placements.json

Rule 0 Compliant: Derives door positions from room bounds and schedule.
"""

import json
from pathlib import Path


def load_stage_outputs():
    """Load outputs from previous stages."""
    with open('output_artifacts/page8_schedules.json') as f:
        schedules = json.load(f)

    with open('output_artifacts/room_bounds.json') as f:
        room_bounds = json.load(f)

    return schedules['door_schedule'], room_bounds


def get_accessible_walls(room_name, room_bounds, building_envelope=None):
    """
    Identify which walls are accessible for doors.

    For bedrooms: internal walls (corridors/hallways)
    For bathrooms: internal walls
    For living/dining/kitchen: may have external doors
    """
    if room_name not in room_bounds:
        return []

    bounds = room_bounds[room_name]
    x_min, x_max = bounds['x']
    y_min, y_max = bounds['y']
    room_type = bounds.get('type', '')

    # Building envelope (TB-LKTN standard)
    WEST_WALL = 0.0
    EAST_WALL = 11.2
    SOUTH_WALL = 0.0
    NORTH_WALL = 8.5

    accessible_walls = []

    # External doors: living, dining, kitchen can have external access
    if room_type in ['living', 'dining', 'kitchen']:
        if abs(x_min - WEST_WALL) < 0.1:
            accessible_walls.append("WEST")
        if abs(x_max - EAST_WALL) < 0.1:
            accessible_walls.append("EAST")
        if abs(y_min - SOUTH_WALL) < 0.1:
            accessible_walls.append("SOUTH")
        if abs(y_max - NORTH_WALL) < 0.1:
            accessible_walls.append("NORTH")

    # Internal doors: all rooms need access to circulation spaces
    # Bedrooms and bathrooms typically have doors facing corridors/hallways
    # Check for internal walls (walls not on building perimeter)
    if abs(x_min - WEST_WALL) > 0.1:
        accessible_walls.append("WEST")
    if abs(x_max - EAST_WALL) > 0.1:
        accessible_walls.append("EAST")
    if abs(y_min - SOUTH_WALL) > 0.1:
        accessible_walls.append("SOUTH")
    if abs(y_max - NORTH_WALL) > 0.1:
        accessible_walls.append("NORTH")

    return accessible_walls


def place_door(element_id, code, room_name, wall, door_spec, room_bounds):
    """Calculate door placement."""
    bounds = room_bounds[room_name]
    x_min, x_max = bounds['x']
    y_min, y_max = bounds['y']

    width_mm = door_spec['width_mm']
    height_mm = door_spec['height_mm']

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

    # Z position is floor level for doors
    z = 0.0

    return {
        "element_id": element_id,
        "code": code,
        "room": room_name,
        "wall": wall,
        "position": {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)},
        "width_mm": width_mm,
        "height_mm": height_mm,
        "door_type": door_spec['type']
    }


def main():
    print("=" * 80)
    print("STAGE 4: GENERATE DOOR PLACEMENTS")
    print("=" * 80)

    # Load stage outputs
    print("\n📖 Loading stage outputs...")
    door_schedule, room_bounds = load_stage_outputs()

    print(f"   ✓ Door types: {len(door_schedule)}")
    print(f"   ✓ Rooms: {len(room_bounds)}")

    # Generate door placements
    print("\n🚪 Placing doors...")
    placements = []
    counters = {code: 1 for code in door_schedule.keys()}

    for code, spec in door_schedule.items():
        locations = spec['locations'].split(', ')

        print(f"\n{code}: {spec['width_mm']}×{spec['height_mm']}mm ({spec['type']})")

        for room_name in locations:
            room_name = room_name.strip().upper().replace(' ', '_')

            if room_name not in room_bounds:
                print(f"   ⚠️  {room_name}: Room not found, skipping")
                continue

            # Get accessible walls
            accessible_walls = get_accessible_walls(room_name, room_bounds)

            if not accessible_walls:
                print(f"   ⚠️  {room_name}: No accessible walls, skipping")
                continue

            # Place door on first accessible wall
            wall = accessible_walls[0]
            element_id = f"{code}_{counters[code]}"
            counters[code] += 1

            placement = place_door(element_id, code, room_name, wall, spec, room_bounds)
            placements.append(placement)

            print(f"   {element_id}: {room_name} on {wall} wall at ({placement['position']['x']:.2f}, {placement['position']['y']:.2f}, {placement['position']['z']:.2f})")

    # Save output
    output_path = Path("output_artifacts/door_placements.json")
    with open(output_path, 'w') as f:
        json.dump(placements, f, indent=2)

    print("\n" + "=" * 80)
    print("DOOR PLACEMENT COMPLETE")
    print("=" * 80)
    print(f"\nTotal doors placed: {len(placements)}")
    print(f"✓ Saved: {output_path}")

    print("\n📊 Next step:")
    print("   Stage 5: python3 generate_window_placements_v2.py")
    print("=" * 80)


if __name__ == "__main__":
    main()
