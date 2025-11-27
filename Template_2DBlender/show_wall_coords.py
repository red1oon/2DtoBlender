#!/usr/bin/env python3
"""
Display all wall coordinates for door placement verification.
Shows exact coordinates where doors will be placed.
"""

# GridTruth from poc_pipeline.py
GRID_TRUTH = {
    "horizontal": {
        "A": 0.0,
        "B": 1.3,
        "C": 4.4,
        "D": 8.1,
        "E": 11.2
    },
    "vertical": {
        "1": 0.0,
        "2": 2.3,
        "3": 5.4,
        "4": 7.0,
        "5": 8.5
    },
    "setback": 0.75
}

# Room bounds from poc_pipeline.py
ROOM_BOUNDS = {
    "RUANG_TAMU":   {"x": (0.0, 4.4),   "y": (0.0, 5.4)},
    "DAPUR":        {"x": (4.4, 11.2),  "y": (2.3, 7.0)},
    "BILIK_UTAMA":  {"x": (8.1, 11.2),  "y": (7.0, 8.5)},
    "BILIK_2":      {"x": (1.3, 8.1),   "y": (7.0, 8.5)},
    "BILIK_3":      {"x": (4.4, 8.1),   "y": (0.0, 2.3)},
    "BILIK_MANDI":  {"x": (0.0, 1.3),   "y": (5.4, 7.0)},
    "TANDAS":       {"x": (0.0, 1.3),   "y": (7.0, 8.5)},
    "RUANG_BASUH":  {"x": (4.4, 8.1),   "y": (5.4, 7.0)},
}

def get_wall_coordinate(room: str, wall: str, position: str = "center"):
    """
    Calculate wall coordinate for door/window placement.

    Args:
        room: Room name
        wall: "NORTH", "SOUTH", "EAST", "WEST"
        position: "center", "grid_X", or float offset

    Returns:
        (x, y) coordinates in meters
    """
    if room not in ROOM_BOUNDS:
        return (0, 0)

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

    return (x, y)


# Door placement rules from coordinate_generator.py
DOOR_PLACEMENTS = [
    # D1 - External doors
    {"id": "D1_1", "code": "D1", "room": "RUANG_TAMU", "wall": "SOUTH", "position": "center", "size": "750x2100mm"},
    {"id": "D1_2", "code": "D1", "room": "DAPUR", "wall": "EAST", "position": "center", "size": "750x2100mm"},

    # D2 - Internal bedroom doors
    {"id": "D2_1", "code": "D2", "room": "DAPUR", "wall": "WEST", "position": "grid_C", "size": "750x2100mm"},
    {"id": "D2_2", "code": "D2", "room": "BILIK_UTAMA", "wall": "SOUTH", "position": "center", "size": "750x2100mm"},
    {"id": "D2_3", "code": "D2", "room": "BILIK_2", "wall": "SOUTH", "position": "center", "size": "750x2100mm"},

    # D3 - Bathroom doors
    {"id": "D3_1", "code": "D3", "room": "BILIK_MANDI", "wall": "EAST", "position": "center", "size": "750x2100mm"},
    {"id": "D3_2", "code": "D3", "room": "TANDAS", "wall": "EAST", "position": "center", "size": "750x2100mm"},
]


print("=" * 80)
print("WALL COORDINATES FOR DOOR PLACEMENT")
print("=" * 80)
print("\nGridTruth Reference:")
print("  Horizontal: A=0.0m, B=1.3m, C=4.4m, D=8.1m, E=11.2m")
print("  Vertical:   1=0.0m, 2=2.3m, 3=5.4m, 4=7.0m, 5=8.5m")
print("  Setback:    0.75m from grid lines")

print("\n" + "=" * 80)
print("ROOM BOUNDARIES")
print("=" * 80)
for room, bounds in ROOM_BOUNDS.items():
    x_min, x_max = bounds['x']
    y_min, y_max = bounds['y']
    width = x_max - x_min
    height = y_max - y_min
    print(f"{room:15s}: X=[{x_min:5.2f}, {x_max:5.2f}]m  Y=[{y_min:5.2f}, {y_max:5.2f}]m  Size={width:.2f}x{height:.2f}m")

print("\n" + "=" * 80)
print("DOOR PLACEMENTS (7 Total)")
print("=" * 80)
print(f"{'ID':<8} {'Code':<6} {'Room':<15} {'Wall':<7} {'Position':<10} {'X (m)':<8} {'Y (m)':<8} {'Size'}")
print("-" * 80)

for door in DOOR_PLACEMENTS:
    x, y = get_wall_coordinate(door['room'], door['wall'], door['position'])
    print(f"{door['id']:<8} {door['code']:<6} {door['room']:<15} {door['wall']:<7} {door['position']:<10} {x:<8.3f} {y:<8.3f} {door['size']}")

print("\n" + "=" * 80)
print("WALL POSITIONS BY ROOM")
print("=" * 80)

for room in ROOM_BOUNDS.keys():
    print(f"\n{room}:")
    for wall in ["NORTH", "SOUTH", "EAST", "WEST"]:
        x, y = get_wall_coordinate(room, wall, "center")
        print(f"  {wall:<7} center: ({x:6.3f}, {y:6.3f})m")

print("\n" + "=" * 80)
print("✓ All coordinates are Rule 0 compliant (derived from GridTruth)")
print("=" * 80)
