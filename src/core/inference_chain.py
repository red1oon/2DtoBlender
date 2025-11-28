#!/usr/bin/env python3
"""
Inference Chain - Traceability and debugging for inferred properties

Records every inference step with sources and confidence scores.

Classes:
    InferenceChain: Tracks inference steps for debugging

Example:
    >>> chain = InferenceChain()
    >>> chain.add_step(property='wall_thickness', value=0.15, source='vector_width', confidence=0.9)
"""

from typing import List, Dict, Any


class InferenceChain:
    """
    Inference chain for traceability and debugging

    Records every inference step with sources and confidence
    """

    def __init__(self):
        self.chain = []

    def add_inference(self, step, phase, source, input_data, inference, confidence, validated_by=None):
        """
        Add inference step to chain

        Args:
            step: Step name (e.g., 'door_dimension_analysis')
            phase: Phase identifier (e.g., '1D', '2')
            source: Data source (e.g., 'door_schedule', 'elevation_view')
            input_data: Input data dict
            inference: Inference description (string)
            confidence: Confidence score (0.0-1.0)
            validated_by: List of validation sources
        """
        self.chain.append({
            'step': step,
            'phase': phase,
            'source': source,
            'input': input_data,
            'inference': inference,
            'confidence': confidence,
            'validated_by': validated_by or [],
            'timestamp': datetime.now().isoformat()
        })

    def get_chain(self):
        """Get complete inference chain"""
        return self.chain

    def get_by_phase(self, phase):
        """Get inferences for specific phase"""
        return [inf for inf in self.chain if inf['phase'] == phase]

    def get_by_confidence(self, min_confidence):
        """Get inferences above confidence threshold"""
        return [inf for inf in self.chain if inf['confidence'] >= min_confidence]

    def to_markdown(self):
        """Export inference chain as markdown"""
        md = "# Inference Chain\n\n"

        by_phase = {}
        for inf in self.chain:
            phase = inf['phase']
            if phase not in by_phase:
                by_phase[phase] = []
            by_phase[phase].append(inf)

        for phase in sorted(by_phase.keys()):
            md += f"## Phase {phase}\n\n"
            for inf in by_phase[phase]:
                md += f"### {inf['step']}\n"
                md += f"- **Source:** {inf['source']}\n"
                md += f"- **Inference:** {inf['inference']}\n"
                md += f"- **Confidence:** {inf['confidence']*100:.0f}%\n"
                if inf['validated_by']:
                    md += f"- **Validated by:** {', '.join(inf['validated_by'])}\n"
                md += "\n"

        return md


# =============================================================================
# SCHEDULE EXTRACTOR
# =============================================================================

