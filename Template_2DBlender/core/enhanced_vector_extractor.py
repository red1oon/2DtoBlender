"""
Enhanced Vector Semantic Extraction
Following SUPPLEMENTARY_VECTOR_EXTRACTION_GUIDE.md

Implements comprehensive extraction for:
1. MEP symbols (electrical from page 2)
2. Plumbing fixtures (from page 1 and 7)
3. Roof plan semantics (from page 3)
4. Door/window schedule (from page 8)
5. Level markers (from elevations)
6. Material codes
"""

import cv2
import numpy as np
import pytesseract
import re
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import pdf2image


@dataclass
class MEPSymbol:
    """MEP symbol detection result"""
    id: str
    code: str
    description: str
    pixel_x: float
    pixel_y: float
    world_x: float
    world_y: float
    room: Optional[str]
    source_page: int
    confidence: float


@dataclass
class PlumbingFixture:
    """Plumbing fixture detection result"""
    id: str
    type: str
    shape_pattern: str
    pixel_x: float
    pixel_y: float
    world_x: float
    world_y: float
    size_pixels: float
    room: Optional[str]


@dataclass
class RoofElement:
    """Roof plan extraction result"""
    eave_polygon: List[Tuple[float, float]]
    ridge_lines: List[Tuple[float, float, float, float]]
    slope_directions: List[str]
    pitch_angle: Optional[float]
    eave_overhang_mm: float
    vent_stacks: List[Dict[str, Any]]


@dataclass
class ScheduleEntry:
    """Door/window schedule entry"""
    code: str
    type: str
    width_mm: int
    height_mm: int
    location: str
    quantity: int


