#!/usr/bin/env python3
"""
Generate SEPARATE 2D visualizations for STR and ARC disciplines
Solves the coordinate system issue - each discipline in its own viewport
"""

import ezdxf
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Terminal 1 bounds from cheatsheet
TERMINAL1_BOUNDS_STR = {
    'min_x': 349412,
    'max_x': 409412,
    'min_y': -216677,
    'max_y': -176677
}

TERMINAL1_BOUNDS_ARC = {
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
    """Check if point is within bounds"""
    return (bounds['min_x'] <= x <= bounds['max_x'] and
            bounds['min_y'] <= y <= bounds['max_y'])

def extract_floor_from_dxf(dxf_path: str, bounds: dict) -> Tuple[List, int, int, int]:
    """Extract entities from DXF file within bounds"""

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        entities = []
        circles, lines, polylines = 0, 0, 0

        for entity in msp:
            entity_type = entity.dxftype()

            if entity_type == 'CIRCLE':
                center = entity.dxf.center
                if point_in_bounds(center.x, center.y, bounds):
                    entities.append({
                        'type': 'circle',
                        'cx': center.x,
                        'cy': center.y,
                        'r': entity.dxf.radius
                    })
                    circles += 1

            elif entity_type == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                if (point_in_bounds(start.x, start.y, bounds) or
                    point_in_bounds(end.x, end.y, bounds)):
                    entities.append({
                        'type': 'line',
                        'x1': start.x, 'y1': start.y,
                        'x2': end.x, 'y2': end.y
                    })
                    lines += 1

            elif entity_type == 'LWPOLYLINE':
                points = list(entity.get_points())
                if any(point_in_bounds(p[0], p[1], bounds) for p in points):
                    entities.append({
                        'type': 'polyline',
                        'points': [(p[0], p[1]) for p in points],
                        'closed': entity.closed
                    })
                    polylines += 1

        return entities, circles, lines, polylines

    except Exception as e:
        print(f"Error reading {dxf_path}: {e}")
        return [], 0, 0, 0

def generate_svg(entities: List[Dict], bounds: dict, width: int = 600) -> str:
    """Generate SVG from entities"""

    if not entities:
        return f'<svg width="{width}" height="{width}"><text x="10" y="30" fill="red">No entities in bounds</text></svg>'

    # Calculate dimensions
    bounds_w = bounds['max_x'] - bounds['min_x']
    bounds_h = bounds['max_y'] - bounds['min_y']

    scale = width / bounds_w
    height = int(bounds_h * scale)

    # Transform function
    def transform(x, y):
        sx = (x - bounds['min_x']) * scale
        sy = (bounds['max_y'] - y) * scale  # Flip Y
        return sx, sy

    svg_parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']
    svg_parts.append(f'<rect width="{width}" height="{height}" fill="#f5f5f5"/>')

    # Draw entities
    for ent in entities:
        if ent['type'] == 'circle':
            cx, cy = transform(ent['cx'], ent['cy'])
            r = max(ent['r'] * scale, 2)
            svg_parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="#3498db" stroke="#2c3e50" stroke-width="1" opacity="0.8"/>')

        elif ent['type'] == 'line':
            x1, y1 = transform(ent['x1'], ent['y1'])
            x2, y2 = transform(ent['x2'], ent['y2'])
            svg_parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#2ecc71" stroke-width="1.5" opacity="0.7"/>')

        elif ent['type'] == 'polyline':
            pts = [transform(p[0], p[1]) for p in ent['points']]
            pts_str = ' '.join(f"{x:.1f},{y:.1f}" for x, y in pts)
            svg_parts.append(f'<polyline points="{pts_str}" fill="none" stroke="#e74c3c" stroke-width="1.5" opacity="0.7"/>')

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)

