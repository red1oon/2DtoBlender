#!/usr/bin/env python3
"""
Discover Natural Grid from Drawings

Instead of imposing an arbitrary grid, DISCOVER the natural grid/lattice
that the architect used when drawing the plans.

How:
1. Analyze ALL drawings first
2. Find repeating spacing patterns (wall intervals, column spacing)
3. Detect natural coordinate grid from the drawing itself
4. Use THAT grid as the placement lattice

This is like reverse-engineering the architect's modular grid system.
"""

import json
import sys
import numpy as np
from collections import Counter
from typing import List, Tuple, Dict


class NaturalGridDiscovery:
    """Discover the natural grid/lattice from architectural drawings"""

    def __init__(self, data):
        self.data = data
        self.objects = data.get('objects', [])
        self.calibration = data.get('calibration_data', {})

    def discover_grid_from_walls(self) -> Dict:
        """
        Discover natural grid by analyzing wall spacing patterns

        Architects use modular grids - walls are placed at regular intervals.
        Find these intervals by analyzing wall positions.
        """
        print("="*80)
        print("DISCOVERING NATURAL GRID FROM DRAWINGS")
        print("="*80)
        print()

        walls = [o for o in self.objects if 'wall' in o.get('object_type', '').lower()]

        if not walls:
            print("❌ No walls found - cannot discover grid")
            return None

        print(f"Analyzing {len(walls)} walls...")

        # Extract all wall endpoint coordinates
        x_coords = []
        y_coords = []

        for wall in walls:
            start = wall.get('position', [0, 0, 0])
            end = wall.get('end_point', start)

            x_coords.extend([start[0], end[0]])
            y_coords.extend([start[1], end[1]])

        x_coords = sorted(set(x_coords))
        y_coords = sorted(set(y_coords))

        print(f"Unique X coordinates: {len(x_coords)}")
        print(f"Unique Y coordinates: {len(y_coords)}")

        # Calculate spacing between coordinates
        x_spacings = [x_coords[i+1] - x_coords[i] for i in range(len(x_coords)-1)]
        y_spacings = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords)-1)]

        # Find most common spacing (the modular grid interval)
        x_spacing_counter = Counter([round(s, 2) for s in x_spacings if s > 0.1])
        y_spacing_counter = Counter([round(s, 2) for s in y_spacings if s > 0.1])

        print("\n📏 X-axis spacing patterns:")
        for spacing, count in x_spacing_counter.most_common(5):
            print(f"   {spacing:.2f}m: appears {count} times")

        print("\n📏 Y-axis spacing patterns:")
        for spacing, count in y_spacing_counter.most_common(5):
            print(f"   {spacing:.2f}m: appears {count} times")

        # Detect the dominant grid interval
        x_grid_interval = x_spacing_counter.most_common(1)[0][0] if x_spacing_counter else 1.0
        y_grid_interval = y_spacing_counter.most_common(1)[0][0] if y_spacing_counter else 1.0

        print(f"\n✅ DISCOVERED GRID INTERVAL:")
        print(f"   X-axis: {x_grid_interval:.2f}m")
        print(f"   Y-axis: {y_grid_interval:.2f}m")

        # Find grid origin (minimum coordinates)
        grid_origin = [min(x_coords), min(y_coords), 0.0]

        print(f"\n✅ DISCOVERED GRID ORIGIN:")
        print(f"   Origin: ({grid_origin[0]:.2f}, {grid_origin[1]:.2f}, {grid_origin[2]:.2f})")

        # Calculate grid dimensions
        width = max(x_coords) - min(x_coords)
        length = max(y_coords) - min(y_coords)

        print(f"\n✅ DISCOVERED BUILDING DIMENSIONS:")
        print(f"   Width: {width:.2f}m")
        print(f"   Length: {length:.2f}m")

        # Calculate number of grid cells
        nx = int(np.ceil(width / x_grid_interval))
        ny = int(np.ceil(length / y_grid_interval))

        print(f"\n✅ NATURAL GRID SIZE:")
        print(f"   {nx} × {ny} cells")
        print(f"   Total: {nx * ny} cells")

        return {
            'origin': grid_origin,
            'x_interval': x_grid_interval,
            'y_interval': y_grid_interval,
            'dimensions': [width, length, 3.0],  # Assume 3m height
            'cells': [nx, ny, 6],  # 0.5m vertical layers
            'x_grid_lines': x_coords,
            'y_grid_lines': y_coords
        }

    def discover_room_sectors(self, grid_config: Dict) -> Dict:
        """
        Discover room sectors/zones from the natural grid

        Like how contractors mark out areas on plans:
        "Kitchen is cells A1-A3, B1-B2"
        """
        print("\n" + "="*80)
        print("DISCOVERING ROOM SECTORS")
        print("="*80)

        # Group objects by room
        rooms = {}
        for obj in self.objects:
            room = obj.get('room')
            if room and room not in ['exterior', 'interior', 'unknown', 'structure']:
                if room not in rooms:
                    rooms[room] = []
                rooms[room].append(obj)

        print(f"\nFound {len(rooms)} rooms")

        room_sectors = {}

        for room_name, room_objects in rooms.items():
            # Get bounding box of room objects
            positions = [o.get('position', [0, 0, 0]) for o in room_objects]
            if not positions:
                continue

            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]

            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            # Convert to grid cells
            origin = grid_config['origin']
            x_interval = grid_config['x_interval']
            y_interval = grid_config['y_interval']

            x_cell_min = int((min_x - origin[0]) / x_interval)
            x_cell_max = int((max_x - origin[0]) / x_interval) + 1
            y_cell_min = int((min_y - origin[1]) / y_interval)
            y_cell_max = int((max_y - origin[1]) / y_interval) + 1

            room_sectors[room_name] = {
                'x_range': (x_cell_min, x_cell_max),
                'y_range': (y_cell_min, y_cell_max),
                'z_range': (0, 6),  # Full height
                'world_bounds': {
                    'min': [min_x, min_y, 0],
                    'max': [max_x, max_y, 3.0]
                }
            }

            width = max_x - min_x
            length = max_y - min_y
            area = width * length

            print(f"\n📐 {room_name.upper()}")
            print(f"   Grid cells: X[{x_cell_min}:{x_cell_max}] Y[{y_cell_min}:{y_cell_max}]")
            print(f"   Dimensions: {width:.2f}m × {length:.2f}m = {area:.2f}m²")
            print(f"   Objects: {len(room_objects)}")

        return room_sectors

    def discover_vertical_layers(self) -> Dict:
        """
        Discover vertical layer structure from Z-coordinates

        Find natural Z-levels (floor, counters, windows, ceiling)
        """
        print("\n" + "="*80)
        print("DISCOVERING VERTICAL LAYERS")
        print("="*80)

        # Extract all Z coordinates
        z_coords = []
        for obj in self.objects:
            pos = obj.get('position', [0, 0, 0])
            z_coords.append(pos[2])

        z_coords = sorted(set(z_coords))

        print(f"\nUnique Z coordinates: {len(z_coords)}")

        # Cluster Z coordinates into layers
        z_clusters = []
        current_cluster = [z_coords[0]]

        for i in range(1, len(z_coords)):
            if z_coords[i] - z_coords[i-1] < 0.3:  # Within 30cm = same layer
                current_cluster.append(z_coords[i])
            else:
                z_clusters.append(current_cluster)
                current_cluster = [z_coords[i]]

        z_clusters.append(current_cluster)

        print(f"\n✅ DISCOVERED {len(z_clusters)} VERTICAL LAYERS:")

        layer_names = ['Floor', 'Low', 'Counter', 'High', 'Window', 'Ceiling']

        layers = {}
        for i, cluster in enumerate(z_clusters):
            avg_z = sum(cluster) / len(cluster)
            layer_name = layer_names[i] if i < len(layer_names) else f'Layer_{i}'

            layers[layer_name] = {
                'z_avg': avg_z,
                'z_range': (min(cluster), max(cluster)),
                'object_count': sum(1 for o in self.objects if min(cluster) <= o.get('position', [0,0,0])[2] <= max(cluster))
            }

            print(f"   {layer_name}: Z={avg_z:.2f}m ({layers[layer_name]['object_count']} objects)")

        return layers

    def generate_natural_lattice(self) -> Dict:
        """
        Generate the complete natural lattice discovered from drawings

        Returns a complete grid specification based on the architect's
        original modular grid system.
        """
        # Discover grid from wall patterns
        grid_config = self.discover_grid_from_walls()

        if not grid_config:
            return None

        # Discover room sectors within grid
        room_sectors = self.discover_room_sectors(grid_config)

        # Discover vertical layers
        vertical_layers = self.discover_vertical_layers()

        # Assemble complete lattice
        lattice = {
            'grid': grid_config,
            'rooms': room_sectors,
            'layers': vertical_layers,
            'metadata': {
                'discovered_from': 'architectural_drawings',
                'method': 'wall_spacing_analysis',
                'confidence': 'high' if len(self.objects) > 50 else 'medium'
            }
        }

        print("\n" + "="*80)
        print("✅ NATURAL LATTICE DISCOVERED")
        print("="*80)
        print(f"Grid cells: {grid_config['cells'][0]} × {grid_config['cells'][1]}")
        print(f"Room sectors: {len(room_sectors)}")
        print(f"Vertical layers: {len(vertical_layers)}")

        return lattice

    def validate_objects_against_lattice(self, lattice: Dict):
        """
        Validate that all objects fit within the discovered natural lattice

        This ensures the discovered grid is correct and objects align with it.
        """
        print("\n" + "="*80)
        print("VALIDATING OBJECTS AGAINST DISCOVERED LATTICE")
        print("="*80)

        grid = lattice['grid']
        origin = grid['origin']
        x_interval = grid['x_interval']
        y_interval = grid['y_interval']

        # Check alignment
        misaligned = []

        for obj in self.objects:
            pos = obj.get('position', [0, 0, 0])

            # Calculate distance to nearest grid line
            x_cell = (pos[0] - origin[0]) / x_interval
            y_cell = (pos[1] - origin[1]) / y_interval

            x_offset = abs(x_cell - round(x_cell)) * x_interval
            y_offset = abs(y_cell - round(y_cell)) * y_interval

            # If more than 20cm off-grid, consider misaligned
            if x_offset > 0.2 or y_offset > 0.2:
                misaligned.append({
                    'name': obj.get('name'),
                    'position': pos,
                    'x_offset': x_offset,
                    'y_offset': y_offset
                })

        if misaligned:
            print(f"\n⚠️  {len(misaligned)} objects slightly off-grid:")
            for obj in misaligned[:10]:
                print(f"   • {obj['name']}: offset ({obj['x_offset']:.3f}m, {obj['y_offset']:.3f}m)")
        else:
            print(f"\n✅ All {len(self.objects)} objects align with discovered grid")

        alignment_ratio = 1 - (len(misaligned) / len(self.objects))
        print(f"\nGrid alignment: {alignment_ratio*100:.1f}%")

        return alignment_ratio > 0.85  # 85% of objects should align


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 discover_natural_grid.py <output.json>")
        sys.exit(1)

    # Load data
    with open(sys.argv[1]) as f:
        data = json.load(f)

    # Discover natural grid
    discoverer = NaturalGridDiscovery(data)
    lattice = discoverer.generate_natural_lattice()

    if lattice:
        # Validate objects against lattice
        valid = discoverer.validate_objects_against_lattice(lattice)

        # Save lattice configuration
        output_path = sys.argv[1].replace('.json', '_LATTICE.json')
        with open(output_path, 'w') as f:
            json.dump(lattice, f, indent=2)

        print(f"\n💾 Lattice saved to: {output_path}")

        if valid:
            print("\n✅ Natural lattice discovered and validated")
            print("   → Use this lattice as coordinate system for all placement")
            sys.exit(0)
        else:
            print("\n⚠️  Lattice discovered but alignment is low")
            print("   → May need manual adjustment")
            sys.exit(1)
    else:
        print("\n❌ Could not discover natural lattice")
        sys.exit(1)


if __name__ == "__main__":
    main()
