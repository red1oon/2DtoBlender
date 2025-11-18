#!/usr/bin/env python3
"""
Generate interactive HTML with layer toggles
Allows turning on/off different DXF layers to see different building systems
"""

import ezdxf
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Terminal 1 bounds
TERMINAL1_BOUNDS_STR = {
    'min_x': 349412, 'max_x': 409412,
    'min_y': -216677, 'max_y': -176677
}

TERMINAL1_BOUNDS_ARC = {
    'min_x': -1620000, 'max_x': -1560000,
    'min_y': -90000, 'max_y': -40000
}

# Layer categories and colors for ARC
ARC_LAYER_GROUPS = {
    'Walls': {
        'layers': ['wall', 'WALL1', 'A-WALL', 'A- WALL', 'CH-WALL'],
        'color': '#2c3e50'
    },
    'Roof/Dome': {
        'layers': ['ROOF', 'roof glass', 'ROOFSTR', 'CH-ROOF', 'A-ROOF'],
        'color': '#e74c3c'
    },
    'Columns': {
        'layers': ['COL', 'column', 'ENGRS COLUMN T1'],
        'color': '#3498db'
    },
    'Windows': {
        'layers': ['WIN', 'window', 'WINO'],
        'color': '#1abc9c'
    },
    'Doors': {
        'layers': ['DOOR', 'DR', 'DOORnew1', 'code-door new', 'DOOR-TIMBER'],
        'color': '#f39c12'
    },
    'Stairs': {
        'layers': ['STAIR', 'staircase'],
        'color': '#9b59b6'
    },
    'Furniture': {
        'layers': ['FURNITURE', 'FIT'],
        'color': '#95a5a6'
    },
    'Grid': {
        'layers': ['GRID', 'GRID1', 'S-GRID-IDEN'],
        'color': '#34495e'
    }
}

def point_in_bounds(x: float, y: float, bounds: dict) -> bool:
    """Check if point is within bounds"""
    return (bounds['min_x'] <= x <= bounds['max_x'] and
            bounds['min_y'] <= y <= bounds['max_y'])

def extract_by_layers(dxf_path: str, bounds: dict, layer_groups: dict) -> Dict[str, List]:
    """Extract entities grouped by layer categories"""

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Build reverse lookup: layer_name -> group_name
    layer_to_group = {}
    for group_name, group_data in layer_groups.items():
        for layer_name in group_data['layers']:
            layer_to_group[layer_name.lower()] = group_name

    grouped_entities = defaultdict(list)

    for entity in msp:
        entity_type = entity.dxftype()
        if entity_type not in ['CIRCLE', 'LINE', 'LWPOLYLINE']:
            continue

        # Get layer
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
        layer_lower = layer.lower()

        # Find which group this layer belongs to
        group_name = layer_to_group.get(layer_lower)
        if not group_name:
            continue

        # Check bounds
        in_bounds = False
        if entity_type == 'CIRCLE':
            center = entity.dxf.center
            in_bounds = point_in_bounds(center.x, center.y, bounds)
            if in_bounds:
                grouped_entities[group_name].append({
                    'type': 'circle',
                    'cx': center.x, 'cy': center.y,
                    'r': entity.dxf.radius
                })

        elif entity_type == 'LINE':
            start, end = entity.dxf.start, entity.dxf.end
            in_bounds = (point_in_bounds(start.x, start.y, bounds) or
                        point_in_bounds(end.x, end.y, bounds))
            if in_bounds:
                grouped_entities[group_name].append({
                    'type': 'line',
                    'x1': start.x, 'y1': start.y,
                    'x2': end.x, 'y2': end.y
                })

        elif entity_type == 'LWPOLYLINE':
            points = list(entity.get_points())
            in_bounds = any(point_in_bounds(p[0], p[1], bounds) for p in points)
            if in_bounds:
                grouped_entities[group_name].append({
                    'type': 'polyline',
                    'points': [(p[0], p[1]) for p in points],
                    'closed': entity.closed
                })

    return dict(grouped_entities)

def generate_svg_for_group(entities: List[Dict], bounds: dict, color: str, width: int = 900) -> str:
    """Generate SVG elements for a group"""

    bounds_w = bounds['max_x'] - bounds['min_x']
    bounds_h = bounds['max_y'] - bounds['min_y']
    scale = width / bounds_w

    def transform(x, y):
        sx = (x - bounds['min_x']) * scale
        sy = (bounds['max_y'] - y) * scale
        return sx, sy

    svg_parts = []
    for ent in entities:
        if ent['type'] == 'circle':
            cx, cy = transform(ent['cx'], ent['cy'])
            r = max(ent['r'] * scale, 2.5)
            svg_parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{color}" stroke="{color}" stroke-width="1" opacity="0.8"/>')

        elif ent['type'] == 'line':
            x1, y1 = transform(ent['x1'], ent['y1'])
            x2, y2 = transform(ent['x2'], ent['y2'])
            svg_parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="1.5" opacity="0.8"/>')

        elif ent['type'] == 'polyline':
            pts = [transform(p[0], p[1]) for p in ent['points']]
            pts_str = ' '.join(f"{x:.1f},{y:.1f}" for x, y in pts)
            svg_parts.append(f'<polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.8"/>')

    return '\n'.join(svg_parts)

