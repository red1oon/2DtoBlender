#!/usr/bin/env python3
"""
Annotation Manager - Persist and Validate OCR Annotations as Ground Truth

Annotations from PDF drawings are FACTS that serve as ground truth for:
1. Error correction - Cross-check extracted objects against original labels
2. Validation - Verify 3D model matches drawing annotations
3. Traceability - Link every object back to source document
4. Re-correlation - Re-process if extraction logic improves
"""

import json
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class AnnotationManager:
    """
    Manage OCR annotations as persistent ground truth

    Annotations are immutable facts from drawings that can be used to
    validate and correct extracted objects.
    """

    def __init__(self):
        self.annotations = {
            'doors': [],
            'windows': [],
            'rooms': [],
            'dimensions': [],
            'other': []
        }
        self.timestamp = datetime.now().isoformat()

    def add_door_annotation(self, text: str, pdf_pos: Dict, building_pos: List[float],
                           bbox: Dict, confidence: int, page: int, associated_object: str = None):
        """
        Add door label annotation (e.g., D1, D2, D3)

        These are FACTS from the drawing that serve as ground truth.
        """
        self.annotations['doors'].append({
            'text': text,
            'pdf_position': {'x': pdf_pos['x'], 'y': pdf_pos['y'], 'page': page},
            'building_position': building_pos,
            'bbox_pdf': bbox,
            'confidence': confidence,
            'associated_object': associated_object,
            'extracted_from': 'floor_plan_label',
            'ocr_timestamp': self.timestamp
        })

    def add_window_annotation(self, text: str, pdf_pos: Dict, building_pos: List[float],
                             bbox: Dict, confidence: int, page: int, associated_object: str = None):
        """
        Add window label annotation (e.g., W1, W2, W3)

        These are FACTS from the drawing that serve as ground truth.
        """
        self.annotations['windows'].append({
            'text': text,
            'pdf_position': {'x': pdf_pos['x'], 'y': pdf_pos['y'], 'page': page},
            'building_position': building_pos,
            'bbox_pdf': bbox,
            'confidence': confidence,
            'associated_object': associated_object,
            'extracted_from': 'floor_plan_label',
            'ocr_timestamp': self.timestamp
        })

    def add_room_annotation(self, text: str, pdf_pos: Dict, building_pos: List[float],
                           bbox: Dict, confidence: int, page: int,
                           associated_room: str = None, language: str = 'Malay'):
        """
        Add room label annotation (e.g., BILIK TIDUR, DAPUR, RUANG TAMU)

        These are FACTS from the drawing that serve as ground truth.
        """
        self.annotations['rooms'].append({
            'text': text,
            'text_normalized': self._normalize_room_label(text),
            'pdf_position': {'x': pdf_pos['x'], 'y': pdf_pos['y'], 'page': page},
            'building_position': building_pos,
            'bbox_pdf': bbox,
            'confidence': confidence,
            'associated_room': associated_room,
            'language': language,
            'extracted_from': 'floor_plan_label',
            'ocr_timestamp': self.timestamp
        })

    def add_dimension_annotation(self, text: str, pdf_pos: Dict, parsed_dims: Dict,
                                associated_object: str, confidence: int, page: int,
                                extracted_from: str = 'schedule'):
        """
        Add dimension annotation (e.g., "900MM X 2100MM")

        These are FACTS from schedules that serve as ground truth.
        """
        self.annotations['dimensions'].append({
            'text': text,
            'pdf_position': {'x': pdf_pos['x'], 'y': pdf_pos['y'], 'page': page},
            'parsed_dimensions': parsed_dims,
            'associated_object': associated_object,
            'extracted_from': extracted_from,
            'confidence': confidence,
            'ocr_timestamp': self.timestamp
        })

    def _normalize_room_label(self, malay_text: str) -> str:
        """Normalize Malay room labels to English"""
        mappings = {
            'BILIK TIDUR UTAMA': 'MASTER BEDROOM',
            'BILIK TIDUR': 'BEDROOM',
            'BILIK AIR': 'BATHROOM',
            'TANDAS': 'TOILET',
            'DAPUR': 'KITCHEN',
            'RUANG TAMU': 'LIVING ROOM',
            'RUANG MAKAN': 'DINING ROOM',
            'STOR': 'STORAGE',
            'CUCIAN': 'LAUNDRY'
        }

        text_upper = malay_text.upper().strip()
        for malay, english in mappings.items():
            if malay in text_upper:
                return english

        return text_upper  # Return as-is if no mapping

    def get_annotations_dict(self) -> Dict:
        """Get all annotations as dictionary for JSON export"""
        return self.annotations

    def save_to_json(self, filepath: str):
        """Save annotations to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.annotations, f, indent=2)
        print(f"💾 Annotations saved to: {filepath}")

    def load_from_json(self, filepath: str):
        """Load annotations from JSON file"""
        with open(filepath) as f:
            self.annotations = json.load(f)
        print(f"📂 Annotations loaded from: {filepath}")


class AnnotationValidator:
    """
    Validate extracted objects against annotation ground truth

    Annotations are FACTS - if extraction doesn't match annotations,
    extraction is likely wrong.
    """

    def __init__(self, annotations: Dict, objects: List[Dict]):
        self.annotations = annotations
        self.objects = objects
        self.issues = []
        self.corrections = []

    def validate_all(self) -> Dict:
        """
        Validate all objects against annotation ground truth

        Returns:
            dict: Validation report with issues and suggested corrections
        """
        print("\n" + "="*80)
        print("VALIDATING OBJECTS AGAINST ANNOTATION GROUND TRUTH")
        print("="*80)

        self.validate_door_annotations()
        self.validate_window_annotations()
        self.validate_room_annotations()
        self.validate_dimension_annotations()

        return {
            'total_annotations': self._count_annotations(),
            'issues_found': len(self.issues),
            'corrections_suggested': len(self.corrections),
            'issues': self.issues,
            'corrections': self.corrections
        }

    def validate_door_annotations(self):
        """Validate door objects match door label annotations"""
        print(f"\n📍 Validating {len(self.annotations['doors'])} door annotations...")

        for ann in self.annotations['doors']:
            # Find associated object
            obj = self._find_object(ann.get('associated_object'))

            if not obj:
                self.issues.append({
                    'type': 'missing_object',
                    'annotation': ann['text'],
                    'category': 'door',
                    'message': f"Annotation {ann['text']} has no associated object",
                    'severity': 'critical'
                })
                continue

            # Check position matches (ground truth position vs object position)
            ann_pos = ann['building_position']
            obj_pos = obj.get('position', [0, 0, 0])

            distance = self._calculate_distance_2d(ann_pos[:2], obj_pos[:2])

            if distance > 0.5:  # More than 50cm mismatch
                self.issues.append({
                    'type': 'position_mismatch',
                    'annotation': ann['text'],
                    'category': 'door',
                    'distance': round(distance, 2),
                    'message': f"Door {ann['text']}: label at {ann_pos[:2]}, object at {obj_pos[:2]} (distance: {distance:.2f}m)",
                    'severity': 'warning' if distance < 1.0 else 'critical'
                })

                # Suggest correction
                self.corrections.append({
                    'object_name': obj.get('name'),
                    'correction_type': 'update_position',
                    'from': obj_pos,
                    'to': ann_pos,
                    'reason': f"Match annotation {ann['text']} ground truth position",
                    'confidence': ann['confidence']
                })

        print(f"   Found {len([i for i in self.issues if i['category'] == 'door'])} door issues")

    def validate_window_annotations(self):
        """Validate window objects match window label annotations"""
        print(f"\n📍 Validating {len(self.annotations['windows'])} window annotations...")

        for ann in self.annotations['windows']:
            obj = self._find_object(ann.get('associated_object'))

            if not obj:
                self.issues.append({
                    'type': 'missing_object',
                    'annotation': ann['text'],
                    'category': 'window',
                    'message': f"Annotation {ann['text']} has no associated object",
                    'severity': 'critical'
                })
                continue

            # Check position
            ann_pos = ann['building_position']
            obj_pos = obj.get('position', [0, 0, 0])
            distance = self._calculate_distance_2d(ann_pos[:2], obj_pos[:2])

            if distance > 0.5:
                self.issues.append({
                    'type': 'position_mismatch',
                    'annotation': ann['text'],
                    'category': 'window',
                    'distance': round(distance, 2),
                    'message': f"Window {ann['text']}: label at {ann_pos[:2]}, object at {obj_pos[:2]} (distance: {distance:.2f}m)",
                    'severity': 'warning' if distance < 1.0 else 'critical'
                })

        print(f"   Found {len([i for i in self.issues if i['category'] == 'window'])} window issues")

    def validate_room_annotations(self):
        """Validate room assignments match room label annotations"""
        print(f"\n📍 Validating {len(self.annotations['rooms'])} room annotations...")

        for ann in self.annotations['rooms']:
            associated_room = ann.get('associated_room')
            if not associated_room:
                continue

            # Find objects in this room
            room_objects = [o for o in self.objects if o.get('room') == associated_room]

            if not room_objects:
                self.issues.append({
                    'type': 'empty_room',
                    'annotation': ann['text'],
                    'category': 'room',
                    'message': f"Room {ann['text']} ({associated_room}) has no objects",
                    'severity': 'warning'
                })
                continue

            # Check if room centroid matches annotation position
            room_centroid = self._calculate_room_centroid(room_objects)
            ann_pos = ann['building_position']
            distance = self._calculate_distance_2d(room_centroid, ann_pos[:2])

            if distance > 2.0:  # Room label should be within room
                self.issues.append({
                    'type': 'room_label_mismatch',
                    'annotation': ann['text'],
                    'category': 'room',
                    'distance': round(distance, 2),
                    'message': f"Room {ann['text']} label position doesn't match room objects centroid (distance: {distance:.2f}m)",
                    'severity': 'warning'
                })

        print(f"   Found {len([i for i in self.issues if i['category'] == 'room'])} room issues")

    def validate_dimension_annotations(self):
        """Validate object dimensions match schedule annotations"""
        print(f"\n📍 Validating {len(self.annotations['dimensions'])} dimension annotations...")

        for ann in self.annotations['dimensions']:
            obj = self._find_object(ann.get('associated_object'))

            if not obj:
                continue

            # Get dimensions from annotation (ground truth)
            ann_dims = ann.get('parsed_dimensions', {})
            width_expected = ann_dims.get('width')
            height_expected = ann_dims.get('height')

            # Get dimensions from object
            width_actual = obj.get('width')
            height_actual = obj.get('height')

            # Check width mismatch
            if width_expected and width_actual:
                width_diff = abs(width_expected - width_actual)
                if width_diff > 0.05:  # More than 5cm difference
                    self.issues.append({
                        'type': 'dimension_mismatch',
                        'annotation': ann['text'],
                        'category': 'dimension',
                        'object': obj.get('name'),
                        'dimension': 'width',
                        'expected': width_expected,
                        'actual': width_actual,
                        'difference': round(width_diff, 2),
                        'message': f"{obj.get('name')} width: schedule says {width_expected}m, object has {width_actual}m",
                        'severity': 'warning'
                    })

                    self.corrections.append({
                        'object_name': obj.get('name'),
                        'correction_type': 'update_dimension',
                        'dimension': 'width',
                        'from': width_actual,
                        'to': width_expected,
                        'reason': f"Match schedule annotation {ann['text']}",
                        'confidence': ann['confidence']
                    })

        print(f"   Found {len([i for i in self.issues if i['category'] == 'dimension'])} dimension issues")

    def _find_object(self, object_name: str) -> Optional[Dict]:
        """Find object by name"""
        if not object_name:
            return None
        for obj in self.objects:
            if obj.get('name') == object_name:
                return obj
        return None

    def _calculate_distance_2d(self, pos1: List[float], pos2: List[float]) -> float:
        """Calculate 2D Euclidean distance"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return math.sqrt(dx*dx + dy*dy)

    def _calculate_room_centroid(self, room_objects: List[Dict]) -> Tuple[float, float]:
        """Calculate centroid of room objects"""
        positions = [o.get('position', [0, 0, 0]) for o in room_objects]
        avg_x = sum(p[0] for p in positions) / len(positions)
        avg_y = sum(p[1] for p in positions) / len(positions)
        return (avg_x, avg_y)

    def _count_annotations(self) -> int:
        """Count total annotations"""
        return sum(len(self.annotations[cat]) for cat in self.annotations.keys())

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*80)
        print("ANNOTATION VALIDATION SUMMARY")
        print("="*80)

        total = self._count_annotations()
        critical = len([i for i in self.issues if i['severity'] == 'critical'])
        warnings = len([i for i in self.issues if i['severity'] == 'warning'])

        print(f"\n📊 Total annotations: {total}")
        print(f"❌ Critical issues: {critical}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"🔧 Corrections suggested: {len(self.corrections)}")

        if self.issues:
            print("\n📋 Issues by category:")
            categories = {}
            for issue in self.issues:
                cat = issue['category']
                categories[cat] = categories.get(cat, 0) + 1

            for cat, count in categories.items():
                print(f"   {cat}: {count} issues")

        print("\n" + "="*80)


class AnnotationCorrector:
    """
    Apply corrections based on annotation ground truth

    Annotations are FACTS - use them to correct extraction errors.
    """

    def __init__(self, objects: List[Dict], corrections: List[Dict]):
        self.objects = objects
        self.corrections = corrections
        self.applied = 0

    def apply_all_corrections(self) -> int:
        """
        Apply all suggested corrections

        Returns:
            int: Number of corrections applied
        """
        print("\n" + "="*80)
        print("APPLYING ANNOTATION-BASED CORRECTIONS")
        print("="*80)

        for correction in self.corrections:
            if self._apply_correction(correction):
                self.applied += 1

        print(f"\n✅ Applied {self.applied}/{len(self.corrections)} corrections")
        return self.applied

    def _apply_correction(self, correction: Dict) -> bool:
        """Apply a single correction"""
        obj_name = correction['object_name']
        corr_type = correction['correction_type']

        # Find object
        obj = None
        for o in self.objects:
            if o.get('name') == obj_name:
                obj = o
                break

        if not obj:
            return False

        # Apply correction based on type
        if corr_type == 'update_position':
            old_pos = correction['from']
            new_pos = correction['to']
            obj['position'] = new_pos
            print(f"   ✓ {obj_name}: position {old_pos} → {new_pos}")
            return True

        elif corr_type == 'update_dimension':
            dim = correction['dimension']
            old_val = correction['from']
            new_val = correction['to']
            obj[dim] = new_val
            print(f"   ✓ {obj_name}: {dim} {old_val}m → {new_val}m")
            return True

        return False


def demo_annotation_workflow():
    """Demonstrate annotation persistence and validation workflow"""
    print("="*80)
    print("ANNOTATION PERSISTENCE WORKFLOW DEMO")
    print("="*80)

    # 1. Create annotation manager
    ann_mgr = AnnotationManager()

    # 2. Add annotations during extraction
    ann_mgr.add_door_annotation(
        text='D1',
        pdf_pos={'x': 245.3, 'y': 387.2},
        building_pos=[2.54, 3.21, 0.0],
        bbox={'x0': 243.1, 'y0': 385.0, 'x1': 248.9, 'y1': 390.5},
        confidence=95,
        page=4,
        associated_object='D1_x25_y32'
    )

    ann_mgr.add_room_annotation(
        text='BILIK TIDUR UTAMA',
        pdf_pos={'x': 198.4, 'y': 256.8},
        building_pos=[1.95, 2.15, 0.0],
        bbox={'x0': 185.2, 'y0': 252.0, 'x1': 215.6, 'y1': 262.5},
        confidence=85,
        page=4,
        associated_room='master_bedroom',
        language='Malay'
    )

    # 3. Save annotations (persist as ground truth)
    annotations = ann_mgr.get_annotations_dict()
    print(f"\n✅ Captured {len(annotations['doors'])} door, {len(annotations['rooms'])} room annotations")

    return annotations


if __name__ == "__main__":
    demo_annotation_workflow()
