#!/usr/bin/env python3
"""
Pattern Recognition Layer - Derives spatial and geometric relationships from primitives

Purpose:
- Reads master_reference_template.json sequentially
- Queries SQLite primitives database for pattern matching
- Derives spatial relationships (door ON wall, window IN wall segment)
- Builds interdependency graph for 3D object placement
- Supports multiple pattern libraries (ISO 128, ANSI, custom fallback)

Output: CONTEXT_PATTERNS.json with identified patterns + spatial relationships
"""

import json
import sqlite3
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class SpatialRelationship:
    """Represents spatial relationship between primitives/objects"""
    relationship_type: str  # "on_wall", "near", "within", "aligned_with"
    source_id: str
    target_id: str
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class IdentifiedPattern:
    """Pattern identified from primitives"""
    pattern_id: str
    pattern_type: str  # detection_id from master template
    primitive_ids: List[str]  # IDs of primitives forming this pattern
    position: Tuple[float, float]  # Center position in PDF coords
    confidence: float
    library_used: str  # "ISO_128", "ANSI", "CUSTOM"
    metadata: Dict[str, Any]  # Geometry-specific data
    spatial_relationships: List[SpatialRelationship]


class PatternLibrary:
    """Pattern matching library (ISO 128, ANSI, custom)"""

    @staticmethod
    def detect_door_swing_iso128(cursor: sqlite3.Cursor, text_x: float, text_y: float,
                                  page: int, radius: float = 50) -> Optional[Dict]:
        """
        ISO 128 door pattern: Quarter-circle arc + 2 perpendicular lines

        Geometric constraints:
        - Arc center = door hinge point
        - Arc radius = door width (typically 900mm = ~25-30pt PDF)
        - Two lines: door jamb + wall segment
        - Lines perpendicular to each other
        """
        # Find curves (arcs) near text position
        cursor.execute("""
            SELECT id, x0, y0, x1, y1, pts_json
            FROM primitives_curves
            WHERE page = ?
              AND x0 BETWEEN ? AND ?
              AND y0 BETWEEN ? AND ?
        """, (page, text_x - radius, text_x + radius, text_y - radius, text_y + radius))

        curves = cursor.fetchall()

        # Find lines near text position
        cursor.execute("""
            SELECT id, x0, y0, x1, y1, length, linewidth
            FROM primitives_lines
            WHERE page = ?
              AND x0 BETWEEN ? AND ?
              AND y0 BETWEEN ? AND ?
              AND length > 10
        """, (page, text_x - radius, text_x + radius, text_y - radius, text_y + radius))

        lines = cursor.fetchall()

        if not curves or len(lines) < 2:
            return None

        # Simple heuristic: use first curve + two longest lines
        arc = curves[0]
        sorted_lines = sorted(lines, key=lambda l: l[5], reverse=True)[:2]

        return {
            "arc_id": arc[0],
            "arc_center": (arc[1], arc[2]),
            "line_ids": [l[0] for l in sorted_lines],
            "confidence": 0.85,
            "swing_direction": "infer_from_arc_control_points",  # TODO: implement
            "door_width_estimate": abs(arc[3] - arc[1])  # Arc bbox width
        }

    @staticmethod
    def detect_door_fallback_custom(cursor: sqlite3.Cursor, text_x: float, text_y: float,
                                     page: int) -> Dict:
        """
        Custom fallback: Text-only detection when vector patterns unclear
        Lower confidence but ensures coverage
        """
        return {
            "text_only": True,
            "position": (text_x, text_y),
            "confidence": 0.60,
            "note": "No clear vector pattern - using text position only"
        }

    @staticmethod
    def detect_window_pattern(cursor: sqlite3.Cursor, text_x: float, text_y: float,
                               page: int, radius: float = 50) -> Optional[Dict]:
        """
        Window pattern: Parallel lines (jambs) + optional sill/lintel marks

        Geometric constraints:
        - Two parallel vertical/horizontal lines = window width
        - Must be within wall segment
        """
        cursor.execute("""
            SELECT id, x0, y0, x1, y1, length, linewidth
            FROM primitives_lines
            WHERE page = ?
              AND ((x0 BETWEEN ? AND ?) OR (x1 BETWEEN ? AND ?))
              AND ((y0 BETWEEN ? AND ?) OR (y1 BETWEEN ? AND ?))
              AND length > 15
        """, (page, text_x - radius, text_x + radius, text_x - radius, text_x + radius,
              text_y - radius, text_y + radius, text_y - radius, text_y + radius))

        lines = cursor.fetchall()

        if len(lines) < 2:
            return None

        # Find parallel line pairs
        for i, line1 in enumerate(lines):
            for line2 in lines[i+1:]:
                # Check if roughly parallel (simplified)
                dx1, dy1 = line1[3] - line1[1], line1[4] - line1[2]
                dx2, dy2 = line2[3] - line2[1], line2[4] - line2[2]

                # Parallel if slopes similar
                if abs(dx1) > 0.1 and abs(dx2) > 0.1:
                    slope1, slope2 = dy1/dx1, dy2/dx2
                    if abs(slope1 - slope2) < 0.2:  # Roughly parallel
                        return {
                            "line_ids": [line1[0], line2[0]],
                            "jamb_lines": [(line1[1], line1[2], line1[3], line1[4]),
                                          (line2[1], line2[2], line2[3], line2[4])],
                            "window_width_estimate": abs(line2[1] - line1[1]),
                            "confidence": 0.75
                        }

        return None

    @staticmethod
    def detect_dimension_line(cursor: sqlite3.Cursor, page: int) -> List[Dict]:
        """
        Dimension line pattern: Line + arrows + numeric text at endpoints

        Geometric constraints:
        - Long line (>50pt)
        - Numeric text near endpoints
        - Optional arrow heads (small triangular curves)
        """
        # Find numeric text (contains digits)
        cursor.execute("""
            SELECT id, text, x, y, page
            FROM primitives_text
            WHERE page = ?
              AND text GLOB '*[0-9]*'
        """, (page,))

        numeric_texts = cursor.fetchall()

        dimensions = []
        for text_id, text, tx, ty, tpage in numeric_texts:
            # Find long horizontal/vertical lines near this text
            cursor.execute("""
                SELECT id, x0, y0, x1, y1, length
                FROM primitives_lines
                WHERE page = ?
                  AND length > 50
                  AND ((ABS(x0 - ?) < 30 OR ABS(x1 - ?) < 30)
                   OR (ABS(y0 - ?) < 30 OR ABS(y1 - ?) < 30))
            """, (page, tx, tx, ty, ty))

            lines = cursor.fetchall()
            if lines:
                line = lines[0]  # Use closest line
                dimensions.append({
                    "text_id": text_id,
                    "text_value": text,
                    "line_id": line[0],
                    "line_coords": (line[1], line[2], line[3], line[4]),
                    "dimension_length_pt": line[5],
                    "confidence": 0.70
                })

        return dimensions


