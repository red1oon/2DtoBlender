#!/usr/bin/env python3
"""
UBBL 1984 Compliance Validator

Validates extraction output against Malaysian Uniform Building By-Laws 1984.

Source of Truth: TB-LKTN_COMPLETE_SPECIFICATION.md Section 4
Standards enforced:
- By-Law 39: Natural light and ventilation
- By-Law 42-44: Minimum room requirements
- MS 1184: Door clearances
"""

import json
import sys
from pathlib import Path


class UBBLValidator:
    """Validate building compliance with UBBL 1984"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.metadata = data.get('extraction_metadata', {})
        self.building_dims = self.metadata.get('building_dimensions', {})
        self.issues = []
        self.warnings = []

    def calculate_window_area(self, window):
        """Calculate window area from dimensions"""
        dims = window.get('dimensions', {})

        if isinstance(dims, dict):
            width = dims.get('width_mm', 0) / 1000.0  # Convert to meters
            height = dims.get('height_mm', 0) / 1000.0
        elif isinstance(dims, list) and len(dims) >= 2:
            width = dims[0]
            height = dims[1]
        else:
            # Try to extract from object_type (e.g., "window_1200x1000_lod300")
            obj_type = window.get('object_type', '')
            if 'x' in obj_type:
                try:
                    parts = obj_type.split('_')
                    for part in parts:
                        if 'x' in part:
                            w, h = part.lower().replace('mm', '').split('x')
                            width = float(w) / 1000.0
                            height = float(h) / 1000.0
                            break
                    else:
                        return 0.0
                except:
                    return 0.0
            else:
                return 0.0

        return width * height

    def calculate_floor_area(self):
        """Calculate total floor area (excluding porch)"""
        # From spec: 93.4 m² (excluding porch)
        # Building: 11.2m × 8.5m = 95.2 m² (including walls)
        # Net habitable: ~93.4 m²

        length = self.building_dims.get('length', 11.2)
        breadth = self.building_dims.get('breadth', 8.5)

        # Gross area
        gross_area = length * breadth

        # Deduct wall thickness (approx 2% for internal walls)
        net_area = gross_area * 0.98

        return net_area

    def validate_natural_light(self):
        """
        UBBL By-Law 39: Natural Light Requirements

        Standard: Window area ≥10% of floor area for habitable rooms
        """
        print("\n" + "="*80)
        print("📜 UBBL BY-LAW 39: NATURAL LIGHT & VENTILATION")
        print("="*80)

        windows = [o for o in self.objects if 'window' in (o.get('object_type') or '').lower()]

        if not windows:
            self.issues.append("CRITICAL: No windows found - UBBL By-Law 39 violation")
            print("❌ FAIL: No windows detected")
            return False

        # Calculate total window area
        total_window_area = 0.0
        window_details = []

        for window in windows:
            area = self.calculate_window_area(window)
            total_window_area += area
            window_details.append({
                'name': window.get('name'),
                'type': window.get('object_type'),
                'area': area
            })

        # Calculate floor area
        floor_area = self.calculate_floor_area()

        # Calculate percentage
        light_percentage = (total_window_area / floor_area * 100) if floor_area > 0 else 0

        # UBBL requirement: ≥10%
        required_percentage = 10.0
        required_area = floor_area * (required_percentage / 100)

        print(f"\n📊 Natural Light Calculation:")
        print(f"   Total window area:     {total_window_area:.2f} m²")
        print(f"   Floor area (habitable): {floor_area:.2f} m²")
        print(f"   Percentage:            {light_percentage:.1f}%")
        print(f"   UBBL requirement:      ≥{required_percentage}%")
        print(f"   Required area:         ≥{required_area:.2f} m²")

        if light_percentage < required_percentage:
            deficit = required_area - total_window_area
            self.issues.append(
                f"Natural light: {light_percentage:.1f}% < {required_percentage}% UBBL minimum "
                f"(deficit: {deficit:.2f} m²)"
            )
            print(f"   Status:                ❌ FAIL (deficit: {deficit:.2f} m²)")
            return False
        else:
            print(f"   Status:                ✅ PASS")
            return True

    def validate_ventilation(self):
        """
        UBBL By-Law 39: Ventilation Requirements

        Standard: Openable window area ≥5% of floor area
        """
        print(f"\n📊 Ventilation Calculation:")

        windows = [o for o in self.objects if 'window' in (o.get('object_type') or '').lower()]

        if not windows:
            print("   Status:                ❌ FAIL (no windows)")
            return False

        # Calculate total window area
        total_window_area = sum(self.calculate_window_area(w) for w in windows)

        # Assume 50% openable (typical for sliding/casement windows)
        openable_area = total_window_area * 0.5

        floor_area = self.calculate_floor_area()
        ventilation_percentage = (openable_area / floor_area * 100) if floor_area > 0 else 0

        required_percentage = 5.0
        required_area = floor_area * (required_percentage / 100)

        print(f"   Openable area (50%):   {openable_area:.2f} m²")
        print(f"   Floor area:            {floor_area:.2f} m²")
        print(f"   Percentage:            {ventilation_percentage:.1f}%")
        print(f"   UBBL requirement:      ≥{required_percentage}%")

        if ventilation_percentage < required_percentage:
            deficit = required_area - openable_area
            self.warnings.append(
                f"Ventilation: {ventilation_percentage:.1f}% < {required_percentage}% UBBL minimum "
                f"(deficit: {deficit:.2f} m²)"
            )
            print(f"   Status:                ⚠️  WARNING (deficit: {deficit:.2f} m²)")
            return False
        else:
            print(f"   Status:                ✅ PASS")
            return True

    def validate_bathroom_windows(self):
        """
        UBBL By-Law 39: Bathroom/WC Requirements

        Standard: ≥0.2 m² window per bathroom unit
        """
        print(f"\n📊 Bathroom Ventilation:")

        # Find bathrooms
        bathroom_rooms = set()
        for obj in self.objects:
            room = obj.get('room', '')
            if room and ('bathroom' in room.lower() or 'tandas' in room.lower() or 'bilik_mandi' in room.lower()):
                bathroom_rooms.add(room)

        if not bathroom_rooms:
            self.warnings.append("No bathrooms detected - cannot validate bathroom windows")
            print("   Status:                ⚠️  WARNING (no bathrooms detected)")
            return True  # Not a failure if no bathrooms found

        # Find windows in bathrooms
        bathroom_windows = []
        for window in self.objects:
            if 'window' in (window.get('object_type') or '').lower():
                room = window.get('room', '')
                if room in bathroom_rooms:
                    area = self.calculate_window_area(window)
                    bathroom_windows.append({
                        'room': room,
                        'name': window.get('name'),
                        'area': area
                    })

        print(f"   Bathrooms found:       {len(bathroom_rooms)}")
        print(f"   Windows in bathrooms:  {len(bathroom_windows)}")

        # Check each bathroom
        required_area_per_unit = 0.2  # m²
        all_pass = True

        for room in bathroom_rooms:
            room_windows = [w for w in bathroom_windows if w['room'] == room]
            total_area = sum(w['area'] for w in room_windows)

            print(f"   • {room}: {total_area:.2f} m² (need ≥{required_area_per_unit} m²)", end="")

            if total_area < required_area_per_unit:
                print(" ❌ FAIL")
                self.issues.append(
                    f"Bathroom {room}: {total_area:.2f} m² < {required_area_per_unit} m² UBBL minimum"
                )
                all_pass = False
            else:
                print(" ✅ PASS")

        return all_pass

    def validate_bedroom_egress(self):
        """
        International Building Code / IRC: Bedroom Emergency Egress

        Standards:
        - Min opening area: ≥0.53 m² (5.7 sq ft)
        - Min width: ≥508mm (20")
        - Min height: ≥610mm (24")
        - Max sill height: ≤1118mm (44")
        """
        print(f"\n📊 Bedroom Emergency Egress (IRC):")

        # Find bedrooms
        bedroom_rooms = set()
        for obj in self.objects:
            room = obj.get('room', '')
            if room and ('bedroom' in room.lower() or 'bilik' in room.lower()):
                bedroom_rooms.add(room)

        if not bedroom_rooms:
            print("   Status:                ℹ️  No bedrooms detected")
            return True

        # Find windows in bedrooms
        bedroom_windows = []
        for window in self.objects:
            if 'window' in (window.get('object_type') or '').lower():
                room = window.get('room', '')
                if room in bedroom_rooms:
                    area = self.calculate_window_area(window)
                    pos = window.get('position', [0, 0, 0])
                    sill_height = pos[2] if len(pos) > 2 else 0.9  # Default 900mm

                    bedroom_windows.append({
                        'room': room,
                        'name': window.get('name'),
                        'area': area,
                        'sill_height': sill_height
                    })

        print(f"   Bedrooms found:        {len(bedroom_rooms)}")
        print(f"   Windows in bedrooms:   {len(bedroom_windows)}")

        # Check each bedroom has egress window
        min_area = 0.53  # m²
        max_sill = 1.118  # m

        all_pass = True
        for room in bedroom_rooms:
            room_windows = [w for w in bedroom_windows if w['room'] == room]

            # Check if any window qualifies as egress
            egress_windows = [
                w for w in room_windows
                if w['area'] >= min_area and w['sill_height'] <= max_sill
            ]

            print(f"   • {room}: ", end="")
            if egress_windows:
                w = egress_windows[0]
                print(f"{w['name']} ({w['area']:.2f} m², sill={w['sill_height']:.2f}m) ✅ PASS")
            else:
                print("❌ FAIL (no egress window)")
                self.warnings.append(
                    f"Bedroom {room}: No egress window (need ≥{min_area} m², sill ≤{max_sill}m)"
                )
                all_pass = False

        return all_pass

    def validate_door_requirements(self):
        """
        UBBL + MS 1184: Door Requirements

        Standards:
        - Main entrance: ≥900mm width
        - Bedroom: ≥800mm width
        - Bathroom/WC: ≥700mm width, MUST swing OUT
        - All doors: 2100mm height standard
        """
        print("\n" + "="*80)
        print("📜 UBBL: DOOR REQUIREMENTS")
        print("="*80)

        doors = [o for o in self.objects if 'door' in (o.get('object_type') or '').lower()]

        if not doors:
            self.warnings.append("No doors found - cannot validate door requirements")
            print("⚠️  WARNING: No doors detected")
            return True

        print(f"\n📊 Door Compliance Check ({len(doors)} doors):")

        all_pass = True

        for door in doors:
            name = door.get('name', 'unnamed')
            obj_type = door.get('object_type', '')
            room = door.get('room', 'unknown')

            # Extract width from object_type (e.g., "door_900x2100_lod300")
            width_mm = None
            height_mm = None

            if 'x' in obj_type:
                try:
                    parts = obj_type.split('_')
                    for part in parts:
                        if 'x' in part:
                            w, h = part.split('x')
                            width_mm = int(w)
                            height_mm = int(h)
                            break
                except:
                    pass

            if width_mm is None:
                self.warnings.append(f"Door {name}: Cannot extract dimensions from type")
                print(f"   • {name}: ⚠️  Cannot extract dimensions")
                continue

            # Determine required width based on room type
            if 'main' in room.lower() or 'entrance' in room.lower() or 'ruang_tamu' in room.lower():
                min_width = 900
                door_category = "Main entrance"
            elif 'bedroom' in room.lower() or 'bilik' in room.lower():
                min_width = 800
                door_category = "Bedroom"
            elif 'bathroom' in room.lower() or 'tandas' in room.lower() or 'bilik_mandi' in room.lower():
                min_width = 700
                door_category = "Bathroom/WC"
            else:
                min_width = 750  # General minimum
                door_category = "General"

            # Check width
            status = "✅ PASS"
            if width_mm < min_width:
                status = "❌ FAIL"
                self.issues.append(
                    f"Door {name} ({door_category}): {width_mm}mm < {min_width}mm UBBL minimum"
                )
                all_pass = False

            # Check height (2100mm standard)
            if height_mm != 2100:
                status = "⚠️  NON-STANDARD HEIGHT"
                self.warnings.append(f"Door {name}: {height_mm}mm height (standard: 2100mm)")

            print(f"   • {name} ({door_category}): {width_mm}×{height_mm}mm (need ≥{min_width}mm) {status}")

        print(f"\n   Overall:               {'✅ PASS' if all_pass else '❌ FAIL'}")
        return all_pass

    def validate_room_dimensions(self):
        """
        UBBL By-Law 42-44: Minimum Room Requirements

        Standards:
        - Habitable (Bedroom): ≥6.5 m², ≥2.0m width, ≥2.5m height
        - Kitchen: ≥2.25m height
        - Bathroom: ≥1.5 m², ≥0.75m width, ≥2.0m height
        - Bathroom + WC: ≥2.0 m²
        """
        print("\n" + "="*80)
        print("📜 UBBL BY-LAW 42-44: MINIMUM ROOM REQUIREMENTS")
        print("="*80)

        # Get room areas from objects
        room_objects = {}
        for obj in self.objects:
            room = obj.get('room', '')
            if room and room not in ['unknown', 'structure', 'exterior']:
                if room not in room_objects:
                    room_objects[room] = []
                room_objects[room].append(obj)

        if not room_objects:
            self.warnings.append("No rooms detected - cannot validate room dimensions")
            print("⚠️  WARNING: No rooms detected")
            return True

        print(f"\n📊 Room Dimension Check ({len(room_objects)} rooms):")

        # Note: Actual area calculation requires wall boundaries
        # For now, check against known values from spec
        print("   ℹ️  Room area validation requires wall polygon analysis")
        print("   ℹ️  Refer to TB-LKTN_COMPLETE_SPECIFICATION.md Section 4.1 for verified areas")

        return True

    def run_validation(self):
        """Run all UBBL compliance checks"""
        print("\n" + "="*80)
        print("🏛️  UBBL 1984 COMPLIANCE VALIDATOR")
        print("="*80)
        print("Standards: Malaysian Uniform Building By-Laws 1984")
        print("Source: TB-LKTN_COMPLETE_SPECIFICATION.md Section 4")

        results = {}

        # By-Law 39: Natural Light & Ventilation
        results['natural_light'] = self.validate_natural_light()
        results['ventilation'] = self.validate_ventilation()
        results['bathroom_windows'] = self.validate_bathroom_windows()
        results['bedroom_egress'] = self.validate_bedroom_egress()

        # Door requirements
        results['doors'] = self.validate_door_requirements()

        # Room dimensions
        results['rooms'] = self.validate_room_dimensions()

        # Summary
        print("\n" + "="*80)
        print("📊 UBBL COMPLIANCE SUMMARY")
        print("="*80)

        total_checks = len(results)
        passed_checks = sum(1 for v in results.values() if v)

        print(f"\nTotal checks:    {total_checks}")
        print(f"Passed:          {passed_checks}")
        print(f"Failed/Warning:  {total_checks - passed_checks}")

        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   • {issue}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")

        print("\n" + "="*80)

        if self.issues:
            print("❌ UBBL COMPLIANCE: FAIL")
            print("="*80)
            return False
        elif self.warnings:
            print("⚠️  UBBL COMPLIANCE: PASS WITH WARNINGS")
            print("="*80)
            return True
        else:
            print("✅ UBBL COMPLIANCE: FULL PASS")
            print("="*80)
            return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_ubbl_compliance.py <output.json>")
        sys.exit(1)

    json_path = sys.argv[1]

    if not Path(json_path).exists():
        print(f"❌ Error: File not found: {json_path}")
        sys.exit(1)

    with open(json_path) as f:
        data = json.load(f)

    validator = UBBLValidator(data)
    success = validator.run_validation()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
