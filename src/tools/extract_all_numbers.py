#!/usr/bin/env python3
"""
Extract ALL Numbers from PDF

Captures every number, dimension, label, coordinate from drawings.
Then analyze patterns to derive relationships.

Strategy: "Capture them first and then see how they fit into a pattern
that will derive everything else" - User
"""

import pdfplumber
import re
import json
import sys
from collections import defaultdict
from typing import Dict, List, Tuple


class NumberExtractor:
    """Extract all numbers from PDF drawings"""

    def __init__(self, pdf_path: str):
        self.pdf = pdfplumber.open(pdf_path)
        self.all_numbers = []

    def extract_all(self) -> List[Dict]:
        """Extract every number from every page"""
        print("="*80)
        print("EXTRACTING ALL NUMBERS FROM PDF")
        print("="*80)
        print()

        for page_idx, page in enumerate(self.pdf.pages):
            print(f"Processing Page {page_idx + 1}...")
            page_numbers = self._extract_from_page(page, page_idx + 1)
            self.all_numbers.extend(page_numbers)

        print(f"\nTotal numbers extracted: {len(self.all_numbers)}")
        return self.all_numbers

    def _extract_from_page(self, page, page_num: int) -> List[Dict]:
        """Extract all numbers from a single page"""
        words = page.extract_words()
        page_numbers = []

        for word in words:
            text = word['text'].strip()

            # Check if text contains any digits
            if not any(c.isdigit() for c in text):
                continue

            # Classify and extract number
            number_info = self._classify_number(text, word, page_num)
            if number_info:
                page_numbers.append(number_info)

        return page_numbers

    def _classify_number(self, text: str, word: Dict, page_num: int) -> Dict:
        """
        Classify what type of number this is

        Categories:
        1. DIMENSION - measurements (900MM, 2100MM, 1300, etc.)
        2. LABEL - object labels (D1, D2, W1, W2, etc.)
        3. GRID - grid references (1, 2, 3, 4, 5)
        4. SCALE - drawing scale (1:100, 1:50)
        5. COORDINATE - coordinates or angles
        6. DRAWING_NUMBER - drawing reference (WD-1/01)
        7. QUANTITY - counts
        8. OTHER - unknown
        """
        text_upper = text.upper()

        category = None
        parsed_value = None
        unit = None

        # 1. DIMENSION (measurements with units)
        dim_patterns = [
            (r'(\d+\.?\d*)\s*MM', 'mm', 'DIMENSION'),
            (r'(\d+\.?\d*)\s*M(?![A-Z])', 'm', 'DIMENSION'),
            (r'(\d+\.?\d*)\s*CM', 'cm', 'DIMENSION'),
            (r'(\d+)\s*X\s*(\d+)', None, 'DIMENSION_PAIR'),  # 900 X 2100
        ]

        for pattern, unit_type, cat in dim_patterns:
            match = re.search(pattern, text_upper)
            if match:
                category = cat
                unit = unit_type
                if cat == 'DIMENSION_PAIR':
                    parsed_value = [int(match.group(1)), int(match.group(2))]
                else:
                    parsed_value = float(match.group(1))
                break

        # 2. LABEL (door/window labels)
        if not category:
            if re.match(r'^[DW]\d+$', text_upper):
                category = 'LABEL_DOOR_WINDOW'
                parsed_value = text_upper

        # 3. GRID (single digit numbers)
        if not category:
            if re.match(r'^\d$', text):
                category = 'GRID_REFERENCE'
                parsed_value = int(text)

        # 4. SCALE (1:100, 1:50)
        if not category:
            if re.match(r'1:\d+', text):
                category = 'SCALE'
                parsed_value = text

        # 5. DRAWING_NUMBER (WD-1/01, etc.)
        if not category:
            if re.search(r'[A-Z]+-?\d+/\d+', text_upper):
                category = 'DRAWING_NUMBER'
                parsed_value = text

        # 6. UTILITY MARKERS (MH1, G2, G3)
        if not category:
            if re.match(r'^[A-Z]{1,3}\d+$', text_upper):
                category = 'UTILITY_MARKER'
                parsed_value = text_upper

        # 7. ANGLE/COORDINATE (numbers with decimals)
        if not category:
            if re.match(r'^\d+\.?\d*$', text):
                try:
                    val = float(text)
                    category = 'NUMBER'
                    parsed_value = val
                except:
                    pass

        # 8. OTHER (contains digits but doesn't match above)
        if not category:
            category = 'OTHER'
            parsed_value = text

        return {
            'text': text,
            'category': category,
            'parsed_value': parsed_value,
            'unit': unit,
            'pdf_position': {
                'x': round(word['x0'], 2),
                'y': round(word['top'], 2),
                'page': page_num
            },
            'bbox': {
                'x0': word['x0'],
                'y0': word['top'],
                'x1': word['x1'],
                'y1': word['bottom']
            }
        }

    def categorize(self) -> Dict[str, List[Dict]]:
        """Group numbers by category"""
        categorized = defaultdict(list)

        for num in self.all_numbers:
            category = num['category']
            categorized[category].append(num)

        return dict(categorized)

    def find_patterns(self) -> Dict:
        """
        Analyze patterns in the numbers

        Patterns to look for:
        1. Dimension pairs (width X height) - likely from schedule
        2. Labels with nearby dimensions (D1 near 900MM X 2100MM)
        3. Grid references along edges
        4. Clustered numbers (table cells)
        """
        patterns = {
            'dimension_pairs': [],
            'label_with_dimensions': [],
            'grid_alignment': [],
            'table_structures': []
        }

        categorized = self.categorize()

        # Find dimension pairs (X Y coordinates close together)
        dimensions = categorized.get('DIMENSION', [])
        for i, dim1 in enumerate(dimensions):
            for dim2 in dimensions[i+1:]:
                # If on same page and close together
                if (dim1['pdf_position']['page'] == dim2['pdf_position']['page'] and
                    abs(dim1['pdf_position']['y'] - dim2['pdf_position']['y']) < 10):

                    x_dist = abs(dim1['pdf_position']['x'] - dim2['pdf_position']['x'])
                    if 20 < x_dist < 150:  # Close but not overlapping
                        patterns['dimension_pairs'].append({
                            'dim1': dim1,
                            'dim2': dim2,
                            'likely_width_height': True,
                            'distance': x_dist
                        })

        # Find labels near dimensions (within 50 pixels)
        labels = categorized.get('LABEL_DOOR_WINDOW', [])
        for label in labels:
            nearby_dims = []
            for dim in dimensions:
                if dim['pdf_position']['page'] == label['pdf_position']['page']:
                    dist = (
                        (dim['pdf_position']['x'] - label['pdf_position']['x'])**2 +
                        (dim['pdf_position']['y'] - label['pdf_position']['y'])**2
                    )**0.5

                    if dist < 100:  # Within 100 pixels
                        nearby_dims.append({
                            'dimension': dim,
                            'distance': dist
                        })

            if nearby_dims:
                patterns['label_with_dimensions'].append({
                    'label': label,
                    'nearby_dimensions': sorted(nearby_dims, key=lambda x: x['distance'])
                })

        # Find grid alignment (numbers with same X or Y coordinate)
        grid_refs = categorized.get('GRID_REFERENCE', [])
        if grid_refs:
            # Group by X coordinate (vertical alignment)
            x_groups = defaultdict(list)
            for ref in grid_refs:
                x_rounded = round(ref['pdf_position']['x'] / 10) * 10
                x_groups[x_rounded].append(ref)

            # Keep only groups with 3+ items (likely a grid)
            for x, refs in x_groups.items():
                if len(refs) >= 3:
                    patterns['grid_alignment'].append({
                        'orientation': 'vertical',
                        'x_coordinate': x,
                        'count': len(refs),
                        'references': sorted(refs, key=lambda r: r['pdf_position']['y'])
                    })

        return patterns

    def save_results(self, output_file: str):
        """Save extracted numbers to JSON"""
        categorized = self.categorize()
        patterns = self.find_patterns()

        results = {
            'total_numbers': len(self.all_numbers),
            'by_category': {
                cat: len(items) for cat, items in categorized.items()
            },
            'numbers': self.all_numbers,
            'categorized': categorized,
            'patterns': patterns
        }

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {output_file}")
        return results

    def print_summary(self):
        """Print summary of extracted numbers"""
        categorized = self.categorize()
        patterns = self.find_patterns()

        print("\n" + "="*80)
        print("EXTRACTION SUMMARY")
        print("="*80)

        print("\nBy Category:")
        for cat in sorted(categorized.keys()):
            count = len(categorized[cat])
            print(f"  {cat:25s}: {count:4d} items")

        print("\n" + "-"*80)
        print("PATTERNS DISCOVERED")
        print("-"*80)

        # Dimension pairs
        dim_pairs = patterns['dimension_pairs']
        print(f"\n1. Dimension Pairs (likely width × height): {len(dim_pairs)}")
        for pair in dim_pairs[:5]:  # Show first 5
            d1 = pair['dim1']
            d2 = pair['dim2']
            print(f"   {d1['parsed_value']}{d1['unit']} × {d2['parsed_value']}{d2['unit']}")
            print(f"      @ Page {d1['pdf_position']['page']}, "
                  f"Y={d1['pdf_position']['y']}")

        # Labels with dimensions
        label_dims = patterns['label_with_dimensions']
        print(f"\n2. Labels with Nearby Dimensions: {len(label_dims)}")
        for item in label_dims[:5]:  # Show first 5
            label = item['label']
            nearby = item['nearby_dimensions'][:2]  # Show closest 2
            print(f"   {label['text']}:")
            for nd in nearby:
                dim = nd['dimension']
                print(f"      → {dim['text']} (distance: {nd['distance']:.1f}px)")

        # Grid alignment
        grid_align = patterns['grid_alignment']
        print(f"\n3. Grid References (aligned): {len(grid_align)} groups")
        for group in grid_align:
            refs = group['references']
            values = [r['parsed_value'] for r in refs]
            print(f"   {group['orientation']}: {values}")

        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_all_numbers.py <pdf_file> [output.json]")
        print()
        print("Extracts ALL numbers from PDF drawings")
        print("Then analyzes patterns to derive relationships")
        sys.exit(1)

    pdf_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'all_numbers_extracted.json'

    extractor = NumberExtractor(pdf_file)
    extractor.extract_all()
    extractor.print_summary()
    results = extractor.save_results(output_file)

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. Review patterns in: " + output_file)
    print("2. Match dimension pairs to labels (D1 → 900MM × 2100MM)")
    print("3. Build relationships from patterns")
    print("4. Derive complete geometry from matched numbers")
    print()


if __name__ == "__main__":
    main()
