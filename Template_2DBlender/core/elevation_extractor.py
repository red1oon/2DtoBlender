#!/usr/bin/env python3
"""
Elevation Extractor - Extract building height dimensions from PDF primitives

Purpose:
    Extract FFL (Finished Floor Level), lintel height, ceiling height, and window sill
    heights from primitives_text table and populate context_dimensions table.

Input:
    - Database: TB-LKTN HOUSE_ANNOTATION_FROM_2D.db
    - Table: primitives_text

Output:
    - Table: context_dimensions
    - Fields: floor_level, lintel_level, ceiling_level, window_sill, building_height

Method:
    1. Search primitives_text for elevation keywords (FFL, LINTEL, CEILING, SILL)
    2. Extract numerical values using regex patterns
    3. Infer building_height from ceiling_level + roof thickness
    4. Store in context_dimensions with confidence scores

Dependencies:
    - Master template: core/master_reference_template.json (Phase 1D elevations)
    - Database schema: context_dimensions table

Author: Claude Code
Date: 2025-11-25
Status: Implementation (GAP 1 resolution)
"""

import sqlite3
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class ElevationExtractor:
    """Extract elevation dimensions from PDF text primitives"""

    # Standard residential dimensions (Malaysian context)
    DEFAULTS = {
        'floor_level': 0.150,        # FFL +150mm typical
        'lintel_level': 2.100,       # Door head at 2100mm
        'ceiling_level': 3.000,      # Ceiling at 3000mm
        'window_sill': 0.900,        # Window sill at 900mm typical
        'roof_thickness': 0.150,     # Roof slab thickness
    }

    # Regex patterns for extraction
    PATTERNS = {
        'ffl_m': r'FFL\s*\+?\s*(\d+\.?\d*)\s*m(?!m)',
        'ffl_mm': r'FFL\s*\+?\s*(\d+)\s*mm',
        'lintel_m': r'LINTEL.*?(\d+\.?\d*)\s*m(?!m)',
        'lintel_mm': r'LINTEL.*?(\d+)\s*mm',
        'door_head_mm': r'(?:DOOR|HEAD).*?(\d+)\s*mm',
        'ceiling_m': r'CEILING.*?(\d+\.?\d*)\s*m(?!m)',
        'ceiling_mm': r'CEILING.*?(\d+)\s*mm',
        'sill_m': r'SILL.*?(\d+\.?\d*)\s*m(?!m)',
        'sill_mm': r'SILL.*?(\d+)\s*mm',
        'ws_m': r'W/?S.*?(\d+\.?\d*)\s*m(?!m)',

        # Generic patterns for common values
        'generic_150mm': r'^150\s*$',        # FFL typical
        'generic_2100mm': r'^2100\s*MM?$',   # Lintel/door head
        'generic_3000mm': r'^3000\s*$',      # Ceiling height
        'generic_900mm': r'^900\s*$',        # Window sill
        'generic_1500mm': r'^1500\s*$',      # High window sill (bathroom)
    }

    def __init__(self, db_path: str):
        """Initialize extractor with database path"""
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        """Context manager entry"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.conn:
            self.conn.close()

    def search_text_pattern(self, pattern: str, pages: List[int] = None) -> List[Tuple[str, int, float, float]]:
        """Search primitives_text for pattern, return (text, page, x, y)"""
        cursor = self.conn.cursor()

        if pages:
            placeholders = ','.join('?' * len(pages))
            query = f"""
                SELECT text, page, x, y
                FROM primitives_text
                WHERE page IN ({placeholders})
                ORDER BY page, y DESC, x
            """
            cursor.execute(query, pages)
        else:
            query = """
                SELECT text, page, x, y
                FROM primitives_text
                ORDER BY page, y DESC, x
            """
            cursor.execute(query)

        results = []
        for row in cursor.fetchall():
            text = row['text'].strip()
            if re.search(pattern, text, re.IGNORECASE):
                results.append((text, row['page'], row['x'], row['y']))

        return results

    def extract_floor_level(self) -> Optional[float]:
        """Extract FFL (Finished Floor Level) in meters"""
        # Try explicit FFL text first
        for pattern in ['ffl_m', 'ffl_mm']:
            matches = self.search_text_pattern(self.PATTERNS[pattern], pages=[1, 2, 3, 4])
            for text, page, x, y in matches:
                match = re.search(self.PATTERNS[pattern], text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    if pattern == 'ffl_mm':
                        value = value / 1000.0
                    print(f"  Found FFL: {value}m from '{text}' (page {page})")
                    return value

        # Try generic 150mm pattern (common FFL value)
        matches = self.search_text_pattern(self.PATTERNS['generic_150mm'], pages=[4, 5, 6])
        if matches:
            print(f"  Inferred FFL: 0.150m from generic '150' pattern ({len(matches)} instances)")
            return 0.150

        return None

    def extract_lintel_level(self) -> Optional[float]:
        """Extract lintel/door head height in meters"""
        # Try explicit lintel text
        for pattern in ['lintel_m', 'lintel_mm', 'door_head_mm']:
            matches = self.search_text_pattern(self.PATTERNS[pattern], pages=[1, 2, 3, 4, 8])
            for text, page, x, y in matches:
                match = re.search(self.PATTERNS[pattern], text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    if pattern.endswith('_mm'):
                        value = value / 1000.0
                    print(f"  Found lintel: {value}m from '{text}' (page {page})")
                    return value

        # Try generic 2100MM pattern (common door head height)
        matches = self.search_text_pattern(self.PATTERNS['generic_2100mm'], pages=[8])
        if matches:
            print(f"  Inferred lintel: 2.100m from '2100MM' pattern ({len(matches)} instances on page 8)")
            return 2.100

        return None

    def extract_ceiling_level(self) -> Optional[float]:
        """Extract ceiling height in meters"""
        # Try explicit ceiling text
        for pattern in ['ceiling_m', 'ceiling_mm']:
            matches = self.search_text_pattern(self.PATTERNS[pattern], pages=[1, 2, 3, 4])
            for text, page, x, y in matches:
                match = re.search(self.PATTERNS[pattern], text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    if pattern == 'ceiling_mm':
                        value = value / 1000.0
                    print(f"  Found ceiling: {value}m from '{text}' (page {page})")
                    return value

        # Try generic 3000mm pattern (common ceiling height)
        matches = self.search_text_pattern(self.PATTERNS['generic_3000mm'], pages=[4, 5, 6])
        if matches:
            print(f"  Inferred ceiling: 3.000m from '3000' pattern ({len(matches)} instances)")
            return 3.000

        return None

    def extract_window_sill(self) -> Optional[float]:
        """Extract window sill height in meters"""
        # Try explicit sill text
        for pattern in ['sill_m', 'sill_mm', 'ws_m']:
            matches = self.search_text_pattern(self.PATTERNS[pattern], pages=[1, 2, 3, 4])
            for text, page, x, y in matches:
                match = re.search(self.PATTERNS[pattern], text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    if pattern.endswith('_mm'):
                        value = value / 1000.0
                    print(f"  Found window sill: {value}m from '{text}' (page {page})")
                    return value

        # Try generic patterns (900mm or 1500mm for high windows)
        for pattern_name, default_val in [('generic_900mm', 0.900), ('generic_1500mm', 1.500)]:
            matches = self.search_text_pattern(self.PATTERNS[pattern_name], pages=[1, 2, 3, 4, 5])
            if matches:
                print(f"  Inferred window sill: {default_val}m from generic pattern")
                return default_val

        return None

    def calculate_building_height(self, ceiling_level: float, floor_level: float) -> float:
        """Calculate total building height from ceiling + roof thickness"""
        roof_thickness = self.DEFAULTS['roof_thickness']
        building_height = ceiling_level + roof_thickness - floor_level
        print(f"  Calculated building height: {building_height}m (ceiling {ceiling_level}m + roof {roof_thickness}m)")
        return building_height

    def extract_all(self) -> Dict[str, Tuple[float, str]]:
        """Extract all elevation dimensions, return {dimension_name: (value, source)}"""
        results = {}

        print("\nExtracting elevations:")

        # Floor level
        ffl = self.extract_floor_level()
        if ffl:
            results['floor_level'] = (ffl, 'extracted')
        else:
            results['floor_level'] = (self.DEFAULTS['floor_level'], 'default')
            print(f"  Using default FFL: {self.DEFAULTS['floor_level']}m")

        # Lintel level
        lintel = self.extract_lintel_level()
        if lintel:
            results['lintel_level'] = (lintel, 'extracted')
        else:
            results['lintel_level'] = (self.DEFAULTS['lintel_level'], 'default')
            print(f"  Using default lintel: {self.DEFAULTS['lintel_level']}m")

        # Ceiling level
        ceiling = self.extract_ceiling_level()
        if ceiling:
            results['ceiling_level'] = (ceiling, 'extracted')
        else:
            results['ceiling_level'] = (self.DEFAULTS['ceiling_level'], 'default')
            print(f"  Using default ceiling: {self.DEFAULTS['ceiling_level']}m")

        # Window sill
        sill = self.extract_window_sill()
        if sill:
            results['window_sill'] = (sill, 'extracted')
        else:
            results['window_sill'] = (self.DEFAULTS['window_sill'], 'default')
            print(f"  Using default window sill: {self.DEFAULTS['window_sill']}m")

        # Building height (derived from ceiling)
        ceiling_val = results['ceiling_level'][0]
        floor_val = results['floor_level'][0]
        building_height = self.calculate_building_height(ceiling_val, floor_val)
        results['building_height'] = (building_height, 'calculated')

        return results

    def populate_context_dimensions(self, dimensions: Dict[str, Tuple[float, str]]):
        """Populate context_dimensions table with extracted values"""
        cursor = self.conn.cursor()

        for dim_name, (value, source) in dimensions.items():
            cursor.execute("""
                INSERT OR REPLACE INTO context_dimensions (dimension_name, value, unit, source)
                VALUES (?, ?, ?, ?)
            """, (dim_name, value, 'm', source))

        self.conn.commit()
        print(f"\n✅ Populated {len(dimensions)} elevation dimensions in context_dimensions table")


def main():
    """Main execution: Extract elevations and populate database"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 elevation_extractor.py <database_path>")
        print("\nExample:")
        print("  python3 elevation_extractor.py 'output_artifacts/TB-LKTN HOUSE_ANNOTATION_FROM_2D.db'")
        sys.exit(1)

    db_path = sys.argv[1]

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    print(f"Elevation Extractor")
    print(f"Database: {db_path}")

    with ElevationExtractor(db_path) as extractor:
        # Extract all dimensions
        dimensions = extractor.extract_all()

        # Show results
        print("\nExtracted Dimensions:")
        print("=" * 60)
        for dim_name, (value, source) in dimensions.items():
            status = "✅" if source == "extracted" else ("🔧" if source == "calculated" else "⚠️")
            print(f"{status} {dim_name:20s}: {value:6.3f}m ({source})")
        print("=" * 60)

        # Populate database
        extractor.populate_context_dimensions(dimensions)

    print("\n✅ Elevation extraction complete!")


if __name__ == "__main__":
    main()
