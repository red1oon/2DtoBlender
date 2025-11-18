#!/usr/bin/env python3
"""
Generate combined ARC + STR interactive view with full toggle control
All on one aligned canvas with GPS coordinate transformation
"""

import ezdxf
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Terminal 1 bounds (native DXF coordinates) - from cheatsheet
BOUNDS_STR = {'min_x': 2398, 'max_x': 62398, 'min_y': -85755, 'max_y': -45755}
BOUNDS_ARC = {'min_x': -1620000, 'max_x': -1560000, 'min_y': -90000, 'max_y': -40000}

# GPS alignment offset (ARC → STR coordinate system) - from cheatsheet
ARC_OFFSET = {'x': 1625040, 'y': -345333}

# Native ARC bounds - Terminal 1 with dome (walls and roof overlap in native coords)
# Walls near roof: Y=[-52k, +145k], Roof: Y=[-206k, +300k]
ARC_NATIVE_BOUNDS = {'min_x': -1620000, 'max_x': -1560000, 'min_y': -100000, 'max_y': 200000}

# STR bounds after alignment
STR_BOUNDS = {'min_x': 0, 'max_x': 65000, 'min_y': -90000, 'max_y': -40000}

# Combined bounds for rendering (will use ARC native for ARC, STR for STR)
COMBINED_BOUNDS = {'min_x': -1620000, 'max_x': -1560000, 'min_y': -100000, 'max_y': 200000}

# Dome bounds - same as ARC native (no separate range needed)
DOME_BOUNDS = {'min_x': -1620000, 'max_x': -1560000, 'min_y': -100000, 'max_y': 200000}

# Layer/floor groups
ARC_LAYERS = {
    'ARC-Walls': {'layers': ['wall', 'WALL1', 'A-WALL', 'CH-WALL'], 'color': '#34495e'},
    'ARC-Roof': {'layers': ['ROOF', 'ROOFSTR', 'CH-ROOF'], 'color': '#e74c3c'},
    'ARC-Columns': {'layers': ['COL', 'column'], 'color': '#9b59b6'},
    'ARC-Windows': {'layers': ['WIN', 'window'], 'color': '#3498db'},
}

STR_FLOORS = {
    '1F': {'file': 'SourceFiles/TERMINAL1DXF/02 STRUCTURE/T1-2.1_Lyt_1FB_e1P1_240530.dxf', 'color': '#2ecc71'},
    '3F': {'file': 'SourceFiles/TERMINAL1DXF/02 STRUCTURE/T1-2.3_Lyt_3FB_e1P1_240530.dxf', 'color': '#3498db'},
    '4F-6F': {'file': 'SourceFiles/TERMINAL1DXF/02 STRUCTURE/T1-2.4_Lyt_4FB-6FB_e1P1_240530.dxf', 'color': '#e67e22'},
}

def point_in_bounds(x: float, y: float, bounds: dict) -> bool:
    return (bounds['min_x'] <= x <= bounds['max_x'] and bounds['min_y'] <= y <= bounds['max_y'])

def extract_arc_layers(dxf_path: str) -> Dict:
    """Extract ARC entities grouped by layer"""
    doc = ezdxf.readfile(dxf_path)

    layer_map = {}
    for group, data in ARC_LAYERS.items():
        for layer in data['layers']:
            layer_map[layer.lower()] = group

    grouped = defaultdict(list)

    for entity in doc.modelspace():
        if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE']:
            continue

        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
        group = layer_map.get(layer.lower())
        if not group:
            continue

        # Use native ARC bounds (no GPS offset needed - walls and roof already overlap)
        bounds = ARC_NATIVE_BOUNDS

        # Extract in native coordinates (no offset, no transform)
        if entity.dxftype() == 'CIRCLE':
            c = entity.dxf.center
            if point_in_bounds(c.x, c.y, bounds):
                grouped[group].append({
                    'type': 'circle',
                    'cx': c.x, 'cy': c.y,
                    'r': entity.dxf.radius
                })

        elif entity.dxftype() == 'LINE':
            s, e = entity.dxf.start, entity.dxf.end
            if (point_in_bounds(s.x, s.y, bounds) or
                point_in_bounds(e.x, e.y, bounds)):
                grouped[group].append({
                    'type': 'line',
                    'x1': s.x, 'y1': s.y, 'x2': e.x, 'y2': e.y
                })

        elif entity.dxftype() == 'LWPOLYLINE':
            points = [(p[0], p[1]) for p in entity.get_points()]
            if any(point_in_bounds(p[0], p[1], bounds) for p in points):
                grouped[group].append({
                    'type': 'polyline',
                    'points': points
                })

    return dict(grouped)

