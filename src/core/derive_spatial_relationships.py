#!/usr/bin/env python3
"""
Stage 2.3: Spatial Relationship Derivation

Analyzes patterns_identified table and builds relationships:
- ON relationships: pattern bbox intersects wall bbox
- IN relationships: pattern position within wall span
- NEAR relationships: proximity between patterns (<2m threshold)
- ALIGNED_H/V: alignment between patterns (same wall, same height)

INPUT: patterns_identified + semantic_walls tables
OUTPUT: spatial_relationships table

Compliance: Rule 0 (First Law) - if relationships wrong → edit constants below, re-run
"""

import sqlite3
import math
import json
from pathlib import Path
from typing import List, Tuple, Dict


# ============================================================================
# HARDCODED PARAMETERS (Rule 0: Edit these if results incorrect)
# ============================================================================

# Step 3: NEAR relationships (distance threshold)
NEAR_THRESHOLD = 2.0              # meters (proximity for adjacency)

# Step 4: ALIGNED relationships (alignment tolerance)
ALIGNED_H_TOLERANCE = 0.2         # meters (vertical alignment Y-axis)
ALIGNED_V_TOLERANCE = 0.2         # meters (horizontal alignment X-axis)


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Euclidean distance between two points"""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def bbox_intersects(bbox1: Tuple, bbox2: Tuple) -> bool:
    """Check if two bounding boxes intersect"""
    x0_1, y0_1, x1_1, y1_1 = bbox1
    x0_2, y0_2, x1_2, y1_2 = bbox2

    # No intersection if separated on any axis
    if x1_1 < x0_2 or x1_2 < x0_1:
        return False
    if y1_1 < y0_2 or y1_2 < y0_1:
        return False

    return True


def point_in_bbox(point: Tuple[float, float], bbox: Tuple) -> bool:
    """Check if point is within bounding box"""
    x, y = point
    x0, y0, x1, y1 = bbox
    return (min(x0, x1) <= x <= max(x0, x1)) and (min(y0, y1) <= y <= max(y0, y1))


# ============================================================================
# Relationship Derivation Functions
# ============================================================================

def derive_on_relationships(cursor: sqlite3.Cursor) -> List[Dict]:
    """
    Step 1: ON relationships - pattern bbox intersects wall bbox

    Used for: doors ON walls, windows ON walls
    """
    print("   Step 1: Deriving ON relationships (pattern ∩ wall)...")

    # Get patterns with bboxes
    cursor.execute("""
        SELECT pattern_id, pattern_type, bbox_x0, bbox_y0, bbox_x1, bbox_y1
        FROM patterns_identified
        WHERE bbox_x0 IS NOT NULL
    """)
    patterns = cursor.fetchall()

    # Get walls with bboxes
    cursor.execute("""
        SELECT wall_id, bbox_x0, bbox_y0, bbox_x1, bbox_y1
        FROM semantic_walls
    """)
    walls = cursor.fetchall()

    relationships = []

    for pattern_id, pattern_type, px0, py0, px1, py1 in patterns:
        pattern_bbox = (px0, py0, px1, py1)

        for wall_id, wx0, wy0, wx1, wy1 in walls:
            wall_bbox = (wx0, wy0, wx1, wy1)

            if bbox_intersects(pattern_bbox, wall_bbox):
                relationships.append({
                    'type': 'ON',
                    'source': pattern_id,
                    'target': f'wall_{wall_id}',
                    'confidence': 1.0,
                    'metadata': {'wall_id': wall_id}
                })

    print(f"      Found {len(relationships)} ON relationships")
    return relationships


def derive_in_relationships(cursor: sqlite3.Cursor) -> List[Dict]:
    """
    Step 2: IN relationships - pattern centroid within wall bbox

    Used for: openings IN wall segment
    """
    print("   Step 2: Deriving IN relationships (centroid in wall)...")

    # Get patterns with positions
    cursor.execute("""
        SELECT pattern_id, pattern_type, position_x, position_y
        FROM patterns_identified
        WHERE position_x IS NOT NULL
    """)
    patterns = cursor.fetchall()

    # Get walls
    cursor.execute("""
        SELECT wall_id, bbox_x0, bbox_y0, bbox_x1, bbox_y1
        FROM semantic_walls
    """)
    walls = cursor.fetchall()

    relationships = []

    for pattern_id, pattern_type, px, py in patterns:
        for wall_id, wx0, wy0, wx1, wy1 in walls:
            wall_bbox = (wx0, wy0, wx1, wy1)

            if point_in_bbox((px, py), wall_bbox):
                relationships.append({
                    'type': 'IN',
                    'source': pattern_id,
                    'target': f'wall_{wall_id}',
                    'confidence': 1.0,
                    'metadata': {'wall_id': wall_id}
                })

    print(f"      Found {len(relationships)} IN relationships")
    return relationships


def derive_proximity_relationships(cursor: sqlite3.Cursor) -> List[Dict]:
    """
    Step 3: NEAR relationships - euclidean distance between pattern centroids

    Used for: switch NEAR door, outlet NEAR door
    """
    print(f"   Step 3: Deriving NEAR relationships (threshold: {NEAR_THRESHOLD}m)...")

    # Get all patterns (positions in building coordinates / meters)
    cursor.execute("""
        SELECT pattern_id, pattern_type, position_x, position_y
        FROM patterns_identified
        WHERE position_x IS NOT NULL
    """)
    patterns = cursor.fetchall()

    relationships = []

    for i, (id1, type1, x1, y1) in enumerate(patterns):
        for id2, type2, x2, y2 in patterns[i+1:]:
            dist = calculate_distance((x1, y1), (x2, y2))

            if dist < NEAR_THRESHOLD:
                relationships.append({
                    'type': 'NEAR',
                    'source': id1,
                    'target': id2,
                    'confidence': 1.0 - (dist / NEAR_THRESHOLD),  # Closer = higher confidence
                    'metadata': {'distance_m': dist}
                })

    print(f"      Found {len(relationships)} NEAR relationships")
    return relationships


def derive_alignment_relationships(cursor: sqlite3.Cursor) -> List[Dict]:
    """
    Step 4: ALIGNED_H/V relationships - alignment between patterns

    Used for: patterns on same wall, same height level
    """
    print(f"   Step 4: Deriving ALIGNED relationships (H_tol={ALIGNED_H_TOLERANCE}m, V_tol={ALIGNED_V_TOLERANCE}m)...")

    cursor.execute("""
        SELECT pattern_id, pattern_type, position_x, position_y
        FROM patterns_identified
        WHERE position_x IS NOT NULL
    """)
    patterns = cursor.fetchall()

    relationships = []

    for i, (id1, type1, x1, y1) in enumerate(patterns):
        for id2, type2, x2, y2 in patterns[i+1:]:
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            # Check vertical alignment (same X, aligned along Y-axis)
            if dx < ALIGNED_V_TOLERANCE:
                relationships.append({
                    'type': 'ALIGNED_V',
                    'source': id1,
                    'target': id2,
                    'confidence': 1.0 - (dx / ALIGNED_V_TOLERANCE),
                    'metadata': {'deviation_m': dx}
                })

            # Check horizontal alignment (same Y, aligned along X-axis)
            if dy < ALIGNED_H_TOLERANCE:
                relationships.append({
                    'type': 'ALIGNED_H',
                    'source': id1,
                    'target': id2,
                    'confidence': 1.0 - (dy / ALIGNED_H_TOLERANCE),
                    'metadata': {'deviation_m': dy}
                })

    print(f"      Found {len(relationships)} ALIGNED relationships")
    return relationships


def persist_relationships(cursor: sqlite3.Cursor, relationships: List[dict]):
    """Write relationships to spatial_relationships table"""
    import json

    for rel in relationships:
        cursor.execute("""
            INSERT INTO spatial_relationships
            (relationship_type, source_pattern_id, target_pattern_id, confidence, metadata_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            rel['type'],
            rel['source'],
            rel['target'],
            rel['confidence'],
            json.dumps(rel['metadata'])
        ))


