#!/usr/bin/env python3
"""
Page-by-Page Data Extraction

Strategy: "we first capture each page description and their numberings,
data into separate tables, and then systematically correlate" - User

Creates separate tables for each page, then builds correlations.
"""

import pdfplumber
import json
import sys
from collections import defaultdict
from typing import Dict, List
import re


class PageByPageExtractor:
    """Extract data page-by-page into separate tables"""

    def __init__(self, pdf_path: str):
        self.pdf = pdfplumber.open(pdf_path)
        self.pages_data = []

    def extract_all_pages(self) -> List[Dict]:
        """Extract each page into separate table"""
        print("="*80)
        print("PAGE-BY-PAGE EXTRACTION")
        print("="*80)
        print()

        for page_idx, page in enumerate(self.pdf.pages):
            page_num = page_idx + 1
            print(f"Extracting Page {page_num}...")

            page_data = self._extract_page(page, page_num)
            self.pages_data.append(page_data)

            # Print summary
            print(f"  Type: {page_data['page_type']}")
            print(f"  Numbers: {page_data['stats']['total_numbers']}")
            print(f"  Labels: {page_data['stats']['door_window_labels']}")
            print(f"  Dimensions: {page_data['stats']['dimensions']}")
            print()

        return self.pages_data

    def _extract_page(self, page, page_num: int) -> Dict:
        """
        Extract complete data from a single page

        Returns structured table:
        - Page metadata
        - Page type (floor plan, elevation, schedule, etc.)
        - All numbers categorized
        - Tables extracted
        - Spatial layout
        """
        words = page.extract_words()

        # Detect page type
        page_type = self._detect_page_type(words, page_num)

        # Extract all text
        all_text = ' '.join([w['text'] for w in words])

        # Extract numbers by category
        numbers = {
            'dimensions': [],
            'labels': [],
            'grid_refs': [],
            'scales': [],
            'drawing_numbers': [],
            'utilities': [],
            'other': []
        }

        for word in words:
            text = word['text'].strip()
            if not any(c.isdigit() for c in text):
                continue

            classified = self._classify_and_store(text, word, numbers)

        # Extract tables (for schedule pages)
        tables = []
        if page_type == 'SCHEDULE':
            tables = self._extract_tables(page, words)

        # Build spatial layout (what's where on the page)
        spatial_layout = self._build_spatial_layout(words, page)

        # Calculate stats
        stats = {
            'total_numbers': sum(len(nums) for nums in numbers.values()),
            'dimensions': len(numbers['dimensions']),
            'door_window_labels': len(numbers['labels']),
            'grid_references': len(numbers['grid_refs']),
            'tables': len(tables)
        }

        return {
            'page_number': page_num,
            'page_type': page_type,
            'description': self._generate_page_description(page_type, stats, all_text),
            'stats': stats,
            'numbers': numbers,
            'tables': tables,
            'spatial_layout': spatial_layout,
            'raw_text_sample': all_text[:200] if len(all_text) > 200 else all_text
        }

    def _detect_page_type(self, words: List[Dict], page_num: int) -> str:
        """
        Detect what type of page this is

        Types:
        - FLOOR_PLAN: Main architectural floor plan
        - ELEVATION: Building elevations
        - SCHEDULE: Door/window schedules, tables
        - SECTION: Cross-sections
        - SITE_PLAN: Site layout
        - DETAIL: Construction details
        """
        all_text = ' '.join([w['text'].upper() for w in words])

        # Schedule indicators
        if any(indicator in all_text for indicator in [
            'DOOR SCHEDULE', 'WINDOW SCHEDULE',
            'TYPE', 'SIZE', 'QUANTITY', 'REFERENCES'
        ]):
            return 'SCHEDULE'

        # Elevation indicators
        if any(indicator in all_text for indicator in [
            'ELEVATION', 'FRONT', 'SIDE', 'REAR',
            'TAMPAK', 'FFL', 'LINTEL'
        ]):
            return 'ELEVATION'

        # Floor plan indicators
        if any(indicator in all_text for indicator in [
            'FLOOR PLAN', 'PELAN', 'LAYOUT',
            'BILIK', 'DAPUR', 'TANDAS'  # Room names
        ]):
            return 'FLOOR_PLAN'

        # Section indicators
        if 'SECTION' in all_text or 'KERATAN' in all_text:
            return 'SECTION'

        # Site plan
        if 'SITE' in all_text or 'TAPAK' in all_text:
            return 'SITE_PLAN'

        # Default based on page number
        if page_num == 1:
            return 'FLOOR_PLAN'
        elif page_num <= 3:
            return 'ELEVATION'
        else:
            return 'OTHER'

    def _classify_and_store(self, text: str, word: Dict, numbers: Dict):
        """Classify number and store in appropriate category"""
        text_upper = text.upper()

        # DIMENSION
        if re.search(r'\d+\.?\d*\s*MM', text_upper):
            match = re.search(r'(\d+\.?\d*)\s*MM', text_upper)
            numbers['dimensions'].append({
                'text': text,
                'value': float(match.group(1)),
                'unit': 'mm',
                'position': {'x': word['x0'], 'y': word['top']}
            })
        elif re.search(r'\d+\.?\d*\s*M(?![A-Z])', text_upper):
            match = re.search(r'(\d+\.?\d*)\s*M', text_upper)
            numbers['dimensions'].append({
                'text': text,
                'value': float(match.group(1)),
                'unit': 'm',
                'position': {'x': word['x0'], 'y': word['top']}
            })

        # LABEL (D1, D2, W1, W2, etc.)
        elif re.match(r'^[DW]\d+$', text_upper):
            numbers['labels'].append({
                'text': text,
                'type': 'door' if text_upper.startswith('D') else 'window',
                'position': {'x': word['x0'], 'y': word['top']}
            })

        # GRID REFERENCE (single digit)
        elif re.match(r'^\d$', text):
            numbers['grid_refs'].append({
                'text': text,
                'value': int(text),
                'position': {'x': word['x0'], 'y': word['top']}
            })

        # SCALE (1:100)
        elif re.match(r'1:\d+', text):
            numbers['scales'].append({
                'text': text,
                'position': {'x': word['x0'], 'y': word['top']}
            })

        # DRAWING NUMBER (WD-1/01)
        elif re.search(r'[A-Z]+-?\d+/\d+', text_upper):
            numbers['drawing_numbers'].append({
                'text': text,
                'position': {'x': word['x0'], 'y': word['top']}
            })

        # UTILITY MARKER (MH1, G2, etc.)
        elif re.match(r'^[A-Z]{1,3}\d+$', text_upper):
            numbers['utilities'].append({
                'text': text,
                'position': {'x': word['x0'], 'y': word['top']}
            })

        # OTHER
        else:
            numbers['other'].append({
                'text': text,
                'position': {'x': word['x0'], 'y': word['top']}
            })

    def _extract_tables(self, page, words: List[Dict]) -> List[Dict]:
        """
        Extract tables from schedule pages

        Tables are identified by:
        - Repeated Y coordinates (rows)
        - Regular X spacing (columns)
        - Header row with labels
        """
        # Group words by Y coordinate (rows)
        rows = defaultdict(list)
        for word in words:
            y_rounded = round(word['top'] / 5) * 5  # Group within 5px
            rows[y_rounded].append(word)

        # Sort each row by X coordinate
        for y in rows:
            rows[y] = sorted(rows[y], key=lambda w: w['x0'])

        # Find table structures (3+ consecutive rows with similar column count)
        tables = []
        y_coords = sorted(rows.keys())

        i = 0
        while i < len(y_coords) - 2:
            y1, y2, y3 = y_coords[i], y_coords[i+1], y_coords[i+2]

            # Check if rows have similar column counts
            col_counts = [len(rows[y1]), len(rows[y2]), len(rows[y3])]
            avg_cols = sum(col_counts) / len(col_counts)

            if max(col_counts) - min(col_counts) <= 3 and avg_cols >= 3:
                # Potential table - extract all consecutive rows
                table_rows = []
                j = i
                while j < len(y_coords):
                    y = y_coords[j]
                    if abs(len(rows[y]) - avg_cols) <= 3:
                        table_rows.append({
                            'y': y,
                            'cells': [w['text'] for w in rows[y]]
                        })
                        j += 1
                    else:
                        break

                if len(table_rows) >= 3:
                    tables.append({
                        'start_y': table_rows[0]['y'],
                        'end_y': table_rows[-1]['y'],
                        'rows': len(table_rows),
                        'columns': int(avg_cols),
                        'data': table_rows
                    })
                    i = j
                    continue

            i += 1

        return tables

    def _build_spatial_layout(self, words: List[Dict], page) -> Dict:
        """
        Build spatial understanding of page layout

        Divides page into quadrants and identifies what's in each area
        """
        # Get page dimensions
        width = page.width
        height = page.height

        # Define quadrants
        quadrants = {
            'top_left': {'x': (0, width/2), 'y': (0, height/2), 'items': []},
            'top_right': {'x': (width/2, width), 'y': (0, height/2), 'items': []},
            'bottom_left': {'x': (0, width/2), 'y': (height/2, height), 'items': []},
            'bottom_right': {'x': (width/2, width), 'y': (height/2, height), 'items': []}
        }

        # Assign words to quadrants
        for word in words:
            x, y = word['x0'], word['top']
            text = word['text']

            if not any(c.isdigit() for c in text):
                continue  # Only track numbers

            for quad_name, quad_bounds in quadrants.items():
                if (quad_bounds['x'][0] <= x < quad_bounds['x'][1] and
                    quad_bounds['y'][0] <= y < quad_bounds['y'][1]):
                    quadrants[quad_name]['items'].append(text)
                    break

        # Summarize each quadrant
        for quad_name in quadrants:
            items = quadrants[quad_name]['items']
            quadrants[quad_name]['count'] = len(items)
            quadrants[quad_name]['sample'] = items[:5]  # First 5 items
            del quadrants[quad_name]['items']  # Remove full list

        return {
            'page_dimensions': {'width': width, 'height': height},
            'quadrants': quadrants
        }

    def _generate_page_description(self, page_type: str, stats: Dict, text: str) -> str:
        """Generate human-readable description of page"""
        descriptions = {
            'FLOOR_PLAN': f"Architectural floor plan with {stats['door_window_labels']} door/window labels, {stats['grid_references']} grid references",
            'ELEVATION': f"Building elevation drawing with {stats['dimensions']} dimensions",
            'SCHEDULE': f"Schedule page with {stats['tables']} tables containing door/window specifications",
            'SECTION': f"Building section with {stats['dimensions']} dimensions",
            'SITE_PLAN': f"Site plan layout",
            'OTHER': f"General drawing page"
        }

        return descriptions.get(page_type, f"{page_type} page")

    def save_results(self, output_file: str):
        """Save page-by-page data"""
        results = {
            'total_pages': len(self.pages_data),
            'pages': self.pages_data
        }

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nPage-by-page data saved to: {output_file}")
        return results

    def print_summary_table(self):
        """Print summary table of all pages"""
        print("\n" + "="*80)
        print("PAGE SUMMARY TABLE")
        print("="*80)
        print()
        print(f"{'Page':<6} {'Type':<15} {'Dims':<6} {'Labels':<7} {'Grid':<6} {'Tables':<7} Description")
        print("-"*80)

        for page_data in self.pages_data:
            p = page_data['page_number']
            t = page_data['page_type']
            d = page_data['stats']['dimensions']
            l = page_data['stats']['door_window_labels']
            g = page_data['stats']['grid_references']
            tb = page_data['stats']['tables']
            desc = page_data['description'][:40]

            print(f"{p:<6} {t:<15} {d:<6} {l:<7} {g:<6} {tb:<7} {desc}")

        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_by_page.py <pdf_file> [output.json]")
        print()
        print("Extracts data page-by-page into separate tables")
        print("Then ready for systematic correlation")
        sys.exit(1)

    pdf_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'pages_data.json'

    extractor = PageByPageExtractor(pdf_file)
    extractor.extract_all_pages()
    extractor.print_summary_table()
    results = extractor.save_results(output_file)

    print("\n" + "="*80)
    print("NEXT STEP: SYSTEMATIC CORRELATION")
    print("="*80)
    print("\nNow that each page is in its own table, we can:")
    print("1. Match labels from Page 1 (floor plan) to dimensions from Page 8 (schedule)")
    print("2. Link grid references across pages")
    print("3. Correlate elevations to floor plan heights")
    print("4. Build complete object database from matched data")
    print()


if __name__ == "__main__":
    main()
