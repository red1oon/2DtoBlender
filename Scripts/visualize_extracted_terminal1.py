#!/usr/bin/env python3
"""
Visualize the extracted Terminal 1 DXF files.
Uses clean, single-building DXF files without coordinate transformations.
"""

import ezdxf
from pathlib import Path
from collections import defaultdict

def extract_entities(dxf_path, layer_filter=None):
    """Extract entities from DXF file"""
    doc = ezdxf.readfile(str(dxf_path))
    entities = []

    for entity in doc.modelspace():
        if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE', 'ARC']:
            continue

        if layer_filter and hasattr(entity.dxf, 'layer'):
            if entity.dxf.layer.upper() not in layer_filter:
                continue

        if entity.dxftype() == 'CIRCLE':
            c = entity.dxf.center
            entities.append({
                'type': 'circle',
                'cx': c.x, 'cy': c.y,
                'r': entity.dxf.radius
            })
        elif entity.dxftype() == 'LINE':
            s, e = entity.dxf.start, entity.dxf.end
            entities.append({
                'type': 'line',
                'x1': s.x, 'y1': s.y, 'x2': e.x, 'y2': e.y
            })
        elif entity.dxftype() == 'LWPOLYLINE':
            points = [(p[0], p[1]) for p in entity.get_points()]
            entities.append({
                'type': 'polyline',
                'points': points
            })
        elif entity.dxftype() == 'ARC':
            c = entity.dxf.center
            entities.append({
                'type': 'arc',
                'cx': c.x, 'cy': c.y,
                'r': entity.dxf.radius,
                'start_angle': entity.dxf.start_angle,
                'end_angle': entity.dxf.end_angle
            })

    return entities

def get_bounds(all_entities):
    """Calculate bounds from all entities"""
    x_coords = []
    y_coords = []

    for entities in all_entities:
        for e in entities:
            if e['type'] == 'circle':
                x_coords.append(e['cx'])
                y_coords.append(e['cy'])
            elif e['type'] == 'line':
                x_coords.extend([e['x1'], e['x2']])
                y_coords.extend([e['y1'], e['y2']])
            elif e['type'] == 'polyline':
                x_coords.extend([p[0] for p in e['points']])
                y_coords.extend([p[1] for p in e['points']])
            elif e['type'] == 'arc':
                # For arcs, use center +/- radius
                x_coords.extend([e['cx'] - e['r'], e['cx'] + e['r']])
                y_coords.extend([e['cy'] - e['r'], e['cy'] + e['r']])

    return {
        'min_x': min(x_coords), 'max_x': max(x_coords),
        'min_y': min(y_coords), 'max_y': max(y_coords)
    }

def generate_svg_content(entities, color, bounds, width):
    """Generate SVG markup for entities"""
    bounds_w = bounds['max_x'] - bounds['min_x']
    bounds_h = bounds['max_y'] - bounds['min_y']
    scale = width / bounds_w

    def transform(x, y):
        return ((x - bounds['min_x']) * scale,
                (bounds['max_y'] - y) * scale)

    svg = []
    for e in entities:
        if e['type'] == 'circle':
            cx, cy = transform(e['cx'], e['cy'])
            r = max(e['r'] * scale, 2)
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                      f'fill="{color}" stroke="{color}" stroke-width="1" opacity="0.7"/>')
        elif e['type'] == 'line':
            x1, y1 = transform(e['x1'], e['y1'])
            x2, y2 = transform(e['x2'], e['y2'])
            svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                      f'stroke="{color}" stroke-width="1.5" opacity="0.7"/>')
        elif e['type'] == 'polyline':
            pts = [transform(p[0], p[1]) for p in e['points']]
            pts_str = ' '.join(f"{x:.1f},{y:.1f}" for x, y in pts)
            svg.append(f'<polyline points="{pts_str}" fill="none" '
                      f'stroke="{color}" stroke-width="1.5" opacity="0.7"/>')
        elif e['type'] == 'arc':
            import math
            cx, cy = transform(e['cx'], e['cy'])
            r = max(e['r'] * scale, 2)
            # Convert angles (DXF uses degrees, SVG uses radians)
            # DXF: counter-clockwise from 3 o'clock
            # SVG: need to flip Y axis
            start_rad = math.radians(e['start_angle'])
            end_rad = math.radians(e['end_angle'])
            # Calculate start and end points
            x1 = cx + r * math.cos(start_rad)
            y1 = cy - r * math.sin(start_rad)  # Flip Y
            x2 = cx + r * math.cos(end_rad)
            y2 = cy - r * math.sin(end_rad)  # Flip Y
            # Large arc flag: if angle > 180 degrees
            angle_diff = (e['end_angle'] - e['start_angle']) % 360
            large_arc = 1 if angle_diff > 180 else 0
            # Sweep direction (counterclockwise in SVG with flipped Y = clockwise)
            sweep = 0
            svg.append(f'<path d="M {x1:.1f} {y1:.1f} A {r:.1f} {r:.1f} 0 {large_arc} {sweep} {x2:.1f} {y2:.1f}" '
                      f'fill="none" stroke="{color}" stroke-width="1.5" opacity="0.7"/>')

    return '\n'.join(svg)

