#!/usr/bin/env python3
"""
Extract minimal "fingerprint" of Terminal 1 - key identifying features only.
Captures: corners, dome outline, column positions, boundary markers.
"""

import ezdxf
import json
from pathlib import Path
from collections import defaultdict

def main():
    print("="*60)
    print("EXTRACTING TERMINAL 1 FINGERPRINT")
    print("="*60)

    base = Path(__file__).parent.parent
    arc_source = base / "SourceFiles/TERMINAL1DXF/01 ARCHITECT/2. BANGUNAN TERMINAL 1.dxf"

    doc = ezdxf.readfile(str(arc_source))

    x_min, x_max = -1650000, -1550000

    fingerprint = {
        'corners': [],      # Building corner points
        'dome_arcs': [],    # Dome curve segments
        'columns': [],      # Column positions
        'boundary': [],     # Outer boundary points
        'dimensions': {}    # Overall dimensions
    }

    # Collect all wall and roof entities by Y-region
    all_walls = []
    all_roof = []
    all_columns = []
    all_arcs = []

    for entity in doc.modelspace():
        if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE', 'ARC']:
            continue

        layer = entity.dxf.layer.upper() if hasattr(entity.dxf, 'layer') else ''

        # Get position
        x, y = None, None
        if entity.dxftype() == 'CIRCLE':
            x, y = entity.dxf.center.x, entity.dxf.center.y
        elif entity.dxftype() == 'ARC':
            x, y = entity.dxf.center.x, entity.dxf.center.y
        elif entity.dxftype() == 'LINE':
            x, y = entity.dxf.start.x, entity.dxf.start.y
        elif entity.dxftype() == 'LWPOLYLINE':
            pts = list(entity.get_points())
            if pts:
                x, y = pts[0][0], pts[0][1]

        if not (x and x_min <= x <= x_max):
            continue

        # Categorize
        if 'WALL' in layer:
            if entity.dxftype() == 'LWPOLYLINE':
                pts = [(p[0], p[1]) for p in entity.get_points()]
                all_walls.append({'y': y, 'points': pts, 'type': 'polyline'})
            elif entity.dxftype() == 'LINE':
                all_walls.append({
                    'y': y,
                    'points': [(entity.dxf.start.x, entity.dxf.start.y),
                              (entity.dxf.end.x, entity.dxf.end.y)],
                    'type': 'line'
                })

        if 'COL' in layer and entity.dxftype() == 'CIRCLE':
            all_columns.append({
                'x': entity.dxf.center.x,
                'y': entity.dxf.center.y,
                'r': entity.dxf.radius
            })

        if entity.dxftype() == 'ARC':
            all_arcs.append({
                'cx': entity.dxf.center.x,
                'cy': entity.dxf.center.y,
                'r': entity.dxf.radius,
                'start': entity.dxf.start_angle,
                'end': entity.dxf.end_angle
            })

        if 'ROOF' in layer:
            if entity.dxftype() == 'LWPOLYLINE':
                pts = [(p[0], p[1]) for p in entity.get_points()]
                all_roof.append({'y': y, 'points': pts})

    print(f"\nRaw data collected:")
    print(f"  Walls: {len(all_walls)}")
    print(f"  Columns: {len(all_columns)}")
    print(f"  Arcs: {len(all_arcs)}")
    print(f"  Roof: {len(all_roof)}")

    # Find the main building floor (Y region with most roof entities)
    y_counts = defaultdict(int)
    for w in all_walls + all_roof:
        bin_key = int(w['y'] / 50000) * 50000
        y_counts[bin_key] += 1

    main_y = max(y_counts.keys(), key=lambda k: y_counts[k])
    y_range = (main_y - 10000, main_y + 60000)

    print(f"\nMain floor Y-range: [{y_range[0]/1000:.0f}k, {y_range[1]/1000:.0f}k]")

    # Extract fingerprint features from main floor

    # 1. Boundary corners - find extreme points
    all_x = []
    all_y = []
    for w in all_walls:
        if y_range[0] <= w['y'] <= y_range[1]:
            for p in w['points']:
                all_x.append(p[0])
                all_y.append(p[1])

    if all_x:
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)

        # Four corners
        fingerprint['corners'] = [
            {'name': 'NW', 'x': min_x/1000, 'y': max_y/1000},
            {'name': 'NE', 'x': max_x/1000, 'y': max_y/1000},
            {'name': 'SW', 'x': min_x/1000, 'y': min_y/1000},
            {'name': 'SE', 'x': max_x/1000, 'y': min_y/1000},
        ]

        fingerprint['dimensions'] = {
            'width_m': (max_x - min_x) / 1000,
            'height_m': (max_y - min_y) / 1000,
            'aspect': (max_y - min_y) / (max_x - min_x)
        }

    # 2. Dome arcs - find large arcs that could be dome
    dome_arcs = [a for a in all_arcs if a['r'] > 1000 and y_range[0] <= a['cy'] <= y_range[1]]
    if dome_arcs:
        # Take the largest ones
        dome_arcs.sort(key=lambda x: -x['r'])
        for arc in dome_arcs[:5]:
            fingerprint['dome_arcs'].append({
                'cx': arc['cx']/1000,
                'cy': arc['cy']/1000,
                'r': arc['r']/1000,
                'angle_span': (arc['end'] - arc['start']) % 360
            })

    # 3. Column positions in main floor
    main_cols = [c for c in all_columns if y_range[0] <= c['y'] <= y_range[1]]
    # Take corner and center columns
    if main_cols:
        # Sort by position to get key ones
        main_cols.sort(key=lambda c: (c['x'], c['y']))
        # Take first, last, and middle
        indices = [0, len(main_cols)//2, -1]
        for i in indices:
            c = main_cols[i]
            fingerprint['columns'].append({
                'x': c['x']/1000,
                'y': c['y']/1000,
                'r': c['r']/1000
            })

    # 4. Boundary outline - sample key points
    # Get outer wall segments
    boundary_pts = []
    for w in all_walls:
        if y_range[0] <= w['y'] <= y_range[1] and w['type'] == 'polyline':
            # Check if it's on the boundary (near min/max x or y)
            for p in w['points']:
                if (abs(p[0] - min_x) < 5000 or abs(p[0] - max_x) < 5000 or
                    abs(p[1] - min_y) < 5000 or abs(p[1] - max_y) < 5000):
                    boundary_pts.append(p)

    # Sample boundary points
    if boundary_pts:
        # Take every Nth point
        step = max(1, len(boundary_pts) // 20)
        for i in range(0, len(boundary_pts), step):
            p = boundary_pts[i]
            fingerprint['boundary'].append({
                'x': p[0]/1000,
                'y': p[1]/1000
            })

    # Save fingerprint
    output = base / "SourceFiles" / "Terminal1_Fingerprint.json"
    with open(output, 'w') as f:
        json.dump(fingerprint, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("FINGERPRINT SUMMARY")
    print(f"{'='*60}")
    print(f"Corners: {len(fingerprint['corners'])}")
    print(f"Dome arcs: {len(fingerprint['dome_arcs'])}")
    print(f"Columns: {len(fingerprint['columns'])}")
    print(f"Boundary points: {len(fingerprint['boundary'])}")
    print(f"\nDimensions: {fingerprint['dimensions']['width_m']:.1f}m x {fingerprint['dimensions']['height_m']:.1f}m")
    print(f"Aspect ratio: {fingerprint['dimensions']['aspect']:.2f}")
    print(f"\nSaved to: {output}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
