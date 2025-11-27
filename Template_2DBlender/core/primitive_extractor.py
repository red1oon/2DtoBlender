#!/usr/bin/env python3
"""
Primitive Extractor - Universal PDF Primitive Extraction

Extracts ALL geometric primitives from PDF (NO interpretation):
- Text (OCR strings with positions)
- Lines (vector line segments)
- Curves (arcs, bezier curves)
- Rectangles (bounding boxes)

Purpose: Create immutable universal ground truth organized by page
NO categorization, NO pattern matching, NO building coordinates
"""

import pdfplumber
import json
from datetime import datetime


class PrimitiveExtractor:
    """Extract universal primitives from PDF - NO interpretation"""

    def __init__(self):
        """Initialize extractor with NO calibration (keeps raw PDF coords)"""
        pass

    def extract_all_primitives(self, pdf_path):
        """
        Extract ALL primitives from PDF organized by page

        Returns universal primitives ground truth:
        {
            'metadata': {...},
            'page_1': {'primitives': {'text': [...], 'lines': [...]}},
            'page_2': {...}
        }
        """
        primitives_data = {
            'metadata': {
                'extracted_at': datetime.now().isoformat(),
                'pdf_source': pdf_path,
                'total_text': 0,
                'total_lines': 0,
                'total_curves': 0,
                'total_rects': 0,
                'total_pages': 0
            }
        }

        with pdfplumber.open(pdf_path) as pdf:
            primitives_data['metadata']['total_pages'] = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                page_key = f'page_{page_num}'

                # Extract primitives for this page
                page_primitives = self._extract_page_primitives(page, page_num)
                primitives_data[page_key] = page_primitives

                # Update metadata counts
                primitives_data['metadata']['total_text'] += len(page_primitives['primitives']['text'])
                primitives_data['metadata']['total_lines'] += len(page_primitives['primitives']['lines'])
                primitives_data['metadata']['total_curves'] += len(page_primitives['primitives']['curves'])
                primitives_data['metadata']['total_rects'] += len(page_primitives['primitives']['rects'])

        return primitives_data

    def _extract_page_primitives(self, page, page_num):
        """Extract all primitives from a single page with smart filtering"""

        primitives = {
            'page_number': page_num,
            'page_dimensions': {
                'width': page.width,
                'height': page.height
            },
            'primitives': {
                'text': [],
                'lines': [],
                'curves': [],
                'rects': []
            },
            'filter_stats': {
                'text_kept': 0,
                'lines_kept': 0,
                'lines_filtered': 0,
                'curves_kept': 0,
                'curves_filtered': 0,
                'rects_kept': 0,
                'rects_filtered': 0
            }
        }

        # Extract text primitives (ALWAYS keep all text)
        words = page.extract_words()
        text_positions = []  # For proximity checks

        for idx, word in enumerate(words):
            text_primitive = {
                'id': f't{page_num:03d}_{idx:04d}',
                'text': word['text'],
                'x': word['x0'],
                'y': word['top'],
                'bbox': {
                    'x0': word['x0'],
                    'y0': word['top'],
                    'x1': word['x1'],
                    'y1': word['bottom']
                }
            }
            primitives['primitives']['text'].append(text_primitive)
            text_positions.append((word['x0'], word['top']))

        # Extract text from PDF annotations (AutoCAD SHX Text, etc.)
        annots = page.annots if hasattr(page, 'annots') else []
        annot_count = 0
        for annot in annots:
            # Check if annotation contains text
            contents = annot.get('contents', '')
            if contents:
                # Use annotation position (adjust for coordinate system)
                x0 = annot.get('x0', 0)
                y0 = annot.get('y0', 0)
                x1 = annot.get('x1', x0)
                y1 = annot.get('y1', y0)

                text_primitive = {
                    'id': f't{page_num:03d}_{len(words) + annot_count:04d}',
                    'text': contents,
                    'x': x0,
                    'y': y0,
                    'bbox': {
                        'x0': x0,
                        'y0': y0,
                        'x1': x1,
                        'y1': y1
                    },
                    'source': 'annotation'  # Mark as annotation text
                }
                primitives['primitives']['text'].append(text_primitive)
                text_positions.append((x0, y0))
                annot_count += 1

        primitives['filter_stats']['text_kept'] = len(words) + annot_count
        if annot_count > 0:
            primitives['filter_stats']['annotation_text'] = annot_count

        # Extract line primitives with filtering
        lines = page.lines if hasattr(page, 'lines') else []
        kept_idx = 0
        for idx, line in enumerate(lines):
            # Calculate line properties
            length = ((line['x1'] - line['x0'])**2 + (line['y1'] - line['y0'])**2)**0.5
            linewidth = line.get('linewidth', line.get('width', 1.0))

            # Filter criteria
            is_significant = length > 10.0 or linewidth > 0.5
            is_near_text = self._is_near_any_text(line['x0'], line['y0'], text_positions, radius=50.0)
            is_in_title_block = self._is_in_title_block(line['x0'], line['y0'], page.width, page.height)

            # Keep if significant OR near text AND not in title block clutter
            if (is_significant or is_near_text) and not is_in_title_block:
                line_primitive = {
                    'id': f'l{page_num:03d}_{kept_idx:04d}',
                    'x0': line['x0'],
                    'y0': line['y0'],
                    'x1': line['x1'],
                    'y1': line['y1'],
                    'linewidth': linewidth
                }
                primitives['primitives']['lines'].append(line_primitive)
                primitives['filter_stats']['lines_kept'] += 1
                kept_idx += 1
            else:
                primitives['filter_stats']['lines_filtered'] += 1

        # Extract curve primitives with filtering
        curves = page.curves if hasattr(page, 'curves') else []
        kept_idx = 0
        for idx, curve in enumerate(curves):
            # Estimate curve size
            width = abs(curve['x1'] - curve['x0'])
            height = abs(curve['y1'] - curve['y0'])
            size = max(width, height)

            # Filter criteria
            is_significant = size > 5.0
            is_near_text = self._is_near_any_text(curve['x0'], curve['y0'], text_positions, radius=50.0)
            is_in_title_block = self._is_in_title_block(curve['x0'], curve['y0'], page.width, page.height)

            # Keep if significant OR near text (door arcs near "D1") AND not in title block
            if (is_significant or is_near_text) and not is_in_title_block:
                curve_primitive = {
                    'id': f'c{page_num:03d}_{kept_idx:04d}',
                    'x0': curve['x0'],
                    'y0': curve['y0'],
                    'x1': curve['x1'],
                    'y1': curve['y1']
                }
                # Add curve-specific data if available
                if 'pts' in curve:
                    curve_primitive['pts'] = curve['pts']
                primitives['primitives']['curves'].append(curve_primitive)
                primitives['filter_stats']['curves_kept'] += 1
                kept_idx += 1
            else:
                primitives['filter_stats']['curves_filtered'] += 1

        # Extract rectangle primitives with filtering
        rects = page.rects if hasattr(page, 'rects') else []
        kept_idx = 0
        for idx, rect in enumerate(rects):
            width = abs(rect['x1'] - rect['x0'])
            height = abs(rect['y1'] - rect['y0'])
            area = width * height

            # Filter criteria
            is_significant = area > 25.0
            is_near_text = self._is_near_any_text(rect['x0'], rect['y0'], text_positions, radius=50.0)
            is_in_title_block = self._is_in_title_block(rect['x0'], rect['y0'], page.width, page.height)

            # Keep if significant OR near text AND not in title block
            if (is_significant or is_near_text) and not is_in_title_block:
                rect_primitive = {
                    'id': f'r{page_num:03d}_{kept_idx:04d}',
                    'x0': rect['x0'],
                    'y0': rect['y0'],
                    'x1': rect['x1'],
                    'y1': rect['y1'],
                    'width': width,
                    'height': height,
                    'linewidth': rect.get('linewidth', 1.0)
                }
                primitives['primitives']['rects'].append(rect_primitive)
                primitives['filter_stats']['rects_kept'] += 1
                kept_idx += 1
            else:
                primitives['filter_stats']['rects_filtered'] += 1

        return primitives

    def _is_near_any_text(self, x, y, text_positions, radius=50.0):
        """Check if point (x, y) is within radius of any text position"""
        radius_sq = radius * radius
        for tx, ty in text_positions:
            dist_sq = (x - tx)**2 + (y - ty)**2
            if dist_sq <= radius_sq:
                return True
        return False

    def _is_in_title_block(self, x, y, page_width, page_height):
        """Check if point is in title block area (typically right edge or bottom)"""
        # Title blocks usually in right 20% or bottom 15% of page
        in_right_edge = x > (page_width * 0.80)
        in_bottom_edge = y > (page_height * 0.85)
        return in_right_edge or in_bottom_edge

    def save_primitives(self, primitives_data, output_path):
        """Save primitives ground truth to JSON"""
        with open(output_path, 'w') as f:
            json.dump(primitives_data, f, indent=2)

        # Calculate total filter stats
        total_lines_filtered = sum(primitives_data[f'page_{i}']['filter_stats']['lines_filtered']
                                   for i in range(1, primitives_data['metadata']['total_pages'] + 1))
        total_curves_filtered = sum(primitives_data[f'page_{i}']['filter_stats']['curves_filtered']
                                    for i in range(1, primitives_data['metadata']['total_pages'] + 1))
        total_rects_filtered = sum(primitives_data[f'page_{i}']['filter_stats']['rects_filtered']
                                   for i in range(1, primitives_data['metadata']['total_pages'] + 1))

        print(f"✅ Universal primitives saved: {output_path}")
        print(f"   Total pages: {primitives_data['metadata']['total_pages']}")
        print(f"   Total text: {primitives_data['metadata']['total_text']} (all kept)")
        print(f"   Total lines: {primitives_data['metadata']['total_lines']} (filtered: {total_lines_filtered})")
        print(f"   Total curves: {primitives_data['metadata']['total_curves']} (filtered: {total_curves_filtered})")
        print(f"   Total rects: {primitives_data['metadata']['total_rects']} (filtered: {total_rects_filtered})")


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: python3 primitive_extractor.py <pdf_file>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Extract all primitives
    extractor = PrimitiveExtractor()
    primitives = extractor.extract_all_primitives(pdf_path)

    # Save primitives ground truth
    pdf_basename = os.path.basename(pdf_path).replace('.pdf', '')
    output_file = f"output_artifacts/{pdf_basename}_ANNOTATION_FROM_2D.json"
    extractor.save_primitives(primitives, output_file)
