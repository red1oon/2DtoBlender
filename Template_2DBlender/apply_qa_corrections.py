#!/usr/bin/env python3
"""
Apply QA corrections to master_template.json
Fixes:
1. Remove W1_2, W1_3, W1_4 (only W1×1 per schedule)
2. Renumber W2/W3 element IDs
3. Add RUANG_MAKAN at C1-D2 (currently BILIK_3 position)
4. Move BILIK_3 to TBD (needs floor plan verification)
5. Add ANJUNG porch to building_envelope
6. Update validation totals
"""

import json
from pathlib import Path

def main():
    # Load master template
    with open('master_template.json', 'r') as f:
        template = json.load(f)

    print("=" * 80)
    print("APPLYING QA CORRECTIONS")
    print("=" * 80)

    # 1. Fix window placements
    print("\n1. Fixing window placements...")
    windows = template['window_placements']
    print(f"   Before: {len(windows)} windows")

    # Keep only W1_1, remove W1_2, W1_3, W1_4
    corrected_windows = []
    w2_counter = 1
    w3_counter = 1

    for win in windows:
        if win['element_id'] == 'W1_1':
            # Keep W1_1 (Dapur only)
            corrected_windows.append(win)
            print(f"   ✓ Kept: {win['element_id']} ({win['room']})")
        elif win['element_id'] in ['W1_2', 'W1_3', 'W1_4']:
            # Remove - not in schedule
            print(f"   ✗ Removed: {win['element_id']} ({win['room']}) - not in Page 8 schedule")
        elif win['code'] == 'W2':
            # Renumber W2
            new_id = f"W2_{w2_counter}"
            win['element_id'] = new_id
            corrected_windows.append(win)
            print(f"   ✓ Renumbered: {new_id} ({win['room']})")
            w2_counter += 1
        elif win['code'] == 'W3':
            # Renumber W3
            new_id = f"W3_{w3_counter}"
            win['element_id'] = new_id
            corrected_windows.append(win)
            print(f"   ✓ Renumbered: {new_id} ({win['room']})")
            w3_counter += 1

    template['window_placements'] = corrected_windows
    print(f"   After: {len(corrected_windows)} windows")

    # 2. Add RUANG_MAKAN, update BILIK_3
    print("\n2. Adding RUANG_MAKAN and updating BILIK_3...")

    # Move current BILIK_3 data to RUANG_MAKAN
    template['room_bounds']['RUANG_MAKAN'] = {
        "grid": "C1-D2",
        "x": [4.4, 8.1],
        "y": [0.0, 2.3],
        "type": "dining",
        "shape": "rectangle",
        "area_m2": 8.51,
        "ubbl_compliant": True,
        "notes": "Central dining room - largest room"
    }
    print("   ✓ Added RUANG_MAKAN at C1-D2 (central position)")

    # Flag BILIK_3 as TBD
    template['room_bounds']['BILIK_3'] = {
        "grid": "TBD",
        "x": [0.0, 0.0],
        "y": [0.0, 0.0],
        "type": "bedroom",
        "shape": "square",
        "area_m2": 0.0,
        "ubbl_compliant": False,
        "notes": "⚠️ POSITION TBD - Needs floor plan verification. Only 2 possible 3.1×3.1 squares exist (B2-C3, D2-E3), both occupied. Awaiting correct grid assignment."
    }
    print("   ✓ BILIK_3 marked as TBD (needs floor plan verification)")

    # 3. Add ANJUNG porch to building_envelope
    print("\n3. Adding ANJUNG porch to building_envelope...")
    template['building_envelope'] = {
        "type": "L-shape",
        "main_body": {
            "description": "Main building footprint (Grid A-E, 1-5)",
            "min": {"x": 0.0, "y": 0.0},
            "max": {"x": 11.2, "y": 8.5},
            "area_m2": 95.2
        },
        "porch": {
            "name": "ANJUNG",
            "description": "Front porch projection",
            "grid": "Approx B1-C0 (outside main grid)",
            "x": [2.3, 5.5],
            "y": [-2.3, 0.0],
            "width_m": 3.2,
            "depth_m": 2.3,
            "area_m2": 7.36,
            "notes": "Porch extends beyond grid boundary (negative Y)"
        },
        "polygon": [
            [0.0, 0.0], [11.2, 0.0], [11.2, 8.5], [0.0, 8.5], [0.0, 0.0]
        ],
        "porch_polygon": [
            [2.3, 0.0], [2.3, -2.3], [5.5, -2.3], [5.5, 0.0]
        ],
        "exterior_walls": {
            "WEST": {"x": 0.0, "y_min": 0.0, "y_max": 8.5, "length_m": 8.5},
            "EAST": {"x": 11.2, "y_min": 0.0, "y_max": 8.5, "length_m": 8.5},
            "SOUTH": {"y": 0.0, "x_min": 0.0, "x_max": 11.2, "length_m": 11.2},
            "NORTH": {"y": 8.5, "x_min": 0.0, "x_max": 11.2, "length_m": 11.2},
            "PORCH_SOUTH": {"y": -2.3, "x_min": 2.3, "x_max": 5.5, "length_m": 3.2}
        },
        "notes": "L-shape with ANJUNG porch. Exterior wall detection must include porch walls."
    }
    print("   ✓ Added ANJUNG porch (L-shape building envelope)")

    # 4. Update validation totals
    print("\n4. Updating validation totals...")
    template['validation']['total_windows'] = 7
    template['validation']['windows_requiring_review'] = 0
    template['validation']['total_floor_area_m2'] = 101.91  # 93.4 + 8.51 (RUANG_MAKAN)
    print("   ✓ Updated: total_windows = 7 (was 10)")

    # 5. Update corrections log
    print("\n5. Updating corrections log...")
    template['corrections_applied'].extend([
        "W1 count: 4 → 1 (Page 8 schedule: Dapur only, not 4 rooms)",
        "W2/W3 element IDs: Renumbered after W1 correction (W2_5-W2_8 → W2_1-W2_4)",
        "Total windows: 10 → 7 (verified against Page 8 OCR)",
        "RUANG_MAKAN: Added at C1-D2 (central dining room, 8.51m²)",
        "BILIK_3: Position TBD - awaiting floor plan verification for correct grid cell",
        "ANJUNG porch: Added to building_envelope (3.2m × 2.3m L-shape extension)",
        "Building envelope: Rectangular → L-shape with porch polygon"
    ])
    print("   ✓ Added 7 corrections to log")

    # 6. Update metadata
    template['metadata']['updated'] = "2025-11-26 (QA corrections applied)"
    template['metadata']['qa_status'] = "⚠️ Partial - BILIK_3 position needs verification"

    # Save corrected template
    output_path = Path('master_template_CORRECTED.json')
    with open(output_path, 'w') as f:
        json.dump(template, f, indent=2)

    print("\n" + "=" * 80)
    print("CORRECTIONS APPLIED SUCCESSFULLY")
    print("=" * 80)
    print(f"\nSaved to: {output_path}")
    print("\nSummary:")
    print(f"  Windows: 10 → 7 (removed W1_2, W1_3, W1_4)")
    print(f"  Rooms: 8 → 9 (added RUANG_MAKAN)")
    print(f"  Building: Rectangular → L-shape (added ANJUNG porch)")
    print(f"  BILIK_3: ⚠️ TBD - needs floor plan verification")
    print("\nNext steps:")
    print("  1. Review master_template_CORRECTED.json")
    print("  2. Verify BILIK_3 position from floor plan")
    print("  3. Rename to master_template.json when approved")
    print("=" * 80)

if __name__ == "__main__":
    main()
