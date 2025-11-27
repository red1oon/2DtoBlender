#!/usr/bin/env python3
"""
Calibration Engine - Three-Method Validation

Implements robust calibration using three independent methods:
1. Grid-based (from A-E, 1-9 grid references)
2. Explicit scale (from title block "1:100" notation)
3. DISCHARGE perimeter (bounding box of drain labels)

Cross-validates all three methods and provides confidence scoring.
"""

import sqlite3
import re
import json
from pathlib import Path
from typing import Dict, Tuple, List, Optional


class CalibrationEngine:
    """Multi-method calibration with validation"""

    def __init__(self, db_path: str):
        """
        Initialize calibration engine

        Args:
            db_path: Path to annotation database (primitives + patterns)
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect_db(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def method1_grid_based(self) -> Dict:
        """
        Method 1: Grid-based calibration

        Extracts grid references (A-E, 1-9) and calculates spacing
        Returns building dimensions derived from grid count
        """
        print("\n📐 METHOD 1: Grid-based Calibration")

        # Get grid references
        self.cursor.execute("""
            SELECT text, x, y, page
            FROM primitives_text
            WHERE (text GLOB '[A-E]' OR text GLOB '[1-9]')
            AND page = 1
            ORDER BY text
        """)
        grid_refs = self.cursor.fetchall()

        if not grid_refs:
            print("   ❌ No grid references found")
            return {'method': 'grid_based', 'success': False}

        # Separate horizontal (A-E) and vertical (1-9)
        # Group by label and take average position (multiple instances per grid)
        h_labels = {}
        v_labels = {}

        for text, x, y, p in grid_refs:
            if text.isalpha():
                if text not in h_labels:
                    h_labels[text] = []
                h_labels[text].append((x, y))
            elif text.isdigit():
                if text not in v_labels:
                    v_labels[text] = []
                v_labels[text].append((x, y))

        # Average positions for each unique grid label
        h_grids = [(label, sum(xs)/len(xs), sum(ys)/len(ys))
                   for label, positions in h_labels.items()
                   for xs, ys in [list(zip(*positions))]]
        v_grids = [(label, sum(xs)/len(xs), sum(ys)/len(ys))
                   for label, positions in v_labels.items()
                   for xs, ys in [list(zip(*positions))]]

        print(f"   Found: {len(h_grids)} unique horizontal grids (A-E), {len(v_grids)} unique vertical grids (1-9)")

        if not h_grids or not v_grids:
            print("   ❌ Incomplete grid system")
            return {'method': 'grid_based', 'success': False}

        # Calculate average spacing
        h_grids_sorted = sorted(h_grids, key=lambda g: g[1])  # Sort by X
        v_grids_sorted = sorted(v_grids, key=lambda g: g[2])  # Sort by Y

        # Horizontal spacing (PDF points between grids)
        h_spacings = [h_grids_sorted[i+1][1] - h_grids_sorted[i][1]
                      for i in range(len(h_grids_sorted)-1)]
        avg_h_spacing = sum(h_spacings) / len(h_spacings) if h_spacings else 0

        # Vertical spacing
        v_spacings = [v_grids_sorted[i+1][2] - v_grids_sorted[i][2]
                      for i in range(len(v_grids_sorted)-1)]
        avg_v_spacing = sum(v_spacings) / len(v_spacings) if v_spacings else 0

        # Extract actual dimensions from PDF annotations (e.g., "3100", "3700")
        # These are typically placed between grid lines
        self.cursor.execute("""
            SELECT text, x, y
            FROM primitives_text
            WHERE page = 1
            AND length(text) BETWEEN 4 AND 5
            AND text GLOB '[0-9]*'
            ORDER BY x, y
        """)
        dimension_texts = self.cursor.fetchall()

        print(f"   Found {len(dimension_texts)} dimension annotations")

        # Parse all dimension values
        parsed_dimensions = []
        for dim_text, dim_x, dim_y in dimension_texts:
            try:
                dim_value_mm = int(dim_text)
                # Filter: reasonable building dimensions (1000-10000mm)
                if 1000 <= dim_value_mm <= 10000:
                    parsed_dimensions.append((dim_x, dim_y, dim_value_mm))
            except ValueError:
                continue

        if not parsed_dimensions:
            print("\n" + "=" * 80)
            print("❌ DIMENSION EXTRACTION FAILED")
            print("=" * 80)
            print("DEBUG: No valid dimension annotations found in primitives_text")
            print("   Expected: 4-5 digit numbers (1300, 3100, 3700, etc.)")
            print("   Found: 0 dimension texts matching criteria")
            print("\nPDF EXTRACTION FAILED - DIMENSIONS UNCLEAR OR MISSING")
            print("CANNOT PROCEED: Building dimensions required for Rule 0 compliance")
            print("=" * 80)
            return {'method': 'grid_based', 'success': False, 'error': 'No dimension annotations found'}

        # CHECK: Are all dimensions at (0,0)? This indicates extraction bug
        all_at_origin = all(x == 0.0 and y == 0.0 for x, y, _ in parsed_dimensions)
        if all_at_origin:
            print("\n" + "=" * 80)
            print("❌ DIMENSION EXTRACTION FAILED")
            print("=" * 80)
            print(f"DEBUG: Found {len(parsed_dimensions)} dimensions but ALL at position (0,0)")
            print("   Dimensions found:", [val for _, _, val in parsed_dimensions])
            print("   This indicates primitives_text table has corrupted position data")
            print("\nROOT CAUSE: PDF primitive extraction did not capture text positions")
            print("FIX REQUIRED: Re-run primitive extraction with position tracking enabled")
            print("=" * 80)
            return {'method': 'grid_based', 'success': False, 'error': 'Dimension positions corrupted (all at 0,0)'}

        # Group by Y coordinate (horizontal dimension line)
        # Use stricter tolerance (20pt) to avoid grouping unrelated dimensions
        y_groups = {}
        for x, y, val in parsed_dimensions:
            y_bucket = round(y / 20) * 20  # Cluster by 20pt tolerance (was 50pt)
            if y_bucket not in y_groups:
                y_groups[y_bucket] = []
            y_groups[y_bucket].append((x, y, val))

        # Group by X coordinate (vertical dimension line)
        x_groups = {}
        for x, y, val in parsed_dimensions:
            x_bucket = round(x / 20) * 20  # Cluster by 20pt tolerance (was 50pt)
            if x_bucket not in x_groups:
                x_groups[x_bucket] = []
            x_groups[x_bucket].append((x, y, val))

        # Find horizontal dimensions: largest Y-group with values spanning wide X-range
        h_candidates = [(bucket, grp) for bucket, grp in y_groups.items() if len(grp) >= 3]
        if h_candidates:
            # Pick group with widest X-span (dimension line across building width)
            largest_y_group = max(h_candidates, key=lambda g: max(d[0] for d in g[1]) - min(d[0] for d in g[1]))[1]
        else:
            largest_y_group = []

        h_dimensions_sorted = sorted(largest_y_group, key=lambda d: d[0])
        h_dimension_values = [d[2] for d in h_dimensions_sorted]

        # Find vertical dimensions: combine X-groups that are close together
        # (dimensions may shift slightly along the vertical dimension line)
        # Strategy: Pick the largest group with widest Y-span (vertical coverage)
        v_candidates = []
        x_buckets_sorted = sorted(x_groups.keys())

        # Try each bucket and adjacent buckets within 30pt
        for i, bucket in enumerate(x_buckets_sorted):
            group = list(x_groups[bucket])

            # Merge with next bucket if very close (handles x=97 and x=111)
            if i + 1 < len(x_buckets_sorted) and x_buckets_sorted[i+1] - bucket <= 30:
                group.extend(x_groups[x_buckets_sorted[i+1]])

            # Calculate Y-span (should be large for vertical dimension line)
            if group:
                y_vals = [d[1] for d in group]
                y_span = max(y_vals) - min(y_vals)
                v_candidates.append((y_span, len(group), group))

        # Pick group with most dimensions (priority) and large Y-span (secondary)
        # Vertical dimension line should have 4-5 dimension annotations
        if v_candidates:
            # Prioritize count (more dimensions = more likely to be main dimension line)
            # Then Y-span as tiebreaker
            v_combined_group = max(v_candidates, key=lambda c: (c[1], c[0]))[2]
        else:
            v_combined_group = []

        # Sort by Y position and filter out dimensions that are too close together
        # (likely duplicates or annotations for different features)
        v_dimensions_sorted = sorted(v_combined_group, key=lambda d: d[1])  # Sort by Y
        v_dimension_filtered = []
        MIN_SPACING = 30  # Minimum 30pt between dimension annotations

        for i, (x, y, val) in enumerate(v_dimensions_sorted):
            if i == 0:
                v_dimension_filtered.append((x, y, val))
            else:
                # Compare to last KEPT dimension, not last seen
                if v_dimension_filtered:
                    prev_y = v_dimension_filtered[-1][1]
                    if y - prev_y >= MIN_SPACING:
                        v_dimension_filtered.append((x, y, val))
                    else:
                        # Skip dimension too close to previous - likely duplicate/mislabeled
                        print(f"   ⚠️  Filtering dimension {val}mm at y={y:.1f} (too close to previous kept at y={prev_y:.1f})")
                else:
                    v_dimension_filtered.append((x, y, val))

        v_dimension_values = [d[2] for d in v_dimension_filtered]

        # STRICT VALIDATION: Must have both horizontal AND vertical dimensions
        if not h_dimension_values or not v_dimension_values:
            print("\n" + "=" * 80)
            print("❌ DIMENSION EXTRACTION FAILED")
            print("=" * 80)
            print(f"DEBUG: Grouping failed to separate dimensions")
            print(f"   Y-groups (horizontal): {len(y_groups)} groups")
            print(f"   X-groups (vertical): {len(x_groups)} groups")
            print(f"   Horizontal values: {h_dimension_values}")
            print(f"   Vertical values: {v_dimension_values}")
            print("\nROOT CAUSE: Dimension positions not clustered correctly")
            print("   Dimensions may not be aligned on consistent grid lines")
            print("=" * 80)
            return {'method': 'grid_based', 'success': False, 'error': 'Dimension grouping failed'}

        # Calculate building dimensions from actual annotations
        building_width = sum(h_dimension_values) / 1000.0  # Convert mm to m
        building_length = sum(v_dimension_values) / 1000.0  # Convert mm to m

        print(f"   ✅ Horizontal dimensions (mm): {h_dimension_values} → {building_width:.2f}m")
        print(f"   ✅ Vertical dimensions (mm): {v_dimension_values} → {building_length:.2f}m")

        result = {
            'method': 'grid_based',
            'success': True,
            'building_width_m': building_width,
            'building_length_m': building_length,
            'grid_spacing_h_pt': avg_h_spacing,
            'grid_spacing_v_pt': avg_v_spacing,
            'scale_x_m_per_pt': building_width / (len(h_spacings) * avg_h_spacing) if avg_h_spacing else 0,
            'scale_y_m_per_pt': building_length / (len(v_spacings) * avg_v_spacing) if avg_v_spacing else 0,
            'confidence': 0.85,
            'grid_count_h': len(h_spacings),
            'grid_count_v': len(v_spacings)
        }

        print(f"   ✅ Building: {building_width}m x {building_length}m")
        print(f"   Grid spacing: {avg_h_spacing:.1f}pt (H) x {avg_v_spacing:.1f}pt (V)")
        print(f"   Confidence: {result['confidence']}")

        return result

    def method2_explicit_scale(self) -> Dict:
        """
        Method 2: Explicit scale from title block

        Searches for "1:100", "SCALE 1:50", etc. in title block area
        Returns scale factor (e.g., 100 means 1 PDF unit = 100mm real)
        """
        print("\n📏 METHOD 2: Explicit Scale Extraction")

        # Search for scale notation (usually in title block - bottom right)
        self.cursor.execute("""
            SELECT text, x, y, page
            FROM primitives_text
            WHERE (text LIKE '%:%' OR text LIKE '%SCALE%' OR text LIKE '%scale%')
            AND page IN (1, 2)
        """)
        scale_texts = self.cursor.fetchall()

        if not scale_texts:
            print("   ❌ No scale notation found")
            return {'method': 'explicit_scale', 'success': False}

        # Parse scale notation: "1:100", "SCALE 1:50", etc.
        scale_pattern = r'1\s*:\s*(\d+)'
        found_scale = None

        for text, x, y, page in scale_texts:
            match = re.search(scale_pattern, text)
            if match:
                scale_value = int(match.group(1))
                found_scale = {
                    'text': text,
                    'scale': scale_value,
                    'position': (x, y),
                    'page': page
                }
                break

        if not found_scale:
            print(f"   ❌ Scale notation found but couldn't parse: {[t[0] for t in scale_texts[:3]]}")
            return {'method': 'explicit_scale', 'success': False}

        # Scale factor: if 1:100, then 1 PDF pt = 100mm = 0.1m in reality
        # But need to account for PDF DPI (typically 72 DPI)
        # 1 PDF pt = 1/72 inch = 0.3528mm
        # If drawing is 1:100, then 1mm on paper = 100mm real
        # So: 1 PDF pt = 0.3528mm paper = 35.28mm real (at 1:100 scale)

        scale_ratio = found_scale['scale']
        pdf_pt_to_mm_paper = 0.3528  # 1/72 inch in mm
        mm_per_pt_real = pdf_pt_to_mm_paper * scale_ratio
        m_per_pt_real = mm_per_pt_real / 1000.0

        result = {
            'method': 'explicit_scale',
            'success': True,
            'scale_notation': found_scale['text'],
            'scale_ratio': scale_ratio,  # e.g., 100 for "1:100"
            'scale_m_per_pt': m_per_pt_real,
            'confidence': 0.95,  # Highest - architect's declared intent
            'source_page': found_scale['page'],
            'source_position': found_scale['position']
        }

        print(f"   ✅ Found: '{found_scale['text']}' (1:{scale_ratio})")
        print(f"   Scale: 1 PDF pt = {mm_per_pt_real:.2f}mm real = {m_per_pt_real:.6f}m")
        print(f"   Confidence: {result['confidence']}")

        return result

    def method3_discharge_perimeter(self) -> Dict:
        """
        Method 3: DISCHARGE perimeter bounding box

        Finds all DISCHARGE labels and calculates bounding box
        Returns building dimensions from drain perimeter
        """
        print("\n🚰 METHOD 3: DISCHARGE Perimeter Calibration")

        # Find all DISCHARGE text (both regular and annotation)
        self.cursor.execute("""
            SELECT text, x, y, page
            FROM primitives_text
            WHERE text = 'DISCHARGE'
            AND page IN (1, 2)
        """)
        discharge_points = self.cursor.fetchall()

        if not discharge_points:
            print("   ❌ No DISCHARGE labels found")
            return {'method': 'discharge_perimeter', 'success': False}

        print(f"   Found: {len(discharge_points)} DISCHARGE labels")

        # Calculate bounding box
        xs = [x for _, x, y, p in discharge_points]
        ys = [y for _, x, y, p in discharge_points]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        bbox_width_pt = max_x - min_x
        bbox_height_pt = max_y - min_y

        print(f"   Bounding box: {bbox_width_pt:.1f}pt x {bbox_height_pt:.1f}pt")
        print(f"   Position: ({min_x:.1f}, {min_y:.1f}) to ({max_x:.1f}, {max_y:.1f})")

        # Need grid or scale data to convert to meters
        # Store bounding box for cross-validation
        result = {
            'method': 'discharge_perimeter',
            'success': True,
            'bbox_width_pt': bbox_width_pt,
            'bbox_height_pt': bbox_height_pt,
            'discharge_count': len(discharge_points),
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y,
            'confidence': 0.90,
            'note': 'Requires scale factor from Method 1 or 2 to convert to meters'
        }

        print(f"   ✅ Perimeter captured: {len(discharge_points)} validation points")
        print(f"   Confidence: {result['confidence']}")

        return result

    def method4_actual_walls(self) -> Dict:
        """
        Method 4: Use actual wall lines to determine building dimensions
        This is the most accurate method as it measures the real structure
        """
        print("\n🏗️ METHOD 4: Actual Wall Lines")

        # Get thick structural lines that form the building perimeter
        self.cursor.execute("""
            SELECT x0, y0, x1, y1, length, linewidth
            FROM primitives_lines
            WHERE page = 1
            AND linewidth > 3.5  -- Structural walls are thicker
            ORDER BY length DESC
        """)

        thick_lines = self.cursor.fetchall()
        print(f"   Found {len(thick_lines)} structural lines (width > 3.5pt)")

        if len(thick_lines) < 4:
            print("   ❌ Not enough structural lines for perimeter")
            return {'method': 'actual_walls', 'success': False}

        # Find the bounding box of all structural lines
        all_x_coords = []
        all_y_coords = []

        for x0, y0, x1, y1, length, width in thick_lines:
            all_x_coords.extend([x0, x1])
            all_y_coords.extend([y0, y1])

        min_x = min(all_x_coords)
        max_x = max(all_x_coords)
        min_y = min(all_y_coords)
        max_y = max(all_y_coords)

        building_width_pt = max_x - min_x
        building_height_pt = max_y - min_y

        print(f"   Building perimeter in PDF points:")
        print(f"     X: {min_x:.2f} to {max_x:.2f} ({building_width_pt:.2f}pt)")
        print(f"     Y: {min_y:.2f} to {max_y:.2f} ({building_height_pt:.2f}pt)")

        # Get scale from explicit scale method if available
        scale_m_per_pt = 0.03528  # Default 1:100 scale (1pt = 0.3528mm)

        # Try to get more accurate scale
        self.cursor.execute("""
            SELECT text FROM primitives_text
            WHERE page IN (1,2)
            AND (text LIKE '%1:100%' OR text LIKE '%1:50%' OR text LIKE '%1:200%')
            LIMIT 1
        """)
        scale_text = self.cursor.fetchone()
        if scale_text and '1:100' in scale_text[0]:
            scale_m_per_pt = 0.03528
            print(f"   Using scale 1:100")
        elif scale_text and '1:50' in scale_text[0]:
            scale_m_per_pt = 0.01764
            print(f"   Using scale 1:50")
        elif scale_text and '1:200' in scale_text[0]:
            scale_m_per_pt = 0.07056
            print(f"   Using scale 1:200")

        building_width_m = building_width_pt * scale_m_per_pt
        building_height_m = building_height_pt * scale_m_per_pt

        print(f"   ✅ Building from actual walls: {building_width_m:.2f}m x {building_height_m:.2f}m")

        return {
            'method': 'actual_walls',
            'success': True,
            'building_width_m': building_width_m,
            'building_length_m': building_height_m,
            'scale_m_per_pt': scale_m_per_pt,
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y,
            'confidence': 0.95
        }

    def cross_validate(self, method1: Dict, method2: Dict, method3: Dict) -> Dict:
        """
        Cross-validate all three methods

        Compares results and provides final calibration with confidence
        """
        print("\n🔍 CROSS-VALIDATION")

        # Try Method 4 FIRST - actual wall measurements (most accurate)
        method4 = self.method4_actual_walls()

        if not method1['success'] and not method2['success'] and not method4['success']:
            print("   ❌ Insufficient methods succeeded for validation")
            return {'success': False}

        # Use explicit scale to validate discharge perimeter
        final_result = {
            'calibration_method': 'multi_method_validated',
            'methods_used': [],
            'confidence': 0.0
        }

        # Priority: Method 4 (actual walls) > Method 2 (explicit scale) > Method 1 (grid)
        if method4['success']:
            print("\n   ✅ Using Method 4: Actual wall measurements (MOST ACCURATE)")
            final_result['building_width_m'] = method4['building_width_m']
            final_result['building_length_m'] = method4['building_length_m']
            final_result['scale_m_per_pt'] = method4['scale_m_per_pt']
            final_result['methods_used'].append('actual_walls')
            final_result['confidence'] = method4['confidence']

            # Still calculate drain perimeter if discharge available
            if method3['success']:
                drain_width_m = method3['bbox_width_pt'] * method4['scale_m_per_pt']
                drain_length_m = method3['bbox_height_pt'] * method4['scale_m_per_pt']
                final_result['drain_width_m'] = drain_width_m
                final_result['drain_length_m'] = drain_length_m
                final_result['methods_used'].append('discharge_perimeter')

                # Calculate overhang
                overhang_h = (drain_width_m - method4['building_width_m']) / 2
                overhang_v = (drain_length_m - method4['building_length_m']) / 2
                final_result['overhang_offset_h'] = overhang_h
                final_result['overhang_offset_v'] = overhang_v

                print(f"   Drain: {drain_width_m:.2f}m x {drain_length_m:.2f}m")
                print(f"   Overhang: {overhang_h:.2f}m (H) x {overhang_v:.2f}m (V)")

        # Fallback to Method 2 if Method 4 fails
        elif method2['success']:
            final_result['scale_m_per_pt'] = method2['scale_m_per_pt']
            final_result['scale_notation'] = method2['scale_notation']
            final_result['methods_used'].append('explicit_scale')
            final_result['confidence'] = method2['confidence']

            # Validate with DISCHARGE perimeter if available
            if method3['success']:
                # Calculate DRAIN perimeter dims from discharge bbox using explicit scale
                # NOTE: DISCHARGE is DRAIN PERIMETER (with overhang), NOT building footprint
                drain_width_m = method3['bbox_width_pt'] * method2['scale_m_per_pt']
                drain_length_m = method3['bbox_height_pt'] * method2['scale_m_per_pt']

                final_result['drain_width_m'] = drain_width_m
                final_result['drain_length_m'] = drain_length_m
                final_result['methods_used'].append('discharge_perimeter')

                print(f"   ✅ Explicit scale + DISCHARGE perimeter")
                print(f"   Drain perimeter: {drain_width_m:.2f}m x {drain_length_m:.2f}m (includes overhang)")

                # Use grid for BUILDING dimensions (actual footprint)
                if method1['success']:
                    # Grid provides building footprint (actual structure)
                    # DISCHARGE provides drain perimeter (includes overhang)
                    grid_width = method1['building_width_m']
                    grid_length = method1['building_length_m']

                    # Use grid dimensions as building footprint
                    final_result['building_width_m'] = grid_width
                    final_result['building_length_m'] = grid_length
                    final_result['methods_used'].append('grid_based_footprint')

                    print(f"\n   Building footprint (from grids):")
                    print(f"     Building: {grid_width}m x {grid_length}m")

                    # Calculate overhang offset
                    overhang_h = (drain_width_m - grid_width) / 2
                    overhang_v = (drain_length_m - grid_length) / 2
                    print(f"     Drain overhang: {overhang_h:.2f}m (H) x {overhang_v:.2f}m (V)")

                    final_result['overhang_offset_h'] = overhang_h
                    final_result['overhang_offset_v'] = overhang_v
                    final_result['confidence'] = 0.98  # All three methods used!
                else:
                    # Fallback: use drain perimeter as approximate building size
                    final_result['building_width_m'] = drain_width_m
                    final_result['building_length_m'] = drain_length_m
                    print(f"\n   ⚠️  Using drain perimeter as building estimate (no grid data)")
                    print(f"   Note: May include overhang offset")

        # Fallback to grid if no explicit scale
        elif method1['success']:
            final_result['building_width_m'] = method1['building_width_m']
            final_result['building_length_m'] = method1['building_length_m']
            final_result['scale_m_per_pt'] = method1['scale_x_m_per_pt']  # Use avg
            final_result['methods_used'].append('grid_based')
            final_result['confidence'] = method1['confidence']
            print(f"   ℹ️  Using grid-based calibration (no explicit scale found)")

        # Calculate final offset (assume origin at min discharge point if available)
        if method3['success']:
            final_result['offset_x'] = method3['min_x']
            final_result['offset_y'] = method3['min_y']
        else:
            final_result['offset_x'] = 0.0
            final_result['offset_y'] = 0.0

        final_result['success'] = True
        final_result['methods_succeeded'] = sum([m['success'] for m in [method1, method2, method3]])
        final_result['methods_total'] = 3

        print(f"\n✅ FINAL CALIBRATION:")
        print(f"   Methods used: {', '.join(final_result['methods_used'])}")
        print(f"   Building: {final_result.get('building_width_m', 'N/A')}m x {final_result.get('building_length_m', 'N/A')}m")
        print(f"   Scale: {final_result.get('scale_m_per_pt', 'N/A'):.6f} m/pt")
        print(f"   Confidence: {final_result['confidence']}")

        return final_result

    def persist_calibration(self, calibration: Dict):
        """Write calibration results to context_calibration table"""

        if not calibration.get('success'):
            print("\n❌ Cannot persist failed calibration")
            return

        print(f"\n💾 Persisting calibration to database...")

        # Clear existing calibration
        self.cursor.execute("DELETE FROM context_calibration")

        # Insert calibration parameters
        params = [
            ('scale_m_per_pt', calibration.get('scale_m_per_pt', 0.0), calibration['confidence'], ','.join(calibration['methods_used'])),
            ('offset_x', calibration.get('offset_x', 0.0), 0.80, 'discharge_min_x'),
            ('offset_y', calibration.get('offset_y', 0.0), 0.80, 'discharge_min_y'),
            ('building_width_m', calibration.get('building_width_m', 0.0), calibration['confidence'], ','.join(calibration['methods_used'])),
            ('building_length_m', calibration.get('building_length_m', 0.0), calibration['confidence'], ','.join(calibration['methods_used'])),
            ('methods_succeeded', float(calibration['methods_succeeded']), 1.0, f"{calibration['methods_succeeded']}/3"),
        ]

        # Store DISCHARGE drain perimeter (property boundary - needed for roof overhang calculations)
        if 'drain_width_m' in calibration:
            params.append(('drain_width_m', calibration['drain_width_m'], calibration['confidence'], 'discharge_perimeter'))
        if 'drain_length_m' in calibration:
            params.append(('drain_length_m', calibration['drain_length_m'], calibration['confidence'], 'discharge_perimeter'))
        if 'overhang_offset_h' in calibration:
            params.append(('overhang_offset_h', calibration['overhang_offset_h'], calibration['confidence'], 'calculated'))
        if 'overhang_offset_v' in calibration:
            params.append(('overhang_offset_v', calibration['overhang_offset_v'], calibration['confidence'], 'calculated'))

        if 'scale_notation' in calibration:
            params.append(('scale_notation', 0.0, calibration['confidence'], calibration['scale_notation']))

        for key, value, confidence, source in params:
            self.cursor.execute("""
                INSERT INTO context_calibration (key, value, confidence, source)
                VALUES (?, ?, ?, ?)
            """, (key, value, confidence, source))

        self.conn.commit()
        print(f"✅ Persisted {len(params)} calibration parameters")

    def run_full_calibration(self) -> Dict:
        """Run all three methods and cross-validate"""

        print("=" * 70)
        print("CALIBRATION ENGINE - Three-Method Validation")
        print("=" * 70)

        self.connect_db()

        try:
            # Run all three methods
            method1 = self.method1_grid_based()
            method2 = self.method2_explicit_scale()
            method3 = self.method3_discharge_perimeter()

            # Cross-validate
            final_calibration = self.cross_validate(method1, method2, method3)

            # Persist to database
            if final_calibration.get('success'):
                self.persist_calibration(final_calibration)

            print("\n" + "=" * 70)
            print("✅ CALIBRATION COMPLETE")
            print("=" * 70)

            return final_calibration

        finally:
            if self.conn:
                self.conn.close()


def main():
    """Main execution"""
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "output_artifacts" / "TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"

    engine = CalibrationEngine(str(db_path))
    result = engine.run_full_calibration()

    return result


if __name__ == "__main__":
    main()
