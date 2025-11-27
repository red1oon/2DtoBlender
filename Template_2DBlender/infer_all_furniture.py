#!/usr/bin/env python3
"""
Stage 5.6-5.8: Infer All Furniture and Fixtures

Rule 0 Compliant: Positions calculated from room bounds + Malaysian standards.

Kitchen: sink, cabinets, stove, refrigerator, switches, outlets
Bedrooms: bed, wardrobe, switches, outlets  
Living: sofa, coffee_table, tv_point, switches, outlets
Dining: dining_table, switches
Laundry: washing_machine, sink, outlet
"""

import json
from pathlib import Path

# Malaysian/Asian furniture standards
FURNITURE_STANDARDS = {
    # Kitchen
    "kitchen_sink": {"object_type": "kitchen_sink_single_bowl_lod200", "height_m": 0.9, "size": [0.6, 0.5]},
    "kitchen_cabinet_base": {"object_type": "kitchen_base_cabinet_900_lod300", "height_m": 0.9, "width": 0.9},
    "kitchen_cabinet_wall": {"object_type": "kitchen_wall_cabinet_900_lod300", "height_m": 1.5, "width": 0.9},
    "stove": {"object_type": "range_hood_wall", "height_m": 0.9, "size": [0.6, 0.6]},  # placeholder
    "refrigerator": {"object_type": "refrigerator", "height_m": 0, "size": [0.7, 0.7]},
    
    # Bedroom
    "bed_queen": {"object_type": "bed_queen_lod300", "height_m": 0.5, "size": [1.5, 2.0]},
    "wardrobe": {"object_type": "furniture_wardrobe", "height_m": 0, "size": [1.2, 0.6]},
    
    # Living
    "sofa_2seater": {"object_type": "sofa_2seater_lod300", "height_m": 0.4, "size": [1.5, 0.8]},
    "coffee_table": {"object_type": "coffee_table", "height_m": 0.4, "size": [1.0, 0.6]},
    "tv_point": {"object_type": "ict_tv_point", "height_m": 1.2, "size": [0.1, 0.1]},
    
    # Dining
    "dining_table_6seat": {"object_type": "dining_table_6seat", "height_m": 0.75, "size": [1.8, 0.9]},
    
    # Electrical (all rooms)
    "switch_standard": {"object_type": "electrical_switch_dimmer", "height_m": 1.2},
    "outlet_standard": {"object_type": "electrical_outlet_double", "height_m": 0.3},
}

def infer_kitchen_furniture(room_name, room_data):
    """Infer kitchen furniture along walls."""
    fixtures = []
    x_min, x_max = room_data['x']
    y_min, y_max = room_data['y']
    width = room_data['width_m']
    
    # Kitchen layout: sink and cabinets along one wall
    # Choose longest exterior wall
    exterior_walls = room_data.get('exterior_walls', [])
    primary_wall = exterior_walls[0] if exterior_walls else "SOUTH"
    
    # Sink position (center of wall)
    if primary_wall in ["SOUTH", "NORTH"]:
        sink_y = y_min if primary_wall == "SOUTH" else y_max
        sink_x = (x_min + x_max) / 2
        rot = 0
    else:
        sink_x = x_min if primary_wall == "WEST" else x_max
        sink_y = (y_min + y_max) / 2
        rot = 90
    
    fixtures.append({
        "element_id": f"{room_name}_SINK",
        "object_type": FURNITURE_STANDARDS["kitchen_sink"]["object_type"],
        "position": [sink_x, sink_y, FURNITURE_STANDARDS["kitchen_sink"]["height_m"]],
        "orientation": rot,
        "room": room_name,
        "phase": "furniture",
        "category": "kitchen"
    })
    
    # Cabinet (left of sink)
    fixtures.append({
        "element_id": f"{room_name}_CABINET_BASE",
        "object_type": FURNITURE_STANDARDS["kitchen_cabinet_base"]["object_type"],
        "position": [sink_x - 1.0, sink_y, FURNITURE_STANDARDS["kitchen_cabinet_base"]["height_m"]],
        "orientation": rot,
        "room": room_name,
        "phase": "furniture",
        "category": "kitchen"
    })
    
    # Outlets (2x near counter)
    for i in range(2):
        fixtures.append({
            "element_id": f"{room_name}_OUTLET_{i+1}",
            "object_type": FURNITURE_STANDARDS["outlet_standard"]["object_type"],
            "position": [sink_x + 0.5 * (i-0.5), sink_y, FURNITURE_STANDARDS["outlet_standard"]["height_m"] + 0.6],
            "orientation": 0,
            "room": room_name,
            "phase": "mep",
            "category": "electrical"
        })
    
    # Switch near door
    fixtures.append({
        "element_id": f"{room_name}_SWITCH",
        "object_type": FURNITURE_STANDARDS["switch_standard"]["object_type"],
        "position": [x_min + 0.15, y_min + 0.1, FURNITURE_STANDARDS["switch_standard"]["height_m"]],
        "orientation": 0,
        "room": room_name,
        "phase": "mep",
        "category": "electrical"
    })
    
    return fixtures