def main():
    print("="*80)
    print("VISUALIZING EXTRACTED TERMINAL 1")
    print("="*80)

    base = Path(__file__).parent.parent
    extract_dir = base / "SourceFiles" / "Terminal1_Extracted"

    # Define layers and colors
    # Note: 'window' layer contains large reference circles, not actual windows
    arc_layers = {
        'Walls': {
            'filter': ['WALL', 'WALL1', 'A-WALL', 'CH-WALL'],
            'color': '#34495e'
        },
        'Roof': {
            'filter': ['ROOF', 'ROOFSTR', 'CH-ROOF'],
            'color': '#e74c3c'
        },
        'Columns': {
            'filter': ['COL', 'COLUMN'],
            'color': '#9b59b6'
        },
    }

    # Extract ARC layers
    print("\n📐 Loading ARC layers...")
    arc_path = extract_dir / "Terminal1_ARC.dxf"
    arc_doc = ezdxf.readfile(str(arc_path))

    arc_groups = {}
    for layer_name, layer_info in arc_layers.items():
        entities = []
        for entity in arc_doc.modelspace():
            if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE', 'ARC']:
                continue
            if not hasattr(entity.dxf, 'layer'):
                continue
            if entity.dxf.layer.upper() not in layer_info['filter']:
                continue

            if entity.dxftype() == 'CIRCLE':
                c = entity.dxf.center
                entities.append({'type': 'circle', 'cx': c.x, 'cy': c.y, 'r': entity.dxf.radius})
            elif entity.dxftype() == 'LINE':
                s, e = entity.dxf.start, entity.dxf.end
                entities.append({'type': 'line', 'x1': s.x, 'y1': s.y, 'x2': e.x, 'y2': e.y})
            elif entity.dxftype() == 'LWPOLYLINE':
                points = [(p[0], p[1]) for p in entity.get_points()]
                entities.append({'type': 'polyline', 'points': points})
            elif entity.dxftype() == 'ARC':
                c = entity.dxf.center
                entities.append({
                    'type': 'arc', 'cx': c.x, 'cy': c.y, 'r': entity.dxf.radius,
                    'start_angle': entity.dxf.start_angle, 'end_angle': entity.dxf.end_angle
                })

        arc_groups[f'ARC-{layer_name}'] = entities
        print(f"  ARC-{layer_name}: {len(entities)} entities")

    # Also extract ALL ARC entities (dome curves) regardless of layer
    dome_arcs = []
    for entity in arc_doc.modelspace():
        if entity.dxftype() == 'ARC':
            c = entity.dxf.center
            dome_arcs.append({
                'type': 'arc', 'cx': c.x, 'cy': c.y, 'r': entity.dxf.radius,
                'start_angle': entity.dxf.start_angle, 'end_angle': entity.dxf.end_angle
            })
    if dome_arcs:
        arc_groups['ARC-Dome'] = dome_arcs
        arc_layers['Dome'] = {'filter': [], 'color': '#27ae60'}  # Green for dome
        print(f"  ARC-Dome: {len(dome_arcs)} entities")

    # Calculate bounds from ARC - use walls, roof, and dome for proper bounds
    main_entities = [
        arc_groups.get('ARC-Walls', []),
        arc_groups.get('ARC-Roof', []),
        arc_groups.get('ARC-Dome', [])
    ]
    bounds = get_bounds(main_entities)
    # Add small padding
    padding = 2000
    bounds['min_x'] -= padding
    bounds['max_x'] += padding
    bounds['min_y'] -= padding
    bounds['max_y'] += padding
    print(f"\n  Bounds: X=[{bounds['min_x']:.0f}, {bounds['max_x']:.0f}], Y=[{bounds['min_y']:.0f}, {bounds['max_y']:.0f}]")

    # Calculate SVG dimensions
    svg_width = 900
    bounds_w = bounds['max_x'] - bounds['min_x']
    bounds_h = bounds['max_y'] - bounds['min_y']
    svg_height = int(svg_width * bounds_h / bounds_w)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal 1 - Extracted DXF Visualization</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 25px; text-align: center; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header p {{ font-size: 14px; opacity: 0.9; }}

        .controls {{ padding: 20px; background: #f8f9fa; }}
        .control-section {{ margin-bottom: 20px; }}
        .control-section h3 {{ margin-bottom: 12px; color: #2c3e50; font-size: 16px; }}
        .toggles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }}

        .toggle-btn {{ display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: white; border: 2px solid #ddd;
                      border-radius: 6px; cursor: pointer; transition: all 0.3s; user-select: none; }}
        .toggle-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        .toggle-btn.active {{ border-color: #2ecc71; background: #ecf9f2; }}
        .color-box {{ width: 20px; height: 20px; border-radius: 3px; border: 2px solid #333; flex-shrink: 0; }}
        .toggle-label {{ flex: 1; font-size: 13px; font-weight: 600; }}
        .toggle-count {{ font-size: 11px; color: #7f8c8d; }}

        .svg-container {{ padding: 30px; background: #fafafa; display: flex; justify-content: center; }}
        svg {{ border: 2px solid #ddd; border-radius: 8px; background: white; }}

        .info {{ padding: 15px; background: #d5f4e6; border-top: 3px solid #2ecc71; text-align: center; color: #27ae60; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Terminal 1 - Extracted DXF View</h1>
            <p>Clean extraction from source DXF | Only Terminal 1 geometry | Click to toggle layers</p>
        </div>

        <div class="controls">
            <div class="control-section">
                <h3>ARC (Architecture) - Element Types</h3>
                <div class="toggles">
"""

    # Add toggle buttons
    for layer_name, layer_info in arc_layers.items():
        group_name = f'ARC-{layer_name}'
        entities = arc_groups.get(group_name, [])
        color = layer_info['color']
        count = len(entities)
        html += f"""                    <div class="toggle-btn active" onclick="toggleLayer('{group_name}')" id="toggle-{group_name}">
                        <div class="color-box" style="background: {color};"></div>
                        <div style="flex: 1;">
                            <div class="toggle-label">{layer_name}</div>
                            <div class="toggle-count">{count} elem</div>
                        </div>
                    </div>
"""

    html += f"""                </div>
            </div>
        </div>

        <div class="svg-container">
            <svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
                <rect width="{svg_width}" height="{svg_height}" fill="#f5f5f5"/>
"""

    # Add SVG groups
    for layer_name, layer_info in arc_layers.items():
        group_name = f'ARC-{layer_name}'
        entities = arc_groups.get(group_name, [])
        color = layer_info['color']
        svg_content = generate_svg_content(entities, color, bounds, svg_width)
        html += f"""                <g id="layer-{group_name}" class="layer-group">
{svg_content}
                </g>
"""

    html += """            </svg>
        </div>

        <div class="info">
            Clean Terminal 1 extraction from source DXF files. Dome and building in same coordinate system.
        </div>
    </div>

    <script>
        function toggleLayer(layerName) {
            const group = document.getElementById('layer-' + layerName);
            const toggle = document.getElementById('toggle-' + layerName);

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

    output = base / "SourceFiles" / "Terminal1_Extracted_View.html"
    with open(output, 'w') as f:
        f.write(html)

    print(f"\n{'='*80}")
    print("SUCCESS!")
    print(f"Output: file://{output.absolute()}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
