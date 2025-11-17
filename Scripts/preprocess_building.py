#!/usr/bin/env python3
"""
Building Preprocessing Script (Layer -1)

Analyzes DXF files and generates/validates building_config.json.
This is the foundation that drives all downstream modeling:
- Floor levels and elevations
- Ceiling heights
- Spatial zones
- Building type inference
- MEP strategy selection

Usage:
    python3 Scripts/preprocess_building.py --analyze    # Analyze DXF and generate config
    python3 Scripts/preprocess_building.py --validate   # Validate existing config
    python3 Scripts/preprocess_building.py --apply      # Apply config to database
"""

import sys
import json
import sqlite3
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
import argparse

try:
    import ezdxf
except ImportError:
    print("❌ ERROR: ezdxf not installed")
    print("Install: pip install ezdxf")
    sys.exit(1)


class BuildingPreprocessor:
    """Analyzes DXF files to understand building topology and generate config."""

    def __init__(self, config_path: str = "building_config.json"):
        self.config_path = Path(config_path)
        self.config = None
        self.analysis_results = {}

    def load_config(self) -> Dict:
        """Load existing building config."""
        if not self.config_path.exists():
            print(f"⚠️ Config not found: {self.config_path}")
            return None

        with open(self.config_path, 'r') as f:
            self.config = json.load(f)

        print(f"✅ Loaded config: {self.config['building_info']['name']}")
        return self.config

    def save_config(self):
        """Save updated config."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✅ Saved config to: {self.config_path}")

    def analyze_dxf_structure(self):
        """Analyze all DXF files to extract floor levels, blocks, layers."""
        print("\n" + "="*80)
        print("ANALYZING DXF FILES")
        print("="*80)

        if not self.config:
            self.load_config()

        dxf_files = []
        source_dir = Path("SourceFiles/TERMINAL1DXF")

        # Collect all DXF files
        for floor in self.config['floor_levels']:
            for discipline, dxf_path in floor.get('dxf_sources', {}).items():
                if dxf_path:
                    full_path = Path(dxf_path)
                    if full_path.exists():
                        dxf_files.append((floor['level_id'], discipline, full_path))

        print(f"\nFound {len(dxf_files)} DXF files to analyze\n")

        # Analyze each file
        for level_id, discipline, dxf_path in dxf_files:
            print(f"\n📄 {level_id} - {discipline}: {dxf_path.name}")
            self._analyze_single_dxf(level_id, discipline, dxf_path)

    def _analyze_single_dxf(self, level_id: str, discipline: str, dxf_path: Path):
        """Analyze a single DXF file for layers, blocks, Z-coordinates."""
        try:
            doc = ezdxf.readfile(str(dxf_path))
            modelspace = doc.modelspace()

            layer_counts = Counter()
            block_counts = Counter()
            z_coords = []

            for entity in modelspace:
                # Count layers
                if hasattr(entity.dxf, 'layer'):
                    layer_counts[entity.dxf.layer] += 1

                # Count blocks
                if entity.dxftype() == 'INSERT' and hasattr(entity.dxf, 'name'):
                    block_counts[entity.dxf.name] += 1

                # Collect Z-coordinates
                try:
                    if entity.dxftype() == 'INSERT':
                        z = float(entity.dxf.insert[2])
                    elif entity.dxftype() == 'LINE':
                        z = float(entity.dxf.start[2])
                    elif hasattr(entity.dxf, 'elevation'):
                        z = float(entity.dxf.elevation)
                    else:
                        z = 0.0
                    z_coords.append(z)
                except:
                    pass

            # Store results
            key = f"{level_id}_{discipline}"
            self.analysis_results[key] = {
                'layer_counts': dict(layer_counts.most_common(10)),
                'block_counts': dict(block_counts.most_common(10)),
                'z_stats': {
                    'min': min(z_coords) if z_coords else 0.0,
                    'max': max(z_coords) if z_coords else 0.0,
                    'unique_levels': len(set([round(z, 1) for z in z_coords]))
                },
                'entity_count': len(list(modelspace))
            }

            print(f"   Layers: {len(layer_counts)}, Blocks: {len(block_counts)}, Entities: {len(list(modelspace))}")
            print(f"   Z-range: {min(z_coords):.1f} to {max(z_coords):.1f}m")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    def detect_building_type(self) -> str:
        """Infer building type from block names, layers, patterns."""
        print("\n" + "="*80)
        print("DETECTING BUILDING TYPE")
        print("="*80)

        # Keyword-based detection
        airport_keywords = ['terminal', 'departure', 'arrival', 'baggage', 'bomba']
        office_keywords = ['office', 'workspace', 'cubicle', 'meeting']
        residential_keywords = ['apartment', 'unit', 'bedroom', 'kitchen']
        retail_keywords = ['shop', 'store', 'retail', 'kiosk']

        # Search in analysis results
        all_blocks = []
        all_layers = []

        for key, data in self.analysis_results.items():
            all_blocks.extend(data.get('block_counts', {}).keys())
            all_layers.extend(data.get('layer_counts', {}).keys())

        combined_text = ' '.join(all_blocks + all_layers).lower()

        # Score each type
        scores = {
            'AIRPORT_TERMINAL': sum(1 for kw in airport_keywords if kw in combined_text),
            'OFFICE': sum(1 for kw in office_keywords if kw in combined_text),
            'RESIDENTIAL': sum(1 for kw in residential_keywords if kw in combined_text),
            'RETAIL': sum(1 for kw in retail_keywords if kw in combined_text)
        }

        detected_type = max(scores, key=scores.get)
        confidence = min(scores[detected_type] / 5.0, 1.0)  # Normalize to 0-1

        print(f"\n🏢 Detected: {detected_type} (confidence: {confidence:.2f})")
        print(f"   Scores: {scores}")

        # Update config
        if self.config:
            self.config['building_info']['building_type'] = detected_type
            self.config['building_info']['detection_confidence']['building_type'] = confidence

        return detected_type

    def detect_floor_levels(self):
        """Extract floor levels from STR DXF files (most reliable source)."""
        print("\n" + "="*80)
        print("DETECTING FLOOR LEVELS")
        print("="*80)

        str_files = [(k, v) for k, v in self.analysis_results.items() if '_STR' in k]

        if not str_files:
            print("⚠️ No STR files found - using config defaults")
            return

        # For each STR file, check Z-coordinates
        floor_elevations = {}

        for key, data in str_files:
            level_id = key.split('_')[0]
            z_min = data['z_stats']['min']
            z_max = data['z_stats']['max']

            # Find the floor in config
            for floor in self.config['floor_levels']:
                if floor['level_id'] == level_id:
                    # Update elevation if significantly different
                    config_elevation = floor['elevation']
                    detected_elevation = z_min  # Use minimum Z as floor level

                    print(f"   {level_id}: Config={config_elevation:.1f}m, Detected={detected_elevation:.1f}m")

                    if abs(detected_elevation - config_elevation) > 0.5:
                        print(f"      ⚠️ Mismatch detected (>0.5m difference)")

                    floor_elevations[level_id] = detected_elevation
                    break

        print(f"\n✅ Detected {len(floor_elevations)} floor levels")

    def detect_spatial_infrastructure(self):
        """Detect vertical shafts, mechanical rooms, corridors from ARC/STR."""
        print("\n" + "="*80)
        print("DETECTING SPATIAL INFRASTRUCTURE")
        print("="*80)
        print("⚠️ Infrastructure detection not yet implemented")
        print("   Will detect:")
        print("   - Vertical shafts (from STR ports)")
        print("   - Mechanical rooms (from large ARC zones)")
        print("   - Corridors (from parallel wall patterns)")
        print("   - Restrooms (from door clusters + fixtures)")

    def validate_config(self) -> bool:
        """Validate config completeness and consistency."""
        print("\n" + "="*80)
        print("VALIDATING CONFIG")
        print("="*80)

        if not self.config:
            self.load_config()

        issues = []
        warnings = []

        # Check required fields
        required_fields = [
            'building_info',
            'floor_levels',
            'spatial_infrastructure',
            'mep_strategy',
            'poc_config'
        ]

        for field in required_fields:
            if field not in self.config:
                issues.append(f"Missing required field: {field}")

        # Check floor levels
        active_floors = [f for f in self.config['floor_levels'] if f.get('active', False)]
        if len(active_floors) == 0:
            warnings.append("No active floors defined")

        # Check POC target
        poc_target = self.config['poc_config']['target_floor']
        if not any(f['level_id'] == poc_target for f in self.config['floor_levels']):
            issues.append(f"POC target floor '{poc_target}' not found in floor_levels")

        # Check DXF paths
        missing_dxf = []
        for floor in self.config['floor_levels']:
            if floor.get('active', False):
                for discipline, dxf_path in floor.get('dxf_sources', {}).items():
                    if dxf_path and not Path(dxf_path).exists():
                        missing_dxf.append(f"{floor['level_id']} {discipline}: {dxf_path}")

        if missing_dxf:
            warnings.append(f"{len(missing_dxf)} DXF files not found (see details)")

        # Print results
        if issues:
            print("\n❌ VALIDATION FAILED:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("\n✅ VALIDATION PASSED")

        if warnings:
            print("\n⚠️ WARNINGS:")
            for warning in warnings:
                print(f"   - {warning}")

        return len(issues) == 0

    def apply_to_database(self, db_path: str):
        """Apply config to database by creating building_metadata table."""
        print("\n" + "="*80)
        print("APPLYING CONFIG TO DATABASE")
        print("="*80)

        if not self.config:
            self.load_config()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create building_metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS building_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                category TEXT,
                confidence REAL,
                source TEXT
            )
        """)

        # Insert building info
        metadata_rows = []

        # Building type
        metadata_rows.append((
            'building_type',
            self.config['building_info']['building_type'],
            'building_info',
            self.config['building_info']['detection_confidence']['building_type'],
            'auto_detected'
        ))

        # Total floors
        metadata_rows.append((
            'total_floors',
            str(self.config['building_info']['total_floors']),
            'floor_info',
            1.0,
            'config'
        ))

        # Floor-to-floor height
        metadata_rows.append((
            'floor_to_floor_height',
            str(self.config['building_info']['floor_to_floor_height']),
            'floor_info',
            1.0,
            'config'
        ))

        # POC target floor
        metadata_rows.append((
            'poc_target_floor',
            self.config['poc_config']['target_floor'],
            'poc_config',
            1.0,
            'config'
        ))

        # Active disciplines
        metadata_rows.append((
            'active_disciplines',
            json.dumps(self.config['poc_config']['active_disciplines']),
            'poc_config',
            1.0,
            'config'
        ))

        # Floor levels (JSON)
        for floor in self.config['floor_levels']:
            if floor.get('active', False) or floor.get('is_poc_target', False):
                metadata_rows.append((
                    f"floor_{floor['level_id']}_elevation",
                    str(floor['elevation']),
                    'floor_info',
                    1.0,
                    'config'
                ))

                metadata_rows.append((
                    f"floor_{floor['level_id']}_ceiling_height",
                    str(floor.get('mep_ceiling_height', 4.0)),
                    'floor_info',
                    1.0,
                    'config'
                ))

        # MEP strategy
        for discipline in ['FP', 'ELEC', 'ACMV', 'SP']:
            if discipline in self.config['mep_strategy']:
                strategy = self.config['mep_strategy'][discipline]
                metadata_rows.append((
                    f"mep_strategy_{discipline}",
                    json.dumps(strategy),
                    'mep_strategy',
                    1.0,
                    'config'
                ))

        # Insert all rows
        cursor.executemany("""
            INSERT OR REPLACE INTO building_metadata
            (key, value, category, confidence, source)
            VALUES (?, ?, ?, ?, ?)
        """, metadata_rows)

        conn.commit()
        conn.close()

        print(f"✅ Inserted {len(metadata_rows)} metadata rows into {db_path}")
        print("\nKey metadata:")
        for key, value, _, _, _ in metadata_rows[:10]:
            print(f"   {key} = {value}")

    def generate_config_template(self):
        """Generate a new config template (if building_config.json doesn't exist)."""
        # Already created manually - this would be for auto-generation
        pass


def main():
    parser = argparse.ArgumentParser(description="Building Preprocessing (Layer -1)")
    parser.add_argument('--analyze', action='store_true', help="Analyze DXF files")
    parser.add_argument('--validate', action='store_true', help="Validate config")
    parser.add_argument('--apply', type=str, help="Apply config to database")
    parser.add_argument('--config', type=str, default="building_config.json", help="Config file path")

    args = parser.parse_args()

    preprocessor = BuildingPreprocessor(config_path=args.config)

    if args.analyze:
        preprocessor.load_config()
        preprocessor.analyze_dxf_structure()
        preprocessor.detect_building_type()
        preprocessor.detect_floor_levels()
        preprocessor.detect_spatial_infrastructure()
        preprocessor.save_config()

    elif args.validate:
        valid = preprocessor.validate_config()
        sys.exit(0 if valid else 1)

    elif args.apply:
        preprocessor.apply_to_database(args.apply)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