def main():
    """Main execution - Stage 2.3 pipeline"""
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "output_artifacts" / "TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"

    print("=" * 80)
    print("STAGE 2.3: SPATIAL RELATIONSHIP DERIVATION")
    print("=" * 80)
    print(f"Database: {db_path.name}")
    print(f"Algorithm: Bbox intersection + distance thresholds (DETERMINISTIC)")
    print()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Clear existing relationships
        cursor.execute("DELETE FROM spatial_relationships")

        # Derive all relationship types
        print("🔗 Deriving spatial relationships (4 types)...")
        all_relationships = []

        # 1. ON relationships (pattern ON wall)
        on_rels = derive_on_relationships(cursor)
        all_relationships.extend(on_rels)

        # 2. IN relationships (pattern IN wall)
        in_rels = derive_in_relationships(cursor)
        all_relationships.extend(in_rels)

        # 3. NEAR relationships (pattern NEAR pattern)
        near_rels = derive_proximity_relationships(cursor)
        all_relationships.extend(near_rels)

        # 4. ALIGNED relationships (pattern ALIGNED pattern)
        aligned_rels = derive_alignment_relationships(cursor)
        all_relationships.extend(aligned_rels)

        # Persist to database
        print(f"\n💾 Persisting {len(all_relationships)} relationships...")
        persist_relationships(cursor, all_relationships)
        conn.commit()

        # Summary
        cursor.execute("""
            SELECT relationship_type, COUNT(*) as count
            FROM spatial_relationships
            GROUP BY relationship_type
            ORDER BY count DESC
        """)
        summary = cursor.fetchall()

        print("\n" + "=" * 80)
        print("✅ STAGE 2.3 COMPLETE - Spatial Relationships Derived")
        print("=" * 80)
        for rel_type, count in summary:
            print(f"   {rel_type}: {count}")

        # Verification examples
        print("\n📋 Sample relationships:")
        cursor.execute("""
            SELECT relationship_type, source_pattern_id, target_pattern_id, confidence
            FROM spatial_relationships
            LIMIT 5
        """)
        samples = cursor.fetchall()
        for rel_type, src, tgt, conf in samples:
            print(f"   {src} {rel_type} {tgt} (confidence: {conf:.2f})")

        total = sum(s[1] for s in summary)
        print(f"\n✅ Total relationships: {total}")
        print(f"   If incorrect → edit constants in {__file__} and re-run")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
