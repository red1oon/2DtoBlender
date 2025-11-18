#!/usr/bin/env python3
"""
Generate Interactive HTML Visualization from DXF Files - Version 2
ACCURATE 2D representation for human inspection
Each discipline in separate panel with proper coordinate scaling
"""

import ezdxf
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any

# Color mapping
IFC_COLORS = {
    'IfcWall': '#e31a1c',
    'IfcColumn': '#b2df8a',
    'IfcBeam': '#808080',
    'IfcSlab': '#33a02c',
    'IfcDoor': '#ff7f00',
    'IfcWindow': '#6a3d9a',
    'IfcStair': '#a6cee3',
    'IfcRoof': '#fdbf6f',
    'Unknown': '#cccccc'
}

def classify_arc_entity(layer: str, entity_type: str) -> str:
    """Classify ARC entities"""
    layer_upper = layer.upper()
    if any(w in layer_upper for w in ['WALL', 'DINDING', 'W-']): return 'IfcWall'
    if any(c in layer_upper for c in ['COLUMN', 'TIANG', 'C-']): return 'IfcColumn'
    if 'ROOF' in layer_upper or 'ATAP' in layer_upper: return 'IfcRoof'
    if 'DOOR' in layer_upper: return 'IfcDoor'
    if 'WINDOW' in layer_upper: return 'IfcWindow'
    if entity_type == 'CIRCLE': return 'IfcColumn'
    if entity_type == 'LWPOLYLINE': return 'IfcWall'
    return 'Unknown'

def classify_str_entity(layer: str, entity_type: str) -> str:
    """Classify STR entities"""
    layer_upper = layer.upper()
    if 'COLUMN' in layer_upper or 'C-' in layer_upper: return 'IfcColumn'
    if 'BEAM' in layer_upper or 'B-' in layer_upper: return 'IfcBeam'
    if 'SLAB' in layer_upper: return 'IfcSlab'
    if entity_type == 'CIRCLE': return 'IfcColumn'
    if entity_type == 'LINE': return 'IfcBeam'
    return 'Unknown'

def extract_dxf_simple(dxf_path: str, discipline: str, bounds: Dict) -> Tuple[List, Dict, Dict]:
    """Simple extraction - returns list of shapes for SVG rendering"""

    print(f"\nExtracting {discipline} from {Path(dxf_path).name}")
    print(f"Bounds: X=[{bounds['min_x']:,}, {bounds['max_x']:,}] Y=[{bounds['min_y']:,}, {bounds['max_y']:,}]")

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    shapes = []
    stats = defaultdict(int)
    all_coords = []

    for entity in msp:
        if entity.dxftype() not in ['LINE', 'CIRCLE', 'LWPOLYLINE']:
            continue

        # Get center for filtering
        if entity.dxftype() == 'CIRCLE':
            center = entity.dxf.center
            x, y = center.x, center.y
        elif entity.dxftype() == 'LINE':
            start, end = entity.dxf.start, entity.dxf.end
            x, y = (start.x + end.x) / 2, (start.y + end.y) / 2
        elif entity.dxftype() == 'LWPOLYLINE':
            points = list(entity.get_points())
            if not points: continue
            x = sum(p[0] for p in points) / len(points)
            y = sum(p[1] for p in points) / len(points)
        else:
            continue

        # Filter
        if not (bounds['min_x'] <= x <= bounds['max_x'] and bounds['min_y'] <= y <= bounds['max_y']):
            continue

        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else 'UNKNOWN'
        ifc_class = classify_arc_entity(layer, entity.dxftype()) if discipline == 'ARC' else classify_str_entity(layer, entity.dxftype())

        # Extract geometry
        if entity.dxftype() == 'CIRCLE':
            center = entity.dxf.center
            shapes.append({
                'type': 'circle',
                'cx': center.x,
                'cy': center.y,
                'r': entity.dxf.radius,
                'class': ifc_class,
                'layer': layer
            })
            all_coords.extend([(center.x - entity.dxf.radius, center.y), (center.x + entity.dxf.radius, center.y)])

        elif entity.dxftype() == 'LINE':
            start, end = entity.dxf.start, entity.dxf.end
            shapes.append({
                'type': 'line',
                'x1': start.x, 'y1': start.y,
                'x2': end.x, 'y2': end.y,
                'class': ifc_class,
                'layer': layer
            })
            all_coords.extend([(start.x, start.y), (end.x, end.y)])

        elif entity.dxftype() == 'LWPOLYLINE':
            points = list(entity.get_points())
            if len(points) >= 2:
                shapes.append({
                    'type': 'polyline',
                    'points': [(p[0], p[1]) for p in points],
                    'class': ifc_class,
                    'layer': layer
                })
                all_coords.extend([(p[0], p[1]) for p in points])

        stats[ifc_class] += 1

    # Calculate actual bounds
    if all_coords:
        xs, ys = zip(*all_coords)
        actual_bounds = {'min_x': min(xs), 'max_x': max(xs), 'min_y': min(ys), 'max_y': max(ys)}
    else:
        actual_bounds = bounds

    print(f"Extracted: {len(shapes)} shapes")
    for cls, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {cls:15s}: {count:4d}")

    return shapes, dict(stats), actual_bounds

