#!/usr/bin/env python3
"""
Stage 5.11: Generate Floor Slab

Rule 0 Compliant Factory:
Reads building_envelope from master_template.json
Generates ground floor slab covering main building + porch
"""

import json
from pathlib import Path

def load_building_envelope():
    """Load building envelope from master_template or room_bounds."""
    master_path = Path("master_template.json")
    if master_path.exists():
        with open(master_path) as f:
            master = json.load(f)
            return master.get('building_envelope', {})
    return {}

def generate_floor_slab_from_envelope(envelope):
    """Generate floor slab object from building envelope."""
    if not envelope:
        return []
    
    # Get main body bounds
    main_body = envelope.get('main_body', {})
    porch = envelope.get('porch', {})
    
    if not main_body:
        return []
    
    min_coords = main_body.get('min', {})
    max_coords = main_body.get('max', {})
    
    x_min = min_coords.get('x', 0.0)
    x_max = max_coords.get('x', 0.0)
    y_min = min_coords.get('y', 0.0)
    y_max = max_coords.get('y', 0.0)
    
    # Extend to include porch if present
    if porch:
        porch_polygon = porch.get('polygon', [])
        if porch_polygon:
            porch_ys = [p[1] for p in porch_polygon]
            y_min = min(y_min, min(porch_ys))  # Extend south for porch
    
    width_m = x_max - x_min
    depth_m = y_max - y_min
    
    # Floor slab object
    floor_slab = {
        "element_id": "FLOOR_SLAB_GROUND",
        "object_type": "roof_slab_flat_lod300",  # Reuse flat slab geometry
        "position": [(x_min + x_max)/2, (y_min + y_max)/2, -0.15],  # Below ground level
        "orientation": 0,
        "phase": "structure",
        "category": "floor",
        "dimensions": {
            "width_m": width_m,
            "depth_m": depth_m,
            "thickness_m": 0.15  # 150mm standard ground slab
        },
        "description": "Ground floor slab (entire building footprint)"
    }
    
    return [floor_slab]

def main():
    print("=" * 80)
    print("STAGE 5.11: GENERATE FLOOR SLAB (FACTORY)")
    print("=" * 80)
    
    print("\n📖 Loading building envelope...")
    envelope = load_building_envelope()
    
    if not envelope:
        print("⚠️  WARNING: No building envelope found")
        return
    
    print("   ✓ Building envelope loaded")
    
    # Generate floor slab
    floor_slab = generate_floor_slab_from_envelope(envelope)
    
    if not floor_slab:
        print("❌ ERROR: Could not generate floor slab")
        return
    
    # Write output
    output_path = Path("output_artifacts/floor_slab.json")
    with open(output_path, 'w') as f:
        json.dump(floor_slab, f, indent=2)
    
    slab = floor_slab[0]
    dims = slab['dimensions']
    print(f"\n✅ Saved: {output_path}")
    print(f"   Objects: 1")
    print(f"   Dimensions: {dims['width_m']:.2f}m × {dims['depth_m']:.2f}m × {dims['thickness_m']:.2f}m thick")
    print(f"   Area: {dims['width_m'] * dims['depth_m']:.2f} m²")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