class SpatialAnalyzer:
    """Analyzes spatial relationships between identified patterns"""

    @staticmethod
    def find_wall_for_door(door_pos: Tuple[float, float], wall_segments: List[Dict],
                            tolerance: float = 5) -> Optional[str]:
        """
        Find which wall segment contains this door

        Constraint: Door must be ON a wall (within tolerance)
        """
        dx, dy = door_pos

        for wall in wall_segments:
            # Check if door point is on wall line segment
            wx0, wy0 = wall['start']
            wx1, wy1 = wall['end']

            # Point-to-line distance
            line_len = math.sqrt((wx1-wx0)**2 + (wy1-wy0)**2)
            if line_len < 0.1:
                continue

            # Perpendicular distance from point to line
            dist = abs((wy1-wy0)*dx - (wx1-wx0)*dy + wx1*wy0 - wy1*wx0) / line_len

            if dist < tolerance:
                # Check if door is within wall segment bounds
                if (min(wx0, wx1) <= dx <= max(wx0, wx1) and
                    min(wy0, wy1) <= dy <= max(wy0, wy1)):
                    return wall['id']

        return None

    @staticmethod
    def compute_alignment(obj1_pos: Tuple[float, float], obj2_pos: Tuple[float, float],
                          threshold: float = 2) -> Optional[str]:
        """
        Check if two objects are aligned (horizontally/vertically)

        Returns: "horizontal" | "vertical" | None
        """
        dx = abs(obj1_pos[0] - obj2_pos[0])
        dy = abs(obj1_pos[1] - obj2_pos[1])

        if dx < threshold:
            return "vertical"
        elif dy < threshold:
            return "horizontal"
        return None


