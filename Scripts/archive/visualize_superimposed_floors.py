#!/usr/bin/env python3
"""
Visualize Terminal 1 with superimposed floor plans and floor toggles.
Each floor is normalized to the same position for overlay.
"""

import ezdxf
import math
from pathlib import Path
from collections import defaultdict

def main():
    print("="*80)
    print("GENERATING SUPERIMPOSED FLOOR VISUALIZATION")
    print("="*80)

    base = Path(__file__).parent.parent
    arc_path = base / "SourceFiles" / "Terminal1_Extracted" / "Terminal1_ARC.dxf"
    doc = ezdxf.readfile(str(arc_path))

    # Define floor boundaries based on Y-coordinate ranges
    # 3 floors in Y range [137166, 317316]
    floor_bounds = [
        ('Floor 1 (Lower)', 137166, 197216, '#3498db'),   # Blue
        ('Floor 2 (Middle)', 197216, 257266, '#e67e22'),  # Orange
        ('Floor 3 (Upper)', 257266, 320000, '#2ecc71'),   # Green
    ]

    # Extract entities by floor
    floors = {}
    for floor_name, y_min, y_max, color in floor_bounds:
        entities = []
        x_coords = []
        y_coords = []

        for entity in doc.modelspace():
            if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE', 'ARC']:
                continue

            # Check if entity is in this floor's Y range
            y = None
            x = None

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

            if y is None or not (y_min <= y < y_max):
                continue

            # Store entity with normalized Y (subtract floor's y_min)
            y_offset = y_min

            if entity.dxftype() == 'CIRCLE':
                c = entity.dxf.center
                entities.append({
                    'type': 'circle',
                    'cx': c.x, 'cy': c.y - y_offset,
                    'r': entity.dxf.radius
                })
                x_coords.append(c.x)
                y_coords.append(c.y - y_offset)
            elif entity.dxftype() == 'ARC':
                c = entity.dxf.center
                entities.append({
                    'type': 'arc',
                    'cx': c.x, 'cy': c.y - y_offset,
                    'r': entity.dxf.radius,
                    'start_angle': entity.dxf.start_angle,
                    'end_angle': entity.dxf.end_angle
                })
                x_coords.extend([c.x - entity.dxf.radius, c.x + entity.dxf.radius])
                y_coords.extend([c.y - y_offset - entity.dxf.radius, c.y - y_offset + entity.dxf.radius])
            elif entity.dxftype() == 'LINE':
                s, e = entity.dxf.start, entity.dxf.end
                entities.append({
                    'type': 'line',
                    'x1': s.x, 'y1': s.y - y_offset,
                    'x2': e.x, 'y2': e.y - y_offset
                })
                x_coords.extend([s.x, e.x])
                y_coords.extend([s.y - y_offset, e.y - y_offset])
            elif entity.dxftype() == 'LWPOLYLINE':
                pts = [(p[0], p[1] - y_offset) for p in entity.get_points()]
                entities.append({
                    'type': 'polyline',
                    'points': pts
                })
                x_coords.extend([p[0] for p in pts])
                y_coords.extend([p[1] for p in pts])

        floors[floor_name] = {
            'entities': entities,
            'color': color,
            'x_coords': x_coords,
            'y_coords': y_coords
        }
        print(f"  {floor_name}: {len(entities)} entities")

    # Calculate combined bounds
    all_x = []
    all_y = []
    for floor_data in floors.values():
        all_x.extend(floor_data['x_coords'])
        all_y.extend(floor_data['y_coords'])

    if not all_x:
        print("No entities found!")
        return

    bounds = {
        'min_x': min(all_x) - 2000,
        'max_x': max(all_x) + 2000,
        'min_y': min(all_y) - 2000,
        'max_y': max(all_y) + 2000
    }

    print(f"\n  Combined bounds: X=[{bounds['min_x']:.0f}, {bounds['max_x']:.0f}], Y=[{bounds['min_y']:.0f}, {bounds['max_y']:.0f}]")

    # SVG dimensions
    svg_width = 900
    bounds_w = bounds['max_x'] - bounds['min_x']
    bounds_h = bounds['max_y'] - bounds['min_y']
    svg_height = int(svg_width * bounds_h / bounds_w)
    scale = svg_width / bounds_w

    def transform(x, y):
        return ((x - bounds['min_x']) * scale,
                (bounds['max_y'] - y) * scale)

    def generate_svg(entities, color):
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
                cx, cy = transform(e['cx'], e['cy'])
                r = max(e['r'] * scale, 2)
                start_rad = math.radians(e['start_angle'])
                end_rad = math.radians(e['end_angle'])
                x1 = cx + r * math.cos(start_rad)
                y1 = cy - r * math.sin(start_rad)
                x2 = cx + r * math.cos(end_rad)
                y2 = cy - r * math.sin(end_rad)
                angle_diff = (e['end_angle'] - e['start_angle']) % 360
                large_arc = 1 if angle_diff > 180 else 0
                svg.append(f'<path d="M {x1:.1f} {y1:.1f} A {r:.1f} {r:.1f} 0 {large_arc} 0 {x2:.1f} {y2:.1f}" '
                          f'fill="none" stroke="{color}" stroke-width="1.5" opacity="0.7"/>')
        return '\n'.join(svg)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal 1 - Superimposed Floor Plans</title>
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
        .toggles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }}

        .toggle-btn {{ display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: white; border: 2px solid #ddd;
                      border-radius: 6px; cursor: pointer; transition: all 0.3s; user-select: none; }}
        .toggle-btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        .toggle-btn.active {{ border-color: #2ecc71; background: #ecf9f2; }}
        .color-box {{ width: 24px; height: 24px; border-radius: 4px; border: 2px solid #333; flex-shrink: 0; }}
        .toggle-label {{ flex: 1; font-size: 14px; font-weight: 600; }}
        .toggle-count {{ font-size: 12px; color: #7f8c8d; }}

        .svg-container {{ padding: 30px; background: #fafafa; display: flex; justify-content: center; }}
        svg {{ border: 2px solid #ddd; border-radius: 8px; background: white; }}

        .info {{ padding: 15px; background: #d5f4e6; border-top: 3px solid #2ecc71; text-align: center; color: #27ae60; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Terminal 1 - Superimposed Floor Plans</h1>
            <p>Each floor normalized and overlaid | Click to toggle floors | Dome arcs visible</p>
        </div>

        <div class="controls">
            <div class="control-section">
                <h3>Floor Plans (Superimposed)</h3>
                <div class="toggles">
"""

    # Add toggle buttons for each floor
    for floor_name, y_min, y_max, color in floor_bounds:
        floor_data = floors[floor_name]
        count = len(floor_data['entities'])
        floor_id = floor_name.replace(' ', '_').replace('(', '').replace(')', '')
        html += f"""                    <div class="toggle-btn active" onclick="toggleLayer('{floor_id}')" id="toggle-{floor_id}">
                        <div class="color-box" style="background: {color};"></div>
                        <div style="flex: 1;">
                            <div class="toggle-label">{floor_name}</div>
                            <div class="toggle-count">{count} entities</div>
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

    # Add SVG groups for each floor
    for floor_name, y_min, y_max, color in floor_bounds:
        floor_data = floors[floor_name]
        floor_id = floor_name.replace(' ', '_').replace('(', '').replace(')', '')
        svg_content = generate_svg(floor_data['entities'], color)
        html += f"""                <g id="layer-{floor_id}" class="layer-group">
{svg_content}
                </g>
"""

    html += """            </svg>
        </div>

        <div class="info">
            Floors are superimposed - toggle individual floors to see each level. Dome arcs shown on each floor.
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

    output = base / "SourceFiles" / "Terminal1_Superimposed_Floors.html"
    with open(output, 'w') as f:
        f.write(html)

    print(f"\n{'='*80}")
    print("SUCCESS!")
    print(f"Output: file://{output.absolute()}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
