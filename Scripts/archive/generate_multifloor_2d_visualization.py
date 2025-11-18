#!/usr/bin/env python3
"""
Generate 2D HTML visualization of Terminal 1 from ALL floors (GB, 1F, 3F, 4F-6F, RF)
Uses known Terminal 1 bounds from cheatsheet for all STR DXF files
"""

import ezdxf
import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Terminal 1 bounds from density analysis (STR native DXF coords in mm)
# Found using column density analysis on 1F DXF: 141 columns in 60m × 40m region
TERMINAL1_BOUNDS = {
    'min_x': 349412,
    'max_x': 409412,
    'min_y': -216677,
    'max_y': -176677
}

# ARC Terminal 1 bounds (ARC native coords in mm)
ARC_TERMINAL1_BOUNDS = {
    'min_x': -1620000,
    'max_x': -1560000,
    'min_y': -90000,
    'max_y': -40000
}

def load_building_config():
    """Load building configuration"""
    config_path = Path(__file__).parent.parent / "building_config.json"
    with open(config_path) as f:
        return json.load(f)

def point_in_bounds(x: float, y: float, bounds: dict) -> bool:
    """Check if point is within Terminal 1 bounds"""
    return (bounds['min_x'] <= x <= bounds['max_x'] and
            bounds['min_y'] <= y <= bounds['max_y'])

def extract_floor_entities(dxf_path: str, discipline: str, floor_id: str) -> Dict:
    """Extract entities from a single floor DXF within Terminal 1 bounds"""

    # Select bounds based on discipline
    bounds = ARC_TERMINAL1_BOUNDS if discipline == 'ARC' else TERMINAL1_BOUNDS

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        entities_by_type = defaultdict(list)

        for entity in msp:
            entity_type = entity.dxftype()

            # Extract based on entity type
            if entity_type == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end

                # Check if line is within bounds (either endpoint)
                if (point_in_bounds(start.x, start.y, bounds) or
                    point_in_bounds(end.x, end.y, bounds)):

                    entities_by_type['LINE'].append({
                        'start': [start.x, start.y],
                        'end': [end.x, end.y],
                        'layer': entity.dxf.layer
                    })

            elif entity_type == 'LWPOLYLINE':
                points = list(entity.get_points())
                if not points:
                    continue

                # Check if any point is within bounds
                in_bounds = any(point_in_bounds(p[0], p[1], bounds) for p in points)

                if in_bounds:
                    entities_by_type['LWPOLYLINE'].append({
                        'points': [[p[0], p[1]] for p in points],
                        'closed': entity.closed,
                        'layer': entity.dxf.layer
                    })

            elif entity_type == 'CIRCLE':
                center = entity.dxf.center

                if point_in_bounds(center.x, center.y, bounds):
                    entities_by_type['CIRCLE'].append({
                        'center': [center.x, center.y],
                        'radius': entity.dxf.radius,
                        'layer': entity.dxf.layer
                    })

            elif entity_type == 'ARC':
                center = entity.dxf.center

                if point_in_bounds(center.x, center.y, bounds):
                    entities_by_type['ARC'].append({
                        'center': [center.x, center.y],
                        'radius': entity.dxf.radius,
                        'start_angle': entity.dxf.start_angle,
                        'end_angle': entity.dxf.end_angle,
                        'layer': entity.dxf.layer
                    })

        return {
            'floor': floor_id,
            'discipline': discipline,
            'dxf_file': Path(dxf_path).name,
            'bounds': bounds,
            'entity_counts': {k: len(v) for k, v in entities_by_type.items()},
            'entities': dict(entities_by_type)
        }

    except Exception as e:
        print(f"Error processing {dxf_path}: {e}")
        return None

