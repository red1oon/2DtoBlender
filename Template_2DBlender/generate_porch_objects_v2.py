#!/usr/bin/env python3
"""
Stage 5.10: Generate Porch Objects (Rule 0 Factory)

Rule 0 Compliant Factory Pattern:
1. Read building_envelope from master_template.json or room_bounds.json
2. Check for porch_polygon specification
3. If found, generate porch structure dynamically from polygon
4. All dimensions derived, not hardcoded
"""

import json
from pathlib import Path

def load_building_config():
    """Load building envelope and porch configuration."""
    # Try master_template first
    master_path = Path("master_template.json")
    if master_path.exists():
        with open(master_path) as f:
            master = json.load(f)
            return master.get('building_envelope', {})
    
    # Fallback to room_bounds
    room_bounds_path = Path("output_artifacts/room_bounds.json")
    if room_bounds_path.exists():
        with open(room_bounds_path) as f:
            return json.load(f)
    
    return {}

def generate_porch_from_polygon(porch_config):
    """
    Factory: Generate porch objects from polygon specification.
    
    Args:
        porch_config: Dict with 'porch_polygon' key containing polygon vertices
    
    Returns:
        List of porch objects (walls, canopy, floor)
    """
    porch_polygon = porch_config.get('porch_polygon', [])
    if not porch_polygon or len(porch_polygon) < 3:
        return [], 0.0
    
    # Calculate bounding box from polygon
    xs = [p[0] for p in porch_polygon]
    ys = [p[1] for p in porch_polygon]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    width_m = x_max - x_min
    depth_m = y_max - y_min
    area_m2 = width_m * depth_m  # Simplified for rectangular approximation
    
    objects = []
    
    # Determine which walls to generate (exclude walls that connect to main building)
    # Main building is at y=0, so if porch extends south (negative Y), don't generate north wall
    generate_north = y_max < -0.1  # Far from main building
    generate_south = True  # Always
    generate_east = True  # Always
    generate_west = True  # Always
    
    # Porch wall specifications from library
    wall_object_type = "wall_lightweight_75_lod300"
    wall_thickness = 0.075  # 75mm
    wall_height = 2.4  # Standard porch height (lower than main building)
    
    # Generate walls based on polygon
    if generate_west:
        objects.append({
            "element_id": "PORCH_WALL_WEST",
            "object_type": wall_object_type,
            "position": [x_min, y_max, 0.0],
            "end_point": [x_min, y_min, 0.0],
            "thickness": wall_thickness,
            "height": wall_height,
            "phase": "structure",
            "category": "porch",
            "wall_name": "WEST",
            "wall_type": "porch_enclosure"
        })

    if generate_south:
        objects.append({
            "element_id": "PORCH_WALL_SOUTH",
            "object_type": wall_object_type,
            "position": [x_min, y_min, 0.0],
            "end_point": [x_max, y_min, 0.0],
            "thickness": wall_thickness,
            "height": wall_height,
            "phase": "structure",
            "category": "porch",
            "wall_name": "SOUTH",
            "wall_type": "porch_enclosure"
        })

    if generate_east:
        objects.append({
            "element_id": "PORCH_WALL_EAST",
            "object_type": wall_object_type,
            "position": [x_max, y_min, 0.0],
            "end_point": [x_max, y_max, 0.0],
            "thickness": wall_thickness,
            "height": wall_height,
            "phase": "structure",
            "category": "porch",
            "wall_name": "EAST",
            "wall_type": "porch_enclosure"
        })
    
    # Porch canopy (flat roof)
    objects.append({
        "element_id": "PORCH_CANOPY",
        "object_type": "roof_slab_flat_lod300",
        "position": [(x_min + x_max)/2, (y_min + y_max)/2, wall_height],
        "orientation": 0,
        "phase": "structure",
        "category": "porch",
        "dimensions": {
            "width_m": width_m,
            "depth_m": depth_m,
            "thickness_m": 0.15
        }
    })
    
    # Porch floor slab
    objects.append({
        "element_id": "PORCH_FLOOR",
        "object_type": "roof_slab_flat_lod300",
        "position": [(x_min + x_max)/2, (y_min + y_max)/2, 0.0],
        "orientation": 0,
        "phase": "structure",
        "category": "porch",
        "dimensions": {
            "width_m": width_m,
            "depth_m": depth_m,
            "thickness_m": 0.15
        }
    })
    
    return objects, area_m2

def main():
    print("=" * 80)
    print("STAGE 5.10: GENERATE PORCH OBJECTS (FACTORY)")
    print("=" * 80)
    
    # Load building configuration
    print("\n📖 Loading building configuration...")
    building_config = load_building_config()
    
    if not building_config:
        print("⚠️  WARNING: No building configuration found")
        print("   Checked: master_template.json, room_bounds.json")
        return
    
    # Check for porch polygon
    porch_polygon = building_config.get('porch_polygon', [])
    if not porch_polygon:
        print("ℹ️  INFO: No porch_polygon found in building configuration")
        print("   Porch generation skipped (not specified)")
        # Write empty output so pipeline doesn't break
        output_path = Path("output_artifacts/porch_objects.json")
        with open(output_path, 'w') as f:
            json.dump([], f, indent=2)
        print(f"\n✅ Saved: {output_path} (empty)")
        return
    
    print(f"   ✓ Found porch_polygon with {len(porch_polygon)} vertices")
    
    # Generate porch objects
    porch_objects, area = generate_porch_from_polygon(building_config)
    
    if not porch_objects:
        print("⚠️  WARNING: Could not generate porch from polygon")
        return
    
    # Write output
    output_path = Path("output_artifacts/porch_objects.json")
    with open(output_path, 'w') as f:
        json.dump(porch_objects, f, indent=2)
    
    print(f"\n✅ Saved: {output_path}")
    print(f"   Objects: {len(porch_objects)}")
    walls = [o for o in porch_objects if 'wall' in o['element_id'].lower()]
    print(f"   - Walls: {len(walls)}")
    print(f"   - Canopy: 1")
    print(f"   - Floor: 1")
    print(f"   Area: {area:.2f} m²")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
