#!/usr/bin/env python3
"""
Generate PROPER 2D Floor Plans from Database
Each floor is a true plan view - all elements projected to XY coordinates
NOT stacked rows, but actual overlapping architectural floor plans
"""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Color scheme
DISCIPLINE_COLORS = {
    'ARC': {
        'IfcWall': '#2c3e50',      # Dark gray
        'IfcColumn': '#9b59b6',    # Purple
        'IfcDoor': '#e74c3c',      # Red
        'IfcWindow': '#3498db',    # Blue
        'IfcRoof': '#f39c12',      # Orange
        'IfcStair': '#1abc9c',     # Teal
        'Unknown': '#bdc3c7'       # Light gray
    },
    'STR': {
        'IfcColumn': '#3498db',    # Blue circles
        'IfcBeam': '#2ecc71',      # Green lines
        'IfcSlab': '#f39c12',      # Orange
        'Unknown': '#95a5a6'       # Gray
    }
}

FLOOR_LABELS = {
    'GB': 'Ground Basement',
    '1F': '1st Floor',
    '3F': '3rd Floor',
    '4F': '4th Floor',
    '5F': '5th Floor',
    '6F': '6th Floor',
    'RF': 'Roof'
}

def load_floor_data_from_db(db_path: str, discipline: str, floor_id: str) -> Tuple[List[Dict], Dict]:
    """Extract all elements for a specific floor from database"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get elements for this floor + discipline (no detailed geometry, just use bbox)
    query = """
        SELECT
            m.guid,
            m.ifc_class,
            t.center_x,
            t.center_y,
            t.center_z,
            t.bbox_length,
            t.bbox_width,
            t.bbox_height
        FROM elements_meta m
        JOIN element_transforms t ON m.guid = t.guid
        WHERE m.storey = ? AND m.discipline = ?
    """

    cursor.execute(query, (floor_id, discipline))
    rows = cursor.fetchall()

    elements = []
    stats = defaultdict(int)

    for row in rows:
        guid, ifc_class, cx, cy, cz, length, width, height = row

        element = {
            'id': guid,
            'ifc_class': ifc_class,
            'x': cx,
            'y': cy,
            'z': cz,
            'width': width or 0.5,  # Default 0.5m if missing
            'height': height or 0.5,
            'depth': length or 0.5,
            'geom': None  # We'll use bbox for 2D visualization
        }

        elements.append(element)
        stats[ifc_class] += 1

    conn.close()

    return elements, dict(stats)

def calculate_bounds(elements: List[Dict]) -> Dict:
    """Calculate XY bounding box for elements"""

    xs, ys = [], []

    for elem in elements:
        x, y = elem['x'], elem['y']
        w, d = elem['width'], elem['depth']

        # Add corners
        xs.extend([x - w/2, x + w/2])
        ys.extend([y - d/2, y + d/2])

        # If has geometry, add those points too
        if elem['geom'] and 'vertices' in elem['geom']:
            for vtx in elem['geom']['vertices']:
                xs.append(vtx[0])
                ys.append(vtx[1])

    if not xs:
        return {'min_x': 0, 'max_x': 1, 'min_y': 0, 'max_y': 1}

    padding = 2.0  # 2m padding
    return {
        'min_x': min(xs) - padding,
        'max_x': max(xs) + padding,
        'min_y': min(ys) - padding,
        'max_y': max(ys) + padding
    }

def generate_svg_for_floor(elements: List[Dict], bounds: Dict, discipline: str, svg_width: int = 800) -> str:
    """Generate SVG content for a single floor (plan view)"""

    if not elements:
        return ""

    # Calculate SVG dimensions
    width_m = bounds['max_x'] - bounds['min_x']
    height_m = bounds['max_y'] - bounds['min_y']

    # Ensure minimum size
    if width_m < 1 or height_m < 1:
        return ""

    scale = svg_width / width_m
    svg_height = int(height_m * scale)

    # Add padding
    padding = 20  # pixels

    # Transform function: world coords → SVG coords
    def transform(x, y):
        """Convert world XY to SVG coordinates"""
        sx = (x - bounds['min_x']) * scale + padding
        sy = (bounds['max_y'] - y) * scale + padding  # Flip Y for SVG
        return sx, sy

    # Adjust SVG size for padding
    svg_width_total = svg_width + 2 * padding
    svg_height_total = svg_height + 2 * padding

    svg_parts = []
    colors = DISCIPLINE_COLORS.get(discipline, {})

    # Sort by drawing order: slabs → beams → walls → columns
    draw_order = {'IfcSlab': 0, 'IfcBeam': 1, 'IfcWall': 2, 'IfcColumn': 3, 'IfcDoor': 4, 'IfcWindow': 5}
    sorted_elements = sorted(elements, key=lambda e: draw_order.get(e['ifc_class'], 99))

    for elem in sorted_elements:
        color = colors.get(elem['ifc_class'], '#cccccc')
        ifc_class = elem['ifc_class']

        # If has detailed geometry, use it
        if elem['geom'] and 'vertices' in elem['geom']:
            vertices = elem['geom']['vertices']
            if len(vertices) >= 2:
                # Project vertices to XY plane
                points = [transform(v[0], v[1]) for v in vertices]
                points_str = ' '.join(f"{x:.2f},{y:.2f}" for x, y in points)

                # Determine if should fill or stroke
                if ifc_class in ['IfcSlab', 'IfcWall']:
                    svg_parts.append(f'<polyline points="{points_str}" fill="{color}" fill-opacity="0.3" stroke="{color}" stroke-width="1.5"/>')
                else:
                    svg_parts.append(f'<polyline points="{points_str}" fill="none" stroke="{color}" stroke-width="2"/>')

        # Otherwise use simple box representation
        else:
            cx, cy = transform(elem['x'], elem['y'])

            # Columns as circles
            if ifc_class == 'IfcColumn':
                # Typical column diameter 540mm = 0.54m
                radius = max(0.27 * scale, 5)  # At least 5px for visibility
                svg_parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" fill="{color}" stroke="black" stroke-width="1.5" opacity="0.9"/>')

            # Beams as lines (use width/depth to show extent)
            elif ifc_class == 'IfcBeam':
                # Draw as a thick line
                w, d = elem['width'] * scale, elem['depth'] * scale
                # Ensure minimum length for visibility
                w = max(w, 5)
                d = max(d, 5)
                if w > d:  # Horizontal beam
                    svg_parts.append(f'<line x1="{cx-w/2:.2f}" y1="{cy:.2f}" x2="{cx+w/2:.2f}" y2="{cy:.2f}" stroke="{color}" stroke-width="3" opacity="0.9"/>')
                else:  # Vertical beam
                    svg_parts.append(f'<line x1="{cx:.2f}" y1="{cy-d/2:.2f}" x2="{cx:.2f}" y2="{cy+d/2:.2f}" stroke="{color}" stroke-width="3" opacity="0.9"/>')

            # Walls/slabs as rectangles
            else:
                w, d = elem['width'] * scale, elem['depth'] * scale
                # Ensure minimum size for visibility
                w = max(w, 2)
                d = max(d, 2)
                x1, y1 = cx - w/2, cy - d/2
                svg_parts.append(f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{w:.2f}" height="{d:.2f}" fill="{color}" fill-opacity="0.6" stroke="{color}" stroke-width="1.5"/>')

    # Add background and return SVG
    svg_bg = f'<rect width="{svg_width_total}" height="{svg_height_total}" fill="#fafafa"/>'
    return f'<svg width="{svg_width_total}" height="{svg_height_total}" xmlns="http://www.w3.org/2000/svg">\n{svg_bg}\n' + '\n'.join(svg_parts) + '\n</svg>'

def generate_html(database_path: str, output_path: str):
    """Generate interactive HTML with proper floor plans"""

    db_path = Path(database_path)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print(f"\n{'='*80}")
    print("GENERATING PROPER 2D FLOOR PLANS FROM DATABASE")
    print(f"{'='*80}\n")

    # Extract all floors from database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT storey FROM elements_meta ORDER BY storey")
    floors = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"Found {len(floors)} floors: {', '.join(floors)}\n")

    # Build floor plan data
    floor_plans = []

    for floor_id in floors:
        print(f"Processing {floor_id}...")

        # Get STR data
        str_elements, str_stats = load_floor_data_from_db(str(db_path), 'STR', floor_id)

        # Get ARC data
        arc_elements, arc_stats = load_floor_data_from_db(str(db_path), 'ARC', floor_id)

        if not str_elements and not arc_elements:
            print(f"  ⚠️  No elements found, skipping")
            continue

        # Calculate bounds (use ARC if available, otherwise STR)
        if arc_elements:
            bounds = calculate_bounds(arc_elements)
        else:
            bounds = calculate_bounds(str_elements)

        # Generate SVGs
        str_svg = generate_svg_for_floor(str_elements, bounds, 'STR') if str_elements else ""
        arc_svg = generate_svg_for_floor(arc_elements, bounds, 'ARC') if arc_elements else ""

        floor_plans.append({
            'id': floor_id,
            'label': FLOOR_LABELS.get(floor_id, floor_id),
            'str_count': len(str_elements),
            'arc_count': len(arc_elements),
            'str_stats': str_stats,
            'arc_stats': arc_stats,
            'str_svg': str_svg,
            'arc_svg': arc_svg
        })

        print(f"  ✅ STR: {len(str_elements)} elements, ARC: {len(arc_elements)} elements")

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal 1 - Proper 2D Floor Plans</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; }}
        .container {{ max-width: 1900px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); padding: 30px; }}
        h1 {{ text-align: center; color: #2c3e50; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 20px; font-size: 14px; }}
        .info-box {{ background: #d5f4e6; border-left: 5px solid #2ecc71; padding: 15px; margin-bottom: 20px; border-radius: 4px; }}
        .info-box strong {{ color: #27ae60; }}

        .floor-selector {{ display: flex; gap: 10px; justify-content: center; margin-bottom: 30px; flex-wrap: wrap; }}
        .floor-btn {{ padding: 10px 20px; background: #ecf0f1; border: 2px solid #bdc3c7; border-radius: 6px; cursor: pointer; font-weight: bold; transition: all 0.3s; }}
        .floor-btn:hover {{ border-color: #3498db; transform: translateY(-2px); }}
        .floor-btn.active {{ background: #3498db; color: white; border-color: #2980b9; }}

        .floor-view {{ display: none; }}
        .floor-view.active {{ display: block; }}

        .floor-header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .floor-header h2 {{ margin: 0 0 5px 0; }}
        .floor-header p {{ margin: 0; font-size: 14px; opacity: 0.9; }}

        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .panel {{ background: #f8f9fa; border: 2px solid #ddd; border-radius: 8px; overflow: hidden; }}
        .panel h3 {{ margin: 0; padding: 15px; background: white; border-bottom: 2px solid #3498db; color: #2c3e50; }}
        .svg-container {{ padding: 20px; background: white; overflow: auto; text-align: center; }}
        svg {{ border: 1px solid #ddd; border-radius: 4px; background: #fafafa; }}

        .stats {{ padding: 15px; background: white; font-size: 12px; font-family: 'Courier New', monospace; }}
        .stat-line {{ display: flex; justify-content: space-between; padding: 3px 0; }}
        .stat-line:nth-child(even) {{ background: #f8f9fa; }}

        .legend {{ padding: 15px; background: #f8f9fa; border-top: 2px solid #ddd; }}
        .legend-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 3px; border: 1px solid #333; }}

    </style>
</head>
<body>
    <div class="container">
        <h1>🏢 Terminal 1 Main Building - Proper 2D Floor Plans</h1>
        <div class="subtitle">True Plan View | All Elements Projected to XY Coordinates | Left: STR (Structure) | Right: ARC (Architecture)</div>

        <div class="info-box">
            <strong>✅ CORRECT 2D FLOOR PLANS:</strong> Each floor shows all elements at their actual XY positions (like real architectural drawings).
            Columns, beams, walls, and other elements overlap naturally. Toggle between floors to see each level separately.
        </div>

        <div class="floor-selector">
"""

    # Add floor selector buttons
    for i, floor in enumerate(floor_plans):
        active = 'active' if i == 0 else ''
        html += f"""            <div class="floor-btn {active}" onclick="showFloor('{floor['id']}')">{floor['label']} ({floor['str_count'] + floor['arc_count']} elem)</div>\n"""

    html += """        </div>\n\n"""

    # Add floor views
    for i, floor in enumerate(floor_plans):
        active = 'active' if i == 0 else ''
        html += f"""        <div class="floor-view {active}" id="floor-{floor['id']}">
            <div class="floor-header">
                <h2>{floor['label']} ({floor['id']})</h2>
                <p>STR: {floor['str_count']} elements | ARC: {floor['arc_count']} elements</p>
            </div>

            <div class="grid">
                <!-- STR Panel -->
                <div class="panel">
                    <h3>STR - Structural ({floor['str_count']} elements)</h3>
                    <div class="svg-container">
                        {floor['str_svg'] or '<p style="padding:40px;color:#999;">No STR elements on this floor</p>'}
                    </div>
                    <div class="stats">
"""

        # Add STR stats
        for cls, count in sorted(floor['str_stats'].items(), key=lambda x: -x[1]):
            html += f"""                        <div class="stat-line"><span>{cls}:</span><span>{count}</span></div>\n"""

        html += """                    </div>
                    <div class="legend">
                        <div class="legend-grid">
"""

        # Add STR legend
        for cls in floor['str_stats'].keys():
            color = DISCIPLINE_COLORS['STR'].get(cls, '#cccccc')
            html += f"""                            <div class="legend-item"><div class="legend-color" style="background:{color}"></div><span>{cls}</span></div>\n"""

        html += """                        </div>
                    </div>
                </div>

                <!-- ARC Panel -->
                <div class="panel">
                    <h3>ARC - Architecture ({floor['arc_count']} elements)</h3>
                    <div class="svg-container">
                        {floor['arc_svg'] or '<p style="padding:40px;color:#999;">No ARC elements on this floor</p>'}
                    </div>
                    <div class="stats">
"""

        # Add ARC stats
        for cls, count in sorted(floor['arc_stats'].items(), key=lambda x: -x[1]):
            html += f"""                        <div class="stat-line"><span>{cls}:</span><span>{count}</span></div>\n"""

        html += """                    </div>
                    <div class="legend">
                        <div class="legend-grid">
"""

        # Add ARC legend
        for cls in floor['arc_stats'].keys():
            color = DISCIPLINE_COLORS['ARC'].get(cls, '#cccccc')
            html += f"""                            <div class="legend-item"><div class="legend-color" style="background:{color}"></div><span>{cls}</span></div>\n"""

        html += """                        </div>
                    </div>
                </div>
            </div>
        </div>
\n"""

    html += """    </div>

    <script>
        function showFloor(floorId) {
            // Hide all floors
            document.querySelectorAll('.floor-view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.floor-btn').forEach(b => b.classList.remove('active'));

            // Show selected floor
            document.getElementById('floor-' + floorId).classList.add('active');
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
"""

    # Write file
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"\n{'='*80}")
    print(f"✅ SUCCESS! Generated proper 2D floor plans")
    print(f"📄 Output: {output_path}")
    print(f"🌐 Open: file://{Path(output_path).absolute()}")
    print(f"{'='*80}\n")

def main():
    """Main execution"""

    # Database path
    db_path = Path(__file__).parent.parent / "BASE_ARC_STR.db"

    # Output path
    output_path = Path(__file__).parent.parent / "SourceFiles" / "Terminal1_Proper_Floor_Plans.html"

    generate_html(str(db_path), str(output_path))

if __name__ == "__main__":
    main()