def generate_svg_for_floor(floor_data: Dict, color: str) -> str:
    """Generate SVG elements for a single floor"""

    if not floor_data:
        return ""

    svg_parts = []
    entities = floor_data['entities']
    bounds = floor_data['bounds']

    # Scale factor (mm to SVG units, typically want ~800px width)
    width_mm = bounds['max_x'] - bounds['min_x']
    scale = 800.0 / width_mm

    # Transform function (flip Y axis for SVG)
    def transform(x, y):
        tx = (x - bounds['min_x']) * scale
        ty = (bounds['max_y'] - y) * scale  # Flip Y
        return tx, ty

    # Draw LINEs
    for line in entities.get('LINE', []):
        x1, y1 = transform(line['start'][0], line['start'][1])
        x2, y2 = transform(line['end'][0], line['end'][1])
        svg_parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                        f'stroke="{color}" stroke-width="0.5" opacity="0.7"/>')

    # Draw LWPOLYLINEs
    for poly in entities.get('LWPOLYLINE', []):
        points = [transform(p[0], p[1]) for p in poly['points']]
        points_str = ' '.join(f"{x:.2f},{y:.2f}" for x, y in points)
        svg_parts.append(f'<polyline points="{points_str}" '
                        f'fill="none" stroke="{color}" stroke-width="1" opacity="0.7"/>')

    # Draw CIRCLEs
    for circle in entities.get('CIRCLE', []):
        cx, cy = transform(circle['center'][0], circle['center'][1])
        r = circle['radius'] * scale
        svg_parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
                        f'fill="none" stroke="{color}" stroke-width="1" opacity="0.7"/>')

    # Draw ARCs
    for arc in entities.get('ARC', []):
        cx, cy = transform(arc['center'][0], arc['center'][1])
        r = arc['radius'] * scale
        # Simplified: draw as circle (proper arc path would need start/end angle conversion)
        svg_parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
                        f'fill="none" stroke="{color}" stroke-width="1" opacity="0.5"/>')

    return '\n'.join(svg_parts)

