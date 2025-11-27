#!/usr/bin/env python3
"""
Systematic Page Correlation

Correlates data across pages to build complete object database:
- Page 1 (floor plan) labels → Page 8 (schedule) dimensions
- Grid references across all pages
- Elevations → floor plan heights
"""

import json
import sys
from typing import Dict, List, Tuple


class PageCorrelator:
    """Systematically correlate data across pages"""

    def __init__(self, pages_data_file: str):
        with open(pages_data_file) as f:
            data = json.load(f)
            self.pages = data['pages']

        self.correlations = {
            'label_to_dimensions': [],
            'grid_references': [],
            'cross_page_objects': [],
            'complete_object_database': []
        }

    def correlate_all(self):
        """Run all correlation analyses"""
        print("="*80)
        print("SYSTEMATIC CORRELATION")
        print("="*80)
        print()

        self.correlate_labels_to_dimensions()
        self.correlate_grid_references()
        self.build_complete_object_database()

        return self.correlations

    def correlate_labels_to_dimensions(self):
        """
        Match floor plan labels (Page 1) to schedule dimensions (Page 8)

        Strategy:
        1. Extract D1, D2, D3, W1, W2, W3 labels from Page 1
        2. Extract dimensions from Page 8 schedule
        3. Match by X coordinate proximity (same column)
        """
        print("-"*80)
        print("CORRELATION 1: Floor Plan Labels → Schedule Dimensions")
        print("-"*80)

        # Get Page 1 (floor plan)
        page1 = self.pages[0]
        floor_plan_labels = page1['numbers']['labels']

        # Get Page 8 (schedule)
        page8 = self.pages[7]
        schedule_labels = page8['numbers']['labels']
        schedule_dimensions = page8['numbers']['dimensions']

        # For each schedule label (D1, D2, D3, W1, W2, W3)
        for sched_label in schedule_labels:
            label_text = sched_label['text']
            label_x = sched_label['position']['x']
            label_y = sched_label['position']['y']

            # Find dimensions in same column (within 150px X range)
            column_dimensions = []
            for dim in schedule_dimensions:
                dim_x = dim['position']['x']
                # Check if dimension is in same column (label X ± 75px)
                if abs(dim_x - label_x) < 150:
                    column_dimensions.append(dim)

            # Sort by Y coordinate (top to bottom)
            column_dimensions.sort(key=lambda d: d['position']['y'])

            # Pair dimensions (assume width × height)
            if len(column_dimensions) >= 2:
                width = column_dimensions[0]
                height = column_dimensions[1]

                # Find corresponding floor plan labels
                floor_labels = [
                    fl for fl in floor_plan_labels
                    if fl['text'] == label_text
                ]

                correlation = {
                    'label': label_text,
                    'type': sched_label['type'],
                    'schedule_page': 8,
                    'floor_plan_page': 1,
                    'floor_plan_occurrences': len(floor_labels),
                    'floor_plan_positions': [
                        fl['position'] for fl in floor_labels
                    ],
                    'dimensions': {
                        'width': {
                            'value': width['value'],
                            'unit': width['unit'],
                            'text': width['text']
                        },
                        'height': {
                            'value': height['value'],
                            'unit': height['unit'],
                            'text': height['text']
                        }
                    },
                    'schedule_position': sched_label['position']
                }

                self.correlations['label_to_dimensions'].append(correlation)

                print(f"\n✅ {label_text} ({sched_label['type']}):")
                print(f"   Schedule (Page 8): {width['text']} × {height['text']}")
                print(f"   Floor plan (Page 1): {len(floor_labels)} occurrences")
                for i, pos in enumerate(correlation['floor_plan_positions'], 1):
                    print(f"     {i}. @ ({pos['x']:.1f}, {pos['y']:.1f})")

        print(f"\n✅ Total correlations: {len(self.correlations['label_to_dimensions'])}")

    def correlate_grid_references(self):
        """
        Correlate grid references across pages

        Grid references (1-5) appear on multiple pages
        Track which pages have which grid refs
        """
        print("\n" + "-"*80)
        print("CORRELATION 2: Grid References Across Pages")
        print("-"*80)

        grid_map = {}

        for page in self.pages:
            page_num = page['page_number']
            grid_refs = page['numbers']['grid_refs']

            for ref in grid_refs:
                ref_value = ref['value']
                if ref_value not in grid_map:
                    grid_map[ref_value] = []

                grid_map[ref_value].append({
                    'page': page_num,
                    'position': ref['position']
                })

        self.correlations['grid_references'] = grid_map

        print()
        for grid_num in sorted(grid_map.keys()):
            pages_with_grid = set([entry['page'] for entry in grid_map[grid_num]])
            print(f"Grid {grid_num}: appears on pages {sorted(pages_with_grid)}")

    def build_complete_object_database(self):
        """
        Build complete object database with all attributes

        For each door/window:
        - Label (D1, D2, etc.)
        - Type (door/window)
        - Dimensions from schedule (width × height)
        - Floor plan positions (x, y on Page 1)
        - Occurrence count
        """
        print("\n" + "-"*80)
        print("BUILDING COMPLETE OBJECT DATABASE")
        print("-"*80)

        object_db = []

        for corr in self.correlations['label_to_dimensions']:
            # Create object entry for each floor plan occurrence
            for idx, fp_pos in enumerate(corr['floor_plan_positions'], 1):
                obj = {
                    'object_id': f"{corr['label']}_{idx}",
                    'label': corr['label'],
                    'type': corr['type'],
                    'occurrence': f"{idx}/{corr['floor_plan_occurrences']}",

                    # From schedule
                    'dimensions': {
                        'width_mm': corr['dimensions']['width']['value'],
                        'height_mm': corr['dimensions']['height']['value'],
                        'width_m': corr['dimensions']['width']['value'] / 1000,
                        'height_m': corr['dimensions']['height']['value'] / 1000
                    },

                    # From floor plan
                    'floor_plan_position_pdf': fp_pos,

                    # Data sources
                    'sources': {
                        'floor_plan_page': corr['floor_plan_page'],
                        'schedule_page': corr['schedule_page']
                    },

                    # Placeholder for building coordinates (needs calibration)
                    'building_position': None,

                    # Placeholder for full geometry (to be calculated)
                    'geometry': None
                }

                object_db.append(obj)

        self.correlations['complete_object_database'] = object_db

        print(f"\n✅ Complete object database: {len(object_db)} objects")
        print("\nSample objects:")
        for obj in object_db[:5]:
            print(f"  {obj['object_id']:10s} - {obj['type']:6s} - "
                  f"{obj['dimensions']['width_mm']:.0f}mm × {obj['dimensions']['height_mm']:.0f}mm - "
                  f"@ ({obj['floor_plan_position_pdf']['x']:.1f}, {obj['floor_plan_position_pdf']['y']:.1f})")

    def save_correlations(self, output_file: str):
        """Save correlation results"""
        with open(output_file, 'w') as f:
            json.dump(self.correlations, f, indent=2)

        print(f"\n\n✅ Correlations saved to: {output_file}")

    def generate_correlation_report(self):
        """Generate human-readable correlation report"""
        print("\n" + "="*80)
        print("CORRELATION REPORT")
        print("="*80)

        # Label to Dimensions
        print(f"\n📊 Label → Dimension Correlations: {len(self.correlations['label_to_dimensions'])}")
        print("\nDoors:")
        for corr in self.correlations['label_to_dimensions']:
            if corr['type'] == 'door':
                w = corr['dimensions']['width']['value']
                h = corr['dimensions']['height']['value']
                occ = corr['floor_plan_occurrences']
                print(f"  {corr['label']}: {w:.0f}mm × {h:.0f}mm ({occ} occurrences on floor plan)")

        print("\nWindows:")
        for corr in self.correlations['label_to_dimensions']:
            if corr['type'] == 'window':
                w = corr['dimensions']['width']['value']
                h = corr['dimensions']['height']['value']
                occ = corr['floor_plan_occurrences']
                print(f"  {corr['label']}: {w:.0f}mm × {h:.0f}mm ({occ} occurrences on floor plan)")

        # Grid references
        print(f"\n📊 Grid References: {len(self.correlations['grid_references'])} unique grids")

        # Complete database
        print(f"\n📊 Complete Object Database: {len(self.correlations['complete_object_database'])} objects")
        print("  Ready for:")
        print("    - Building coordinate transformation (apply calibration)")
        print("    - Full geometry calculation (bounding boxes, vertices)")
        print("    - Relationship mapping (door → wall, object → room)")

        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 correlate_pages.py <pages_data.json> [output.json]")
        print()
        print("Systematically correlates data across pages")
        print("Builds complete object database with matched dimensions")
        sys.exit(1)

    pages_data_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'correlations.json'

    correlator = PageCorrelator(pages_data_file)
    correlator.correlate_all()
    correlator.generate_correlation_report()
    correlator.save_correlations(output_file)

    print("\n" + "="*80)
    print("NEXT STEP: DERIVE COMPLETE GEOMETRY")
    print("="*80)
    print("\nNow that we have correlated data, we can:")
    print("1. Apply calibration to PDF positions → Building coordinates")
    print("2. Calculate full geometry (width × height → bounding boxes)")
    print("3. Build relationships (match objects to walls, rooms)")
    print("4. Generate final enhanced output JSON")
    print()


if __name__ == "__main__":
    main()
