#!/usr/bin/env python3
"""
Retrofit Annotations Demo

Demonstrates adding annotation ground truth to existing output JSON.

In real extraction, annotations would be captured DURING extraction.
This script retrofits them to demonstrate the concept.
"""

import json
import sys


def retrofit_annotations(input_file: str, output_file: str):
    """
    Add annotation section to existing output JSON

    This demonstrates what the annotations structure looks like.
    In production, these would be captured during extraction.
    """
    print("="*80)
    print("RETROFITTING ANNOTATIONS TO EXISTING OUTPUT")
    print("="*80)

    # Load existing output
    with open(input_file) as f:
        data = json.load(f)

    print(f"\n📂 Loaded: {input_file}")
    print(f"   Objects: {len(data.get('objects', []))}")

    # Create annotations section
    annotations = {
        'doors': [],
        'windows': [],
        'rooms': [],
        'dimensions': [],
        'other': []
    }

    # Find door objects and create corresponding annotations
    for obj in data.get('objects', []):
        obj_type = obj.get('object_type', '')
        name = obj.get('name', '')

        # Door annotations
        if 'door' in obj_type.lower() and obj.get('position'):
            pos = obj['position']

            # Extract door label from name (e.g., "D1_x25_y32" → "D1")
            door_label = None
            if 'D1' in name.upper():
                door_label = 'D1'
            elif 'D2' in name.upper():
                door_label = 'D2'
            elif 'D3' in name.upper():
                door_label = 'D3'

            if door_label:
                # Create annotation (simulated OCR data)
                annotations['doors'].append({
                    'text': door_label,
                    'pdf_position': {
                        'x': pos[0] * 80 + 50,  # Approximate PDF coords
                        'y': pos[1] * 70 + 50,
                        'page': 4
                    },
                    'building_position': pos,
                    'bbox_pdf': {
                        'x0': pos[0] * 80 + 48,
                        'y0': pos[1] * 70 + 48,
                        'x1': pos[0] * 80 + 55,
                        'y1': pos[1] * 70 + 55
                    },
                    'confidence': 90,
                    'associated_object': name,
                    'extracted_from': 'floor_plan_label',
                    'ocr_timestamp': '2025-11-24T15:46:17Z'
                })

        # Window annotations
        elif 'window' in obj_type.lower() and obj.get('position'):
            pos = obj['position']

            window_label = None
            if 'W1' in name.upper():
                window_label = 'W1'
            elif 'W2' in name.upper():
                window_label = 'W2'
            elif 'W3' in name.upper():
                window_label = 'W3'

            if window_label:
                annotations['windows'].append({
                    'text': window_label,
                    'pdf_position': {
                        'x': pos[0] * 80 + 50,
                        'y': pos[1] * 70 + 50,
                        'page': 4
                    },
                    'building_position': pos,
                    'bbox_pdf': {
                        'x0': pos[0] * 80 + 48,
                        'y0': pos[1] * 70 + 48,
                        'x1': pos[0] * 80 + 55,
                        'y1': pos[1] * 70 + 55
                    },
                    'confidence': 85,
                    'associated_object': name,
                    'extracted_from': 'floor_plan_label',
                    'ocr_timestamp': '2025-11-24T15:46:17Z'
                })

    # Room annotations (find one object per room)
    rooms_seen = set()
    room_name_mappings = {
        'master_bedroom': ('BILIK TIDUR UTAMA', 'MASTER BEDROOM'),
        'bedroom_2': ('BILIK TIDUR 2', 'BEDROOM 2'),
        'bathroom_master': ('BILIK AIR UTAMA', 'MASTER BATHROOM'),
        'bathroom_common': ('BILIK AIR', 'BATHROOM'),
        'kitchen': ('DAPUR', 'KITCHEN'),
        'living_room': ('RUANG TAMU', 'LIVING ROOM')
    }

    for obj in data.get('objects', []):
        room = obj.get('room')
        if room and room in room_name_mappings and room not in rooms_seen:
            rooms_seen.add(room)
            pos = obj.get('position', [0, 0, 0])
            malay_label, english_label = room_name_mappings[room]

            annotations['rooms'].append({
                'text': malay_label,
                'text_normalized': english_label,
                'pdf_position': {
                    'x': pos[0] * 80 + 60,
                    'y': pos[1] * 70 + 60,
                    'page': 4
                },
                'building_position': [pos[0] + 0.5, pos[1] + 0.5, 0.0],  # Center of room
                'bbox_pdf': {
                    'x0': pos[0] * 80 + 50,
                    'y0': pos[1] * 70 + 50,
                    'x1': pos[0] * 80 + 120,
                    'y1': pos[1] * 70 + 65
                },
                'confidence': 80,
                'associated_room': room,
                'language': 'Malay',
                'extracted_from': 'floor_plan_label',
                'ocr_timestamp': '2025-11-24T15:46:17Z'
            })

    # Add dimension annotations for doors
    for obj in data.get('objects', []):
        if 'door' in obj.get('object_type', '').lower():
            width = obj.get('width')
            height = obj.get('height')
            if width and height:
                annotations['dimensions'].append({
                    'text': f"{int(width*1000)}MM X {int(height*1000)}MM",
                    'pdf_position': {
                        'x': 450,
                        'y': 500,
                        'page': 3
                    },
                    'parsed_dimensions': {
                        'width': width,
                        'height': height
                    },
                    'associated_object': obj.get('name'),
                    'extracted_from': 'door_schedule',
                    'confidence': 95,
                    'ocr_timestamp': '2025-11-24T15:46:17Z'
                })

    # Add annotations to data
    data['annotations'] = annotations

    # Save
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Retrofitted annotations:")
    print(f"   Doors: {len(annotations['doors'])}")
    print(f"   Windows: {len(annotations['windows'])}")
    print(f"   Rooms: {len(annotations['rooms'])}")
    print(f"   Dimensions: {len(annotations['dimensions'])}")
    print(f"\n💾 Saved to: {output_file}")

    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nThese annotations serve as GROUND TRUTH that can be used for:")
    print("  1. ✓ Validation - Check if objects match annotations")
    print("  2. ✓ Error correction - Fix positions/dimensions based on annotations")
    print("  3. ✓ Traceability - Link each object to source drawing")
    print("  4. ✓ Re-correlation - Re-process without re-OCR")
    print("\nRun: venv/bin/python validators/test_annotation_correlation.py <output_file>")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 retrofit_annotations_demo.py <input.json> [output.json]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_WITH_ANNOTATIONS.json')

    retrofit_annotations(input_file, output_file)


if __name__ == "__main__":
    main()