def generate_html_visualization(all_floors_data: List[Dict], output_path: str):
    """Generate interactive HTML with all floors overlaid"""

    # Calculate overall bounds (use STR bounds as reference)
    ref_bounds = TERMINAL1_BOUNDS
    width_mm = ref_bounds['max_x'] - ref_bounds['min_x']
    height_mm = ref_bounds['max_y'] - ref_bounds['min_y']

    svg_width = 800
    svg_height = int(800 * height_mm / width_mm)

    # Floor colors
    floor_colors = {
        'GB': '#FF6B6B',   # Red
        '1F': '#4ECDC4',   # Teal
        '3F': '#45B7D1',   # Blue
        '4F': '#96CEB4',   # Green
        '5F': '#FFEAA7',   # Yellow
        '6F': '#DFE6E9',   # Gray
        'RF': '#A29BFE'    # Purple
    }

    # Generate SVG content for each floor
    floor_svgs = []
    for floor_data in all_floors_data:
        if floor_data:
            floor_id = floor_data['floor']
            color = floor_colors.get(floor_id, '#000000')
            svg_content = generate_svg_for_floor(floor_data, color)

            floor_svgs.append({
                'id': floor_id,
                'color': color,
                'svg': svg_content,
                'entity_counts': floor_data['entity_counts'],
                'discipline': floor_data['discipline']
            })

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal 1 - Multi-Floor 2D View</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
        }}
        .controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .floor-toggle {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .floor-toggle:hover {{
            border-color: #3498db;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .floor-toggle.active {{
            border-color: #2ecc71;
            background: #ecf0f1;
        }}
        .color-box {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
            border: 1px solid #999;
        }}
        .svg-container {{
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            background: #fafafa;
            overflow: auto;
        }}
        svg {{
            border: 1px solid #ccc;
            background: white;
        }}
        .stats {{
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .stats h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-card {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}
        .stat-card h4 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 14px;
        }}
        .stat-card .count {{
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏢 Terminal 1 Main Building - Multi-Floor 2D View</h1>
        <div class="subtitle">Ferry/Jetty Terminal - All Structural Floors (GB to RF)</div>

        <div class="controls">
            <strong style="width: 100%; margin-bottom: 10px;">Toggle Floors:</strong>
"""

    # Add floor toggles
    for floor_svg in floor_svgs:
        floor_id = floor_svg['id']
        color = floor_svg['color']
        html += f"""            <div class="floor-toggle active" onclick="toggleFloor('{floor_id}')" id="toggle-{floor_id}">
                <div class="color-box" style="background-color: {color};"></div>
                <span><strong>{floor_id}</strong></span>
                <span style="font-size: 12px; color: #7f8c8d;">({sum(floor_svg['entity_counts'].values())} entities)</span>
            </div>
"""

    html += """        </div>

        <div class="svg-container">
"""

    # Add SVG with all floor groups
    html += f"""            <svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
"""

    for floor_svg in floor_svgs:
        floor_id = floor_svg['id']
        html += f"""                <g id="floor-{floor_id}" class="floor-group">
{floor_svg['svg']}
                </g>
"""

    html += """            </svg>
        </div>

        <div class="stats">
            <h3>📊 Extraction Statistics</h3>
            <div class="stat-grid">
"""

    # Add statistics for each floor
    for floor_svg in floor_svgs:
        floor_id = floor_svg['id']
        total = sum(floor_svg['entity_counts'].values())
        html += f"""                <div class="stat-card">
                    <h4>{floor_id} ({floor_svg['discipline']})</h4>
                    <div class="count">{total}</div>
                    <div style="font-size: 12px; color: #7f8c8d; margin-top: 8px;">
"""
        for entity_type, count in floor_svg['entity_counts'].items():
            html += f"                        {entity_type}: {count}<br>\n"

        html += """                    </div>
                </div>
"""

    html += """            </div>
        </div>
    </div>

    <script>
        function toggleFloor(floorId) {
            const group = document.getElementById('floor-' + floorId);
            const toggle = document.getElementById('toggle-' + floorId);

            if (group.style.display === 'none') {
                group.style.display = 'block';
                toggle.classList.add('active');
            } else {
                group.style.display = 'none';
                toggle.classList.remove('active');
            }
        }
    </script>
</body>
</html>
"""

    # Write to file
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ Generated HTML visualization: {output_path}")

def main():
    """Main execution"""
    print("=" * 80)
    print("TERMINAL 1 MULTI-FLOOR 2D VISUALIZATION GENERATOR")
    print("=" * 80)

    # Load config
    config = load_building_config()
    base_path = Path(__file__).parent.parent

    # Extract from all floors
    all_floors_data = []

    for floor in config['floor_levels']:
        floor_id = floor['level_id']

        # Process STR discipline
        str_dxf = floor['dxf_sources'].get('STR')
        if str_dxf:
            print(f"\n📂 Processing {floor_id} (STR)...")
            dxf_path = base_path / str_dxf

            if dxf_path.exists():
                floor_data = extract_floor_entities(str(dxf_path), 'STR', floor_id)
                if floor_data and sum(floor_data['entity_counts'].values()) > 0:
                    all_floors_data.append(floor_data)
                    print(f"   ✅ Extracted {sum(floor_data['entity_counts'].values())} entities")
                else:
                    print(f"   ⚠️  No entities found in Terminal 1 bounds")
            else:
                print(f"   ❌ DXF not found: {dxf_path}")

    # Generate HTML
    if all_floors_data:
        output_path = base_path / "SourceFiles" / "Terminal1_MultiFloor_2D_View.html"
        generate_html_visualization(all_floors_data, str(output_path))

        print("\n" + "=" * 80)
        print(f"✅ SUCCESS! Generated visualization with {len(all_floors_data)} floors")
        print(f"📄 Output: {output_path}")
        print("=" * 80)
    else:
        print("\n❌ No floor data extracted!")

if __name__ == "__main__":
    main()
