#!/usr/bin/env python3
"""
Extract Terminal 1 from source DXF files into clean, separate DXF files.
This creates verified source files with only Terminal 1 geometry.
"""

import ezdxf
from pathlib import Path
import json

def extract_terminal1():
    print("="*80)
    print("EXTRACTING TERMINAL 1 FROM SOURCE DXF FILES")
    print("="*80)

    base = Path(__file__).parent.parent
    output_dir = base / "SourceFiles" / "Terminal1_Extracted"
    output_dir.mkdir(exist_ok=True)

    # Load cheatsheet for Terminal 1 identification
    # Terminal 1 = the one with the dome

    # =========================================================================
    # EXTRACT ARC (Architecture)
    # =========================================================================
    print("\n📐 Extracting ARC (Architecture)...")

    arc_source = base / "SourceFiles/TERMINAL1DXF/01 ARCHITECT/2. BANGUNAN TERMINAL 1.dxf"
    arc_doc = ezdxf.readfile(str(arc_source))

    # Find Terminal 1 by looking for the dome
    # First, find all roof entities and their Y-range
    roof_entities = []
    for entity in arc_doc.modelspace():
        if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE']:
            continue
        if not hasattr(entity.dxf, 'layer'):
            continue
        if entity.dxf.layer.upper() not in ['ROOF', 'ROOFSTR', 'CH-ROOF']:
            continue

        if entity.dxftype() == 'CIRCLE':
            roof_entities.append({'y': entity.dxf.center.y, 'x': entity.dxf.center.x})
        elif entity.dxftype() == 'LINE':
            roof_entities.append({'y': entity.dxf.start.y, 'x': entity.dxf.start.x})
        elif entity.dxftype() == 'LWPOLYLINE':
            points = list(entity.get_points())
            if points:
                roof_entities.append({'y': points[0][1], 'x': points[0][0]})

    if roof_entities:
        # Find the cluster with the most roof entities (that's Terminal 1 with dome)
        roof_x = [e['x'] for e in roof_entities]
        roof_y = [e['y'] for e in roof_entities]

        print(f"  Found {len(roof_entities)} roof entities")
        print(f"  Roof X range: [{min(roof_x):.0f}, {max(roof_x):.0f}]")
        print(f"  Roof Y range: [{min(roof_y):.0f}, {max(roof_y):.0f}]")

        # Find the cluster with most roof entities (that's the dome building)
        # Terminal 1 dome is at Y=[-94k, -46k] based on analysis
        roof_y_sorted = sorted(roof_y)

        # Find gaps to identify clusters
        gaps = []
        for i in range(1, len(roof_y_sorted)):
            gap = roof_y_sorted[i] - roof_y_sorted[i-1]
            if gap > 50000:  # 50m gap indicates separate drawings
                gaps.append((roof_y_sorted[i-1], roof_y_sorted[i]))

        # Find cluster boundaries
        cluster_bounds = []
        current_start = min(roof_y)
        for g in gaps:
            cluster_bounds.append((current_start, g[0]))
            current_start = g[1]
        cluster_bounds.append((current_start, max(roof_y)))

        # Find the cluster with most entities
        best_cluster = None
        best_count = 0
        for c in cluster_bounds:
            count = len([y for y in roof_y if c[0] <= y <= c[1]])
            if count > best_count:
                best_count = count
                best_cluster = c

        print(f"  Dome cluster: Y=[{best_cluster[0]:.0f}, {best_cluster[1]:.0f}] with {best_count} roof entities")

        # Terminal 1 plan view - use the dome cluster bounds directly
        # Dome cluster at Y=[-93626, -45926] with 418 roof entities
        arc_bounds = {
            'min_x': -1650000,
            'max_x': -1550000,
            'min_y': best_cluster[0] - 5000,  # Small padding
            'max_y': best_cluster[1] + 5000
        }
    else:
        print("  WARNING: No roof entities found, using default bounds")
        arc_bounds = {'min_x': -1620000, 'max_x': -1560000, 'min_y': -100000, 'max_y': 200000}

    print(f"  Extraction bounds: X=[{arc_bounds['min_x']:.0f}, {arc_bounds['max_x']:.0f}], Y=[{arc_bounds['min_y']:.0f}, {arc_bounds['max_y']:.0f}]")

    # Create new DXF with only Terminal 1 entities
    arc_new = ezdxf.new('R2010')
    arc_msp = arc_new.modelspace()

    # Copy layers
    for layer in arc_doc.layers:
        if layer.dxf.name not in arc_new.layers:
            arc_new.layers.new(name=layer.dxf.name)

    # Copy entities within bounds
    arc_count = 0
    arc_entity_count = 0  # Track ARC entities specifically
    for entity in arc_doc.modelspace():
        if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE', 'ARC', 'POINT']:
            continue

        # Check if entity is within bounds
        in_bounds = False
        if entity.dxftype() == 'CIRCLE':
            c = entity.dxf.center
            in_bounds = (arc_bounds['min_x'] <= c.x <= arc_bounds['max_x'] and
                        arc_bounds['min_y'] <= c.y <= arc_bounds['max_y'])
        elif entity.dxftype() == 'LINE':
            s, e = entity.dxf.start, entity.dxf.end
            in_bounds = ((arc_bounds['min_x'] <= s.x <= arc_bounds['max_x'] and
                         arc_bounds['min_y'] <= s.y <= arc_bounds['max_y']) or
                        (arc_bounds['min_x'] <= e.x <= arc_bounds['max_x'] and
                         arc_bounds['min_y'] <= e.y <= arc_bounds['max_y']))
        elif entity.dxftype() == 'LWPOLYLINE':
            points = list(entity.get_points())
            in_bounds = any(arc_bounds['min_x'] <= p[0] <= arc_bounds['max_x'] and
                           arc_bounds['min_y'] <= p[1] <= arc_bounds['max_y']
                           for p in points)
        elif entity.dxftype() == 'ARC':
            c = entity.dxf.center
            in_bounds = (arc_bounds['min_x'] <= c.x <= arc_bounds['max_x'] and
                        arc_bounds['min_y'] <= c.y <= arc_bounds['max_y'])
            if in_bounds:
                arc_entity_count += 1

        if in_bounds:
            # Copy entity to new DXF
            arc_msp.add_entity(entity.copy())
            arc_count += 1

    arc_output = output_dir / "Terminal1_ARC.dxf"
    arc_new.saveas(str(arc_output))
    print(f"  ✅ Extracted {arc_count} entities ({arc_entity_count} dome arcs) to {arc_output.name}")

    # =========================================================================
    # EXTRACT STR (Structure) - Multiple floor files
    # =========================================================================
    print("\n🏗️  Extracting STR (Structure)...")

    str_files = [
        ('1F', 'T1-2.1_Lyt_1FB_e1P1_240530.dxf'),
        ('3F', 'T1-2.3_Lyt_3FB_e1P1_240530.dxf'),
        ('4F-6F', 'T1-2.4_Lyt_4FB-6FB_e1P1_240530.dxf'),
    ]

    # STR bounds from cheatsheet (native coordinates)
    str_bounds = {'min_x': 2398, 'max_x': 62398, 'min_y': -85755, 'max_y': -45755}

    for floor_id, filename in str_files:
        str_source = base / f"SourceFiles/TERMINAL1DXF/02 STRUCTURE/{filename}"
        if not str_source.exists():
            print(f"  ⚠️  {filename} not found, skipping")
            continue

        str_doc = ezdxf.readfile(str(str_source))

        # Create new DXF
        str_new = ezdxf.new('R2010')
        str_msp = str_new.modelspace()

        # Copy layers
        for layer in str_doc.layers:
            if layer.dxf.name not in str_new.layers:
                str_new.layers.new(name=layer.dxf.name)

        # Copy entities within bounds
        str_count = 0
        for entity in str_doc.modelspace():
            if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE', 'ARC', 'POINT']:
                continue

            in_bounds = False
            if entity.dxftype() == 'CIRCLE':
                c = entity.dxf.center
                in_bounds = (str_bounds['min_x'] <= c.x <= str_bounds['max_x'] and
                            str_bounds['min_y'] <= c.y <= str_bounds['max_y'])
            elif entity.dxftype() == 'LINE':
                s, e = entity.dxf.start, entity.dxf.end
                in_bounds = ((str_bounds['min_x'] <= s.x <= str_bounds['max_x'] and
                             str_bounds['min_y'] <= s.y <= str_bounds['max_y']) or
                            (str_bounds['min_x'] <= e.x <= str_bounds['max_x'] and
                             str_bounds['min_y'] <= e.y <= str_bounds['max_y']))
            elif entity.dxftype() == 'LWPOLYLINE':
                points = list(entity.get_points())
                in_bounds = any(str_bounds['min_x'] <= p[0] <= str_bounds['max_x'] and
                               str_bounds['min_y'] <= p[1] <= str_bounds['max_y']
                               for p in points)
            elif entity.dxftype() == 'ARC':
                c = entity.dxf.center
                in_bounds = (str_bounds['min_x'] <= c.x <= str_bounds['max_x'] and
                            str_bounds['min_y'] <= c.y <= str_bounds['max_y'])

            if in_bounds:
                str_msp.add_entity(entity.copy())
                str_count += 1

        str_output = output_dir / f"Terminal1_STR_{floor_id}.dxf"
        str_new.saveas(str(str_output))
        print(f"  ✅ {floor_id}: Extracted {str_count} entities to {str_output.name}")

    # =========================================================================
    # Save extraction metadata
    # =========================================================================
    metadata = {
        'description': 'Terminal 1 extracted from source DXF files',
        'arc_bounds': arc_bounds,
        'str_bounds': str_bounds,
        'files': {
            'arc': 'Terminal1_ARC.dxf',
            'str_1f': 'Terminal1_STR_1F.dxf',
            'str_3f': 'Terminal1_STR_3F.dxf',
            'str_4f_6f': 'Terminal1_STR_4F-6F.dxf'
        },
        'notes': [
            'ARC and STR are in different coordinate systems',
            'ARC extracted by dome bounds (roof entities)',
            'STR extracted using cheatsheet bounds',
            'These files contain ONLY Terminal 1 (no Terminal 2)'
        ]
    }

    meta_output = output_dir / "extraction_metadata.json"
    with open(meta_output, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n{'='*80}")
    print("✅ EXTRACTION COMPLETE!")
    print(f"📁 Output directory: {output_dir}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    extract_terminal1()