def infer_bedroom_furniture(room_name, room_data):
    """Infer bedroom furniture (bed, wardrobe, electrical)."""
    fixtures = []
    x_min, x_max = room_data['x']
    y_min, y_max = room_data['y']
    width = room_data['width_m']
    height = room_data['height_m']
    
    # Bed: Center against longest wall
    bed_size = FURNITURE_STANDARDS["bed_queen"]["size"]
    if width > height:
        bed_x = (x_min + x_max) / 2
        bed_y = y_min + 0.5
        bed_rot = 0
    else:
        bed_x = x_min + 0.5
        bed_y = (y_min + y_max) / 2
        bed_rot = 90
    
    fixtures.append({
        "element_id": f"{room_name}_BED",
        "object_type": FURNITURE_STANDARDS["bed_queen"]["object_type"],
        "position": [bed_x, bed_y, FURNITURE_STANDARDS["bed_queen"]["height_m"]],
        "orientation": bed_rot,
        "room": room_name,
        "phase": "furniture",
        "category": "bedroom"
    })
    
    # Wardrobe: Opposite wall from bed
    if width > height:
        wardrobe_x = (x_min + x_max) / 2
        wardrobe_y = y_max - 0.3
    else:
        wardrobe_x = x_max - 0.3
        wardrobe_y = (y_min + y_max) / 2
    
    fixtures.append({
        "element_id": f"{room_name}_WARDROBE",
        "object_type": FURNITURE_STANDARDS["wardrobe"]["object_type"],
        "position": [wardrobe_x, wardrobe_y, FURNITURE_STANDARDS["wardrobe"]["height_m"]],
        "orientation": bed_rot + 180,
        "room": room_name,
        "phase": "furniture",
        "category": "bedroom"
    })
    
    # Switch + outlet near door
    fixtures.extend([
        {
            "element_id": f"{room_name}_SWITCH",
            "object_type": FURNITURE_STANDARDS["switch_standard"]["object_type"],
            "position": [x_min + 0.15, y_min + 0.1, FURNITURE_STANDARDS["switch_standard"]["height_m"]],
            "orientation": 0,
            "room": room_name,
            "phase": "mep",
            "category": "electrical"
        },
        {
            "element_id": f"{room_name}_OUTLET",
            "object_type": FURNITURE_STANDARDS["outlet_standard"]["object_type"],
            "position": [x_min + 0.5, y_min + 0.1, FURNITURE_STANDARDS["outlet_standard"]["height_m"]],
            "orientation": 0,
            "room": room_name,
            "phase": "mep",
            "category": "electrical"
        }
    ])
    
    return fixtures