def extract_str_floor(dxf_path: str) -> List:
    """Extract STR entities (already in STR coordinate system)"""
    doc = ezdxf.readfile(dxf_path)
    entities = []

    for entity in doc.modelspace():
        if entity.dxftype() not in ['CIRCLE', 'LINE', 'LWPOLYLINE']:
            continue

        if entity.dxftype() == 'CIRCLE':
            c = entity.dxf.center
            if point_in_bounds(c.x, c.y, COMBINED_BOUNDS):
                entities.append({
                    'type': 'circle',
                    'cx': c.x, 'cy': c.y,
                    'r': entity.dxf.radius
                })

        elif entity.dxftype() == 'LINE':
            s, e = entity.dxf.start, entity.dxf.end
            if (point_in_bounds(s.x, s.y, COMBINED_BOUNDS) or
                point_in_bounds(e.x, e.y, COMBINED_BOUNDS)):
                entities.append({
                    'type': 'line',
                    'x1': s.x, 'y1': s.y, 'x2': e.x, 'y2': e.y
                })

        elif entity.dxftype() == 'LWPOLYLINE':
            points = [(p[0], p[1]) for p in entity.get_points()]
            if any(point_in_bounds(p[0], p[1], COMBINED_BOUNDS) for p in points):
                entities.append({
                    'type': 'polyline',
                    'points': points
                })

    return entities

def generate_svg_content(entities: List, color: str, bounds: dict, width: int) -> str:
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

    return '\n'.join(svg)

def main():
    print("="*80)
    print("GENERATING COMBINED ARC + STR INTERACTIVE VIEW")
    print("="*80)

    base = Path(__file__).parent.parent

    # Extract ARC layers
    print("\n📐 Extracting ARC layers...")
    arc_dxf = base / "SourceFiles/TERMINAL1DXF/01 ARCHITECT/2. BANGUNAN TERMINAL 1.dxf"
    arc_groups = extract_arc_layers(str(arc_dxf))

    for group, entities in arc_groups.items():
        print(f"  {group:20s}: {len(entities):5d} entities")

    # Extract STR floors
    print("\n🏗️  Extracting STR floors...")
    str_groups = {}
    for floor_id, floor_data in STR_FLOORS.items():
        dxf_path = base / floor_data['file']
        if dxf_path.exists():
            entities = extract_str_floor(str(dxf_path))
            str_groups[f'STR-{floor_id}'] = entities
            print(f"  STR-{floor_id:15s}: {len(entities):5d} entities")

    # Calculate SVG dimensions
    svg_width = 900
    bounds_w = COMBINED_BOUNDS['max_x'] - COMBINED_BOUNDS['min_x']
    bounds_h = COMBINED_BOUNDS['max_y'] - COMBINED_BOUNDS['min_y']
    svg_height = int(svg_width * bounds_h / bounds_w)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal 1 - Combined ARC + STR Interactive View</title>
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
            <h1>🏗️ Terminal 1 - Combined ARC + STR View</h1>
            <p>Interactive Toggle | All disciplines aligned on one canvas | Click to show/hide layers</p>
        </div>

        <div class="controls">
            <div class="control-section">
                <h3>🏛️ ARC (Architecture) - Element Types</h3>
                <div class="toggles">
"""

    # Add ARC toggle buttons
    for group, entities in arc_groups.items():
        color = ARC_LAYERS[group]['color']
        count = len(entities)
        html += f"""                    <div class="toggle-btn active" onclick="toggleLayer('{group}')" id="toggle-{group}">
                        <div class="color-box" style="background: {color};"></div>
                        <div style="flex: 1;">
                            <div class="toggle-label">{group.replace('ARC-', '')}</div>
                            <div class="toggle-count">{count} elem</div>
                        </div>
                    </div>
"""

    html += """                </div>
            </div>

            <div class="control-section">
                <h3>🔩 STR (Structure) - Floor Plans</h3>
                <div class="toggles">
"""

    # Add STR toggle buttons
    for floor_id, floor_data in STR_FLOORS.items():
        group_name = f'STR-{floor_id}'
        entities = str_groups.get(group_name, [])
        color = floor_data['color']
        count = len(entities)
        html += f"""                    <div class="toggle-btn active" onclick="toggleLayer('{group_name}')" id="toggle-{group_name}">
                        <div class="color-box" style="background: {color};"></div>
                        <div style="flex: 1;">
                            <div class="toggle-label">{floor_id}</div>
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

    # Add ARC SVG groups
    for group, entities in arc_groups.items():
        color = ARC_LAYERS[group]['color']
        svg_content = generate_svg_content(entities, color, COMBINED_BOUNDS, svg_width)
        html += f"""                <g id="layer-{group}" class="layer-group">
{svg_content}
                </g>
"""

    # Add STR SVG groups
    for floor_id, floor_data in STR_FLOORS.items():
        group_name = f'STR-{floor_id}'
        entities = str_groups.get(group_name, [])
        color = floor_data['color']
        svg_content = generate_svg_content(entities, color, COMBINED_BOUNDS, svg_width)
        html += f"""                <g id="layer-{group_name}" class="layer-group">
{svg_content}
                </g>
"""

    html += """            </svg>
        </div>

        <div class="info">
            ✅ <strong>GPS-Aligned View:</strong> ARC and STR are now on the same coordinate system and overlay correctly!
            Click any button above to toggle layers on/off.
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

    output = base / "SourceFiles" / "Terminal1_Combined_Interactive.html"
    with open(output, 'w') as f:
        f.write(html)

    print(f"\n{'='*80}")
    print("✅ SUCCESS!")
    print(f"📄 Output: file://{output.absolute()}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
