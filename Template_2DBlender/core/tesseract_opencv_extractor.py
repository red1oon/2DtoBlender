#!/usr/bin/env python3
"""
Combined Tesseract + OpenCV Extraction Pipeline
================================================
Extracts BOTH text AND geometric primitives from architectural PDFs.
100% Rule 0 compliant - pure deterministic extraction, no AI/ML.

Features:
1. Text with positions (Tesseract OCR PSM 12 for sparse text)
2. Door arcs with swing angles (OpenCV arc detection)
3. Wall lines with thickness classification (OpenCV line detection)
4. Grid dimensions with spatial context
"""

import cv2
import numpy as np
import pytesseract
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pdf2image


class TesseractOpenCVExtractor:
    """
    Combined extraction pipeline for architectural drawings.
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """Create tables for raw semantic extraction"""

        # Text with spatial context (Tesseract)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ocr_text (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER NOT NULL,
                text TEXT NOT NULL,
                x INTEGER,
                y INTEGER,
                width INTEGER,
                height INTEGER,
                confidence REAL,

                -- Semantic classification
                text_type TEXT,  -- 'dimension', 'grid_label', 'room_name', etc.

                -- Metadata
                psm_mode INTEGER DEFAULT 12,  -- Tesseract Page Segmentation Mode
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Door arcs (OpenCV)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS door_arcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER NOT NULL,

                -- Arc geometry
                center_x REAL,
                center_y REAL,
                radius REAL,
                start_angle REAL,  -- degrees
                end_angle REAL,    -- degrees
                sweep_angle REAL,  -- swing arc (typically 90°)

                -- Door properties
                swing_direction TEXT,  -- 'clockwise', 'counter-clockwise'
                hinge_side TEXT,       -- 'left', 'right', 'top', 'bottom'

                -- Visual properties
                line_thickness REAL,
                is_dashed BOOLEAN DEFAULT 0,

                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Wall lines (OpenCV)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS wall_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER NOT NULL,

                -- Line geometry
                x1 REAL,
                y1 REAL,
                x2 REAL,
                y2 REAL,
                length REAL,
                angle REAL,  -- degrees from horizontal

                -- Line properties
                thickness REAL,
                line_type TEXT,  -- 'solid', 'dashed', 'dotted'
                is_structural BOOLEAN DEFAULT 0,  -- thick = structural

                -- Semantic hints
                parallel_to TEXT,  -- 'horizontal', 'vertical', 'diagonal'

                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Grid detection results
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS grid_system (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER NOT NULL,

                -- Grid label
                label TEXT NOT NULL,  -- 'A', 'B', '1', '2', etc.
                grid_type TEXT,       -- 'horizontal', 'vertical'

                -- Position
                x REAL,
                y REAL,

                -- Associated dimension (if found nearby)
                dimension_value INTEGER,
                dimension_unit TEXT DEFAULT 'mm',

                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[np.ndarray]:
        """Convert PDF pages to images for processing"""
        images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
        return [np.array(img) for img in images]

    def extract_text_with_position(self, image: np.ndarray, page_num: int) -> List[Dict]:
        """
        Extract text with positions using Tesseract.
        PSM 12: Sparse text with OSD (Orientation and Script Detection)
        """
        extracted = []

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # PSM modes to try for architectural drawings
        psm_modes = [
            12,  # Sparse text with OSD
            11,  # Sparse text without OSD
            6,   # Uniform block of text
        ]

        for psm in psm_modes:
            try:
                # Get detailed OCR data
                config = f'--psm {psm} --oem 3'  # OEM 3 = Default (LSTM)
                data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, config=config)

                # Extract text with positions
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    if text:
                        confidence = data['conf'][i]
                        if confidence > 0:  # -1 means no confidence
                            item = {
                                'text': text,
                                'x': data['left'][i],
                                'y': data['top'][i],
                                'width': data['width'][i],
                                'height': data['height'][i],
                                'confidence': confidence,
                                'psm_mode': psm
                            }

                            # Classify text type
                            item['text_type'] = self._classify_text(text)

                            # Store in database
                            self.cursor.execute("""
                                INSERT INTO ocr_text
                                (page, text, x, y, width, height, confidence, text_type, psm_mode)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (page_num, text, item['x'], item['y'], item['width'],
                                  item['height'], confidence, item['text_type'], psm))

                            extracted.append(item)

            except Exception as e:
                print(f"PSM {psm} failed: {e}")

        self.conn.commit()
        return extracted

    def _classify_text(self, text: str) -> str:
        """Classify text type based on patterns"""
        text_upper = text.upper()

        # Grid labels
        if text_upper in ['A', 'B', 'C', 'D', 'E']:
            return 'grid_horizontal'
        if text_upper in ['1', '2', '3', '4', '5']:
            return 'grid_vertical'

        # Dimensions
        if text.isdigit() and int(text) > 500 and int(text) < 10000:
            return 'dimension'
        if 'MM' in text_upper or '°' in text:
            return 'dimension'

        # Door/window codes
        if text_upper.startswith(('D1', 'D2', 'D3', 'W1', 'W2', 'W3')):
            return 'opening_code'

        # Room names
        room_keywords = ['ROOM', 'BILIK', 'DAPUR', 'KITCHEN', 'TANDAS', 'BATHROOM']
        if any(keyword in text_upper for keyword in room_keywords):
            return 'room_name'

        return 'other'

    def extract_door_arcs(self, image: np.ndarray, page_num: int) -> List[Dict]:
        """
        Extract door swing arcs using OpenCV.
        Detects quarter-circle arcs typical in architectural drawings.
        """
        arcs = []

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Detect circles/arcs using Hough transform
        circles = cv2.HoughCircles(
            edges,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=10,
            maxRadius=100
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))

            for circle in circles[0, :]:
                center_x, center_y, radius = circle

                # Check if this is likely a door arc (quarter circle)
                arc_pixels = self._trace_arc(edges, center_x, center_y, radius)

                if arc_pixels:
                    arc_ratio = len(arc_pixels) / (2 * np.pi * radius)

                    # Door arcs are typically 90° (quarter circle)
                    if 0.20 < arc_ratio < 0.30:  # ~90° arc
                        # Determine swing direction
                        start_angle, end_angle = self._calculate_arc_angles(arc_pixels, center_x, center_y)
                        sweep = abs(end_angle - start_angle)

                        direction = 'clockwise' if end_angle > start_angle else 'counter-clockwise'

                        arc = {
                            'center_x': float(center_x),
                            'center_y': float(center_y),
                            'radius': float(radius),
                            'start_angle': start_angle,
                            'end_angle': end_angle,
                            'sweep_angle': sweep,
                            'swing_direction': direction
                        }

                        # Store in database
                        self.cursor.execute("""
                            INSERT INTO door_arcs
                            (page, center_x, center_y, radius, start_angle, end_angle,
                             sweep_angle, swing_direction)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (page_num, arc['center_x'], arc['center_y'], arc['radius'],
                              arc['start_angle'], arc['end_angle'], arc['sweep_angle'],
                              arc['swing_direction']))

                        arcs.append(arc)

        self.conn.commit()
        return arcs

    def _trace_arc(self, edges: np.ndarray, cx: int, cy: int, r: int) -> List[Tuple[int, int]]:
        """Trace arc pixels around a center point"""
        arc_pixels = []

        # Sample points around the circle
        for angle in range(0, 360, 5):
            rad = np.radians(angle)
            x = int(cx + r * np.cos(rad))
            y = int(cy + r * np.sin(rad))

            # Check if point is on an edge (with tolerance)
            if 0 <= y < edges.shape[0] and 0 <= x < edges.shape[1]:
                if edges[y, x] > 0:
                    arc_pixels.append((x, y))

        return arc_pixels

    def _calculate_arc_angles(self, pixels: List[Tuple[int, int]], cx: int, cy: int) -> Tuple[float, float]:
        """Calculate start and end angles of an arc"""
        if not pixels:
            return 0, 0

        angles = []
        for x, y in pixels:
            angle = np.degrees(np.arctan2(y - cy, x - cx))
            if angle < 0:
                angle += 360
            angles.append(angle)

        return min(angles), max(angles)

    def extract_wall_lines(self, image: np.ndarray, page_num: int) -> List[Dict]:
        """
        Extract wall lines using OpenCV line detection.
        Classifies lines by thickness (structural vs non-structural).
        """
        lines_data = []

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Line detection using HoughLinesP
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=50,
            minLineLength=30,
            maxLineGap=10
        )

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # Calculate line properties
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                angle = np.degrees(np.arctan2(y2-y1, x2-x1))

                # Determine thickness (sample perpendicular pixels)
                thickness = self._measure_line_thickness(gray, x1, y1, x2, y2)

                # Classify line orientation
                if abs(angle) < 5 or abs(angle - 180) < 5:
                    parallel_to = 'horizontal'
                elif abs(angle - 90) < 5 or abs(angle + 90) < 5:
                    parallel_to = 'vertical'
                else:
                    parallel_to = 'diagonal'

                # Structural walls are typically thicker
                is_structural = thickness > 3.0

                line_data = {
                    'x1': float(x1),
                    'y1': float(y1),
                    'x2': float(x2),
                    'y2': float(y2),
                    'length': float(length),
                    'angle': float(angle),
                    'thickness': float(thickness),
                    'is_structural': is_structural,
                    'parallel_to': parallel_to
                }

                # Store in database
                self.cursor.execute("""
                    INSERT INTO wall_lines
                    (page, x1, y1, x2, y2, length, angle, thickness,
                     is_structural, parallel_to, line_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (page_num, line_data['x1'], line_data['y1'], line_data['x2'],
                      line_data['y2'], line_data['length'], line_data['angle'],
                      line_data['thickness'], is_structural, parallel_to, 'solid'))

                lines_data.append(line_data)

        self.conn.commit()
        return lines_data

    def _measure_line_thickness(self, image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> float:
        """Measure line thickness by sampling perpendicular pixels"""
        # Simplified thickness measurement
        # In production, would sample multiple points along the line
        thickness = 1.0  # Default

        # Sample a few pixels perpendicular to the line
        angle = np.arctan2(y2-y1, x2-x1)
        perp_angle = angle + np.pi/2

        # Check pixels perpendicular to line midpoint
        mid_x = (x1 + x2) // 2
        mid_y = (y1 + y2) // 2

        dark_pixels = 0
        for dist in range(-10, 11):
            x = int(mid_x + dist * np.cos(perp_angle))
            y = int(mid_y + dist * np.sin(perp_angle))

            if 0 <= y < image.shape[0] and 0 <= x < image.shape[1]:
                if image[y, x] < 128:  # Dark pixel
                    dark_pixels += 1

        thickness = max(1.0, dark_pixels / 2.0)
        return thickness

    def extract_grid_system(self, page_num: int) -> Dict:
        """
        Correlate grid labels with nearby dimensions.
        This creates the grid system from OCR results.
        """
        # Get grid labels
        self.cursor.execute("""
            SELECT text, x, y
            FROM ocr_text
            WHERE page = ? AND text_type IN ('grid_horizontal', 'grid_vertical')
            ORDER BY text
        """, (page_num,))

        grid_labels = []
        for text, x, y in self.cursor.fetchall():
            grid_labels.append({'label': text, 'x': x, 'y': y})

        # Get dimensions
        self.cursor.execute("""
            SELECT text, x, y
            FROM ocr_text
            WHERE page = ? AND text_type = 'dimension'
            ORDER BY CAST(text AS INTEGER)
        """, (page_num,))

        dimensions = []
        for text, x, y in self.cursor.fetchall():
            try:
                value = int(''.join(filter(str.isdigit, text)))
                dimensions.append({'value': value, 'x': x, 'y': y})
            except:
                pass

        # Correlate dimensions with grid labels (find nearby pairs)
        grid_system = {'horizontal': {}, 'vertical': {}}

        for label in grid_labels:
            # Find closest dimension
            min_dist = float('inf')
            closest_dim = None

            for dim in dimensions:
                dist = np.sqrt((label['x'] - dim['x'])**2 + (label['y'] - dim['y'])**2)
                if dist < min_dist and dist < 100:  # Within 100 pixels
                    min_dist = dist
                    closest_dim = dim

            if closest_dim:
                # Store correlation
                self.cursor.execute("""
                    INSERT INTO grid_system
                    (page, label, grid_type, x, y, dimension_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (page_num, label['label'],
                      'horizontal' if label['label'] in 'ABCDE' else 'vertical',
                      label['x'], label['y'], closest_dim['value']))

        self.conn.commit()
        return grid_system

    def process_pdf(self, pdf_path: str) -> Dict:
        """Process entire PDF through extraction pipeline"""
        stats = {
            'pages_processed': 0,
            'text_extracted': 0,
            'arcs_found': 0,
            'lines_found': 0,
            'grids_mapped': 0
        }

        print("=" * 70)
        print("TESSERACT + OPENCV EXTRACTION PIPELINE")
        print("=" * 70)
        print(f"PDF: {pdf_path}")
        print()

        # Convert PDF to images
        print("Converting PDF to images...")
        images = self.pdf_to_images(pdf_path)
        print(f"  ✓ {len(images)} pages")

        for page_num, image in enumerate(images, 1):
            print(f"\nProcessing page {page_num}...")

            # Extract text with positions
            print("  Extracting text (Tesseract)...")
            text_items = self.extract_text_with_position(image, page_num)
            stats['text_extracted'] += len(text_items)
            print(f"    ✓ {len(text_items)} text items")

            # Extract door arcs
            print("  Detecting door arcs (OpenCV)...")
            arcs = self.extract_door_arcs(image, page_num)
            stats['arcs_found'] += len(arcs)
            print(f"    ✓ {len(arcs)} door arcs")

            # Extract wall lines
            print("  Detecting wall lines (OpenCV)...")
            lines = self.extract_wall_lines(image, page_num)
            stats['lines_found'] += len(lines)
            print(f"    ✓ {len(lines)} wall lines")

            # Build grid system
            print("  Correlating grid system...")
            grid = self.extract_grid_system(page_num)
            print(f"    ✓ Grid system mapped")

            stats['pages_processed'] += 1

        print("\n" + "=" * 70)
        print("EXTRACTION COMPLETE")
        print("=" * 70)
        print(f"Pages: {stats['pages_processed']}")
        print(f"Text items: {stats['text_extracted']}")
        print(f"Door arcs: {stats['arcs_found']}")
        print(f"Wall lines: {stats['lines_found']}")
        print(f"\n✓ Raw semantics saved to {self.db_path}")

        return stats

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test Tesseract+OpenCV extraction"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 tesseract_opencv_extractor.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    db_path = "output_artifacts/tesseract_opencv_raw.db"

    extractor = TesseractOpenCVExtractor(db_path)

    try:
        stats = extractor.process_pdf(pdf_path)

        # Show sample results
        print("\nSample extracted grid dimensions:")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT label, dimension_value
            FROM grid_system
            WHERE dimension_value IS NOT NULL
            ORDER BY label
            LIMIT 10
        """)

        for label, dim in cursor.fetchall():
            print(f"  Grid {label}: {dim}mm")

        conn.close()

    finally:
        extractor.close()


if __name__ == "__main__":
    main()