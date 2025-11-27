#!/usr/bin/env python3
"""
Comprehensive Annotation Extractor - GIGO Ground Truth Capture

Extracts ALL text annotations from PDF systematically:
- Door/window labels (D1, W1)
- Grid references (A, B, 1, 2)
- Dimension annotations (measurements)
- Room labels (BILIK TIDUR, DAPUR)
- All other text

Purpose: Create immutable ground truth for validation
"""

import pdfplumber
import json
import re
from datetime import datetime


class ComprehensiveAnnotationExtractor:
    """Systematically extract ALL annotations from PDF for ground truth"""

    def __init__(self, calibration_engine):
        self.calibration = calibration_engine

    def extract_all_annotations(self, pdf_path):
        """
        Extract ALL text annotations from PDF

        Returns comprehensive annotation ground truth:
        {
            'doors': [...],
            'windows': [...],
            'rooms': [...],
            'dimensions': [...],
            'grid_references': [...],
            'electrical': [...],
            'other': [...]
        }
        """
        annotations = {
            'doors': [],
            'windows': [],
            'rooms': [],
            'dimensions': [],
            'grid_references': [],
            'electrical': [],
            'plumbing': [],
            'furniture': [],
            'other': [],
            'metadata': {
                'extracted_at': datetime.now().isoformat(),
                'pdf_source': pdf_path,
                'total_annotations': 0
            }
        }

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                words = page.extract_words()

                for word in words:
                    text = word['text'].strip()
                    text_upper = text.upper()

                    # Calculate building coordinates if calibration available
                    building_pos = None
                    if self.calibration and hasattr(self.calibration, 'transform_to_building'):
                        try:
                            x, y = self.calibration.transform_to_building(word['x0'], word['top'])
                            building_pos = [x, y, 0.0]
                        except:
                            building_pos = None

                    annotation = {
                        'text': text,
                        'pdf_position': {
                            'x': word['x0'],
                            'y': word['top'],
                            'page': page_num
                        },
                        'building_position': building_pos,
                        'bbox_pdf': {
                            'x0': word['x0'],
                            'y0': word['top'],
                            'x1': word['x1'],
                            'y1': word['bottom']
                        },
                        'confidence': 95
                    }

                    # Categorize annotation
                    categorized = False

                    # Door labels (D1, D2, D3)
                    if re.match(r'^D\d+$', text_upper):
                        annotation['category'] = 'door_label'
                        annotation['label_id'] = text_upper
                        annotations['doors'].append(annotation)
                        categorized = True

                    # Window labels (W1, W2, W3)
                    elif re.match(r'^W\d+$', text_upper):
                        annotation['category'] = 'window_label'
                        annotation['label_id'] = text_upper
                        annotations['windows'].append(annotation)
                        categorized = True

                    # Electrical labels (S, L, LAM)
                    elif text_upper in ['S', 'L', 'LAM', 'CF', 'FAN']:
                        annotation['category'] = 'electrical_symbol'
                        annotation['symbol_type'] = text_upper
                        annotations['electrical'].append(annotation)
                        categorized = True

                    # Plumbing labels (WC, BASIN, SINK, SHOWER, FD)
                    elif text_upper in ['WC', 'BASIN', 'SINK', 'SHOWER', 'FD', 'IC', 'DP']:
                        annotation['category'] = 'plumbing_symbol'
                        annotation['symbol_type'] = text_upper
                        annotations['plumbing'].append(annotation)
                        categorized = True

                    # Dimension annotations (contains numbers + MM/M or x)
                    elif re.search(r'\d+(MM|M|mm|m|X|x|@)', text_upper):
                        annotation['category'] = 'dimension'
                        # Try to parse dimension
                        match = re.search(r'(\d+\.?\d*)\s*[xX]\s*(\d+\.?\d*)', text)
                        if match:
                            annotation['parsed'] = {
                                'width': float(match.group(1)),
                                'height': float(match.group(2))
                            }
                        annotations['dimensions'].append(annotation)
                        categorized = True

                    # Grid references (single letter A-Z or number 1-9)
                    elif re.match(r'^[A-Z]$', text_upper) or re.match(r'^\d$', text):
                        annotation['category'] = 'grid_reference'
                        annotation['grid_id'] = text_upper
                        annotations['grid_references'].append(annotation)
                        categorized = True

                    # Room labels (longer text, Malay/English words)
                    elif len(text) > 4 and text.isalpha():
                        annotation['category'] = 'room_label'
                        # Try to identify room type
                        if any(x in text_upper for x in ['BILIK', 'TIDUR', 'BEDROOM', 'KATIL']):
                            annotation['room_type'] = 'bedroom'
                        elif any(x in text_upper for x in ['DAPUR', 'KITCHEN']):
                            annotation['room_type'] = 'kitchen'
                        elif any(x in text_upper for x in ['BILIK AIR', 'BATHROOM', 'TOILET']):
                            annotation['room_type'] = 'bathroom'
                        elif any(x in text_upper for x in ['RUANG', 'LIVING', 'HALL']):
                            annotation['room_type'] = 'living_room'
                        annotations['rooms'].append(annotation)
                        categorized = True

                    # Furniture labels (BED, WARDROBE, TABLE, SOFA, TV)
                    elif any(x in text_upper for x in ['BED', 'WARDROBE', 'TABLE', 'SOFA', 'TV', 'REF', 'FRIDGE']):
                        annotation['category'] = 'furniture_label'
                        annotation['furniture_type'] = text_upper
                        annotations['furniture'].append(annotation)
                        categorized = True

                    # Everything else
                    if not categorized:
                        annotation['category'] = 'other'
                        annotations['other'].append(annotation)

        # Update metadata
        annotations['metadata']['total_annotations'] = sum([
            len(annotations['doors']),
            len(annotations['windows']),
            len(annotations['rooms']),
            len(annotations['dimensions']),
            len(annotations['grid_references']),
            len(annotations['electrical']),
            len(annotations['plumbing']),
            len(annotations['furniture']),
            len(annotations['other'])
        ])

        return annotations

    def save_ground_truth(self, annotations, output_path):
        """Save annotation ground truth to JSON"""
        with open(output_path, 'w') as f:
            json.dump(annotations, f, indent=2)

        print(f"✅ Annotation ground truth saved: {output_path}")
        print(f"   Total annotations: {annotations['metadata']['total_annotations']}")
        print(f"   - Doors: {len(annotations['doors'])}")
        print(f"   - Windows: {len(annotations['windows'])}")
        print(f"   - Rooms: {len(annotations['rooms'])}")
        print(f"   - Dimensions: {len(annotations['dimensions'])}")
        print(f"   - Grid refs: {len(annotations['grid_references'])}")
        print(f"   - Electrical: {len(annotations['electrical'])}")
        print(f"   - Plumbing: {len(annotations['plumbing'])}")
        print(f"   - Furniture: {len(annotations['furniture'])}")
        print(f"   - Other: {len(annotations['other'])}")


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from extraction_engine import CalibrationEngine

    if len(sys.argv) < 2:
        print("Usage: python3 comprehensive_annotation_extractor.py <pdf_file> [building_width] [building_length]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    building_width = float(sys.argv[2]) if len(sys.argv) > 2 else 9.8
    building_length = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0

    # Initialize calibration
    with pdfplumber.open(pdf_path) as pdf:
        calibration = CalibrationEngine(pdf, building_width, building_length)

    # Extract all annotations
    extractor = ComprehensiveAnnotationExtractor(calibration)
    annotations = extractor.extract_all_annotations(pdf_path)

    # Save ground truth
    output_file = f"output_artifacts/{pdf_path.replace('.pdf', '')}_ANNOTATION_GROUND_TRUTH.json"
    extractor.save_ground_truth(annotations, output_file)