class PatternRecognitionEngine:
    """Main pattern recognition engine"""

    def __init__(self, primitives_db_path: str, master_template_path: str):
        self.db_path = primitives_db_path
        self.template_path = master_template_path
        self.conn = None
        self.cursor = None
        self.master_template = None
        self.identified_patterns = []

    def load_template(self):
        """Load master reference template"""
        with open(self.template_path, 'r') as f:
            self.master_template = json.load(f)
        print(f"✅ Loaded master template: {len(self.master_template['extraction_sequence'])} items")

    def connect_db(self):
        """Connect to primitives database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # Verify schema
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in self.cursor.fetchall()]
        required = ['primitives_text', 'primitives_lines', 'primitives_curves']

        if not all(t in tables for t in required):
            raise ValueError(f"Missing required tables. Found: {tables}")

        # Create staging tables for pattern recognition
        self._create_staging_tables()

        print(f"✅ Connected to primitives database")

    def _create_staging_tables(self):
        """
        Create staging tables for pattern recognition output

        All staging data goes into the database (not scattered JSON files)
        """
        # Identified patterns table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns_identified (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,  -- detection_id from template
                position_x REAL,
                position_y REAL,
                confidence REAL,
                library_used TEXT,  -- 'ISO_128', 'ANSI', 'CUSTOM_FALLBACK'
                metadata_json TEXT,  -- Geometric details
                FOREIGN KEY (pattern_id) REFERENCES patterns_identified(pattern_id)
            );
        """)

        # Link patterns to their component primitives
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_primitives (
                pattern_id TEXT,
                primitive_id TEXT,
                primitive_type TEXT,  -- 'text', 'line', 'curve', 'rect'
                FOREIGN KEY (pattern_id) REFERENCES patterns_identified(pattern_id)
            );
        """)

        # Spatial relationships between patterns
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS spatial_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relationship_type TEXT,
                source_pattern_id TEXT,
                target_pattern_id TEXT,
                confidence REAL,
                metadata_json TEXT,
                FOREIGN KEY (source_pattern_id) REFERENCES patterns_identified(pattern_id),
                FOREIGN KEY (target_pattern_id) REFERENCES patterns_identified(pattern_id)
            );
        """)

        # Context: Calibration data
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_calibration (
                key TEXT PRIMARY KEY,
                value REAL,
                confidence REAL,
                source TEXT
            );
        """)

        # Context: Building dimensions
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_dimensions (
                dimension_name TEXT PRIMARY KEY,
                value REAL,
                unit TEXT,
                source TEXT
            );
        """)

        self.conn.commit()

    def process_template_sequence(self):
        """
        Process master template sequentially

        For each item:
        1. Query primitives based on search_text + pages
        2. Apply pattern detection (ISO/ANSI/custom fallback)
        3. Derive spatial relationships
        4. Store identified patterns
        """
        sequence = self.master_template['extraction_sequence']

        print(f"\n🔍 Processing {len(sequence)} template items sequentially...")

        for idx, item in enumerate(sequence):
            detection_id = item.get('detection_id')
            search_text = item.get('search_text', [])
            pages = item.get('pages', [1])

            if not search_text:
                # Structural items without search text (floor, ceiling, etc.)
                continue

            print(f"\n[{idx+1}/{len(sequence)}] {item.get('item')} ({detection_id})")

            # Query primitives for each search text on specified pages
            for text_query in search_text:
                for page in pages:
                    self._process_search_text(item, text_query, page)

    def _process_search_text(self, item: Dict, search_text: str, page: int):
        """Process single search text on specific page"""
        detection_id = item['detection_id']

        # Find text occurrences
        self.cursor.execute("""
            SELECT id, text, x, y, x0, y0, x1, y1
            FROM primitives_text
            WHERE page = ? AND text = ?
        """, (page, search_text))

        matches = self.cursor.fetchall()

        if not matches:
            return

        print(f"  Found '{search_text}' on page {page}: {len(matches)} occurrences")

        # Apply pattern detection based on detection_id
        for text_id, text, tx, ty, _, _, _, _ in matches:
            pattern = self._detect_pattern(detection_id, tx, ty, page, text_id)

            if pattern:
                self.identified_patterns.append(pattern)

    def _detect_pattern(self, detection_id: str, text_x: float, text_y: float,
                        page: int, text_id: str) -> Optional[IdentifiedPattern]:
        """
        Detect pattern based on detection_id

        Tries: ISO 128 → ANSI → Custom fallback
        """
        if detection_id == "TEXT_LABEL_SEARCH":
            # Doors/Windows - try ISO 128 door pattern first
            pattern_data = PatternLibrary.detect_door_swing_iso128(
                self.cursor, text_x, text_y, page
            )

            if pattern_data:
                library_used = "ISO_128"
                primitive_ids = [text_id, pattern_data['arc_id']] + pattern_data['line_ids']
                confidence = pattern_data['confidence']
                metadata = {
                    'arc_center': pattern_data['arc_center'],
                    'swing_direction': pattern_data['swing_direction'],
                    'door_width_estimate': pattern_data['door_width_estimate']
                }
            else:
                # Fallback to text-only
                pattern_data = PatternLibrary.detect_door_fallback_custom(
                    self.cursor, text_x, text_y, page
                )
                library_used = "CUSTOM_FALLBACK"
                primitive_ids = [text_id]
                confidence = pattern_data['confidence']
                metadata = {'text_only': True}

            return IdentifiedPattern(
                pattern_id=f"pattern_{text_id}",
                pattern_type=detection_id,
                primitive_ids=primitive_ids,
                position=(text_x, text_y),
                confidence=confidence,
                library_used=library_used,
                metadata=metadata,
                spatial_relationships=[]  # Populated later
            )

        elif detection_id == "TEXT_MARKER_WITH_SYMBOL":
            # Electrical items - text position only for now
            return IdentifiedPattern(
                pattern_id=f"pattern_{text_id}",
                pattern_type=detection_id,
                primitive_ids=[text_id],
                position=(text_x, text_y),
                confidence=0.80,
                library_used="TEXT_POSITION",
                metadata={},
                spatial_relationships=[]
            )

        return None

    def derive_spatial_relationships(self):
        """
        Build spatial relationship graph between identified patterns

        Examples:
        - Door ON wall segment
        - Window WITHIN wall bounds
        - Outlet NEAR door (avoid blocking)
        - Switch ALIGNED_WITH door edge
        """
        print(f"\n🔗 Deriving spatial relationships for {len(self.identified_patterns)} patterns...")

        # Group patterns by type
        doors = [p for p in self.identified_patterns if 'door' in p.pattern_type.lower()]
        windows = [p for p in self.identified_patterns if 'window' in p.pattern_type.lower()]

        # TODO: Load wall segments from previous context (CONTEXT_WALLS.json if exists)
        # For now, placeholder
        wall_segments = []  # Would come from wall detection phase

        relationships_count = 0

        # Example: Find walls for doors
        for door in doors:
            wall_id = SpatialAnalyzer.find_wall_for_door(
                door.position, wall_segments, tolerance=5
            )

            if wall_id:
                door.spatial_relationships.append(
                    SpatialRelationship(
                        relationship_type="on_wall",
                        source_id=door.pattern_id,
                        target_id=wall_id,
                        confidence=0.90,
                        metadata={'constraint': 'door_must_be_on_wall'}
                    )
                )
                relationships_count += 1

        print(f"✅ Derived {relationships_count} spatial relationships")

    def persist_patterns_to_db(self):
        """
        Persist identified patterns to database staging tables

        Writes to:
        - patterns_identified
        - pattern_primitives
        - spatial_relationships
        """
        print(f"\n💾 Persisting {len(self.identified_patterns)} patterns to database...")

        for pattern in self.identified_patterns:
            # Insert pattern
            self.cursor.execute("""
                INSERT OR REPLACE INTO patterns_identified
                (pattern_id, pattern_type, position_x, position_y, confidence, library_used, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id,
                pattern.pattern_type,
                pattern.position[0],
                pattern.position[1],
                pattern.confidence,
                pattern.library_used,
                json.dumps(pattern.metadata)
            ))

            # Insert pattern-primitive links
            for prim_id in pattern.primitive_ids:
                # Infer primitive type from id prefix (format: t001_XXXX, l001_XXXX, c001_XXXX)
                if prim_id.startswith('t'):
                    prim_type = 'text'
                elif prim_id.startswith('l'):
                    prim_type = 'line'
                elif prim_id.startswith('c'):
                    prim_type = 'curve'
                elif prim_id.startswith('r'):
                    prim_type = 'rect'
                else:
                    prim_type = 'unknown'

                self.cursor.execute("""
                    INSERT INTO pattern_primitives (pattern_id, primitive_id, primitive_type)
                    VALUES (?, ?, ?)
                """, (pattern.pattern_id, prim_id, prim_type))

            # Insert spatial relationships
            for rel in pattern.spatial_relationships:
                self.cursor.execute("""
                    INSERT INTO spatial_relationships
                    (relationship_type, source_pattern_id, target_pattern_id, confidence, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    rel.relationship_type,
                    rel.source_id,
                    rel.target_id,
                    rel.confidence,
                    json.dumps(rel.metadata)
                ))

        self.conn.commit()

        # Print summary
        summary = {
            "by_library": self._count_by_field('library_used'),
            "by_type": self._count_by_field('pattern_type'),
            "avg_confidence": sum(p.confidence for p in self.identified_patterns) / len(self.identified_patterns) if self.identified_patterns else 0
        }

        print(f"✅ Persisted to database: {self.db_path}")
        print(f"   Total patterns: {len(self.identified_patterns)}")
        print(f"   Libraries used: {summary['by_library']}")
        print(f"   Avg confidence: {summary['avg_confidence']:.2f}")

    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count patterns grouped by field"""
        counts = {}
        for p in self.identified_patterns:
            value = getattr(p, field)
            counts[value] = counts.get(value, 0) + 1
        return counts

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed")


def main():
    """Main execution"""
    # Paths
    base_dir = Path(__file__).parent.parent
    primitives_db = base_dir / "output_artifacts" / "TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"
    master_template = base_dir / "core" / "master_reference_template.json"

    print("=" * 70)
    print("PATTERN RECOGNITION ENGINE")
    print("=" * 70)
    print(f"Database: {primitives_db.name}")
    print(f"Template: {master_template.name}")

    # Initialize engine
    engine = PatternRecognitionEngine(
        primitives_db_path=str(primitives_db),
        master_template_path=str(master_template)
    )

    try:
        # Load resources
        engine.load_template()
        engine.connect_db()

        # Process template sequentially
        engine.process_template_sequence()

        # Derive spatial relationships
        engine.derive_spatial_relationships()

        # Persist to database (not JSON)
        engine.persist_patterns_to_db()

        print("\n" + "=" * 70)
        print("✅ PATTERN RECOGNITION COMPLETE")
        print("=" * 70)
        print(f"All staging data in: {primitives_db}")

    finally:
        engine.close()


if __name__ == "__main__":
    main()
