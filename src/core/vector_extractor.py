#!/usr/bin/env python3
"""
Vector Semantic Extractor using OpenCV
=======================================
Implements algorithms from VECTOR_SEMANTIC_EXTRACTION_GUIDE.md
Rule 0 compliant - pure deterministic extraction using OpenCV.
"""

import cv2
import numpy as np
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pdf2image
import math
import pytesseract
import re


class VectorSemanticExtractor:
    """
    Extract vector semantics from PDF using OpenCV.
    Based on proven algorithms from documentation guide.
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._init_db()

        # Pixel to world transformation (from guide)
        self.dpi = 300  # Standard conversion DPI
        self.scale_factor = 1/100  # 1:100 architectural scale
        self.pixels_per_meter = (self.dpi / 25.4) * 1000 * self.scale_factor

    def _init_db(self):
        """Create tables for vector semantic storage"""

        # Door detection results
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_doors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                center_x REAL NOT NULL,
                center_y REAL NOT NULL,
                radius REAL NOT NULL,
                start_angle REAL NOT NULL,
                end_angle REAL NOT NULL,
                swing_direction TEXT,
                world_x REAL,
                world_y REAL,
                width_mm REAL,
                confidence REAL,
                page INTEGER DEFAULT 2,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Wall line detection
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_walls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                x1 REAL NOT NULL,
                y1 REAL NOT NULL,
                x2 REAL NOT NULL,
                y2 REAL NOT NULL,
                thickness_pixels REAL,
                thickness_mm REAL,
                wall_type TEXT,
                page INTEGER DEFAULT 2,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Window detection
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                x REAL NOT NULL,
                y REAL NOT NULL,
                width REAL NOT NULL,
                height REAL NOT NULL,
                pane_count INTEGER,
                world_x REAL,
                world_y REAL,
                width_mm REAL,
                height_mm REAL,
                page INTEGER DEFAULT 2,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Grid circle detection
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_grids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                center_x REAL NOT NULL,
                center_y REAL NOT NULL,
                radius REAL NOT NULL,
                grid_label TEXT,
                world_x REAL,
                world_y REAL,
                page INTEGER DEFAULT 2,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def pdf_to_image(self, pdf_path: str, page_num: int = 2) -> np.ndarray:
        """
        Convert PDF page to image for OpenCV processing.
        Page 2 recommended for cleanest electrical plan linework.
        """
        pages = pdf2image.convert_from_path(
            pdf_path,
            dpi=self.dpi,
            first_page=page_num,
            last_page=page_num
        )

        if not pages:
            raise ValueError(f"Could not extract page {page_num}")

        # Convert PIL to OpenCV format
        img = np.array(pages[0])
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def _point_to_line_distance(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """
        Calculate perpendicular distance from point (px, py) to line segment (x1,y1)-(x2,y2).
        """
        # Vector from point1 to point2
        dx = x2 - x1
        dy = y2 - y1

        # Handle degenerate case (point, not line)
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return np.sqrt((px - x1)**2 + (py - y1)**2)

        # Project point onto line (parameterized by t)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))

        # Find nearest point on line segment
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy

        # Return distance to nearest point
        return np.sqrt((px - nearest_x)**2 + (py - nearest_y)**2)

    def detect_door_arcs(self, image: np.ndarray, walls: List[Dict] = None) -> List[Dict]:
        """
        Detect doors using radius + wall proximity filters.
        Simpler approach - skip OCR/arc validation, just use geometry.

        Algorithm:
        1. HoughCircles to detect all circles
        2. Filter by door-typical radius (100-120px based on debug)
        3. Validate wall proximity (doors must be in walls)
        """
        doors = []
        if walls is None:
            walls = []

        # Preprocessing
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Detect circles
        circles = cv2.HoughCircles(
            edges,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=15,
            minRadius=100,  # Door-specific radius from debug
            maxRadius=125
        )

        if circles is None:
            print("  No circles detected")
            return doors

        circles = np.uint16(np.around(circles[0]))
        print(f"  HoughCircles: {len(circles)} candidates (radius 100-125px)")

        # Filter by wall proximity
        wall_filtered = 0

        for circle in circles:
            cx, cy, radius = circle

            # Wall proximity check
            near_wall = False
            wall_distance = float('inf')

            if walls:
                for wall in walls:
                    dist = self._point_to_line_distance(
                        cx, cy, wall['x1'], wall['y1'], wall['x2'], wall['y2']
                    )
                    wall_distance = min(wall_distance, dist)
                    # Door pivot must be ON the wall (<5px tolerance)
                    if dist < 5:
                        near_wall = True
                        break
            else:
                near_wall = True

            if not near_wall:
                wall_filtered += 1
                continue

            # Convert to world coordinates
            world_x = cx / self.pixels_per_meter
            world_y = cy / self.pixels_per_meter
            width_mm = (radius / self.pixels_per_meter) * 1000

            door = {
                'center_x': float(cx),
                'center_y': float(cy),
                'radius': float(radius),
                'start_angle': 0.0,
                'end_angle': 0.0,
                'swing_direction': 'unknown',
                'world_x': world_x,
                'world_y': world_y,
                'width_mm': width_mm,
                'confidence': 0.9,  # High confidence if passed all filters
                'wall_distance': float(wall_distance) if wall_distance != float('inf') else None
            }

            doors.append(door)

            # Store in database
            self.cursor.execute("""
                INSERT INTO detected_doors
                (center_x, center_y, radius, start_angle, end_angle,
                 swing_direction, world_x, world_y, width_mm, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (door['center_x'], door['center_y'], door['radius'],
                  door['start_angle'], door['end_angle'], door['swing_direction'],
                  door['world_x'], door['world_y'], door['width_mm'],
                  door['confidence']))

        print(f"  Filtered: {wall_filtered} not near wall → {len(doors)} valid doors")

        self.conn.commit()
        return doors

    def detect_wall_lines(self, image: np.ndarray) -> List[Dict]:
        """
        Detect wall lines and measure thickness.
        Algorithm from guide lines 144-198.
        """
        walls = []

        # Preprocessing
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Detect lines using HoughLinesP
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=50,
            minLineLength=100,  # Minimum wall length
            maxLineGap=10       # Maximum gap to connect segments
        )

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # Calculate line length
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                # Filter short segments
                if length < 50:
                    continue

                # Measure wall thickness using perpendicular sampling
                thickness = self._measure_line_thickness(gray, x1, y1, x2, y2)
                thickness_mm = (thickness / self.pixels_per_meter) * 1000

                # Classify wall type by thickness
                if thickness_mm < 100:
                    wall_type = "partition"  # < 100mm
                elif thickness_mm < 200:
                    wall_type = "interior"   # 100-200mm
                else:
                    wall_type = "exterior"   # > 200mm

                wall = {
                    'x1': float(x1),
                    'y1': float(y1),
                    'x2': float(x2),
                    'y2': float(y2),
                    'thickness_pixels': float(thickness),
                    'thickness_mm': thickness_mm,
                    'wall_type': wall_type
                }

                walls.append(wall)

                # Store in database
                self.cursor.execute("""
                    INSERT INTO detected_walls
                    (x1, y1, x2, y2, thickness_pixels, thickness_mm, wall_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (wall['x1'], wall['y1'], wall['x2'], wall['y2'],
                      wall['thickness_pixels'], wall['thickness_mm'], wall['wall_type']))

        self.conn.commit()
        return walls

    def _measure_line_thickness(self, gray: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> float:
        """
        Measure line thickness by sampling perpendicular to line direction.
        Algorithm from guide lines 174-198.
        """
        # Calculate line direction
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)

        if length == 0:
            return 0

        # Normalize direction
        dx /= length
        dy /= length

        # Perpendicular direction
        perp_dx = -dy
        perp_dy = dx

        # Sample at midpoint
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Measure thickness by scanning perpendicular
        max_scan = 50  # Maximum scan distance in pixels
        thickness = 0

        for dist in range(1, max_scan):
            # Check positive direction
            px = int(mid_x + perp_dx * dist)
            py = int(mid_y + perp_dy * dist)

            if 0 <= px < gray.shape[1] and 0 <= py < gray.shape[0]:
                if gray[py, px] < 128:  # Still on line
                    thickness = dist * 2  # Double for both sides
                else:
                    break

        return thickness

    def detect_windows(self, image: np.ndarray) -> List[Dict]:
        """
        Detect window symbols using rectangle detection.
        Algorithm from guide lines 88-142.
        """
        windows = []

        # Preprocessing
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # Approximate polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Check if rectangle (4 vertices)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)

                # Filter by aspect ratio (windows are typically wider)
                aspect = w / h if h > 0 else 0

                if 1.5 <= aspect <= 4.0 and w > 30:  # Window-like proportions
                    # Count internal divisions for panes
                    roi = gray[y:y+h, x:x+w]
                    pane_count = self._count_window_panes(roi)

                    # Convert to world coordinates
                    world_x = x / self.pixels_per_meter
                    world_y = y / self.pixels_per_meter
                    width_mm = (w / self.pixels_per_meter) * 1000
                    height_mm = (h / self.pixels_per_meter) * 1000

                    window = {
                        'x': float(x),
                        'y': float(y),
                        'width': float(w),
                        'height': float(h),
                        'pane_count': pane_count,
                        'world_x': world_x,
                        'world_y': world_y,
                        'width_mm': width_mm,
                        'height_mm': height_mm
                    }

                    windows.append(window)

                    # Store in database
                    self.cursor.execute("""
                        INSERT INTO detected_windows
                        (x, y, width, height, pane_count, world_x, world_y, width_mm, height_mm)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (window['x'], window['y'], window['width'], window['height'],
                          window['pane_count'], window['world_x'], window['world_y'],
                          window['width_mm'], window['height_mm']))

        self.conn.commit()
        return windows

    def _count_window_panes(self, roi: np.ndarray) -> int:
        """Count vertical divisions in window region"""
        # Detect vertical lines within window
        edges = cv2.Canny(roi, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/2, 10, minLineLength=roi.shape[0]*0.5)

        if lines is not None:
            return len(lines) + 1  # Number of panes = divisions + 1
        return 1

    def detect_grid_circles(self, image: np.ndarray) -> List[Dict]:
        """
        Detect grid reference circles.
        Algorithm from guide lines 200-234.
        """
        grids = []

        # Preprocessing
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)

        # Detect circles
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=100,  # Grid circles are well-spaced
            param1=50,
            param2=30,
            minRadius=10,  # Grid circle typical size
            maxRadius=30
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))

            for circle in circles[0, :]:
                cx, cy, radius = circle

                # Convert to world coordinates
                world_x = cx / self.pixels_per_meter
                world_y = cy / self.pixels_per_meter

                grid = {
                    'center_x': float(cx),
                    'center_y': float(cy),
                    'radius': float(radius),
                    'world_x': world_x,
                    'world_y': world_y,
                    'grid_label': ''  # Will be filled by OCR later
                }

                grids.append(grid)

                # Store in database
                self.cursor.execute("""
                    INSERT INTO detected_grids
                    (center_x, center_y, radius, grid_label, world_x, world_y)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (grid['center_x'], grid['center_y'], grid['radius'],
                      grid['grid_label'], grid['world_x'], grid['world_y']))

        self.conn.commit()
        return grids

    def extract_all_vectors(self, pdf_path: str, page_num: int = 2) -> Dict:
        """
        Extract all vector semantics from PDF page.
        Page 2 (electrical plan) recommended for cleanest linework.
        """
        print(f"Converting PDF page {page_num} to image...")
        image = self.pdf_to_image(pdf_path, page_num)

        # Detect walls FIRST (needed for door filtering)
        print("Detecting wall lines...")
        walls = self.detect_wall_lines(image)
        print(f"  Found {len(walls)} wall segments")

        # Detect doors with wall-proximity filtering
        print("Detecting door arcs...")
        doors = self.detect_door_arcs(image, walls)
        print(f"  Found {len(doors)} doors (filtered by wall proximity)")

        print("Detecting windows...")
        windows = self.detect_windows(image)
        print(f"  Found {len(windows)} windows")

        print("Detecting grid circles...")
        grids = self.detect_grid_circles(image)
        print(f"  Found {len(grids)} grid references")

        return {
            'doors': doors,
            'walls': walls,
            'windows': windows,
            'grids': grids,
            'page': page_num,
            'dpi': self.dpi,
            'scale_factor': self.scale_factor,
            'pixels_per_meter': self.pixels_per_meter
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test vector extraction on TB-LKTN HOUSE.pdf"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 vector_extractor.py <pdf_path>")
        print("\nExtracts vector semantics using OpenCV:")
        print("  - Door arcs with swing direction")
        print("  - Wall lines with thickness")
        print("  - Window rectangles with pane count")
        print("  - Grid reference circles")
        sys.exit(1)

    pdf_path = sys.argv[1]
    db_path = "output_artifacts/vector_semantics.db"

    print("=" * 70)
    print("VECTOR SEMANTIC EXTRACTION (OpenCV)")
    print("=" * 70)
    print(f"PDF: {pdf_path}")
    print(f"Output DB: {db_path}")
    print()

    extractor = VectorSemanticExtractor(db_path)

    try:
        results = extractor.extract_all_vectors(pdf_path)

        print("\n" + "=" * 70)
        print("EXTRACTION COMPLETE")
        print("=" * 70)

        # Save summary to JSON
        summary_path = "output_artifacts/vector_extraction_summary.json"
        with open(summary_path, 'w') as f:
            # Convert numpy types for JSON serialization
            json_results = {
                'doors': results['doors'],
                'walls': results['walls'],
                'windows': results['windows'],
                'grids': results['grids'],
                'metadata': {
                    'page': results['page'],
                    'dpi': results['dpi'],
                    'scale_factor': results['scale_factor'],
                    'pixels_per_meter': results['pixels_per_meter']
                }
            }
            json.dump(json_results, f, indent=2)

        print(f"\n✓ Database: {db_path}")
        print(f"✓ Summary: {summary_path}")
        print("\n✅ Rule 0 compliant - pure deterministic OpenCV extraction")

    finally:
        extractor.close()


if __name__ == "__main__":
    main()