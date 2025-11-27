#!/usr/bin/env python3
"""
Stage 5.9: Generate Roof Objects

Converts roof_geometry.json to placeable roof objects.
Rule 0 compliant: All positions calculated from building envelope + Malaysian standards.
"""

import json
from pathlib import Path
import math

def generate_gable_roof_objects(roof_data):
    """Generate objects for gable roof (2 slopes + gutters + fascia)."""
    main_roof = roof_data.get('main_roof', {})
    
    # Extract roof parameters
    outline = main_roof.get('outline_m', [])
    ridge_lines = main_roof.get('ridge_lines', [])
    overhangs = main_roof.get('overhangs_m', {})
    eave_height = main_roof.get('height_to_eave_m', 2.7)
    ridge_height = main_roof.get('height_to_ridge_m', 4.32)
    slope = main_roof.get('slope_degrees', 25)
    
    if not outline or not ridge_lines:
        return []
    
    # Calculate outline bounds
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    # Ridge line (center of gable) - pure math from ridge endpoints
    ridge = ridge_lines[0] if ridge_lines else {}
    ridge_x = ridge.get('start', [0, 0])[0]

    # Calculate ridge Y position (center of footprint, not edge)
    # For gable roof, ridge runs along centerline from start to end
    ridge_y_start = ridge.get('start', [0, 0])[1]
    ridge_y_end = ridge.get('end', [0, 0])[1]
    ridge_y_center = (ridge_y_start + ridge_y_end) / 2

    objects = []

    # North slope (from ridge center to north eave)
    north_slope_width = x_max - x_min  # Full width
    north_slope_length = (y_max - ridge_y_center) / math.cos(math.radians(slope))

    objects.append({
        "element_id": "ROOF_NORTH_SLOPE",
        "object_type": "roof_tile_9.7x7_lod300",
        "position": [ridge_x, y_max, eave_height],
        "orientation": 0,
        "phase": "structure",
        "category": "roof",
        "dimensions": {
            "width_m": north_slope_width,
            "length_m": north_slope_length,
            "slope_degrees": slope
        },
        "ridge_point": [ridge_x, ridge_y_center, ridge_height],
        "eave_point": [ridge_x, y_max, eave_height]
    })

    # South slope (from ridge center to south eave)
    south_slope_length = (ridge_y_center - y_min) / math.cos(math.radians(slope))
    
    objects.append({
        "element_id": "ROOF_SOUTH_SLOPE",
        "object_type": "roof_tile_9.7x7_lod300",
        "position": [ridge_x, y_min, eave_height],
        "orientation": 180,
        "phase": "structure",
        "category": "roof",
        "dimensions": {
            "width_m": north_slope_width,
            "length_m": south_slope_length,
            "slope_degrees": slope
        },
        "ridge_point": [ridge_x, ridge_y_center, ridge_height],
        "eave_point": [ridge_x, y_min, eave_height]
    })
    
    # Gutters on all 4 sides
    gutter_height = eave_height
    
    gutters = [
        {"id": "GUTTER_NORTH", "start": [x_min, y_max, gutter_height], "end": [x_max, y_max, gutter_height], "wall": "NORTH"},
        {"id": "GUTTER_SOUTH", "start": [x_min, y_min, gutter_height], "end": [x_max, y_min, gutter_height], "wall": "SOUTH"},
        {"id": "GUTTER_EAST", "start": [x_max, y_min, gutter_height], "end": [x_max, y_max, gutter_height], "wall": "EAST"},
        {"id": "GUTTER_WEST", "start": [x_min, y_min, gutter_height], "end": [x_min, y_max, gutter_height], "wall": "WEST"},
    ]
    
    for gutter in gutters:
        objects.append({
            "element_id": gutter["id"],
            "object_type": "roof_gutter_100_lod300",
            "position": gutter["start"],
            "end_point": gutter["end"],
            "orientation": 0 if gutter["wall"] in ["NORTH", "SOUTH"] else 90,
            "phase": "structure",
            "category": "roof",
            "wall": gutter["wall"]
        })
    
    # Fascia boards
    for gutter in gutters:
        objects.append({
            "element_id": gutter["id"].replace("GUTTER", "FASCIA"),
            "object_type": "roof_fascia_200_lod300",
            "position": gutter["start"],
            "end_point": gutter["end"],
            "orientation": 0 if gutter["wall"] in ["NORTH", "SOUTH"] else 90,
            "phase": "structure",
            "category": "roof",
            "wall": gutter["wall"]
        })
    
    return objects

def main():
    print("=" * 80)
    print("STAGE 5.9: GENERATE ROOF OBJECTS")
    print("=" * 80)
    
    # Load roof geometry
    roof_path = Path("output_artifacts/roof_geometry.json")
    if not roof_path.exists():
        print("❌ ERROR: roof_geometry.json not found")
        return
    
    with open(roof_path) as f:
        roof_data = json.load(f)
    
    # Generate roof objects
    roof_type = roof_data.get('main_roof', {}).get('type', '')
    print(f"\n🏠 Roof type: {roof_type}")
    
    if roof_type == "gable_ns":
        roof_objects = generate_gable_roof_objects(roof_data)
    else:
        print(f"⚠️  WARNING: Roof type '{roof_type}' not supported yet")
        roof_objects = []
    
    # Write output
    output_path = Path("output_artifacts/roof_objects.json")
    with open(output_path, 'w') as f:
        json.dump(roof_objects, f, indent=2)
    
    print(f"\n✅ Saved: {output_path}")
    print(f"   Roof objects: {len(roof_objects)}")
    print(f"   - Slopes: 2")
    print(f"   - Gutters: 4")
    print(f"   - Fascia: 4")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
