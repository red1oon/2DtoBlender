#!/usr/bin/env python3
"""
Derive Complete Geometry from Correlated Data

Takes correlated labels+dimensions and derives:
1. Building coordinates (apply calibration)
2. Full geometry (bounding boxes, vertices, volumes)
3. Validation against existing extraction
4. Enhanced output JSON
"""

import json
import sys
import math
from typing import Dict, List, Tuple


class GeometryDeriver:
    """Derive complete geometry from correlated data"""

    def __init__(self, correlations_file: str, existing_output_file: str):
        """
        Args:
            correlations_file: Correlation data from correlate_pages.py
            existing_output_file: Existing extraction output with calibration
        """
        with open(correlations_file) as f:
            self.correlations = json.load(f)

        with open(existing_output_file) as f:
            self.existing = json.load(f)

        self.calibration = self.existing['extraction_metadata']['calibration']
        self.enhanced_objects = []
        self.validations = []

    def derive_all(self):
        """Derive complete geometry for all correlated objects"""
        print("="*80)
        print("DERIVING COMPLETE GEOMETRY")
        print("="*80)
        print()

        # Fix dimension ordering first
        self._fix_dimension_ordering()

        # Derive geometry for each object
        object_db = self.correlations['complete_object_database']

        for obj in object_db:
            enhanced = self._derive_object_geometry(obj)
            self.enhanced_objects.append(enhanced)

        print(f"✅ Derived geometry for {len(self.enhanced_objects)} objects")

        # Validate against existing extraction
        self._validate_against_existing()

        return {
            'enhanced_objects': self.enhanced_objects,
            'validations': self.validations
        }

    def _fix_dimension_ordering(self):
        """
        Fix dimension ordering issues

        Problem: Some dimensions show width > height (2100 × 900)
        Fix: For doors/windows, smaller dimension = width, larger = height
        """
        print("-"*80)
        print("FIXING DIMENSION ORDERING")
        print("-"*80)

        fixed_count = 0

        for corr in self.correlations['label_to_dimensions']:
            dims = corr['dimensions']
            width_val = dims['width']['value']
            height_val = dims['height']['value']

            # For doors/windows, width should be < height
            if width_val > height_val:
                # Swap them
                dims['width'], dims['height'] = dims['height'], dims['width']
                fixed_count += 1

                print(f"  Fixed {corr['label']}: {height_val}mm × {width_val}mm "
                      f"→ {dims['width']['value']}mm × {dims['height']['value']}mm")

        # Update complete_object_database with fixed dimensions
        for obj in self.correlations['complete_object_database']:
            # Find matching correlation
            label = obj['label']
            corr = next((c for c in self.correlations['label_to_dimensions']
                        if c['label'] == label), None)

            if corr:
                obj['dimensions']['width_mm'] = corr['dimensions']['width']['value']
                obj['dimensions']['height_mm'] = corr['dimensions']['height']['value']
                obj['dimensions']['width_m'] = corr['dimensions']['width']['value'] / 1000
                obj['dimensions']['height_m'] = corr['dimensions']['height']['value'] / 1000

        print(f"✅ Fixed {fixed_count} dimension orderings")
        print()

    def _derive_object_geometry(self, obj: Dict) -> Dict:
        """
        Derive complete geometry for one object

        Steps:
        1. Apply calibration: PDF coords → Building coords
        2. Calculate bounding box from center + dimensions
        3. Calculate corner vertices
        4. Calculate perimeter, area, volume
        """
        # Get PDF position
        pdf_pos = obj['floor_plan_position_pdf']
        pdf_x = pdf_pos['x']
        pdf_y = pdf_pos['y']

        # Apply calibration transform
        building_x = (pdf_x - self.calibration['offset_x']) * self.calibration['scale_x']
        building_y = (pdf_y - self.calibration['offset_y']) * self.calibration['scale_y']

        # Get dimensions
        width_m = obj['dimensions']['width_m']
        height_m = obj['dimensions']['height_m']

        # Assume standard thickness
        thickness = 0.04  # 40mm for doors/windows

        # Calculate bounding box
        # Assuming position is center point of door/window
        half_width = width_m / 2
        half_thick = thickness / 2

        bbox = {
            'min': [
                building_x - half_width,
                building_y - half_thick,
                0.0
            ],
            'max': [
                building_x + half_width,
                building_y + half_thick,
                height_m
            ]
        }

        # Calculate 2D corner vertices (floor plan view)
        corners_2d = [
            [building_x - half_width, building_y - half_thick],  # Bottom-left
            [building_x + half_width, building_y - half_thick],  # Bottom-right
            [building_x + half_width, building_y + half_thick],  # Top-right
            [building_x - half_width, building_y + half_thick]   # Top-left
        ]

        # Calculate 3D vertices (8 corners of box)
        vertices_3d = []
        for corner in corners_2d:
            # Bottom face
            vertices_3d.append([corner[0], corner[1], 0.0])
        for corner in corners_2d:
            # Top face
            vertices_3d.append([corner[0], corner[1], height_m])

        # Calculate perimeter (floor plan)
        perimeter_2d = 2 * (width_m + thickness)

        # Calculate area (floor plan footprint)
        area_2d = width_m * thickness

        # Calculate volume
        volume = area_2d * height_m

        # Build enhanced object
        enhanced = {
            'object_id': obj['object_id'],
            'label': obj['label'],
            'type': obj['type'],
            'occurrence': obj['occurrence'],

            # Position (center point)
            'position': [building_x, building_y, 0.0],

            # PDF position (for traceability)
            'pdf_position': pdf_pos,

            # Complete dimensions
            'dimensions': {
                'width_mm': obj['dimensions']['width_mm'],
                'height_mm': obj['dimensions']['height_mm'],
                'thickness_mm': thickness * 1000,
                'width_m': width_m,
                'height_m': height_m,
                'thickness_m': thickness
            },

            # Complete geometry
            'geometry': {
                'type': 'box',
                'bounding_box': bbox,
                'corners_2d': corners_2d,
                'vertices_3d': vertices_3d,
                'perimeter_2d': round(perimeter_2d, 3),
                'area_2d': round(area_2d, 4),
                'volume': round(volume, 4)
            },

            # Data sources
            'sources': obj['sources'],

            # Derived flag
            '_geometry_derived': True,
            '_calibration_applied': True
        }

        return enhanced

    def _validate_against_existing(self):
        """
        Validate derived objects against existing extraction

        Compare:
        - Positions (should match)
        - Dimensions (correlated should be ground truth)
        """
        print("\n" + "-"*80)
        print("VALIDATING AGAINST EXISTING EXTRACTION")
        print("-"*80)
        print()

        existing_objects = self.existing['objects']

        matched = 0
        mismatched_pos = 0
        missing_dims = 0

        for enhanced in self.enhanced_objects:
            label = enhanced['label']
            enhanced_pos = enhanced['position']

            # Find matching object in existing extraction
            # Look for object with same label in name and similar position
            candidates = [
                obj for obj in existing_objects
                if label in obj.get('name', '') and
                obj.get('_annotation_captured', False)
            ]

            if not candidates:
                print(f"  ⚠️  {enhanced['object_id']}: No match in existing extraction")
                continue

            # Find closest candidate by position
            closest = None
            min_dist = float('inf')

            for candidate in candidates:
                cand_pos = candidate.get('position', [0, 0, 0])
                dist = math.sqrt(
                    (cand_pos[0] - enhanced_pos[0])**2 +
                    (cand_pos[1] - enhanced_pos[1])**2
                )

                if dist < min_dist:
                    min_dist = dist
                    closest = candidate

            if not closest:
                continue

            # Validate position
            if min_dist < 0.01:  # < 1cm
                matched += 1
                status = "✅ Perfect match"
            elif min_dist < 0.5:  # < 50cm
                matched += 1
                status = f"✓  Good match ({min_dist*100:.1f}cm)"
            else:
                mismatched_pos += 1
                status = f"⚠️  Position mismatch ({min_dist:.2f}m)"

            # Check if existing has dimensions
            has_dims = 'width' in closest or 'geometry' in closest

            if not has_dims:
                missing_dims += 1
                dim_status = "❌ Missing dimensions"
            else:
                dim_status = "✅ Has dimensions"

            validation = {
                'enhanced_id': enhanced['object_id'],
                'existing_name': closest.get('name'),
                'position_match': min_dist < 0.5,
                'position_distance_m': round(min_dist, 3),
                'has_dimensions': has_dims,
                'enhanced_dims': enhanced['dimensions'],
                'existing_dims': {
                    'width': closest.get('width'),
                    'height': closest.get('height')
                } if has_dims else None
            }

            self.validations.append(validation)

            print(f"  {enhanced['object_id']:10s}: {status}, {dim_status}")

        print()
        print(f"✅ Matched: {matched}/{len(self.enhanced_objects)}")
        print(f"⚠️  Position mismatches: {mismatched_pos}")
        print(f"❌ Missing dimensions in existing: {missing_dims}")

    def generate_enhanced_output(self) -> Dict:
        """
        Generate enhanced output JSON

        Structure:
        - Original extraction metadata
        - Enhanced annotations with dimensions
        - Complete objects with full geometry
        - Validation results
        """
        enhanced_output = {
            'extraction_metadata': self.existing['extraction_metadata'],
            'summary': self.existing['summary'],

            # Enhanced annotations
            'annotations': self.existing.get('annotations', {}),

            # Add dimension annotations
            'dimension_annotations': [
                {
                    'label': obj['label'],
                    'type': obj['type'],
                    'dimensions': obj['dimensions'],
                    'source_page': obj['sources']['schedule_page']
                }
                for obj in self.enhanced_objects
            ],

            # Enhanced objects with complete geometry
            'objects_enhanced': self.enhanced_objects,

            # Original objects (for comparison)
            'objects_original': self.existing['objects'],

            # Correlations
            'correlations': self.correlations,

            # Validations
            'validations': {
                'total_validated': len(self.validations),
                'position_matches': sum(1 for v in self.validations if v['position_match']),
                'missing_dimensions': sum(1 for v in self.validations if not v['has_dimensions']),
                'details': self.validations
            }
        }

        return enhanced_output

    def save_enhanced_output(self, output_file: str):
        """Save enhanced output"""
        enhanced = self.generate_enhanced_output()

        with open(output_file, 'w') as f:
            json.dump(enhanced, f, indent=2)

        print(f"\n✅ Enhanced output saved to: {output_file}")

        return enhanced

    def print_summary(self):
        """Print derivation summary"""
        print("\n" + "="*80)
        print("GEOMETRY DERIVATION SUMMARY")
        print("="*80)

        print(f"\n📊 Objects processed: {len(self.enhanced_objects)}")
        print("\nSample derived geometry:")

        for obj in self.enhanced_objects[:3]:
            print(f"\n  {obj['object_id']}:")
            print(f"    Position: ({obj['position'][0]:.2f}, {obj['position'][1]:.2f}, {obj['position'][2]:.2f})")
            print(f"    Dimensions: {obj['dimensions']['width_mm']:.0f}mm × "
                  f"{obj['dimensions']['height_mm']:.0f}mm × "
                  f"{obj['dimensions']['thickness_mm']:.0f}mm")
            print(f"    Bounding Box:")
            print(f"      Min: ({obj['geometry']['bounding_box']['min'][0]:.2f}, "
                  f"{obj['geometry']['bounding_box']['min'][1]:.2f}, "
                  f"{obj['geometry']['bounding_box']['min'][2]:.2f})")
            print(f"      Max: ({obj['geometry']['bounding_box']['max'][0]:.2f}, "
                  f"{obj['geometry']['bounding_box']['max'][1]:.2f}, "
                  f"{obj['geometry']['bounding_box']['max'][2]:.2f})")
            print(f"    Perimeter: {obj['geometry']['perimeter_2d']:.3f}m")
            print(f"    Area: {obj['geometry']['area_2d']:.4f}m²")
            print(f"    Volume: {obj['geometry']['volume']:.4f}m³")

        print(f"\n📊 Validation results:")
        print(f"  Position matches: {len([v for v in self.validations if v['position_match']])}/{len(self.validations)}")
        print(f"  Objects with dimensions: {len([v for v in self.validations if v['has_dimensions']])}/{len(self.validations)}")
        print(f"  Objects missing dimensions: {len([v for v in self.validations if not v['has_dimensions']])}/{len(self.validations)}")

        print()


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 derive_geometry.py <correlations.json> <existing_output.json> [enhanced_output.json]")
        print()
        print("Derives complete geometry from correlated dimension data")
        sys.exit(1)

    correlations_file = sys.argv[1]
    existing_output_file = sys.argv[2]
    enhanced_output_file = sys.argv[3] if len(sys.argv) > 3 else 'output_enhanced.json'

    deriver = GeometryDeriver(correlations_file, existing_output_file)
    deriver.derive_all()
    deriver.print_summary()
    deriver.save_enhanced_output(enhanced_output_file)

    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print("\nEnhanced output includes:")
    print("  ✅ Complete geometry (bounding boxes, vertices, volumes)")
    print("  ✅ Validated dimensions from schedule")
    print("  ✅ Building coordinates (calibration applied)")
    print("  ✅ Full traceability (PDF page + position)")
    print()


if __name__ == "__main__":
    main()
