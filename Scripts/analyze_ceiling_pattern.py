#!/usr/bin/env python3
"""
Analyze ceiling tile (IfcPlate) patterns to create intelligent inference rules.

Goal: Understand how ceiling tiles are distributed so we can generate them
      from 2D DWG files even if they're not explicitly drawn.
"""

import sqlite3
import struct
import numpy as np
from collections import defaultdict

DB_PATH = "/home/red1/Documents/bonsai/DatabaseFiles/FullExtractionTesellated.db"

def decode_vertices(blob_data):
    """Decode vertex BLOB into list of (x,y,z) tuples."""
    if not blob_data:
        return []

    # Vertices stored as float32 triplets (x,y,z)
    num_floats = len(blob_data) // 4
    vertices = struct.unpack(f'{num_floats}f', blob_data)

    # Group into (x,y,z) triplets
    return [(vertices[i], vertices[i+1], vertices[i+2])
            for i in range(0, len(vertices)-2, 3)]

def analyze_ceiling_plates():
    """Analyze IfcPlate distribution to find inference rules."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("="*80)
    print("CEILING TILE (IfcPlate) PATTERN ANALYSIS")
    print("="*80)
    print()

    # Get all IfcPlate elements with geometry
    query = """
        SELECT
            em.guid,
            em.element_name,
            em.element_type,
            em.storey,
            bg.vertices
        FROM elements_meta em
        JOIN element_instances ei ON em.guid = ei.guid
        JOIN base_geometries bg ON ei.geometry_hash = bg.geometry_hash
        WHERE em.ifc_class = 'IfcPlate'
        LIMIT 1000
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    print(f"Analyzing {len(rows)} ceiling plates (sampled from 33,324 total)...")
    print()

    z_heights = []
    storey_z_map = defaultdict(list)

    for guid, name, elem_type, storey, vertices_blob in rows:
        vertices = decode_vertices(vertices_blob)

        if not vertices:
            continue

        # Extract all z-coordinates
        z_coords = [v[2] for v in vertices]
        avg_z = np.mean(z_coords)
        min_z = min(z_coords)
        max_z = max(z_coords)

        z_heights.append(avg_z)
        if storey:
            storey_z_map[storey].append(avg_z)

    conn.close()

    # Statistical analysis
    print("STATISTICAL SUMMARY")
    print("-" * 80)
    print(f"Total plates analyzed: {len(z_heights)}")
    print(f"Average Z-height: {np.mean(z_heights):.3f} m")
    print(f"Median Z-height: {np.median(z_heights):.3f} m")
    print(f"Min Z-height: {min(z_heights):.3f} m")
    print(f"Max Z-height: {max(z_heights):.3f} m")
    print(f"Std deviation: {np.std(z_heights):.3f} m")
    print()

    # Z-height distribution (histogram)
    print("Z-HEIGHT DISTRIBUTION (bins)")
    print("-" * 80)
    hist, bin_edges = np.histogram(z_heights, bins=10)
    for i, count in enumerate(hist):
        print(f"  {bin_edges[i]:6.2f}m - {bin_edges[i+1]:6.2f}m: {count:4d} plates {'█' * (count//10)}")
    print()

    # Storey-based analysis
    if storey_z_map:
        print("CEILING HEIGHT BY STOREY")
        print("-" * 80)
        for storey in sorted(storey_z_map.keys()):
            z_list = storey_z_map[storey]
            print(f"  {storey:30s}: avg={np.mean(z_list):6.3f}m, "
                  f"count={len(z_list):4d}, "
                  f"range=[{min(z_list):.2f}, {max(z_list):.2f}]")
        print()

    # Identify ceiling height clusters (simple binning approach)
    print("IDENTIFIED CEILING HEIGHT PATTERNS")
    print("-" * 80)

    # Simple clustering: group by 0.5m bins
    z_array = np.array(z_heights)
    bin_size = 0.5
    z_bins = {}

    for z in z_heights:
        bin_key = round(z / bin_size) * bin_size
        if bin_key not in z_bins:
            z_bins[bin_key] = []
        z_bins[bin_key].append(z)

    # Filter bins with significant counts (>1% of total)
    significant_bins = {k: v for k, v in z_bins.items()
                        if len(v) > len(z_heights) * 0.01}

    print(f"Found {len(significant_bins)} distinct ceiling height groups:")
    print()

    for bin_height in sorted(significant_bins.keys()):
        z_list = significant_bins[bin_height]
        print(f"  ~{bin_height:5.1f}m: {len(z_list):4d} plates "
              f"(avg={np.mean(z_list):.3f}m ± {np.std(z_list):.3f}m) "
              f"{'█' * (len(z_list)//20)}")

    print()
    print("="*80)
    print("INFERENCE RULES FOR DXF → DATABASE CONVERSION")
    print("="*80)
    print()
    print("Based on this analysis, we can infer ceiling tiles by:")
    print()
    print("1. SPATIAL INFERENCE:")
    print("   - When we detect a room/space boundary in DXF")
    print("   - Generate ceiling tiles at standard heights")
    print(f"   - Primary height: {np.median(z_heights):.2f}m")
    print()
    print("2. ROOM-BASED GENERATION:")
    print("   - Parse closed polylines on ARC-CEILING or similar layers")
    print("   - Generate grid of ceiling tiles to fill the space")
    print("   - Standard tile size: 600mm x 600mm (typical)")
    print()
    print("3. STOREY-BASED HEIGHTS:")
    if storey_z_map:
        print("   - Use storey information if available in DXF")
        for storey in sorted(storey_z_map.keys())[:5]:
            avg_height = np.mean(storey_z_map[storey])
            print(f"   - {storey}: {avg_height:.2f}m")
    print()

    return {
        'mean_z': np.mean(z_heights),
        'median_z': np.median(z_heights),
        'std_z': np.std(z_heights),
        'storey_heights': {k: np.mean(v) for k, v in storey_z_map.items()}
    }

if __name__ == "__main__":
    try:
        stats = analyze_ceiling_plates()

        print()
        print("RECOMMENDED TEMPLATE ADDITION:")
        print("-" * 80)
        print("""
CREATE TEMPLATE: ARC_IfcPlate_CeilingInferred
  Type: SPATIAL_INFERENCE
  Trigger: Detect room boundaries (closed polylines on ceiling layers)
  Generation:
    - Identify room polygon from DXF
    - Generate 600x600mm tile grid
    - Set z-height from storey or use default: {:.2f}m
    - Material: "Metal Deck" or similar
    - Count: Based on room area / (0.6m × 0.6m)
        """.format(stats['median_z']))

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
