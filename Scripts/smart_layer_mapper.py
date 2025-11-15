#!/usr/bin/env python3
"""
Smart Layer Mapper - Phase 1: Intelligent Pattern Recognition

Uses keyword matching, frequency analysis, and confidence scoring to automatically
map DXF layer names to BIM disciplines.

Usage:
    python3 smart_layer_mapper.py [dxf_file] [output_json]
"""

import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent))
from dwg_parser import DWGParser


class SmartLayerMapper:
    """Intelligent layer name → discipline mapping with pattern recognition."""

    def __init__(self):
        self.layer_stats = {}
        self.mappings = {}
        self.confidence_scores = {}
        self.unmapped_layers = []

        # Tier 1: Keyword-based patterns (case-insensitive)
        self.keyword_patterns = {
            'FP': [
                'bomba', 'fire', 'sprinkler', 'smoke', 'detector',
                'alarm', 'hose', 'hydrant', 'suppression'
            ],
            'ACMV': [
                'ac-', 'ac ', 'hvac', 'duct', 'griille', 'grille',
                'tower', 'cooling', 'ventilation', 'ahv'
            ],
            'SP': [
                'wet', 'sw-', 'rh-', 'san', 'sani', 'plumbing',
                'drain', 'sewage', 'waste', 'water', 'rwdp',
                'overflow', 'incoming', 'dropper'
            ],
            'CW': [
                'cw-', 'chilled', 'cooling water', 'tank'
            ],
            'LPG': [
                'lpg', 'gas', 'cylinder'
            ],
            'ELEC': [
                'el', 'elec', 'light', 'power', 'cable',
                'socket', 'switch', 'panel', 'electrical'
            ],
            'ARC': [
                'wall', 'win', 'window', 'door', 'furniture',
                'stair', 'roof', 'floor', 'ceiling', 'room',
                'toilet', 'finish', 'tile', 'plaster', 'render',
                'railing', 'timber', 'concrete', 'brick'
            ],
            'STR': [
                'col', 'column', 'beam', 'slab', 'truss',
                'grid', 'foundation', 'footing', 'structure'
            ],
        }

        # Tier 2: Entity type hints (for ambiguous layers)
        self.entity_type_hints = {
            'DIMENSION': 'ARC',  # Dimensions usually architectural
            'TEXT': 'ARC',       # Text annotations
            'MTEXT': 'ARC',
            'HATCH': 'ARC',      # Hatching patterns
        }

        # Known prefixes that indicate discipline
        self.prefix_patterns = {
            'z-ac-': 'ACMV',
            'z-fire-': 'FP',
            'z-wet-': 'SP',
            'z-sw-': 'SP',
            'z-rh-': 'SP',
            'z-cw-': 'CW',
            'z-lpg-': 'LPG',
            'z-lift-': 'ARC',
            'z-mech-': 'ACMV',
            'z-kitchen-': 'ARC',
            'c-bomba': 'FP',
            'ch-': 'ARC',  # CH likely means "ceiling height" or finish codes
        }

    def analyze_layers(self, dxf_file: str) -> Dict:
        """Parse DXF and analyze all layers."""
        print(f"📊 Analyzing layers in: {Path(dxf_file).name}")

        parser = DWGParser(dxf_file)
        parser.parse()

        # Collect layer statistics
        for entity in parser.entities:
            layer = entity.layer

            if layer not in self.layer_stats:
                self.layer_stats[layer] = {
                    'count': 0,
                    'entity_types': defaultdict(int),
                    'blocks': set(),
                    'sample_positions': []
                }

            stats = self.layer_stats[layer]
            stats['count'] += 1
            stats['entity_types'][entity.entity_type] += 1

            if entity.block_name:
                stats['blocks'].add(entity.block_name)

            # Sample first few positions for spatial analysis (if available)
            if len(stats['sample_positions']) < 5:
                if hasattr(entity, 'position') and entity.position:
                    stats['sample_positions'].append(entity.position)
                elif hasattr(entity, 'attributes') and entity.attributes:
                    # Try to get position from attributes
                    if 'position' in entity.attributes:
                        stats['sample_positions'].append(entity.attributes['position'])

        print(f"✅ Found {len(self.layer_stats)} unique layers")
        print(f"✅ Analyzed {len(parser.entities)} entities\n")

        return self.layer_stats

    def map_layers(self) -> Dict:
        """Apply intelligent mapping to all layers."""
        print("🎯 Phase 1: Smart Auto-Mapping")
        print("=" * 70)

        mapped_count = 0
        high_confidence = 0

        for layer, stats in sorted(self.layer_stats.items(),
                                   key=lambda x: x[1]['count'],
                                   reverse=True):

            # Try to map this layer
            discipline, confidence, reason = self._classify_layer(layer, stats)

            if discipline:
                self.mappings[layer] = discipline
                self.confidence_scores[layer] = {
                    'confidence': confidence,
                    'reason': reason,
                    'entity_count': stats['count']
                }
                mapped_count += 1

                if confidence >= 0.8:
                    high_confidence += 1
                    status = "✅"
                elif confidence >= 0.6:
                    status = "⚠️"
                else:
                    status = "❓"

                # Print interesting mappings (top layers or low confidence)
                if stats['count'] > 100 or confidence < 0.7:
                    print(f"{status} {layer:<35} → {discipline:>5} "
                          f"({confidence:.0%} confidence, {stats['count']:>5} entities)")
                    print(f"   Reason: {reason}")
            else:
                self.unmapped_layers.append(layer)

        print(f"\n{'=' * 70}")
        print(f"📈 Mapping Results:")
        print(f"   Mapped: {mapped_count}/{len(self.layer_stats)} "
              f"({mapped_count/len(self.layer_stats):.1%})")
        print(f"   High confidence (≥80%): {high_confidence}")
        print(f"   Medium confidence (60-80%): {mapped_count - high_confidence}")
        print(f"   Unmapped: {len(self.unmapped_layers)}")

        return self.mappings

    def _classify_layer(self, layer: str, stats: Dict) -> Tuple[Optional[str], float, str]:
        """
        Classify a single layer using multiple strategies.

        Returns: (discipline, confidence_score, reason)
        """
        layer_lower = layer.lower()

        # Strategy 1: Exact prefix match (highest confidence)
        for prefix, discipline in self.prefix_patterns.items():
            if layer_lower.startswith(prefix):
                return (discipline, 0.95, f"Exact prefix match: '{prefix}'")

        # Strategy 2: Keyword matching (high confidence)
        discipline_scores = defaultdict(float)
        matched_keywords = defaultdict(list)

        for discipline, keywords in self.keyword_patterns.items():
            for keyword in keywords:
                if keyword in layer_lower:
                    # Weight by keyword specificity (shorter = more specific)
                    weight = 1.0 / (len(keyword) / 5.0) if len(keyword) >= 3 else 0.3
                    discipline_scores[discipline] += weight
                    matched_keywords[discipline].append(keyword)

        if discipline_scores:
            # Get top match
            top_discipline = max(discipline_scores.items(), key=lambda x: x[1])
            discipline = top_discipline[0]
            score = min(top_discipline[1], 1.0)  # Cap at 1.0

            # Adjust confidence based on score
            confidence = 0.6 + (score * 0.3)  # 60-90% range

            keywords_str = ', '.join(matched_keywords[discipline])
            return (discipline, confidence, f"Keywords: {keywords_str}")

        # Strategy 3: Entity type hints (medium confidence)
        if stats['entity_types']:
            dominant_type = max(stats['entity_types'].items(), key=lambda x: x[1])
            entity_type = dominant_type[0]
            entity_ratio = dominant_type[1] / stats['count']

            if entity_ratio > 0.7 and entity_type in self.entity_type_hints:
                discipline = self.entity_type_hints[entity_type]
                confidence = 0.5 + (entity_ratio * 0.2)  # 50-70% range
                return (discipline, confidence,
                       f"Dominant entity type: {entity_type} ({entity_ratio:.0%})")

        # Strategy 4: Spatial hints (low confidence)
        if stats['sample_positions']:
            # Check z-height patterns
            z_values = [pos[2] for pos in stats['sample_positions'] if len(pos) > 2]
            if z_values:
                avg_z = sum(z_values) / len(z_values)

                # Ceiling-mounted (likely MEP)
                if avg_z > 3.0:
                    return ('ACMV', 0.4, f"Ceiling-mounted (avg z={avg_z:.1f}m)")
                # Floor-mounted
                elif avg_z < 0.5:
                    return ('ARC', 0.4, f"Floor-mounted (avg z={avg_z:.1f}m)")

        # Couldn't classify
        return (None, 0.0, "No matching patterns")

    def generate_report(self) -> str:
        """Generate detailed mapping report."""
        report = []
        report.append("\n" + "=" * 70)
        report.append("SMART LAYER MAPPING REPORT")
        report.append("=" * 70)

        # Group by discipline
        by_discipline = defaultdict(list)
        for layer, discipline in self.mappings.items():
            by_discipline[discipline].append(layer)

        # Count entities per discipline
        discipline_counts = defaultdict(int)
        for layer, discipline in self.mappings.items():
            discipline_counts[discipline] += self.layer_stats[layer]['count']

        report.append("\n📊 Mapped Layers by Discipline:")
        report.append("-" * 70)

        for discipline in sorted(by_discipline.keys()):
            layers = by_discipline[discipline]
            total_entities = discipline_counts[discipline]
            report.append(f"\n{discipline} - {len(layers)} layers, {total_entities} entities:")

            # Show top 5 layers by entity count
            sorted_layers = sorted(layers,
                                  key=lambda l: self.layer_stats[l]['count'],
                                  reverse=True)

            for layer in sorted_layers[:10]:
                count = self.layer_stats[layer]['count']
                conf = self.confidence_scores[layer]['confidence']
                reason = self.confidence_scores[layer]['reason']
                report.append(f"  • {layer:<30} ({count:>5} entities, {conf:.0%} conf)")
                if conf < 0.7:
                    report.append(f"    ⚠️  {reason}")

        # Show unmapped layers (need review)
        if self.unmapped_layers:
            report.append(f"\n❓ Unmapped Layers ({len(self.unmapped_layers)}):")
            report.append("-" * 70)

            sorted_unmapped = sorted(self.unmapped_layers,
                                    key=lambda l: self.layer_stats[l]['count'],
                                    reverse=True)

            for layer in sorted_unmapped[:20]:
                count = self.layer_stats[layer]['count']
                types = self.layer_stats[layer]['entity_types']
                top_type = max(types.items(), key=lambda x: x[1])[0] if types else 'N/A'
                report.append(f"  • {layer:<30} ({count:>5} entities, type: {top_type})")

        # Statistics
        report.append(f"\n📈 Overall Statistics:")
        report.append("-" * 70)
        total_entities = sum(stats['count'] for stats in self.layer_stats.values())
        mapped_entities = sum(discipline_counts.values())

        report.append(f"Total layers: {len(self.layer_stats)}")
        report.append(f"Mapped layers: {len(self.mappings)} ({len(self.mappings)/len(self.layer_stats):.1%})")
        report.append(f"Unmapped layers: {len(self.unmapped_layers)}")
        report.append(f"")
        report.append(f"Total entities: {total_entities}")
        report.append(f"Mapped entities: {mapped_entities} ({mapped_entities/total_entities:.1%})")
        report.append(f"Unmapped entities: {total_entities - mapped_entities}")

        return "\n".join(report)

    def export_mappings(self, output_file: str):
        """Export mappings to JSON with metadata."""
        output_path = Path(output_file)

        export_data = {
            'version': '1.0',
            'total_layers': len(self.layer_stats),
            'mapped_layers': len(self.mappings),
            'mapping_coverage': len(self.mappings) / len(self.layer_stats),
            'mappings': {},
            'unmapped_layers': self.unmapped_layers,
            'statistics': {
                'by_discipline': defaultdict(int)
            }
        }

        # Add mappings with metadata
        for layer, discipline in self.mappings.items():
            export_data['mappings'][layer] = {
                'discipline': discipline,
                'confidence': self.confidence_scores[layer]['confidence'],
                'reason': self.confidence_scores[layer]['reason'],
                'entity_count': self.confidence_scores[layer]['entity_count']
            }
            export_data['statistics']['by_discipline'][discipline] += 1

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"\n💾 Mappings exported to: {output_path}")
        print(f"   - {len(self.mappings)} layer mappings")
        print(f"   - {len(self.unmapped_layers)} layers need review")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 smart_layer_mapper.py [dxf_file] [output_json]")
        print("\nExample:")
        print('  python3 smart_layer_mapper.py "Terminal1.dxf" layer_mappings.json')
        sys.exit(1)

    dxf_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "layer_mappings.json"

    if not Path(dxf_file).exists():
        print(f"❌ Error: DXF file not found: {dxf_file}")
        sys.exit(1)

    # Create mapper
    mapper = SmartLayerMapper()

    # Analyze layers
    mapper.analyze_layers(dxf_file)

    # Apply smart mapping
    mapper.map_layers()

    # Generate report
    report = mapper.generate_report()
    print(report)

    # Export mappings
    mapper.export_mappings(output_file)

    print("\n✅ Phase 1 Complete!")
    print(f"\nNext steps:")
    print(f"1. Review unmapped layers in: {output_file}")
    print(f"2. Manually map remaining layers if needed")
    print(f"3. Re-run conversion with mappings: ./run_conversion.sh")


if __name__ == '__main__':
    main()
