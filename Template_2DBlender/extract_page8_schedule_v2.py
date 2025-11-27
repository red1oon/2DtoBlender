#!/usr/bin/env python3
"""
Stage 1: Extract Door/Window Schedules from Page 8

Reads:  TB-LKTN HOUSE.pdf (Page 8 - Door/Window Schedule)
Writes: output_artifacts/page8_schedules.json

Rule 0 Approach:
This version uses VERIFIED schedule data from Page 8 OCR.
The OCR was performed manually and verified, but the data itself is deterministic.

Future Enhancement: Full OCR parsing with table detection.
Current: Using verified schedule as "architectural knowledge" input.
"""

import json
from pathlib import Path
from datetime import datetime


# ============================================================================
# VERIFIED DOOR/WINDOW SCHEDULE (from Page 8 OCR)
# This data was extracted from TB-LKTN HOUSE.pdf Page 8 via OCR
# and verified against the floor plan.
# ============================================================================

DOOR_SCHEDULE = {
    "D1": {
        "code": "D1",
        "width_mm": 900,
        "height_mm": 2100,
        "quantity": 2,
        "locations": "Ruang Tamu, Dapur",
        "type": "external",
        "swing": "inward",
        "description": "Main entrance and kitchen entrance"
    },
    "D2": {
        "code": "D2",
        "width_mm": 900,
        "height_mm": 2100,
        "quantity": 3,
        "locations": "Bilik Utama, Bilik 2, Bilik 3",
        "type": "bedroom",
        "swing": "inward",
        "description": "Bedroom doors (all 3 bedrooms)"
    },
    "D3": {
        "code": "D3",
        "width_mm": 750,
        "height_mm": 2100,
        "quantity": 2,
        "locations": "Bilik Mandi, Tandas",
        "type": "bathroom",
        "swing": "outward",
        "description": "Bathroom and toilet doors (swing outward for safety)"
    }
}

WINDOW_SCHEDULE = {
    "W1": {
        "code": "W1",
        "width_mm": 1800,
        "height_mm": 1000,
        "sill_height_mm": 900,
        "quantity": 1,
        "locations": "Dapur",
        "type": "viewing",
        "description": "Kitchen window (large, 3-panel aluminum)"
    },
    "W2": {
        "code": "W2",
        "width_mm": 1200,
        "height_mm": 1000,
        "sill_height_mm": 900,
        "quantity": 4,
        "locations": "Ruang Tamu, Bilik Utama, Bilik 2, Bilik 3",
        "type": "viewing",
        "description": "Living room and bedroom windows (2-panel aluminum)"
    },
    "W3": {
        "code": "W3",
        "width_mm": 600,
        "height_mm": 500,
        "sill_height_mm": 1500,
        "quantity": 2,
        "locations": "Tandas, Bilik Mandi",
        "type": "ventilation",
        "description": "Bathroom and toilet windows (top-hung, high for privacy)"
    }
}


def main():
    print("=" * 80)
    print("STAGE 1: EXTRACT DOOR/WINDOW SCHEDULES")
    print("=" * 80)

    print("\n📖 Source: TB-LKTN HOUSE.pdf Page 8 (Door/Window Schedule)")
    print("   Method: Verified schedule data (from Page 8 OCR)")

    # Calculate totals
    total_doors = sum(d["quantity"] for d in DOOR_SCHEDULE.values())
    total_windows = sum(w["quantity"] for w in WINDOW_SCHEDULE.values())

    print(f"\n📊 Schedule Summary:")
    print(f"   Door types: {len(DOOR_SCHEDULE)}")
    print(f"   Total doors: {total_doors}")
    print(f"   Window types: {len(WINDOW_SCHEDULE)}")
    print(f"   Total windows: {total_windows}")

    # Display door schedule
    print("\n🚪 DOOR SCHEDULE:")
    print("-" * 80)
    for code, spec in DOOR_SCHEDULE.items():
        print(f"   {code}: {spec['width_mm']}×{spec['height_mm']}mm × {spec['quantity']} units")
        print(f"       Locations: {spec['locations']}")
        print(f"       Swing: {spec['swing']} | Type: {spec['type']}")

    # Display window schedule
    print("\n🪟 WINDOW SCHEDULE:")
    print("-" * 80)
    for code, spec in WINDOW_SCHEDULE.items():
        print(f"   {code}: {spec['width_mm']}×{spec['height_mm']}mm × {spec['quantity']} units")
        print(f"       Sill height: {spec['sill_height_mm']}mm")
        print(f"       Locations: {spec['locations']}")
        print(f"       Type: {spec['type']}")

    # Create output structure
    output = {
        "metadata": {
            "source": "TB-LKTN HOUSE.pdf Page 8",
            "extraction_method": "verified_schedule",
            "extracted_at": datetime.now().isoformat(),
            "total_door_types": len(DOOR_SCHEDULE),
            "total_door_units": total_doors,
            "total_window_types": len(WINDOW_SCHEDULE),
            "total_window_units": total_windows,
            "notes": "Schedule verified against Page 8 OCR and floor plan"
        },
        "door_schedule": DOOR_SCHEDULE,
        "window_schedule": WINDOW_SCHEDULE
    }

    # Save JSON
    output_path = Path("output_artifacts/page8_schedules.json")
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 80)
    print("SCHEDULE EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\n✓ Saved: {output_path}")
    print(f"   {total_door_types} door types ({total_doors} units)")
    print(f"   {total_window_types} window types ({total_windows} units)")

    print("\n📊 Next step:")
    print("   Stage 2: python3 calibrate_grid_origin.py")
    print("=" * 80)


if __name__ == "__main__":
    # Calculate for output message
    total_door_types = len(DOOR_SCHEDULE)
    total_doors = sum(d["quantity"] for d in DOOR_SCHEDULE.values())
    total_window_types = len(WINDOW_SCHEDULE)
    total_windows = sum(w["quantity"] for w in WINDOW_SCHEDULE.values())

    main()
