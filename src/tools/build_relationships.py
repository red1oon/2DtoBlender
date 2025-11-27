#!/usr/bin/env python3
"""
Build Object Relationships

Builds relationships between objects:
1. Door/Window → Wall (opening in wall)
2. Object → Room (inside room)
3. Wall → Wall (connections)
"""

import json
import sys
import math
from typing import Dict, List, Tuple, Optional


class RelationshipBuilder:
    """Build spatial relationships between objects"""

    def __init__(self, complete_file: str):
        with open(complete_file) as f:
            data = json.load(f)
            self.objects = data.get('objects_complete', [])

        self.relationships = []
        self.stats = {
            'opening_in_wall': 0,
            'wall_connection': 0,
            'object_near_wall': 0
        }

    def build_all(self):
        """Build all relationships"""
        print("="*80)
        print("BUILDING OBJECT RELATIONSHIPS")
        print("="*80)
        print()

        # Get object lists
        self.doors = [o for o in self.objects if o.get('type') == 'door']
        self.windows = [o for o in self.objects if o.get('type') == 'window']
        self.walls = [o for o in self.objects if o.get('type') == 'wall']

        print(f"Found:")
        print(f"  Doors:   {len(self.doors)}")
        print(f"  Windows: {len(self.windows)}")
        print(f"  Walls:   {len(self.walls)}")
        print()

        # Build relationships
        self._build_opening_wall_relationships()
        self._build_wall_connections()

        return self.relationships

    def _build_opening_wall_relationships(self):
        """Match doors/windows to walls"""
        print("-"*80)
        print("MATCHING OPENINGS TO WALLS")
        print("-"*80)
        print()

        openings = self.doors + self.windows

        for opening in openings:
            opening_pos = opening['position']
            opening_id = opening.get('object_id') or opening.get('name')
            opening_type = opening.get('type')

            # Find nearest wall
            nearest_wall, distance = self._find_nearest_wall(opening_pos)

            if nearest_wall and distance < 0.5:  # Within 50cm
                # Calculate position along wall
                wall_start = nearest_wall['position']
                wall_end = nearest_wall['end_point']
                dist_from_start = self._distance_along_line(
                    opening_pos, wall_start, wall_end
                )

                relationship = {
                    'id': f'rel_{len(self.relationships)}',
                    'type': 'opening_in_wall',
                    'source': {
                        'id': opening_id,
                        'type': opening_type,
                        'position': opening_pos
                    },
                    'target': {
                        'id': nearest_wall.get('object_id') or nearest_wall.get('name'),
                        'type': 'wall',
                        'object_type': nearest_wall.get('object_type')
                    },
                    'properties': {
                        'distance_from_wall': round(distance, 3),
                        'distance_from_wall_start': round(dist_from_start, 3),
                        'wall_length': round(nearest_wall['dimensions']['length'], 3),
                        'position_ratio': round(dist_from_start / nearest_wall['dimensions']['length'], 3) if nearest_wall['dimensions']['length'] > 0 else 0
                    }
                }

                self.relationships.append(relationship)
                self.stats['opening_in_wall'] += 1

                status = "✅" if distance < 0.15 else "✓ "
                print(f"{status} {opening_id:15s} → {nearest_wall.get('name'):20s}  "
                      f"({distance*100:.1f}cm from wall, {dist_from_start:.2f}m from start)")

            else:
                print(f"⚠️  {opening_id:15s} → No nearby wall found (closest: {distance:.2f}m)")

        print(f"\n✅ Matched {self.stats['opening_in_wall']}/{len(openings)} openings to walls")

    def _find_nearest_wall(self, point: List[float]) -> Tuple[Optional[Dict], float]:
        """Find nearest wall to a point"""
        min_distance = float('inf')
        nearest_wall = None

        for wall in self.walls:
            wall_start = wall['position']
            wall_end = wall['end_point']

            distance = self._point_to_line_distance(point, wall_start, wall_end)

            if distance < min_distance:
                min_distance = distance
                nearest_wall = wall

        return nearest_wall, min_distance

    def _point_to_line_distance(self, point: List[float], line_start: List[float], line_end: List[float]) -> float:
        """Calculate distance from point to line segment"""
        px, py = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        # Line vector
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            # Line is a point
            return math.sqrt((px - x1)**2 + (py - y1)**2)

        # Parameter t for closest point on line
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx**2 + dy**2)))

        # Closest point on line
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Distance
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

    def _distance_along_line(self, point: List[float], line_start: List[float], line_end: List[float]) -> float:
        """Calculate distance from line start to closest point to given point"""
        px, py = point[0], point[1]
        x1, y1 = line_start[0], line_start[1]
        x2, y2 = line_end[0], line_end[1]

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return 0

        # Parameter t
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx**2 + dy**2)))

        # Distance along line
        return t * math.sqrt(dx**2 + dy**2)

    def _build_wall_connections(self):
        """Find wall-to-wall connections (endpoints that meet)"""
        print("\n" + "-"*80)
        print("FINDING WALL CONNECTIONS")
        print("-"*80)
        print()

        connection_threshold = 0.1  # 10cm

        for i, wall1 in enumerate(self.walls):
            for wall2 in self.walls[i+1:]:
                # Check if endpoints connect
                w1_start = wall1['position']
                w1_end = wall1['end_point']
                w2_start = wall2['position']
                w2_end = wall2['end_point']

                connections = []

                # Check all endpoint combinations
                if self._points_close(w1_start, w2_start, connection_threshold):
                    connections.append(('start', 'start'))
                if self._points_close(w1_start, w2_end, connection_threshold):
                    connections.append(('start', 'end'))
                if self._points_close(w1_end, w2_start, connection_threshold):
                    connections.append(('end', 'start'))
                if self._points_close(w1_end, w2_end, connection_threshold):
                    connections.append(('end', 'end'))

                for conn_type in connections:
                    relationship = {
                        'id': f'rel_{len(self.relationships)}',
                        'type': 'wall_connection',
                        'source': {
                            'id': wall1.get('object_id') or wall1.get('name'),
                            'type': 'wall',
                            'endpoint': conn_type[0]
                        },
                        'target': {
                            'id': wall2.get('object_id') or wall2.get('name'),
                            'type': 'wall',
                            'endpoint': conn_type[1]
                        }
                    }

                    self.relationships.append(relationship)
                    self.stats['wall_connection'] += 1

        print(f"✅ Found {self.stats['wall_connection']} wall connections")

    def _points_close(self, p1: List[float], p2: List[float], threshold: float) -> bool:
        """Check if two points are within threshold distance"""
        distance = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        return distance < threshold

    def save_relationships(self, output_file: str):
        """Save relationships to file"""
        output = {
            'total_relationships': len(self.relationships),
            'by_type': self.stats,
            'relationships': self.relationships
        }

        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n✅ Relationships saved to: {output_file}")
        return output

    def print_summary(self):
        """Print relationship summary"""
        print("\n" + "="*80)
        print("RELATIONSHIP SUMMARY")
        print("="*80)

        print(f"\n📊 Total relationships: {len(self.relationships)}")
        print(f"\nBy type:")
        for rel_type, count in self.stats.items():
            print(f"  {rel_type:20s}: {count:3d}")

        # Sample relationships
        print(f"\nSample relationships:")
        for rel in self.relationships[:5]:
            src = rel['source']['id']
            tgt = rel['target']['id']
            rel_type = rel['type']
            print(f"  {src:15s} → {tgt:20s} ({rel_type})")

        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 build_relationships.py <complete.json> [relationships.json]")
        print()
        print("Builds spatial relationships between objects")
        sys.exit(1)

    complete_file = sys.argv[1]
    relationships_file = sys.argv[2] if len(sys.argv) > 2 else 'relationships.json'

    builder = RelationshipBuilder(complete_file)
    builder.build_all()
    builder.print_summary()
    builder.save_relationships(relationships_file)

    print("="*80)
    print("RELATIONSHIPS COMPLETE")
    print("="*80)
    print("\nRelationships enable:")
    print("  → Validation (doors must be on walls)")
    print("  → Room topology (trace wall boundaries)")
    print("  → Collision detection (openings in walls)")
    print("  → BIM connectivity (wall network)")
    print()


if __name__ == "__main__":
    main()
