#!/usr/bin/env python3
"""
Stage 5.5: Infer Bathroom Fixtures

Rule 0 Compliant: Calculates fixture positions from room bounds using Malaysian standards.

For each bathroom (BILIK_MANDI, TANDAS):
- Toilet (WC): Against back wall, 0.4m from side wall
- Basin: Adjacent to toilet, 0.7m spacing
- Shower (BILIK_MANDI only): Opposite corner
- Showerhead (BILIK_MANDI only): Above shower position
- Switch: 1.2m height, inside door on wall
- Outlet: 0.3m height, near basin

References:
- MS 1064:1986 (Malaysian Standard for WC installation)
- UBBL 1984 (Clearances and spacing)
"""

import json
from pathlib import Path

# Malaysian standards for bathroom fixtures
FIXTURE_STANDARDS = {
    "toilet": {
        "clearance_front_m": 0.6,  # MS 1064: min 600mm in front
        "clearance_side_m": 0.4,   # MS 1064: min 400mm from wall
        "height_m": 0.4,            # Seat height
        "object_type": "floor_mounted_toilet_lod300"
    },
    "basin": {
        "height_m": 0.85,           # Standard basin height
        "clearance_front_m": 0.5,
        "object_type": "basin_residential_lod300"
    },
    "shower": {
        "size_m": 0.9,              # 900mm shower enclosure
        "object_type": "shower_enclosure_900"
    },
    "showerhead": {
        "height_m": 2.1,
        "object_type": "showerhead_fixed_lod200"
    },
    "switch": {
        "height_m": 1.2,            # Malaysian standard
        "offset_from_door_m": 0.15,
        "object_type": "electrical_switch_weatherproof"
    },
    "outlet": {
        "height_m": 0.3,
        "object_type": "electrical_outlet_weatherproof"
    }
}

