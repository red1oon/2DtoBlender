#!/usr/bin/env python3
"""
Room Detector - Detect room boundaries and labels from PDF

Extracts room geometry and identifies room labels from text annotations.

Classes:
    RoomBoundaryDetector: Infer room boundaries from walls
    RoomLabelExtractor: Extract room names from PDF text

Example:
    >>> boundary_detector = RoomBoundaryDetector(walls)
    >>> rooms = boundary_detector.infer_rooms()
    >>> label_extractor = RoomLabelExtractor(calibration_engine)
    >>> labels = label_extractor.extract_labels(page)
"""

import re
from typing import Dict, List, Tuple, Any


class RoomBoundaryDetector:
    """
    Detect room boundaries from wall network

    Simplified approach: Filter walls that form enclosures
    """

    def __init__(self, walls):
        self.walls = walls
        self.rooms = []

    def detect_rooms_simple(self):
        """
        Simplified room detection: Look for rectangular enclosures

        Returns walls that likely form room boundaries
        """
        # Build wall graph
        wall_endpoints = set()
        for wall in self.walls:
            start = (round(wall['start_point'][0], 1), round(wall['start_point'][1], 1))
            end = (round(wall['end_point'][0], 1), round(wall['end_point'][1], 1))
            wall_endpoints.add(start)
            wall_endpoints.add(end)

        # Find walls that connect to multiple walls (likely structural)
        room_walls = []
        for wall in self.walls:
            start = (round(wall['start_point'][0], 1), round(wall['start_point'][1], 1))
            end = (round(wall['end_point'][0], 1), round(wall['end_point'][1], 1))

            # Count how many other walls share endpoints
            start_connections = sum(1 for w in self.walls if w != wall and (
                self._point_matches(w['start_point'], wall['start_point']) or
                self._point_matches(w['end_point'], wall['start_point'])
            ))

            end_connections = sum(1 for w in self.walls if w != wall and (
                self._point_matches(w['start_point'], wall['end_point']) or
                self._point_matches(w['end_point'], wall['end_point'])
            ))

            # Wall is structural if both ends connect to other walls
            if start_connections >= 1 and end_connections >= 1:
                room_walls.append(wall)

        return room_walls

    def _point_matches(self, point1, point2, tolerance=0.2):
        """Check if two points match within tolerance"""
        dx = abs(point1[0] - point2[0])
        dy = abs(point1[1] - point2[1])
        return dx < tolerance and dy < tolerance


# =============================================================================
# ELEVATION EXTRACTOR (Phase 1D)
# =============================================================================


class RoomLabelExtractor:
    """
    Extract room labels from floor plan (Malay text)

    Pattern matching for Malaysian house room labels
    """

    def __init__(self, calibration_engine):
        self.calibration = calibration_engine

        # Malay room label patterns (TEMPLATE-DRIVEN)
        self.ROOM_PATTERNS = {
            # Bedrooms
            r'BILIK\s*TIDUR\s*(\d+)': lambda m: f'bedroom_{m.group(1)}',
            r'B\.?\s*TIDUR\s*(\d+)': lambda m: f'bedroom_{m.group(1)}',
            r'BILIK\s*TIDUR\s*UTAMA': 'master_bedroom',
            r'B\.?\s*T\.?\s*UTAMA': 'master_bedroom',

            # Bathrooms
            r'BILIK\s*AIR\s*(\d+)': lambda m: f'bathroom_{m.group(1)}',
            r'B\.?\s*AIR\s*(\d+)': lambda m: f'bathroom_{m.group(1)}',
            r'TANDAS\s*(\d+)?': lambda m: f'toilet_{m.group(1)}' if m.group(1) else 'toilet',
            r'W\.?C\.?': 'toilet',

            # Kitchen
            r'DAPUR': 'kitchen',
            r'KITCHEN': 'kitchen',

            # Living areas
            r'RUANG\s*TAMU': 'living_room',
            r'R\.?\s*TAMU': 'living_room',
            r'RUANG\s*MAKAN': 'dining_room',
            r'R\.?\s*MAKAN': 'dining_room',
            r'LIVING': 'living_room',
            r'DINING': 'dining_room',

            # Utility areas
            r'STOR': 'storage',
            r'STORE': 'storage',
            r'CUCIAN': 'laundry',
            r'LAUNDRY': 'laundry',
            r'UTILITY': 'utility_room',

            # Other
            r'KORIDOR': 'corridor',
            r'CORRIDOR': 'corridor',
            r'BALKONI': 'balcony',
            r'BALCONY': 'balcony',
            r'BERANDA': 'porch',
            r'PORCH': 'porch'
        }

    def extract_room_labels(self, page):
        """
        Extract room labels from floor plan page

        Args:
            page: pdfplumber page object

        Returns:
            list: Room data with positions and classifications
        """
        words = page.extract_words()
        rooms = []

        for word in words:
            text = word['text'].upper().strip()

            # Skip empty or very short text
            if len(text) < 2:
                continue

            # Try each pattern
            for pattern, room_type in self.ROOM_PATTERNS.items():
                match = re.search(pattern, text)
                if match:
                    # Get room type (might be function result)
                    if callable(room_type):
                        type_name = room_type(match)
                    else:
                        type_name = room_type

                    # Convert PDF coordinates to building coordinates
                    pdf_x, pdf_y = word['x0'], word['top']
                    building_x, building_y = self.calibration.transform_to_building(pdf_x, pdf_y)

                    rooms.append({
                        'name': word['text'],  # Original text (Malay)
                        'type': type_name,     # Standardized type (English)
                        'position': [building_x, building_y, 0.0],
                        'pdf_bbox': {
                            'x0': word['x0'], 'top': word['top'],
                            'x1': word['x1'], 'bottom': word['bottom']
                        },
                        'confidence': 90
                    })
                    break  # Found match, stop searching patterns

        return rooms


# =============================================================================
# WINDOW SILL HEIGHT INFERENCE (Phase 1D)
# =============================================================================

