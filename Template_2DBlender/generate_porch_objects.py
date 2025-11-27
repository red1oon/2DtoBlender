#!/usr/bin/env python3
"""
Stage 5.10: Generate ANJUNG Porch Objects

Rule 0 Compliant: Porch dimensions from TB-LKTN HOUSE.pdf §2.2 specification.

ANJUNG porch: 3.2m × 2.3m L-shape extension south of main building
Polygon: [[2.3, 0.0], [2.3, -2.3], [5.5, -2.3], [5.5, 0.0]]
Area: 7.36 m²
"""

import json
from pathlib import Path

def generate_anjung_porch():
    """Generate ANJUNG porch structure (walls + canopy + floor)."""
    
    # ANJUNG porch polygon from specification
    porch_polygon = [
        [2.3, 0.0],   # Connect to main building SOUTH wall
        [2.3, -2.3],  # Southwest corner
        [5.5, -2.3],  # Southeast corner
        [5.5, 0.0]    # Connect to main building SOUTH wall
    ]
    
    x_min = 2.3
    x_max = 5.5
    y_min = -2.3
    y_max = 0.0
    
    width_m = x_max - x_min  # 3.2m
    depth_m = y_max - y_min  # 2.3m
    area_m2 = width_m * depth_m  # 7.36 m²
    
    objects = []
    
    # Porch walls (3 sides - west, south, east, no north as it connects to main building)
    # Using lightweight walls for porch (75mm instead of 250mm)
    wall_thickness = 0.075
    wall_height = 2.4  # Lower than main building
    
    porch_walls = [
        {
            "id": "PORCH_WALL_WEST",
            "start": [x_min, y_max, 0.0],
            "end": [x_min, y_min, 0.0],
            "wall": "WEST",
            "object_type": "wall_lightweight_75_lod300"
        },
        {
            "id": "PORCH_WALL_SOUTH",
            "start": [x_min, y_min, 0.0],
            "end": [x_max, y_min, 0.0],
            "wall": "SOUTH",
            "object_type": "wall_lightweight_75_lod300"
        },
        {
            "id": "PORCH_WALL_EAST",
            "start": [x_max, y_min, 0.0],
            "end": [x_max, y_max, 0.0],
            "wall": "EAST",
            "object_type": "wall_lightweight_75_lod300"
        }
    ]
    
    for wall in porch_walls:
        objects.append({
            "element_id": wall["id"],
            "object_type": wall["object_type"],
            "position": wall["start"],
            "end_point": wall["end"],
            "thickness": wall_thickness,
            "height": wall_height,
            "phase": "structure",
            "category": "porch",
            "wall_name": wall["wall"],
            "wall_type": "porch_enclosure"
        })
    
    # Porch canopy roof (flat or slight slope)
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
        "object_type": "roof_slab_flat_lod300",  # Reuse slab object
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
    print("STAGE 5.10: GENERATE ANJUNG PORCH OBJECTS")
    print("=" * 80)
    
    print("\n🏡 ANJUNG porch specification:")
    print("   Dimensions: 3.2m × 2.3m")
    print("   Area: 7.36 m²")
    print("   Location: South of main building")
    
    porch_objects, area = generate_anjung_porch()
    
    output_path = Path("output_artifacts/porch_objects.json")
    with open(output_path, 'w') as f:
        json.dump(porch_objects, f, indent=2)
    
    print(f"\n✅ Saved: {output_path}")
    print(f"   Objects: {len(porch_objects)}")
    print(f"   - Walls: 3 (west, south, east)")
    print(f"   - Canopy: 1")
    print(f"   - Floor: 1")
    print(f"   Area: {area:.2f} m²")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