def infer_fixtures_for_bathroom(room_name, room_data, is_full_bathroom=True):
    """
    Infer fixture positions for bathroom.
    
    Args:
        room_name: Room identifier
        room_data: Room bounds dict
        is_full_bathroom: True for BILIK_MANDI (shower), False for TANDAS (no shower)
    
    Returns:
        List of fixture placement dicts
    """
    fixtures = []
    
    x_min, x_max = room_data['x']
    y_min, y_max = room_data['y']
    width = room_data['width_m']
    height = room_data['height_m']
    
    # Find door wall (wall with door)
    # Assume door on longest wall for better circulation
    door_wall = "WEST" if width < height else "SOUTH"
    
    # Toilet: Against back wall (opposite door), offset from side
    if door_wall in ["SOUTH", "NORTH"]:
        toilet_x = x_min + FIXTURE_STANDARDS["toilet"]["clearance_side_m"]
        toilet_y = y_max - 0.3 if door_wall == "SOUTH" else y_min + 0.3
        toilet_rotation = 0 if door_wall == "SOUTH" else 180
    else:  # door on EAST/WEST
        toilet_x = x_max - 0.3 if door_wall == "WEST" else x_min + 0.3
        toilet_y = y_min + FIXTURE_STANDARDS["toilet"]["clearance_side_m"]
        toilet_rotation = 90 if door_wall == "WEST" else 270
    
    fixtures.append({
        "element_id": f"{room_name}_TOILET",
        "object_type": FIXTURE_STANDARDS["toilet"]["object_type"],
        "position": [toilet_x, toilet_y, FIXTURE_STANDARDS["toilet"]["height_m"]],
        "orientation": toilet_rotation,
        "room": room_name,
        "phase": "mep",
        "category": "plumbing"
    })
    
    # Basin: Adjacent to toilet
    basin_offset = 0.7  # 700mm spacing from toilet
    if door_wall in ["SOUTH", "NORTH"]:
        basin_x = toilet_x + basin_offset
        basin_y = toilet_y
        basin_rotation = toilet_rotation
    else:
        basin_x = toilet_x
        basin_y = toilet_y + basin_offset
        basin_rotation = toilet_rotation
    
    fixtures.append({
        "element_id": f"{room_name}_BASIN",
        "object_type": FIXTURE_STANDARDS["basin"]["object_type"],
        "position": [basin_x, basin_y, FIXTURE_STANDARDS["basin"]["height_m"]],
        "orientation": basin_rotation,
        "room": room_name,
        "phase": "mep",
        "category": "plumbing"
    })
    
    # Shower (only in full bathroom)
    if is_full_bathroom:
        # Shower in opposite corner from toilet
        shower_size = FIXTURE_STANDARDS["shower"]["size_m"]
        if door_wall in ["SOUTH", "NORTH"]:
            shower_x = x_max - shower_size
            shower_y = y_min if door_wall == "SOUTH" else y_max - shower_size
        else:
            shower_x = x_min if door_wall == "WEST" else x_max - shower_size
            shower_y = y_max - shower_size
        
        fixtures.append({
            "element_id": f"{room_name}_SHOWER",
            "object_type": FIXTURE_STANDARDS["shower"]["object_type"],
            "position": [shower_x, shower_y, 0.0],
            "orientation": 0,
            "room": room_name,
            "phase": "mep",
            "category": "plumbing"
        })
        
        # Showerhead above shower center
        fixtures.append({
            "element_id": f"{room_name}_SHOWERHEAD",
            "object_type": FIXTURE_STANDARDS["showerhead"]["object_type"],
            "position": [shower_x + shower_size/2, shower_y + shower_size/2, FIXTURE_STANDARDS["showerhead"]["height_m"]],
            "orientation": 180,
            "room": room_name,
            "phase": "mep",
            "category": "plumbing"
        })
    
    # Switch: Near door, 1.2m height
    switch_offset = FIXTURE_STANDARDS["switch"]["offset_from_door_m"]
    if door_wall == "SOUTH":
        switch_pos = [x_min + switch_offset, y_min + 0.1, FIXTURE_STANDARDS["switch"]["height_m"]]
    elif door_wall == "NORTH":
        switch_pos = [x_min + switch_offset, y_max - 0.1, FIXTURE_STANDARDS["switch"]["height_m"]]
    elif door_wall == "WEST":
        switch_pos = [x_min + 0.1, y_min + switch_offset, FIXTURE_STANDARDS["switch"]["height_m"]]
    else:  # EAST
        switch_pos = [x_max - 0.1, y_min + switch_offset, FIXTURE_STANDARDS["switch"]["height_m"]]
    
    fixtures.append({
        "element_id": f"{room_name}_SWITCH",
        "object_type": FIXTURE_STANDARDS["switch"]["object_type"],
        "position": switch_pos,
        "orientation": 0,
        "room": room_name,
        "phase": "mep",
        "category": "electrical"
    })
    
    # Outlet: Near basin, 0.3m height
    outlet_pos = [basin_x + 0.3, basin_y, FIXTURE_STANDARDS["outlet"]["height_m"]]
    fixtures.append({
        "element_id": f"{room_name}_OUTLET",
        "object_type": FIXTURE_STANDARDS["outlet"]["object_type"],
        "position": outlet_pos,
        "orientation": 0,
        "room": room_name,
        "phase": "mep",
        "category": "electrical"
    })
    
    return fixtures

def main():
    print("=" * 80)
    print("STAGE 5.5: INFER BATHROOM FIXTURES")
    print("=" * 80)
    
    # Load room bounds
    room_bounds_path = Path("output_artifacts/room_bounds.json")
    if not room_bounds_path.exists():
        print("❌ ERROR: room_bounds.json not found")
        return
    
    with open(room_bounds_path) as f:
        room_bounds = json.load(f)
    
    # Process bathrooms
    all_fixtures = []
    
    for room_name, room_data in room_bounds.items():
        room_type = room_data.get('type', '')
        
        if room_type == 'bathroom':
            print(f"\n🚿 Processing: {room_name} (full bathroom)")
            fixtures = infer_fixtures_for_bathroom(room_name, room_data, is_full_bathroom=True)
            all_fixtures.extend(fixtures)
            print(f"   ✅ Generated {len(fixtures)} fixtures")
            
        elif room_type == 'toilet':
            print(f"\n🚽 Processing: {room_name} (toilet only)")
            fixtures = infer_fixtures_for_bathroom(room_name, room_data, is_full_bathroom=False)
            all_fixtures.extend(fixtures)
            print(f"   ✅ Generated {len(fixtures)} fixtures")
    
    # Write output
    output_path = Path("output_artifacts/bathroom_fixtures.json")
    with open(output_path, 'w') as f:
        json.dump(all_fixtures, f, indent=2)
    
    print(f"\n✅ Saved: {output_path}")
    print(f"   Total fixtures: {len(all_fixtures)}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
