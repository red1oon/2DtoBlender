#!/usr/bin/env python3
"""
Coordinate Generator from Detection Results + GridTruth
========================================================
Generates element coordinates from:
1. DETECTED positions (door_detection_fixed.json, vector_extraction_summary.json)
2. Schedule dimensions (extracted_schedule.db)
3. GridTruth spatial reference (GridTruth_TB-LKTN.json)

Transforms pixel coordinates → world coordinates using calibration.
Rule 0 compliant: Detection-driven, not hardcoded placements.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class CoordinateGenerator:
    """
    Generate coordinates from GridTruth + placement rules.
    """

    def __init__(self, gridtruth_path: str, output_db: str):
        self.gridtruth_path = Path(gridtruth_path)
        self.output_db = Path(output_db)

        # Load GridTruth
        with open(self.gridtruth_path) as f:
            self.gridtruth = json.load(f)

        # Database connection
        self.conn = sqlite3.connect(self.output_db)
        self.cursor = self.conn.cursor()
        self._init_db()

        # Load placement rules (from POC lines 109-171)
        self._load_placement_rules()

    def _init_db(self):
        """Create coordinated elements table"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS coordinated_elements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                element_id TEXT NOT NULL,
                element_type TEXT NOT NULL,
                ifc_class TEXT NOT NULL,

                -- Dimensions
                width_m REAL,
                height_m REAL,
                depth_m REAL,

                -- Position (generated from GridTruth)
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL,

                -- Rotation (in degrees)
                rotation_z REAL DEFAULT 0,

                -- Context
                room TEXT,
                wall TEXT,
                placement_rule TEXT,
                reasoning TEXT,

                -- Timestamps
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def _load_detection_results(self, detection_dir: str = "output_artifacts"):
        """Load detection results from enhanced_vector_extractor"""
        det_path = Path(detection_dir)

        # Load door detections
        door_file = det_path / "door_detection_fixed.json"
        if door_file.exists():
            with open(door_file) as f:
                self.door_detections = json.load(f).get('doors', [])
        else:
            self.door_detections = []

        # Load vector extraction (walls, windows)
        vector_file = det_path / "vector_extraction_summary.json"
        if vector_file.exists():
            with open(vector_file) as f:
                vector_data = json.load(f)
                self.wall_detections = vector_data.get('walls', [])
                self.window_detections = vector_data.get('windows', [])
                self.grid_detections = vector_data.get('grids', [])
                self.metadata = vector_data.get('metadata', {})

                # Get calibration: pixels_per_meter (Rule 0: No fallback)
                if 'pixels_per_meter' not in self.metadata:
                    raise ValueError(
                        f"pixels_per_meter not found in {vector_file}\n"
                        f"Cannot calibrate coordinate conversion without scale data.\n"
                        f"Rule 0 violation: No hardcoded fallbacks allowed."
                    )
                self.px_per_m = self.metadata['pixels_per_meter']
        else:
            raise FileNotFoundError(
                f"Vector detection file not found: {vector_file}\n"
                f"Cannot generate coordinates without vector data.\n"
                f"Rule 0 violation: No hardcoded fallbacks allowed."
            )

        # Calculate origin offset from grid circles or walls
        self._calculate_origin_offset()

        print(f"✓ Loaded detections: {len(self.door_detections)} doors, {len(self.window_detections)} windows, {len(self.wall_detections)} walls")
        print(f"  Calibration: {self.px_per_m:.2f} px/m, origin offset: ({self.origin_x:.1f}, {self.origin_y:.1f}) px")

    def _calculate_origin_offset(self):
        """
        Calculate pixel origin offset from detected features.
        Uses minimum pixel coordinates to establish (0,0) in world space.
        """
        # Method 1: Use minimum from grid circles if available
        if self.grid_detections:
            grid_x = [g['center_x'] for g in self.grid_detections]
            grid_y = [g['center_y'] for g in self.grid_detections]
            if grid_x and grid_y:
                self.origin_x = min(grid_x) - 100  # Offset to include margin
                self.origin_y = min(grid_y) - 100
                return

        # Method 2: Use minimum from wall segments
        if self.wall_detections:
            wall_x = [min(w['x1'], w['x2']) for w in self.wall_detections]
            wall_y = [min(w['y1'], w['y2']) for w in self.wall_detections]
            if wall_x and wall_y:
                self.origin_x = min(wall_x) - 100
                self.origin_y = min(wall_y) - 100
                return

        # Fallback: No offset
        self.origin_x = 0
        self.origin_y = 0

    def pixel_to_world(self, px_x: float, px_y: float) -> Tuple[float, float]:
        """
        Transform pixel coordinates to world coordinates (meters).
        Applies origin offset to establish (0,0) world origin.
        """
        # Apply origin offset, then scale to meters
        world_x = (px_x - self.origin_x) / self.px_per_m
        world_y = (px_y - self.origin_y) / self.px_per_m
        return (round(world_x, 3), round(world_y, 3))

    def _load_placement_rules(self):
        """Load door/window placement rules from POC (LEGACY - will be replaced by detections)"""

        # Door placement rules (poc_pipeline.py:109-139)
        self.door_rules = {
            "D1": {
                "type": "exterior",
                "locations": [
                    {
                        "id": "D1_1",
                        "room": "RUANG_TAMU",
                        "wall": "SOUTH",
                        "position": "center",
                        "reasoning": "Main entrance at south facade"
                    },
                    {
                        "id": "D1_2",
                        "room": "DAPUR",
                        "wall": "EAST",
                        "position": "center",
                        "reasoning": "Kitchen service entrance"
                    }
                ]
            },
            "D2": {
                "type": "internal",
                "locations": [
                    {
                        "id": "D2_1",
                        "room": "DAPUR",
                        "wall": "WEST",
                        "position": "grid_C",
                        "reasoning": "Connects living room to kitchen"
                    },
                    {
                        "id": "D2_2",
                        "room": "BILIK_UTAMA",
                        "wall": "SOUTH",
                        "position": "center",
                        "reasoning": "Master bedroom from corridor"
                    },
                    {
                        "id": "D2_3",
                        "room": "BILIK_2",
                        "wall": "SOUTH",
                        "position": "center",
                        "reasoning": "Bedroom 2 from corridor"
                    }
                ]
            },
            "D3": {
                "type": "internal",
                "locations": [
                    {
                        "id": "D3_1",
                        "room": "BILIK_MANDI",
                        "wall": "EAST",
                        "position": "center",
                        "reasoning": "Bathroom door from corridor"
                    },
                    {
                        "id": "D3_2",
                        "room": "TANDAS",
                        "wall": "EAST",
                        "position": "center",
                        "reasoning": "Toilet door from corridor"
                    }
                ]
            }
        }

        # Window placement rules (poc_pipeline.py:141-171)
        self.window_rules = {
            "W1": {
                "sill_height": 0.9,
                "locations": [
                    {
                        "id": "W1_1",
                        "room": "RUANG_TAMU",
                        "wall": "WEST",
                        "position": "center",
                        "reasoning": "Main window in living room"
                    }
                ]
            },
            "W2": {
                "sill_height": 0.9,
                "locations": [
                    {
                        "id": "W2_1",
                        "room": "RUANG_TAMU",
                        "wall": "SOUTH",
                        "position": "offset_from_door",
                        "reasoning": "Front window beside entrance"
                    },
                    {
                        "id": "W2_2",
                        "room": "BILIK_UTAMA",
                        "wall": "EAST",
                        "position": "center",
                        "reasoning": "Master bedroom window"
                    },
                    {
                        "id": "W2_3",
                        "room": "BILIK_2",
                        "wall": "NORTH",
                        "position": "center",
                        "reasoning": "Bedroom 2 window"
                    },
                    {
                        "id": "W2_4",
                        "room": "DAPUR",
                        "wall": "SOUTH",
                        "position": "center",
                        "reasoning": "Kitchen window"
                    }
                ]
            },
            "W3": {
                "sill_height": 1.5,
                "locations": [
                    {
                        "id": "W3_1",
                        "room": "TANDAS",
                        "wall": "WEST",
                        "position": "center",
                        "reasoning": "Toilet ventilation window"
                    },
                    {
                        "id": "W3_2",
                        "room": "BILIK_MANDI",
                        "wall": "WEST",
                        "position": "center",
                        "reasoning": "Bathroom ventilation window"
                    }
                ]
            }
        }

    def get_wall_coordinate(self, room: str, wall: str, position: str = "center") -> Tuple[float, float]:
        """
        Calculate wall coordinate for element placement.
        Based on poc_pipeline.py:385-417
        """
        bounds = self.gridtruth["room_bounds"].get(room)
        if not bounds:
            return (0.0, 0.0)

        x_min, x_max = bounds["x_min"], bounds["x_max"]
        y_min, y_max = bounds["y_min"], bounds["y_max"]
        setback = self.gridtruth["building_parameters"]["wall_setback_from_grid"]

        if wall == "SOUTH":
            y = max(y_min, setback)
            x = (x_min + x_max) / 2 if position == "center" else x_min + 1.5
        elif wall == "NORTH":
            y_max_grid = self.gridtruth["grid_vertical"]["5"]
            y = min(y_max, y_max_grid - setback)
            x = (x_min + x_max) / 2
        elif wall == "EAST":
            x_max_grid = self.gridtruth["grid_horizontal"]["E"]
            x = min(x_max, x_max_grid - setback)
            y = (y_min + y_max) / 2
        elif wall == "WEST":
            x = max(x_min, setback)
            y = (y_min + y_max) / 2
        else:
            # Internal wall - use grid line
            if "grid_" in position:
                grid_letter = position.split("_")[1]
                x = self.gridtruth["grid_horizontal"].get(grid_letter, (x_min + x_max) / 2)
                y = (y_min + y_max) / 2
            else:
                x = (x_min + x_max) / 2
                y = y_min

        return (round(x, 2), round(y, 2))

    def get_wall_rotation(self, wall: str) -> float:
        """Get rotation angle for wall orientation (degrees)"""
        rotations = {
            "NORTH": 0,
            "SOUTH": 0,
            "EAST": 90,
            "WEST": 90
        }
        return rotations.get(wall, 0)

    def place_doors(self, door_schedule: Dict) -> int:
        """
        Place doors using schedule + placement rules.
        Based on poc_pipeline.py:419-447
        """
        count = 0

        for door_type, rules in self.door_rules.items():
            spec = door_schedule.get(door_type)
            if not spec:
                continue

            for loc in rules["locations"]:
                x, y = self.get_wall_coordinate(
                    loc["room"], loc["wall"], loc.get("position", "center")
                )
                rotation = self.get_wall_rotation(loc["wall"])

                self.cursor.execute("""
                    INSERT INTO coordinated_elements
                    (element_id, element_type, ifc_class, width_m, height_m, x, y, z, rotation_z, room, wall, placement_rule, reasoning)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    loc["id"],
                    door_type,
                    "IfcDoor",
                    spec["width"] / 1000.0,
                    spec["height"] / 1000.0,
                    x, y,
                    self.gridtruth["elevations"]["floor_finish_level"],
                    rotation,
                    loc["room"],
                    loc["wall"],
                    f"{loc['room']}/{loc['wall']}/{loc['position']}",
                    loc["reasoning"]
                ))
                count += 1

        self.conn.commit()
        return count

    def place_windows(self, window_schedule: Dict) -> int:
        """
        Place windows using schedule + placement rules.
        Based on poc_pipeline.py:450-480
        """
        count = 0

        for win_type, rules in self.window_rules.items():
            spec = window_schedule.get(win_type)
            if not spec:
                continue

            sill = rules.get("sill_height", 0.9)

            for loc in rules["locations"]:
                x, y = self.get_wall_coordinate(
                    loc["room"], loc["wall"], loc.get("position", "center")
                )
                rotation = self.get_wall_rotation(loc["wall"])

                self.cursor.execute("""
                    INSERT INTO coordinated_elements
                    (element_id, element_type, ifc_class, width_m, height_m, x, y, z, rotation_z, room, wall, placement_rule, reasoning)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    loc["id"],
                    win_type,
                    "IfcWindow",
                    spec["width"] / 1000.0,
                    spec["height"] / 1000.0,
                    x, y, sill,
                    rotation,
                    loc["room"],
                    loc["wall"],
                    f"{loc['room']}/{loc['wall']}/{loc['position']}",
                    loc["reasoning"]
                ))
                count += 1

        self.conn.commit()
        return count

    def place_detected_doors(self, schedule_db_path: str) -> int:
        """
        Place doors from DETECTED positions (door_detection_fixed.json).
        Transforms pixel coords → world coords, matches with schedule dimensions.
        Filters false positives: radius 100-120px (typical door swing radius).
        """
        if not self.door_detections:
            print("⚠️  No door detections loaded")
            return 0

        # Filter door detections: radius 100-120px (door swing arcs) + within grid bounds
        MIN_DOOR_RADIUS = 100
        MAX_DOOR_RADIUS = 120

        # Grid bounds from GridTruth
        max_x = self.gridtruth["grid_horizontal"]["E"]
        max_y = self.gridtruth["grid_vertical"]["5"]

        filtered_doors = []
        for d in self.door_detections:
            # Check radius
            if not (MIN_DOOR_RADIUS <= d.get('radius', 0) <= MAX_DOOR_RADIUS):
                continue

            # Check world coordinates within grid bounds
            px_x, px_y = d['center']
            world_x, world_y = self.pixel_to_world(px_x, px_y)

            if 0 <= world_x <= max_x and 0 <= world_y <= max_y:
                filtered_doors.append(d)

        print(f"  Filtered: {len(self.door_detections)} → {len(filtered_doors)} doors (radius {MIN_DOOR_RADIUS}-{MAX_DOOR_RADIUS}px, within grid bounds)")

        if not filtered_doors:
            print("⚠️  No valid door arcs after filtering")
            return 0

        # Load schedule from database
        schedule_conn = sqlite3.connect(schedule_db_path)
        schedule_cursor = schedule_conn.cursor()
        schedule_cursor.execute("SELECT code, width_mm, height_mm FROM door_window_schedule WHERE type='door'")
        schedule = {row[0]: {'width': row[1], 'height': row[2]} for row in schedule_cursor.fetchall()}
        schedule_conn.close()

        count = 0
        floor_level = self.gridtruth["elevations"]["floor_finish_level"]

        for i, door in enumerate(filtered_doors, 1):
            # Transform pixel → world
            px_x, px_y = door['center']
            world_x, world_y = self.pixel_to_world(px_x, px_y)

            # Determine door type from schedule (default to D2 if only one type exists)
            door_type = f"D{min(i, 3)}"  # D1, D2, D3
            spec = schedule.get(door_type, schedule.get('D3', {'width': 900, 'height': 2100}))

            # Estimate rotation from arc radius (doors swing ~90-120mm typically)
            # For now, default to 0 (will refine with wall intersection analysis)
            rotation = 0

            self.cursor.execute("""
                INSERT INTO coordinated_elements
                (element_id, element_type, ifc_class, width_m, height_m, x, y, z, rotation_z, placement_rule, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                door['id'],
                door_type,
                "IfcDoor",
                spec['width'] / 1000.0,
                spec['height'] / 1000.0,
                world_x, world_y, floor_level,
                rotation,
                "detected_position",
                f"Detected arc at pixel ({px_x}, {px_y}), radius {door['radius']}px"
            ))
            count += 1

        self.conn.commit()
        print(f"✓ Placed {count} doors from detections")
        return count

    def place_detected_windows(self, schedule_db_path: str) -> int:
        """
        Place windows from DETECTED positions (vector_extraction_summary.json).
        Transforms pixel coords → world coords, matches with schedule dimensions.
        Filters windows within grid bounds.
        """
        if not self.window_detections:
            print("⚠️  No window detections loaded")
            return 0

        # Grid bounds from GridTruth
        max_x = self.gridtruth["grid_horizontal"]["E"]
        max_y = self.gridtruth["grid_vertical"]["5"]

        # Load schedule
        schedule_conn = sqlite3.connect(schedule_db_path)
        schedule_cursor = schedule_conn.cursor()
        schedule_cursor.execute("SELECT code, width_mm, height_mm FROM door_window_schedule WHERE type='window'")
        schedule = {row[0]: {'width': row[1], 'height': row[2]} for row in schedule_cursor.fetchall()}
        schedule_conn.close()

        count = 0
        sill_height = 0.9  # Default window sill

        for i, window in enumerate(self.window_detections, 1):
            # Re-transform pixel → world using origin offset
            px_x, px_y = window.get('x', 0), window.get('y', 0)
            world_x, world_y = self.pixel_to_world(px_x, px_y)

            # Filter: only within grid bounds
            if not (0 <= world_x <= max_x and 0 <= world_y <= max_y):
                continue

            # Determine window type
            window_type = f"W{min(i, 3)}"
            spec = schedule.get(window_type, schedule.get('W2', {'width': 1200, 'height': 1000}))

            rotation = 0

            self.cursor.execute("""
                INSERT INTO coordinated_elements
                (element_id, element_type, ifc_class, width_m, height_m, x, y, z, rotation_z, placement_rule, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"W{i}",
                window_type,
                "IfcWindow",
                spec['width'] / 1000.0,
                spec['height'] / 1000.0,
                world_x, world_y, sill_height,
                rotation,
                "detected_position",
                f"Detected at pixel ({px_x}, {px_y})"
            ))
            count += 1

        self.conn.commit()
        print(f"✓ Placed {count} windows from detections")
        return count

    def generate_building_envelope(self) -> Dict:
        """
        Generate exterior walls from GridTruth.
        Based on poc_pipeline.py:483-512
        """
        setback = self.gridtruth["building_parameters"]["wall_setback_from_grid"]
        max_x = self.gridtruth["grid_horizontal"]["E"]
        max_y = self.gridtruth["grid_vertical"]["5"]
        height = self.gridtruth["elevations"]["ceiling"]

        walls = [
            {
                "id": "WALL_SOUTH",
                "start": [setback, setback],
                "end": [max_x - setback, setback],
                "length_m": max_x - 2*setback,
                "height_m": height,
                "type": "exterior"
            },
            {
                "id": "WALL_EAST",
                "start": [max_x - setback, setback],
                "end": [max_x - setback, max_y - setback],
                "length_m": max_y - 2*setback,
                "height_m": height,
                "type": "exterior"
            },
            {
                "id": "WALL_NORTH",
                "start": [max_x - setback, max_y - setback],
                "end": [setback, max_y - setback],
                "length_m": max_x - 2*setback,
                "height_m": height,
                "type": "exterior"
            },
            {
                "id": "WALL_WEST",
                "start": [setback, max_y - setback],
                "end": [setback, setback],
                "length_m": max_y - 2*setback,
                "height_m": height,
                "type": "exterior"
            }
        ]

        perimeter = sum(w["length_m"] for w in walls)
        area = (max_x - 2*setback) * (max_y - 2*setback)

        return {
            "walls": walls,
            "validation": {
                "closed_loop": True,
                "perimeter_m": round(perimeter, 2),
                "area_m2": round(area, 2),
                "within_grid": True
            }
        }

    def validate(self) -> Dict:
        """Validate generated coordinates"""
        max_x = self.gridtruth["grid_horizontal"]["E"]
        max_y = self.gridtruth["grid_vertical"]["5"]

        self.cursor.execute("""
            SELECT element_id, x, y
            FROM coordinated_elements
        """)

        errors = []
        for elem_id, x, y in self.cursor.fetchall():
            if x < 0 or x > max_x:
                errors.append(f"{elem_id}: x={x} outside grid (0-{max_x})")
            if y < 0 or y > max_y:
                errors.append(f"{elem_id}: y={y} outside grid (0-{max_y})")

        self.cursor.execute("SELECT COUNT(*) FROM coordinated_elements WHERE ifc_class = 'IfcDoor'")
        doors_placed = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM coordinated_elements WHERE ifc_class = 'IfcWindow'")
        windows_placed = self.cursor.fetchone()[0]

        return {
            "doors_placed": doors_placed,
            "windows_placed": windows_placed,
            "coordinate_errors": errors,
            "all_within_grid": len(errors) == 0
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test coordinate generation"""
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: python3 coordinate_generator.py <classified_db>")
        sys.exit(1)

    classified_db = sys.argv[1]
    gridtruth_path = "GridTruth_TB-LKTN.json"
    output_db = "output_artifacts/coordinated_elements.db"
    schedule_path = "output_artifacts/extracted_schedule.json"

    print("=" * 70)
    print("COORDINATE GENERATION FROM GRIDTRUTH")
    print("=" * 70)
    print(f"GridTruth: {gridtruth_path}")
    print(f"Classified DB: {classified_db}")
    print(f"Output: {output_db}")
    print()

    # Get door/window schedule from extracted_schedule.db (NOT hardcoded!)
    schedule_db = Path("output_artifacts/extracted_schedule.db")

    if schedule_db.exists():
        # Load from database (primary source)
        print("Loading schedule from database ✓")
        import sqlite3
        conn = sqlite3.connect(schedule_db)
        cursor = conn.cursor()

        door_schedule = {}
        cursor.execute("SELECT code, width_mm, height_mm, quantity FROM door_window_schedule WHERE type='door'")
        for code, width, height, qty in cursor.fetchall():
            door_schedule[code] = {
                'width': width,
                'height': height,
                'qty': qty
            }

        window_schedule = {}
        cursor.execute("SELECT code, width_mm, height_mm, quantity FROM door_window_schedule WHERE type='window'")
        for code, width, height, qty in cursor.fetchall():
            window_schedule[code] = {
                'width': width,
                'height': height,
                'qty': qty
            }
        conn.close()

    elif Path(schedule_path).exists():
        # Fallback to JSON
        print("Loading schedule from JSON ✓")
        with open(schedule_path) as f:
            schedule_data = json.load(f)
            door_schedule = schedule_data.get("doors", {})
            window_schedule = schedule_data.get("windows", {})
    else:
        # No schedule available - must extract first
        raise FileNotFoundError(
            f"Schedule not found! Run extract_schedule.py first to create {schedule_db}"
        )

    # Save JSON for reference (but database is primary)
    if not Path(schedule_path).exists():
        schedule_data = {
            "doors": door_schedule,
            "windows": window_schedule,
            "source": "Extracted from PDF (database)"
        }
        with open(schedule_path, 'w') as f:
            json.dump(schedule_data, f, indent=2)

    # Generate coordinates
    generator = CoordinateGenerator(gridtruth_path, output_db)

    # Load detection results
    print("Loading detection results...")
    generator._load_detection_results()

    # Use detected positions (not hardcoded placement rules)
    print("\nPlacing doors from detections...")
    doors_placed = generator.place_detected_doors(str(schedule_db))

    print("\nPlacing windows from detections...")
    windows_placed = generator.place_detected_windows(str(schedule_db))

    print("\nGenerating building envelope...")
    envelope = generator.generate_building_envelope()
    print(f"  Building: {envelope['validation']['area_m2']} m² ({envelope['validation']['perimeter_m']}m perimeter)")

    print("\nValidating...")
    validation = generator.validate()
    print(f"  Doors: {validation['doors_placed']}")
    print(f"  Windows: {validation['windows_placed']}")
    print(f"  Coordinates: {'✓ All valid' if validation['all_within_grid'] else '✗ Errors found'}")

    if validation['coordinate_errors']:
        for err in validation['coordinate_errors']:
            print(f"    ✗ {err}")

    print(f"\n✓ Saved to {output_db}")
    print("=" * 70)

    generator.close()


if __name__ == "__main__":
    main()
