#!/usr/bin/env python3
"""
Normalize Dimension Keys in JSON

Fixes inconsistent dimension schemas across objects:
- width_m → width
- height_m → height
- depth → height
- diameter → width
- Ensures all objects use: width, height, length (or thickness)
"""

import json
import sys


def normalize_dimensions(obj):
    """Normalize dimension keys to standard schema"""

    if 'dimensions' not in obj:
        return obj

    dims = obj['dimensions']

    # Standard schema: width, height, length (or thickness)
    normalized = {}

    # WIDTH (in meters)
    if 'width' in dims:
        normalized['width'] = dims['width']
    elif 'width_m' in dims:
        normalized['width'] = dims['width_m']
    elif 'diameter' in dims:
        normalized['width'] = dims['diameter']
    else:
        normalized['width'] = 0.1  # Default 10cm

    # HEIGHT (in meters)
    if 'height' in dims:
        normalized['height'] = dims['height']
    elif 'height_m' in dims:
        normalized['height'] = dims['height_m']
    elif 'depth' in dims:
        normalized['height'] = dims['depth']
    else:
        normalized['height'] = 0.1  # Default 10cm

    # LENGTH/THICKNESS (in meters)
    if 'length' in dims:
        normalized['length'] = dims['length']
    elif 'thickness' in dims:
        normalized['length'] = dims['thickness']
    elif 'thickness_m' in dims:
        normalized['length'] = dims['thickness_m']
    else:
        normalized['length'] = 0.1  # Default 10cm

    # Replace dimensions with normalized version
    obj['dimensions'] = normalized

    return obj


def normalize_json(input_file, output_file):
    """Normalize all objects in JSON file"""

    print("="*80)
    print("NORMALIZING DIMENSION KEYS")
    print("="*80)
    print()

    with open(input_file) as f:
        data = json.load(f)

    objects = data.get('objects_complete', [])

    print(f"Processing {len(objects)} objects...")
    print()

    # Track changes
    changes = {
        'width_m → width': 0,
        'height_m → height': 0,
        'depth → height': 0,
        'diameter → width': 0,
        'already_standard': 0
    }

    for obj in objects:
        if 'dimensions' not in obj:
            continue

        dims_before = obj['dimensions'].copy()
        obj = normalize_dimensions(obj)
        dims_after = obj['dimensions']

        # Track what changed
        if 'width_m' in dims_before:
            changes['width_m → width'] += 1
        if 'height_m' in dims_before:
            changes['height_m → height'] += 1
        if 'depth' in dims_before and 'height' not in dims_before:
            changes['depth → height'] += 1
        if 'diameter' in dims_before:
            changes['diameter → width'] += 1
        if 'width' in dims_before and 'height' in dims_before:
            changes['already_standard'] += 1

    # Update data
    data['objects_complete'] = objects

    # Save
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print("Normalization Summary:")
    for change_type, count in changes.items():
        if count > 0:
            print(f"  {change_type:30s}: {count:3d}")
    print()

    print(f"✅ Normalized dimensions saved to: {output_file}")
    print()
    print("All objects now use standard schema:")
    print("  - width  (meters)")
    print("  - height (meters)")
    print("  - length (meters)")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 normalize_dimensions.py <input.json> [output.json]")
        print()
        print("Normalizes dimension keys to standard schema (width, height, length)")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_normalized.json')

    normalize_json(input_file, output_file)

    print("="*80)
    print("NORMALIZATION COMPLETE")
    print("="*80)
    print()
    print("Ready for Blender import!")
    print()


if __name__ == "__main__":
    main()