def infer_living_furniture(room_name, room_data):
    """Infer living room furniture."""
    fixtures = []
    x_min, x_max = room_data['x']
    y_min, y_max = room_data['y']
    
    # Sofa: Center of room
    sofa_x = (x_min + x_max) / 2
    sofa_y = (y_min + y_max) / 2
    
    fixtures.append({
        "element_id": f"{room_name}_SOFA",
        "object_type": FURNITURE_STANDARDS["sofa_2seater"]["object_type"],
        "position": [sofa_x, sofa_y, FURNITURE_STANDARDS["sofa_2seater"]["height_m"]],
        "orientation": 0,
        "room": room_name,
        "phase": "furniture",
        "category": "living"
    })
    
    # Coffee table in front
    fixtures.append({
        "element_id": f"{room_name}_COFFEE_TABLE",
        "object_type": FURNITURE_STANDARDS["coffee_table"]["object_type"],
        "position": [sofa_x, sofa_y - 1.0, FURNITURE_STANDARDS["coffee_table"]["height_m"]],
        "orientation": 0,
        "room": room_name,
        "phase": "furniture",
        "category": "living"
    })
    
    # TV point on wall
    fixtures.append({
        "element_id": f"{room_name}_TV",
        "object_type": FURNITURE_STANDARDS["tv_point"]["object_type"],
        "position": [sofa_x, y_min + 0.1, FURNITURE_STANDARDS["tv_point"]["height_m"]],
        "orientation": 0,
        "room": room_name,
        "phase": "mep",
        "category": "electrical"
    })
    
    # Switch + outlets
    fixtures.extend([
        {
            "element_id": f"{room_name}_SWITCH",
            "object_type": FURNITURE_STANDARDS["switch_standard"]["object_type"],
            "position": [x_min + 0.15, y_min + 0.1, FURNITURE_STANDARDS["switch_standard"]["height_m"]],
            "orientation": 0,
            "room": room_name,
            "phase": "mep",
            "category": "electrical"
        },
        {
            "element_id": f"{room_name}_OUTLET_1",
            "object_type": FURNITURE_STANDARDS["outlet_standard"]["object_type"],
            "position": [x_min + 0.5, y_min + 0.1, FURNITURE_STANDARDS["outlet_standard"]["height_m"]],
            "orientation": 0,
            "room": room_name,
            "phase": "mep",
            "category": "electrical"
        }
    ])
    
    return fixtures

def infer_dining_furniture(room_name, room_data):
    """Infer dining room furniture."""
    x_min, x_max = room_data['x']
    y_min, y_max = room_data['y']
    
    # Dining table: center
    return [{
        "element_id": f"{room_name}_TABLE",
        "object_type": FURNITURE_STANDARDS["dining_table_6seat"]["object_type"],
        "position": [(x_min + x_max)/2, (y_min + y_max)/2, FURNITURE_STANDARDS["dining_table_6seat"]["height_m"]],
        "orientation": 0,
        "room": room_name,
        "phase": "furniture",
        "category": "dining"
    }, {
        "element_id": f"{room_name}_SWITCH",
        "object_type": FURNITURE_STANDARDS["switch_standard"]["object_type"],
        "position": [x_min + 0.15, y_min + 0.1, FURNITURE_STANDARDS["switch_standard"]["height_m"]],
        "orientation": 0,
        "room": room_name,
        "phase": "mep",
        "category": "electrical"
    }]

def main():
    print("=" * 80)
    print("STAGES 5.6-5.8: INFER ALL FURNITURE & FIXTURES")
    print("=" * 80)
    
    room_bounds_path = Path("output_artifacts/room_bounds.json")
    if not room_bounds_path.exists():
        print("❌ ERROR: room_bounds.json not found")
        return
    
    with open(room_bounds_path) as f:
        room_bounds = json.load(f)
    
    all_furniture = []
    
    for room_name, room_data in room_bounds.items():
        room_type = room_data.get('type', '')
        
        if room_type == 'kitchen':
            print(f"\n🍳 {room_name} (kitchen)")
            furniture = infer_kitchen_furniture(room_name, room_data)
            all_furniture.extend(furniture)
            print(f"   ✅ {len(furniture)} items")
            
        elif room_type == 'bedroom':
            print(f"\n🛏️  {room_name} (bedroom)")
            furniture = infer_bedroom_furniture(room_name, room_data)
            all_furniture.extend(furniture)
            print(f"   ✅ {len(furniture)} items")
            
        elif room_type == 'living':
            print(f"\n🛋️  {room_name} (living)")
            furniture = infer_living_furniture(room_name, room_data)
            all_furniture.extend(furniture)
            print(f"   ✅ {len(furniture)} items")
            
        elif room_type == 'dining':
            print(f"\n🍽️  {room_name} (dining)")
            furniture = infer_dining_furniture(room_name, room_data)
            all_furniture.extend(furniture)
            print(f"   ✅ {len(furniture)} items")
    
    output_path = Path("output_artifacts/furniture_fixtures.json")
    with open(output_path, 'w') as f:
        json.dump(all_furniture, f, indent=2)
    
    print(f"\n✅ Saved: {output_path}")
    print(f"   Total items: {len(all_furniture)}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