class EnhancedVectorExtractor:
    """
    Enhanced extractor implementing full supplementary guide
    """

    # MEP Symbol codes from legend
    MEP_CODES = {
        'M': 'Electricity Meter',
        'FP': 'Ceiling Fan Point',
        'LC': 'Ceiling Light Point',
        'SW': 'Switch (1/2/3 gang)',
        'PP': '3 pin 13A power point',
        'WL': 'Wall Mounted Light'
    }

    # Plumbing fixture patterns
    PLUMBING_PATTERNS = {
        'kitchen_sink': {
            'shape': 'rectangle_with_x',
            'size_range': (30, 50),
            'aspect': (1.2, 2.0),
            'internal': 'diagonal_cross'
        },
        'wc': {
            'shape': 'oval_plus_rectangle',
            'size_range': (25, 40),
            'components': ['ellipse', 'rectangle']
        },
        'basin': {
            'shape': 'small_rectangle',
            'size_range': (15, 25),
            'aspect': (0.8, 1.2)
        },
        'floor_trap': {
            'shape': 'circle_with_x',
            'radius_range': (8, 15),
            'internal': 'cross'
        },
        'tap': {
            'shape': 'cross',
            'size_range': (10, 20)
        },
        'shower': {
            'shape': 'rectangle_with_parallel_lines',
            'size_range': (35, 50)
        }
    }

    # Material codes
    MATERIAL_CODES = {
        'CT': 'Ceramic Tiles',
        'CR': 'Cement Render',
        'TB': 'Tasblock Wall',
        'CW': 'Ceramic Wall Tiles',
        'CP': 'Copping',
        'GB': 'Gypsum Board',
        'MR': 'Metal Roofing',
        'GF': 'GI Flashing',
        'FG': 'Fair-faced'
    }

    # Level heights
    LEVEL_HEIGHTS = {
        'GRD. LEVEL': 0,
        'APRON LEVEL': 150,
        'GRD. FLOOR LEVEL': 150,
        'BEAM/CEILING LEVEL': 3150,
    }

    def __init__(self, pdf_path: str, dpi: int = 300):
        self.pdf_path = Path(pdf_path)
        self.dpi = dpi
        self.scale_factor = 1/100  # 1:100 architectural scale
        self.pixels_per_meter = (dpi / 25.4) * 1000 * self.scale_factor

    def extract_all_pages(self) -> Dict[str, Any]:
        """
        Extract semantics from all pages per the supplementary guide
        """
        results = {
            'project': 'TBLKTN_HOUSE',
            'scale': '1:100',
            'pages': {}
        }

        # Convert PDF to images
        images = pdf2image.convert_from_path(self.pdf_path, dpi=self.dpi)

        # Process each page based on its content
        for page_num, image in enumerate(images, 1):
            img_array = np.array(image)

            if page_num == 1:
                # Floor plan - extract doors, windows, fixtures, room names
                results['pages']['floor_plan'] = self.extract_floor_plan(img_array)

            elif page_num == 2:
                # Electrical plan - extract MEP symbols
                results['pages']['electrical'] = self.extract_electrical_plan(img_array)

            elif page_num == 3:
                # Roof plan
                results['pages']['roof'] = self.extract_roof_plan(img_array)

            elif page_num in [4, 5, 6]:
                # Elevations and sections
                results['pages'][f'elevation_{page_num}'] = self.extract_elevations(img_array, page_num)

            elif page_num == 7:
                # Plumbing diagrams
                results['pages']['plumbing'] = self.extract_plumbing_diagram(img_array)

            elif page_num == 8:
                # Door/window schedule
                results['pages']['schedule'] = self.extract_schedule(img_array)

        return results

    def extract_legend_templates(self, image: np.ndarray, legend_roi: Tuple[int, int, int, int]) -> Dict[str, np.ndarray]:
        """
        Extract real symbol templates from legend area (page 2)
        """
        x1, y1, x2, y2 = legend_roi
        legend = image[y1:y2, x1:x2]

        # OCR to find symbol codes
        text_data = pytesseract.image_to_data(legend, output_type=pytesseract.Output.DICT)

        templates = {}
        for i, text in enumerate(text_data['text']):
            if text in self.MEP_CODES:
                # Extract region left of text (symbol area)
                x = text_data['left'][i]
                y = text_data['top'][i]

                if x > 40:  # Ensure there's space to the left
                    symbol_x = x - 40
                    symbol_y = y - 5
                    template = legend[symbol_y:symbol_y+30, symbol_x:symbol_x+30]

                    if template.size > 0:
                        templates[text] = template

        return templates

    def match_mep_symbols(self, image: np.ndarray, templates: Dict[str, np.ndarray]) -> List[MEPSymbol]:
        """
        Match extracted legend templates across floor plan
        """
        detections = []

        for code, template in templates.items():
            if template.size == 0:
                continue

            # Template matching
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.7
            loc = np.where(result >= threshold)

            for pt in zip(*loc[::-1]):
                # Convert to world coordinates
                world_x = pt[0] / self.pixels_per_meter
                world_y = pt[1] / self.pixels_per_meter

                detection = MEPSymbol(
                    id=f"{code}_{len(detections)+1:03d}",
                    code=code,
                    description=self.MEP_CODES.get(code, "Unknown"),
                    pixel_x=float(pt[0]),
                    pixel_y=float(pt[1]),
                    world_x=world_x,
                    world_y=world_y,
                    room=None,  # To be determined by containment
                    source_page=2,
                    confidence=float(result[pt[1], pt[0]])
                )
                detections.append(detection)

        # Apply non-maximum suppression
        return self.nms_symbols(detections)

    def detect_plumbing_fixtures(self, image: np.ndarray) -> List[PlumbingFixture]:
        """
        Detect plumbing fixtures using shape patterns
        """
        fixtures = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Find contours
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)

            if area < 100:  # Skip very small contours
                continue

            # Check against patterns
            fixture_type = self.classify_fixture(contour, w, h)

            if fixture_type:
                cx = x + w/2
                cy = y + h/2

                fixture = PlumbingFixture(
                    id=f"PLB_{len(fixtures)+1:03d}",
                    type=fixture_type,
                    shape_pattern=self.PLUMBING_PATTERNS[fixture_type]['shape'],
                    pixel_x=cx,
                    pixel_y=cy,
                    world_x=cx / self.pixels_per_meter,
                    world_y=cy / self.pixels_per_meter,
                    size_pixels=max(w, h),
                    room=None
                )
                fixtures.append(fixture)

        return fixtures

    def classify_fixture(self, contour: np.ndarray, width: float, height: float) -> Optional[str]:
        """
        Classify plumbing fixture based on contour shape
        """
        aspect_ratio = width / height if height > 0 else 0
        size = max(width, height)

        # Check each pattern
        for fixture_type, pattern in self.PLUMBING_PATTERNS.items():
            size_range = pattern.get('size_range', (0, 100))

            if size_range[0] <= size <= size_range[1]:
                if 'aspect' in pattern:
                    aspect_range = pattern['aspect']
                    if aspect_range[0] <= aspect_ratio <= aspect_range[1]:
                        return fixture_type
                else:
                    # Additional shape checks could go here
                    return fixture_type

        return None

    def extract_roof_plan(self, image: np.ndarray) -> RoofElement:
        """
        Extract roof plan semantics (page 3)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # 1. Detect eave outline (outermost rectangle)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        eave_contour = None
        if contours:
            eave_contour = max(contours, key=cv2.contourArea)
            eave_polygon = [(float(pt[0][0]), float(pt[0][1])) for pt in eave_contour]
        else:
            eave_polygon = []

        # 2. Detect ridge lines (diagonal lines inside roof)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50,
                                minLineLength=100, maxLineGap=10)

        ridge_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if self.is_diagonal(x1, y1, x2, y2):
                    ridge_lines.append((float(x1), float(y1), float(x2), float(y2)))

        # 3. OCR for dimensions and angles
        text = pytesseract.image_to_string(image, config='--psm 12')

        # Find angles
        angles = re.findall(r'(\d+)°', text)
        pitch_angle = float(angles[0]) if angles else 25.0  # Default 25°

        # Find overhang dimension
        overhangs = re.findall(r'(\d{3,4})', text)
        eave_overhang = 700.0  # Default from guide
        for dim in overhangs:
            if 500 <= int(dim) <= 1000:  # Reasonable overhang range
                eave_overhang = float(dim)
                break

        # 4. Detect vent stacks (small circles)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT,
                                   dp=1, minDist=20,
                                   param1=50, param2=25,
                                   minRadius=5, maxRadius=15)

        vent_stacks = []
        if circles is not None:
            for circle in circles[0]:
                x, y, r = circle
                vent_stacks.append({
                    'position': (float(x), float(y)),
                    'radius': float(r),
                    'type': 'vent_pipe'
                })

        return RoofElement(
            eave_polygon=eave_polygon,
            ridge_lines=ridge_lines,
            slope_directions=['N', 'S'],  # Simplified
            pitch_angle=pitch_angle,
            eave_overhang_mm=eave_overhang,
            vent_stacks=vent_stacks
        )

    def extract_schedule(self, image: np.ndarray) -> Dict[str, List[ScheduleEntry]]:
        """
        Extract door/window schedule from page 8
        """
        # Use Tesseract PSM 6 for uniform text block
        text = pytesseract.image_to_string(image, config='--psm 6')

        schedule = {
            'doors': [],
            'windows': []
        }

        # Door schedule pattern: D1, D2, D3 with sizes
        door_pattern = r'(D\d)\s+.*?(\d{3,4})\s*MM?\s*X\s*(\d{3,4})\s*MM?\s+.*?(\d)\s*NOS'

        for match in re.finditer(door_pattern, text, re.IGNORECASE | re.DOTALL):
            code, width, height, qty = match.groups()

            # Find location info
            location = self.extract_location(text, code)

            entry = ScheduleEntry(
                code=code,
                type='door',
                width_mm=int(width),
                height_mm=int(height),
                location=location,
                quantity=int(qty)
            )
            schedule['doors'].append(entry)

        # Window schedule pattern
        window_pattern = r'(W\d)\s+.*?(\d{3,4})\s*MM?\s*X\s*(\d{3,4})\s*MM?\s+.*?(\d)\s*NOS'

        for match in re.finditer(window_pattern, text, re.IGNORECASE | re.DOTALL):
            code, width, height, qty = match.groups()

            location = self.extract_location(text, code)

            entry = ScheduleEntry(
                code=code,
                type='window',
                width_mm=int(width),
                height_mm=int(height),
                location=location,
                quantity=int(qty)
            )
            schedule['windows'].append(entry)

        return schedule

    def extract_location(self, text: str, code: str) -> str:
        """
        Extract location information for door/window code
        """
        # Look for location patterns near the code
        pattern = rf'{code}.*?(?:Ruang|Bilik|Dapur|Tandas|Mandi)[\w\s,]+'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            # Extract room names
            location_text = match.group()
            rooms = re.findall(r'(Ruang\s+\w+|Bilik\s+\w+|Dapur|Tandas|Mandi)',
                               location_text, re.IGNORECASE)
            return ', '.join(rooms) if rooms else 'Unknown'

        return 'Unknown'

    def extract_electrical_plan(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract electrical plan (page 2)
        """
        # Legend is typically on the right side
        height, width = image.shape[:2]
        legend_roi = (int(width * 0.75), 0, width, height)

        # Extract templates from legend
        templates = self.extract_legend_templates(image, legend_roi)

        # Match symbols in drawing area
        symbols = self.match_mep_symbols(image, templates)

        # Group by type
        result = {
            'fan_points': [s for s in symbols if s.code == 'FP'],
            'light_points': [s for s in symbols if s.code == 'LC'],
            'switches': [s for s in symbols if s.code == 'SW'],
            'power_points': [s for s in symbols if s.code == 'PP'],
            'wall_lights': [s for s in symbols if s.code == 'WL'],
            'meters': [s for s in symbols if s.code == 'M']
        }

        return result

    def extract_floor_plan(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract floor plan elements (page 1)
        """
        result = {
            'plumbing_fixtures': self.detect_plumbing_fixtures(image),
            'room_labels': self.extract_room_labels(image),
            'grid_references': self.extract_grid_references(image),
            'material_codes': self.extract_material_codes(image, 1)
        }

        return result

    def extract_plumbing_diagram(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract plumbing diagram (page 7)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Detect pipe lines
        lines = cv2.HoughLinesP(edges, 1, np.pi/180,
                                threshold=30, minLineLength=20, maxLineGap=10)

        # Find junctions (T and L connections)
        junctions = self.find_line_intersections(lines) if lines is not None else []

        # OCR for pipe sizes
        text = pytesseract.image_to_string(image, config='--psm 12')
        pipe_sizes = re.findall(r'(\d+)\s*[øo]\s*(\w+)', text)

        return {
            'pipe_routes': lines.tolist() if lines is not None else [],
            'junctions': junctions,
            'pipe_sizes': pipe_sizes
        }

    def extract_elevations(self, image: np.ndarray, page_num: int) -> Dict[str, Any]:
        """
        Extract elevation information
        """
        # OCR for level markers
        text = pytesseract.image_to_string(image, config='--psm 12')

        levels = []
        level_patterns = [
            r'GRD\.?\s*LEVEL',
            r'GRD\.?\s*FLOOR\s*LEVEL',
            r'APRON\s*LEVEL',
            r'BEAM.*CEILING\s*LEVEL',
            r'ROOF.*LEVEL',
            r'FFL'
        ]

        for pattern in level_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                level_name = match.group().upper()
                levels.append({
                    'name': level_name,
                    'height_mm': self.LEVEL_HEIGHTS.get(level_name, 0)
                })

        # Extract material codes
        materials = self.extract_material_codes(image, page_num)

        return {
            'levels': levels,
            'materials': materials
        }

    def extract_room_labels(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Extract room labels using OCR
        """
        text_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        room_keywords = ['RUANG', 'BILIK', 'DAPUR', 'TANDAS', 'MANDI', 'PORCH']
        rooms = []

        for i, text in enumerate(text_data['text']):
            if any(keyword in text.upper() for keyword in room_keywords):
                rooms.append({
                    'text': text,
                    'x': text_data['left'][i],
                    'y': text_data['top'][i],
                    'width': text_data['width'][i],
                    'height': text_data['height'][i]
                })

        return rooms

    def extract_grid_references(self, image: np.ndarray) -> Dict[str, List[float]]:
        """
        Extract grid references using circles detection
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect grid circles
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT,
                                   dp=1, minDist=30,
                                   param1=50, param2=30,
                                   minRadius=10, maxRadius=25)

        grids = {'horizontal': {}, 'vertical': {}}

        if circles is not None:
            # OCR around each circle to get grid label
            for circle in circles[0]:
                x, y, r = circle

                # Extract region around circle
                roi = image[int(y-r-10):int(y+r+10), int(x-r-10):int(x+r+10)]

                if roi.size > 0:
                    text = pytesseract.image_to_string(roi, config='--psm 8')
                    text = text.strip()

                    if re.match(r'^[A-E]$', text):
                        grids['horizontal'][text] = float(x)
                    elif re.match(r'^[1-5]$', text):
                        grids['vertical'][text] = float(y)

        return grids

    def extract_material_codes(self, image: np.ndarray, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract material codes from any page
        """
        text = pytesseract.image_to_string(image, config='--psm 12')

        found_codes = []
        for code, desc in self.MATERIAL_CODES.items():
            matches = re.finditer(rf'\b{code}\b', text)
            for match in matches:
                # Get surrounding context
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context = text[start:end].strip()

                found_codes.append({
                    'code': code,
                    'description': desc,
                    'page': page_num,
                    'context': context
                })

        return found_codes

    def is_diagonal(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """
        Check if line is diagonal (not horizontal or vertical)
        """
        angle = abs(np.degrees(np.arctan2(y2-y1, x2-x1)))
        return 20 < angle < 70 or 110 < angle < 160

    def find_line_intersections(self, lines: np.ndarray) -> List[Tuple[float, float]]:
        """
        Find intersections between lines (T and L junctions)
        """
        if lines is None:
            return []

        intersections = []

        for i, line1 in enumerate(lines):
            x1, y1, x2, y2 = line1[0]

            for j, line2 in enumerate(lines[i+1:], i+1):
                x3, y3, x4, y4 = line2[0]

                # Check if lines intersect
                pt = self.line_intersection(x1, y1, x2, y2, x3, y3, x4, y4)
                if pt:
                    intersections.append(pt)

        return intersections

    def line_intersection(self, x1, y1, x2, y2, x3, y3, x4, y4) -> Optional[Tuple[float, float]]:
        """
        Calculate intersection point of two line segments
        """
        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)

        if abs(denom) < 1e-10:
            return None

        t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
        u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return (float(x), float(y))

        return None

    def nms_symbols(self, symbols: List[MEPSymbol], threshold: float = 20) -> List[MEPSymbol]:
        """
        Non-maximum suppression for symbol detections
        """
        if not symbols:
            return []

        # Sort by confidence
        symbols.sort(key=lambda x: x.confidence, reverse=True)

        keep = []
        while symbols:
            best = symbols.pop(0)
            keep.append(best)

            # Remove overlapping detections
            symbols = [s for s in symbols
                      if np.sqrt((s.pixel_x - best.pixel_x)**2 +
                                (s.pixel_y - best.pixel_y)**2) > threshold]

        return keep

    def save_to_database(self, results: Dict[str, Any], db_path: str):
        """
        Save extraction results to SQLite database
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mep_symbols (
                id TEXT PRIMARY KEY,
                code TEXT,
                description TEXT,
                pixel_x REAL,
                pixel_y REAL,
                world_x REAL,
                world_y REAL,
                room TEXT,
                source_page INTEGER,
                confidence REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plumbing_fixtures (
                id TEXT PRIMARY KEY,
                type TEXT,
                shape_pattern TEXT,
                pixel_x REAL,
                pixel_y REAL,
                world_x REAL,
                world_y REAL,
                size_pixels REAL,
                room TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS door_window_schedule (
                code TEXT PRIMARY KEY,
                type TEXT,
                width_mm INTEGER,
                height_mm INTEGER,
                location TEXT,
                quantity INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roof_elements (
                id INTEGER PRIMARY KEY,
                element_type TEXT,
                data TEXT
            )
        ''')

        # Insert MEP symbols
        if 'electrical' in results['pages']:
            for symbol_type, symbols in results['pages']['electrical'].items():
                for symbol in symbols:
                    if isinstance(symbol, MEPSymbol):
                        cursor.execute('''
                            INSERT OR REPLACE INTO mep_symbols
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            symbol.id, symbol.code, symbol.description,
                            symbol.pixel_x, symbol.pixel_y,
                            symbol.world_x, symbol.world_y,
                            symbol.room, symbol.source_page, symbol.confidence
                        ))

        # Insert plumbing fixtures
        if 'floor_plan' in results['pages']:
            fixtures = results['pages']['floor_plan'].get('plumbing_fixtures', [])
            for fixture in fixtures:
                if isinstance(fixture, PlumbingFixture):
                    cursor.execute('''
                        INSERT OR REPLACE INTO plumbing_fixtures
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        fixture.id, fixture.type, fixture.shape_pattern,
                        fixture.pixel_x, fixture.pixel_y,
                        fixture.world_x, fixture.world_y,
                        fixture.size_pixels, fixture.room
                    ))

        # Insert schedule
        if 'schedule' in results['pages']:
            schedule = results['pages']['schedule']

            for door in schedule.get('doors', []):
                if isinstance(door, ScheduleEntry):
                    cursor.execute('''
                        INSERT OR REPLACE INTO door_window_schedule
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        door.code, door.type,
                        door.width_mm, door.height_mm,
                        door.location, door.quantity
                    ))

            for window in schedule.get('windows', []):
                if isinstance(window, ScheduleEntry):
                    cursor.execute('''
                        INSERT OR REPLACE INTO door_window_schedule
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        window.code, window.type,
                        window.width_mm, window.height_mm,
                        window.location, window.quantity
                    ))

        # Insert roof elements
        if 'roof' in results['pages']:
            roof = results['pages']['roof']
            if isinstance(roof, RoofElement):
                cursor.execute('''
                    INSERT INTO roof_elements (element_type, data)
                    VALUES (?, ?)
                ''', ('roof_plan', json.dumps(asdict(roof))))

        conn.commit()
        conn.close()


def main():
    """
    Test the enhanced extractor
    """
    pdf_path = "/home/red1/Documents/bonsai/2DtoBlender/Template_2DBlender/TB-LKTN HOUSE.pdf"

    print("=" * 70)
    print("ENHANCED VECTOR EXTRACTION")
    print("=" * 70)

    extractor = EnhancedVectorExtractor(pdf_path)

    # Extract all pages
    results = extractor.extract_all_pages()

    # Save to database
    db_path = "output_artifacts/enhanced_extraction.db"
    extractor.save_to_database(results, db_path)

    # Save JSON summary
    json_path = "output_artifacts/enhanced_extraction_summary.json"

    # Convert dataclass objects to dicts for JSON serialization
    def convert_to_dict(obj):
        if hasattr(obj, '__dict__'):
            return asdict(obj) if hasattr(obj, '__dataclass_fields__') else obj.__dict__
        elif isinstance(obj, list):
            return [convert_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_to_dict(value) for key, value in obj.items()}
        else:
            return obj

    json_results = convert_to_dict(results)

    with open(json_path, 'w') as f:
        json.dump(json_results, f, indent=2, default=str)

    # Print summary
    print(f"\n✓ Saved database: {db_path}")
    print(f"✓ Saved JSON: {json_path}")

    # Print extraction statistics
    if 'electrical' in results['pages']:
        elec = results['pages']['electrical']
        print(f"\nElectrical symbols extracted:")
        for symbol_type, symbols in elec.items():
            print(f"  - {symbol_type}: {len(symbols)}")

    if 'schedule' in results['pages']:
        sched = results['pages']['schedule']
        print(f"\nSchedule extracted:")
        print(f"  - Doors: {len(sched.get('doors', []))}")
        print(f"  - Windows: {len(sched.get('windows', []))}")

    if 'roof' in results['pages']:
        roof = results['pages']['roof']
        if isinstance(roof, RoofElement):
            print(f"\nRoof elements:")
            print(f"  - Eave polygon: {len(roof.eave_polygon)} vertices")
            print(f"  - Ridge lines: {len(roof.ridge_lines)}")
            print(f"  - Pitch angle: {roof.pitch_angle}°")
            print(f"  - Vent stacks: {len(roof.vent_stacks)}")


if __name__ == "__main__":
    main()