def generate_html(arc_shapes, arc_stats, arc_bounds, str_shapes, str_stats, str_bounds, output_path):
    """Generate HTML with embedded SVG visualization"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal 1 DXF - Source of Truth Visualization</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }}
        .container {{ max-width: 1800px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header p {{ font-size: 14px; opacity: 0.9; }}
        .note {{ background: #fff3cd; border-left: 5px solid #ffc107; padding: 15px 20px; color: #856404; font-size: 13px; }}
        .panels {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px; }}
        .panel {{ border: 2px solid #ddd; border-radius: 8px; background: white; overflow: hidden; }}
        .panel-header {{ padding: 12px 15px; font-weight: bold; color: white; font-size: 16px; }}
        .arc-header {{ background: #ff7f00; }}
        .str-header {{ background: #808080; }}
        .svg-wrapper {{ background: #f5f5f5; padding: 10px; overflow: auto; max-height: 600px; }}
        svg {{ background: white; display: block; border: 1px solid #ddd; }}
        .stats {{ padding: 12px 15px; background: #fafafa; font-size: 12px; font-family: monospace; border-top: 1px solid #ddd; }}
        .stat-line {{ display: flex; justify-content: space-between; padding: 3px 0; }}
        .legend {{ padding: 12px 15px; background: #fff; border-top: 1px solid #ddd; }}
        .legend-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 11px; }}
        .legend-color {{ width: 16px; height: 16px; border-radius: 3px; border: 1px solid #999; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Terminal 1 Main Building - DXF Source of Truth</h1>
            <p>Accurate 2D Visualization for Human Inspection | Direct DXF Extraction | Terminal 1 DOME Building</p>
        </div>

        <div class="note">
            ⚠️ <strong>Coordinate System Note:</strong> ARC and STR are in completely different DXF coordinate systems (consultants used different local origins). ARC center: -1,592km, STR center: +32km. This is normal for multi-consultant projects. Each is shown separately for accurate inspection.
        </div>

        <div class="panels">
            <!-- ARC Panel -->
            <div class="panel">
                <div class="panel-header arc-header">ARC (Architect) - Terminal 1 DOME Building</div>
                <div class="stats">
                    <div class="stat-line"><strong>Total Elements:</strong> <span>{len(arc_shapes)}</span></div>
                    {chr(10).join(f'<div class="stat-line"><span>{cls}:</span> <span>{count}</span></div>' for cls, count in sorted(arc_stats.items(), key=lambda x: -x[1]))}
                    <div class="stat-line"><strong>Coordinate Range:</strong></div>
                    <div class="stat-line"><span>X:</span> <span>{arc_bounds['min_x']:.0f} to {arc_bounds['max_x']:.0f} mm ({(arc_bounds['max_x']-arc_bounds['min_x'])/1000:.1f}m)</span></div>
                    <div class="stat-line"><span>Y:</span> <span>{arc_bounds['min_y']:.0f} to {arc_bounds['max_y']:.0f} mm ({(arc_bounds['max_y']-arc_bounds['min_y'])/1000:.1f}m)</span></div>
                </div>
                <div class="svg-wrapper">
                    <svg id="arc-svg" width="850" height="550"></svg>
                </div>
                <div class="legend">
                    <div class="legend-grid">
                        {chr(10).join(f'<div class="legend-item"><div class="legend-color" style="background:{IFC_COLORS.get(cls, "#ccc")}"></div><span>{cls} ({count})</span></div>' for cls, count in sorted(arc_stats.items(), key=lambda x: -x[1]))}
                    </div>
                </div>
            </div>

            <!-- STR Panel -->
            <div class="panel">
                <div class="panel-header str-header">STR (Structure) - Terminal 1 Structural Frame</div>
                <div class="stats">
                    <div class="stat-line"><strong>Total Elements:</strong> <span>{len(str_shapes)}</span></div>
                    {chr(10).join(f'<div class="stat-line"><span>{cls}:</span> <span>{count}</span></div>' for cls, count in sorted(str_stats.items(), key=lambda x: -x[1]))}
                    <div class="stat-line"><strong>Coordinate Range:</strong></div>
                    <div class="stat-line"><span>X:</span> <span>{str_bounds['min_x']:.0f} to {str_bounds['max_x']:.0f} mm ({(str_bounds['max_x']-str_bounds['min_x'])/1000:.1f}m)</span></div>
                    <div class="stat-line"><span>Y:</span> <span>{str_bounds['min_y']:.0f} to {str_bounds['max_y']:.0f} mm ({(str_bounds['max_y']-str_bounds['min_y'])/1000:.1f}m)</span></div>
                    <div class="stat-line"><strong>IFC Ground Truth:</strong> <span>68 columns + 432 beams</span></div>
                </div>
                <div class="svg-wrapper">
                    <svg id="str-svg" width="850" height="550"></svg>
                </div>
                <div class="legend">
                    <div class="legend-grid">
                        {chr(10).join(f'<div class="legend-item"><div class="legend-color" style="background:{IFC_COLORS.get(cls, "#ccc")}"></div><span>{cls} ({count})</span></div>' for cls, count in sorted(str_stats.items(), key=lambda x: -x[1]))}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const arcShapes = {json.dumps(arc_shapes, indent=2)};
        const arcBounds = {json.dumps(arc_bounds)};
        const strShapes = {json.dumps(str_shapes, indent=2)};
        const strBounds = {json.dumps(str_bounds)};
        const colors = {json.dumps(IFC_COLORS)};

        function renderSVG(svgId, shapes, bounds) {{
            const svg = document.getElementById(svgId);
            const width = 850, height = 550, padding = 30;

            // Calculate scale
            const dataWidth = bounds.max_x - bounds.min_x;
            const dataHeight = bounds.max_y - bounds.min_y;
            const scaleX = (width - 2 * padding) / dataWidth;
            const scaleY = (height - 2 * padding) / dataHeight;
            const scale = Math.min(scaleX, scaleY) * 0.95; // 95% to add margin

            // Center offset
            const centerX = (bounds.min_x + bounds.max_x) / 2;
            const centerY = (bounds.min_y + bounds.max_y) / 2;
            const offsetX = width / 2 - centerX * scale;
            const offsetY = height / 2 + centerY * scale; // Flip Y

            console.log(`Rendering ${{shapes.length}} shapes, scale=${{scale.toFixed(6)}}`);

            // Background
            const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            bg.setAttribute('width', width);
            bg.setAttribute('height', height);
            bg.setAttribute('fill', '#ffffff');
            svg.appendChild(bg);

            // Render shapes
            shapes.forEach((shape, idx) => {{
                const color = colors[shape.class] || '#cccccc';

                if (shape.type === 'circle') {{
                    const cx = shape.cx * scale + offsetX;
                    const cy = height - (shape.cy * scale + offsetY);
                    const r = Math.max(2, shape.r * scale);

                    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                    circle.setAttribute('cx', cx);
                    circle.setAttribute('cy', cy);
                    circle.setAttribute('r', r);
                    circle.setAttribute('fill', color);
                    circle.setAttribute('stroke', '#000');
                    circle.setAttribute('stroke-width', '0.5');
                    circle.setAttribute('opacity', '0.8');
                    svg.appendChild(circle);

                }} else if (shape.type === 'line') {{
                    const x1 = shape.x1 * scale + offsetX;
                    const y1 = height - (shape.y1 * scale + offsetY);
                    const x2 = shape.x2 * scale + offsetX;
                    const y2 = height - (shape.y2 * scale + offsetY);

                    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    line.setAttribute('x1', x1);
                    line.setAttribute('y1', y1);
                    line.setAttribute('x2', x2);
                    line.setAttribute('y2', y2);
                    line.setAttribute('stroke', color);
                    line.setAttribute('stroke-width', '1.5');
                    line.setAttribute('opacity', '0.8');
                    svg.appendChild(line);

                }} else if (shape.type === 'polyline') {{
                    const points = shape.points.map(p => {{
                        const x = p[0] * scale + offsetX;
                        const y = height - (p[1] * scale + offsetY);
                        return `${{x}},${{y}}`;
                    }}).join(' ');

                    const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
                    polyline.setAttribute('points', points);
                    polyline.setAttribute('fill', 'none');
                    polyline.setAttribute('stroke', color);
                    polyline.setAttribute('stroke-width', '1.5');
                    polyline.setAttribute('opacity', '0.8');
                    svg.appendChild(polyline);
                }}
            }});

            console.log(`✓ Rendered ${{shapes.length}} shapes to #${{svgId}}`);
        }}

        // Render both
        renderSVG('arc-svg', arcShapes, arcBounds);
        renderSVG('str-svg', strShapes, strBounds);
    </script>
</body>
</html>
"""

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"\n✓ Interactive HTML saved to: {output_path}")