def generate_html_for_discipline(discipline: str, floor_data: List[Dict], output_path: str):
    """Generate HTML for a single discipline"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal 1 - {discipline} 2D Floor Plans (from DXF)</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
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
        .info {{
            background: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }}
        .floor-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .floor-card {{
            border: 2px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            background: white;
        }}
        .floor-header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 15px;
            font-weight: bold;
            font-size: 16px;
        }}
        .floor-content {{
            padding: 15px;
            background: #fafafa;
            text-align: center;
        }}
        svg {{
            border: 1px solid #ccc;
            background: white;
            border-radius: 4px;
        }}
        .stats {{
            padding: 12px;
            background: white;
            font-size: 13px;
            border-top: 1px solid #ddd;
        }}
        .stat-line {{
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
        }}
        .legend {{
            margin-top: 20px;
            padding: 15px;
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 8px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 3px;
            border: 1px solid #333;
            vertical-align: middle;
            margin-right: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ Terminal 1 - {discipline} Floor Plans</h1>
        <div class="subtitle">Direct DXF Extraction | Visual Proof of Source Data</div>

        <div class="info">
            <strong>📐 Source:</strong> Raw DXF files extracted with native coordinates<br>
            <strong>🎯 Purpose:</strong> Visual verification of source data before 3D transformation
        </div>

        <div class="legend">
            <strong>Legend:</strong><br>
            <div class="legend-item">
                <span class="legend-color" style="background: #3498db;"></span>
                <span>Circles (Columns/Piles)</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #2ecc71;"></span>
                <span>Lines (Beams/Grid)</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #e74c3c;"></span>
                <span>Polylines (Walls/Boundaries)</span>
            </div>
        </div>

        <div class="floor-grid">
"""

    # Add floor cards
    for floor in floor_data:
        html += f"""
            <div class="floor-card">
                <div class="floor-header">
                    {floor['floor_id']} - {floor['file_name']}
                </div>
                <div class="floor-content">
                    {floor['svg']}
                </div>
                <div class="stats">
                    <div class="stat-line">
                        <strong>Total Entities:</strong>
                        <span>{floor['total']}</span>
                    </div>
                    <div class="stat-line">
                        <span>Circles:</span>
                        <span>{floor['circles']}</span>
                    </div>
                    <div class="stat-line">
                        <span>Lines:</span>
                        <span>{floor['lines']}</span>
                    </div>
                    <div class="stat-line">
                        <span>Polylines:</span>
                        <span>{floor['polylines']}</span>
                    </div>
                </div>
            </div>
"""

    html += """
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ Generated: {output_path}")

def main():
    """Main execution"""

    print("="*80)
    print("GENERATING SEPARATE DISCIPLINE 2D VIEWS")
    print("="*80)

    config = load_building_config()
    base_path = Path(__file__).parent.parent

    # Process STR discipline
    print("\n📊 Processing STR (Structure)...")
    str_floors = []

    for floor in config['floor_levels']:
        floor_id = floor['level_id']
        str_dxf = floor['dxf_sources'].get('STR')

        if str_dxf:
            dxf_path = base_path / str_dxf
            if dxf_path.exists():
                print(f"  Extracting {floor_id}...")
                entities, circles, lines, polylines = extract_floor_from_dxf(str(dxf_path), TERMINAL1_BOUNDS_STR)
                total = circles + lines + polylines

                if total > 0:
                    svg = generate_svg(entities, TERMINAL1_BOUNDS_STR, 600)
                    str_floors.append({
                        'floor_id': floor_id,
                        'file_name': Path(str_dxf).name,
                        'svg': svg,
                        'circles': circles,
                        'lines': lines,
                        'polylines': polylines,
                        'total': total
                    })
                    print(f"    ✅ {total} entities ({circles} circles, {lines} lines, {polylines} polylines)")
                else:
                    print(f"    ⚠️  No entities in bounds")

    # Process ARC discipline
    print("\n🏛️ Processing ARC (Architecture)...")
    arc_floors = []

    for floor in config['floor_levels']:
        floor_id = floor['level_id']
        arc_dxf = floor['dxf_sources'].get('ARC')

        if arc_dxf:
            dxf_path = base_path / arc_dxf
            if dxf_path.exists():
                print(f"  Extracting {floor_id}...")
                entities, circles, lines, polylines = extract_floor_from_dxf(str(dxf_path), TERMINAL1_BOUNDS_ARC)
                total = circles + lines + polylines

                if total > 0:
                    svg = generate_svg(entities, TERMINAL1_BOUNDS_ARC, 600)
                    arc_floors.append({
                        'floor_id': floor_id,
                        'file_name': Path(arc_dxf).name,
                        'svg': svg,
                        'circles': circles,
                        'lines': lines,
                        'polylines': polylines,
                        'total': total
                    })
                    print(f"    ✅ {total} entities ({circles} circles, {lines} lines, {polylines} polylines)")
                else:
                    print(f"    ⚠️  No entities in bounds")

    # Generate HTML files
    print("\n📄 Generating HTML files...")

    if str_floors:
        str_output = base_path / "SourceFiles" / "Terminal1_STR_2D_Plans.html"
        generate_html_for_discipline("STR (Structure)", str_floors, str(str_output))

    if arc_floors:
        arc_output = base_path / "SourceFiles" / "Terminal1_ARC_2D_Plans.html"
        generate_html_for_discipline("ARC (Architecture)", arc_floors, str(arc_output))

    print("\n" + "="*80)
    print("✅ SUCCESS!")
    if str_floors:
        print(f"📄 STR: file://{str_output.absolute()}")
    if arc_floors:
        print(f"📄 ARC: file://{arc_output.absolute()}")
    print("="*80)

if __name__ == "__main__":
    main()
