#!/usr/bin/env python3
"""
Elevation Extractor - Extract elevation data from PDF text

Extracts floor levels, ceiling heights, and other vertical dimensions.

Classes:
    ElevationExtractor: Extract elevation annotations from PDF

Example:
    >>> extractor = ElevationExtractor(calibration_engine)
    >>> elevations = extractor.extract_elevations(pdf)
"""

import re
from typing import Dict, List, Optional, Any


class ElevationExtractor:
    """
    Extract elevation data from elevation views using regex patterns

    Pages:
    - Page 3 (Front/Rear Elevation)
    - Page 4 (Left/Right Elevation)

    Extracts:
    - Floor levels (FFL)
    - Lintel levels (door/window tops)
    - Ceiling heights
    - Window sill heights
    """

    def __init__(self, pdf):
        self.pdf = pdf

        # Regex patterns for dimension extraction (TEMPLATE-DRIVEN)
        self.PATTERNS = {
            # Floor level: "FFL +0.150" or "FLOOR LEVEL +150mm"
            'floor_level': [
                (r'FFL\s*\+?\s*(\d+\.?\d*)\s*m(?!m)', 1.0),  # "FFL +0.150m" (meters)
                (r'FFL\s*\+?\s*(\d+)\s*mm', 0.001),           # "FFL +150mm" (convert to m)
                (r'FLOOR\s+LEVEL\s*\+?\s*(\d+\.?\d*)\s*m(?!m)', 1.0),
                (r'FINISHED\s+FLOOR\s+LEVEL\s*\+?\s*(\d+\.?\d*)', 1.0)
            ],

            # Lintel level: "LINTEL LEVEL 2100mm" or "LINTEL +2.1m"
            'lintel_level': [
                (r'LINTEL.*?(\d+\.?\d*)\s*m(?!m)', 1.0),      # "LINTEL +2.1m"
                (r'LINTEL.*?(\d+)\s*mm', 0.001),               # "LINTEL 2100mm"
                (r'LINTEL\s+LEVEL.*?(\d+\.?\d*)', 1.0),
                (r'DOOR\s+HEAD.*?(\d+\.?\d*)', 1.0)
            ],

            # Ceiling level: "CEILING LEVEL 3000mm"
            'ceiling_level': [
                (r'CEILING.*?(\d+\.?\d*)\s*m(?!m)', 1.0),
                (r'CEILING.*?(\d+)\s*mm', 0.001),
                (r'SOFFIT.*?(\d+\.?\d*)', 1.0),
                (r'ROOF\s+LEVEL.*?(\d+\.?\d*)', 1.0)
            ],

            # Window sill: "SILL 1000mm" or "W/S +1.0m"
            'window_sill': [
                (r'SILL.*?(\d+\.?\d*)\s*m(?!m)', 1.0),
                (r'SILL.*?(\d+)\s*mm', 0.001),
                (r'W/?S.*?(\d+\.?\d*)\s*m(?!m)', 1.0),
                (r'WINDOW\s+SILL.*?(\d+\.?\d*)', 1.0)
            ]
        }

    def extract_from_page(self, page_number=2):
        """
        Extract elevation data from elevation view page

        Args:
            page_number: 0-indexed (2 = Page 3, 3 = Page 4)

        Returns:
            dict: {floor_level, lintel_level, ceiling_level, window_sill}
        """
        try:
            page = self.pdf.pages[page_number]
        except IndexError:
            print(f"⚠️  Page {page_number} not found, using defaults")
            return self._default_elevations()

        words = page.extract_words()
        if not words:
            print(f"⚠️  No text on page {page_number}, using defaults")
            return self._default_elevations()

        # Concatenate all text for pattern matching
        full_text = ' '.join([w['text'] for w in words])

        elevations = {}

        for label, patterns in self.PATTERNS.items():
            value = self._extract_dimension(full_text, patterns)
            if value is not None:
                elevations[label] = value

        # Fill in missing values with defaults
        return self._fill_defaults(elevations)

    def _extract_dimension(self, text, patterns):
        """
        Extract dimension value from text using regex patterns

        Args:
            text: Full text content
            patterns: List of (regex, multiplier) tuples

        Returns:
            float: Dimension in meters, or None if not found
        """
        for pattern, multiplier in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_str = match.group(1)
                value = float(value_str) * multiplier
                return value

        return None

    def _default_elevations(self):
        """Default elevation values for Malaysian houses (UBBL standards)"""
        return {
            'floor_level': 0.15,     # FFL +150mm (typical raised floor)
            'lintel_level': 2.1,     # 2100mm (standard door height)
            'ceiling_level': 3.0,    # 3000mm (typical residential ceiling)
            'window_sill': 1.0       # 1000mm (typical window sill height)
        }

    def _fill_defaults(self, elevations):
        """Fill missing elevation values with defaults"""
        defaults = self._default_elevations()

        for key, default_value in defaults.items():
            if key not in elevations:
                elevations[key] = default_value
                print(f"   ℹ️  {key} not found, using default: {default_value}m")

        return elevations

    def extract_complete(self):
        """
        Extract elevation data from all elevation pages

        Returns:
            dict: {elevations: {...}, confidence: {...}}
        """
        # Try Page 3 (Front/Rear Elevation)
        page3_data = self.extract_from_page(2)

        # Try Page 4 (Left/Right Elevation) for validation
        page4_data = self.extract_from_page(3)

        # Merge data (Page 3 takes precedence)
        combined = {}
        confidence_scores = {}

        for key in page3_data.keys():
            val3 = page3_data.get(key)
            val4 = page4_data.get(key)

            if val3 is not None and val4 is not None:
                # Both pages have value - check if they match
                if abs(val3 - val4) < 0.05:  # 50mm tolerance
                    combined[key] = val3
                    confidence_scores[key] = 95  # High confidence (validated)
                else:
                    combined[key] = val3  # Use Page 3
                    confidence_scores[key] = 75  # Medium confidence (mismatch)
                    print(f"   ⚠️  {key} mismatch: Page3={val3}m, Page4={val4}m (using Page3)")
            elif val3 is not None:
                combined[key] = val3
                confidence_scores[key] = 85  # Medium-high (single source)
            else:
                combined[key] = val4 or self._default_elevations()[key]
                confidence_scores[key] = 60  # Low (default used)

        return {
            'elevations': combined,
            'confidence': confidence_scores
        }


# =============================================================================
# ROOM LABEL EXTRACTOR (Phase 1D)
# =============================================================================