def main():
    # Cheatsheet bounds (source of truth)
    arc_filter = {
        'min_x': -1620000, 'max_x': -1560000,
        'min_y': -90000, 'max_y': -40000
    }

    str_filter = {
        'min_x': 2398, 'max_x': 62398,
        'min_y': -85755, 'max_y': -45755
    }

    # DXF paths
    base = Path(__file__).parent.parent / 'SourceFiles' / 'TERMINAL1DXF'
    arc_dxf = base / '01 ARCHITECT' / '2. BANGUNAN TERMINAL 1.dxf'
    str_dxf = base / '02 STRUCTURE' / 'T1-2.1_Lyt_1FB_e1P1_240530.dxf'

    # Extract
    print("\n" + "="*80)
    print("GENERATING DXF SOURCE OF TRUTH VISUALIZATION")
    print("="*80)

    arc_shapes, arc_stats, arc_bounds = extract_dxf_simple(str(arc_dxf), 'ARC', arc_filter)
    str_shapes, str_stats, str_bounds = extract_dxf_simple(str(str_dxf), 'STR', str_filter)

    # Generate HTML
    output = Path(__file__).parent.parent / 'SourceFiles' / 'Terminal1_DXF_SourceOfTruth.html'
    generate_html(arc_shapes, arc_stats, arc_bounds, str_shapes, str_stats, str_bounds, str(output))

    print(f"\n✓ Open: file://{output.absolute()}")
    print("="*80)

if __name__ == '__main__':
    main()