def generate_interactive_html(dxf_path: str, bounds: dict, layer_groups: dict,
                              output_path: str, title: str):
    """Generate interactive HTML with layer toggles"""

    print(f"\n📂 Processing {title}...")
    grouped = extract_by_layers(dxf_path, bounds, layer_groups)

    # Calculate SVG dimensions
    bounds_w = bounds['max_x'] - bounds['min_x']
    bounds_h = bounds['max_y'] - bounds['min_y']
    svg_width = 900
    svg_height = int(900 * bounds_h / bounds_w)

    # Generate SVG content for each group
    svg_groups = {}
    for group_name in layer_groups.keys():
        entities = grouped.get(group_name, [])
        color = layer_groups[group_name]['color']
        svg_content = generate_svg_for_group(entities, bounds, color, svg_width)
        svg_groups[group_name] = {
            'svg': svg_content,
            'count': len(entities),
            'color': color
        }
        print(f"  {group_name:15s}: {len(entities):5d} entities")

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title} - Interactive Layer View</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 25px;
            text-align: center;
        }}
        .header h1 {{ font-size: 26px; margin-bottom: 8px; }}
        .header p {{ font-size: 14px; opacity: 0.9; }}

        .controls {{
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 2px solid #ddd;
        }}
        .controls h3 {{ margin-bottom: 15px; color: #2c3e50; }}
        .layer-toggles {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
        }}
        .toggle-btn {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
            background: white;
            border: 2px solid #ddd;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
            user-select: none;
        }}
        .toggle-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .toggle-btn.active {{
            border-color: #2ecc71;
            background: #ecf9f2;
        }}
        .color-indicator {{
            width: 24px;
            height: 24px;
            border-radius: 4px;
            border: 2px solid #333;
            flex-shrink: 0;
        }}
        .toggle-info {{
            flex: 1;
        }}
        .toggle-name {{
            font-weight: bold;
            font-size: 14px;
            color: #2c3e50;
        }}
        .toggle-count {{
            font-size: 12px;
            color: #7f8c8d;
        }}

        .svg-container {{
            padding: 30px;
            background: #fafafa;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        svg {{
            border: 2px solid #ddd;
            border-radius: 8px;
            background: white;
        }}

        .instructions {{
            padding: 20px;
            background: #fff3cd;
            border-top: 2px solid #ffc107;
            color: #856404;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ {title}</h1>
            <p>Interactive Layer Toggle | Click to show/hide building systems</p>
        </div>

        <div class="controls">
            <h3>🎛️ Layer Controls (Click to toggle on/off)</h3>
            <div class="layer-toggles">
"""

    # Add toggle buttons
    for group_name, data in svg_groups.items():
        color = data['color']
        count = data['count']
        html += f"""                <div class="toggle-btn active" onclick="toggleLayer('{group_name}')" id="toggle-{group_name}">
                    <div class="color-indicator" style="background: {color};"></div>
                    <div class="toggle-info">
                        <div class="toggle-name">{group_name}</div>
                        <div class="toggle-count">{count} elements</div>
                    </div>
                </div>
"""

    html += f"""            </div>
        </div>

        <div class="svg-container">
            <svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
                <rect width="{svg_width}" height="{svg_height}" fill="#f5f5f5"/>
"""

    # Add SVG groups
    for group_name, data in svg_groups.items():
        html += f"""                <g id="layer-{group_name}" class="layer-group">
{data['svg']}
                </g>
"""

    html += f"""            </svg>
        </div>

        <div class="instructions">
            💡 <strong>Tip:</strong> Click the layer buttons above to show/hide different building systems.
            This lets you inspect walls, roof, columns, etc. individually or in combination.
        </div>
    </div>

    <script>
        function toggleLayer(layerName) {{
            const group = document.getElementById('layer-' + layerName);
            const toggle = document.getElementById('toggle-' + layerName);

            if (group.style.display === 'none') {{
                group.style.display = 'block';
                toggle.classList.add('active');
            }} else {{
                group.style.display = 'none';
                toggle.classList.remove('active');
            }}
        }}
    </script>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ Generated: {output_path}")

def main():
    """Main execution"""

    print("="*80)
    print("GENERATING INTERACTIVE LAYER TOGGLE VIEWS")
    print("="*80)

    base_path = Path(__file__).parent.parent

    # Generate ARC interactive view
    arc_dxf = base_path / "SourceFiles/TERMINAL1DXF/01 ARCHITECT/2. BANGUNAN TERMINAL 1.dxf"
    arc_output = base_path / "SourceFiles" / "Terminal1_ARC_Interactive.html"

    generate_interactive_html(
        str(arc_dxf),
        TERMINAL1_BOUNDS_ARC,
        ARC_LAYER_GROUPS,
        str(arc_output),
        "Terminal 1 - ARC (Architecture)"
    )

    print("\n" + "="*80)
    print("✅ SUCCESS!")
    print(f"📄 Open: file://{arc_output.absolute()}")
    print("="*80)

if __name__ == "__main__":
    main()
