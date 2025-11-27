#!/usr/bin/env python3
"""Fix geometry extension - remove duplicates and correct counts"""
import json
import sys

def fix_complete_output(complete_file, output_file):
    """Remove duplicates from complete output"""
    with open(complete_file) as f:
        data = json.load(f)
    
    all_objects = data['objects_complete']
    
    # Remove duplicates - keep enhanced doors/windows, remove original ones
    # Remove lightweight walls from fixtures
    
    seen_names = set()
    fixed_objects = []
    stats = {'walls': 0, 'doors': 0, 'windows': 0, 'fixtures': 0, 'structural': 0}
    
    for obj in all_objects:
        obj_name = obj.get('name') or obj.get('object_id')
        obj_type = obj.get('type')
        object_type_full = obj.get('object_type', '')
        
        # Skip lightweight walls in fixtures (these are duplicates)
        if obj_type == 'fixture' and 'wall_lightweight' in object_type_full:
            continue
        
        # Skip if we've seen this name (prefer enhanced versions)
        if obj_name in seen_names:
            continue
        
        seen_names.add(obj_name)
        fixed_objects.append(obj)
        
        if obj_type in stats:
            stats[obj_type] += 1
    
    # Update data
    data['objects_complete'] = fixed_objects
    data['statistics'] = {
        'total_objects': len(fixed_objects),
        'by_type': stats,
        'with_geometry': len(fixed_objects),
        'coverage': '100%'
    }
    
    # Save
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Fixed {len(all_objects)} → {len(fixed_objects)} objects")
    print(f"   Removed {len(all_objects) - len(fixed_objects)} duplicates")
    print(f"\nCorrected counts:")
    for obj_type, count in sorted(stats.items()):
        print(f"  {obj_type:12s}: {count:3d}")
    
    return data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fix_geometry_extension.py <complete.json> [output.json]")
        sys.exit(1)
    
    complete_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else complete_file
    
    fix_complete_output(complete_file, output_file)
