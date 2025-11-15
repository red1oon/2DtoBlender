"""
Data model for the entire project configuration
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class GlobalDefaults:
    """Global default settings for the project"""

    ceiling: Dict = field(default_factory=lambda: {
        "type": "Acoustic_Tile_600x600",
        "height": 18.5,
        "grid_spacing": [0.6, 0.6]
    })

    mep_standards: Dict = field(default_factory=lambda: {
        "fire_protection": {
            "code": "NFPA_13_Light_Hazard",
            "sprinkler_spacing": 3.0,
            "coverage_radius": 7.5,
            "height_below_ceiling": 0.3,
            "auto_route_pipes": True,
            "confidence": 0.95
        },
        "lighting": {
            "illuminance": 500,
            "spacing": 4.0,
            "type": "Recessed_LED_40W",
            "height": 18.0,
            "confidence": 0.90
        },
        "hvac": {
            "supply_spacing": 6.0,
            "return_spacing": 8.0,
            "air_changes_per_hour": 8,
            "confidence": 0.85
        }
    })

    seating_density: Dict = field(default_factory=lambda: {
        "waiting_area": {
            "template": "Terminal_Padded_Bench",
            "density_m2_per_seat": 1.5,
            "row_spacing": 2.0,
            "pattern": "rows_facing_center"
        },
        "office": {
            "template": "Office_Workstation",
            "density_m2_per_person": 6.0
        },
        "restaurant": {
            "template": "4_Seat_Table",
            "density_m2_per_seat": 2.0
        }
    })

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "ceiling": self.ceiling,
            "mep_standards": self.mep_standards,
            "seating_density": self.seating_density
        }


@dataclass
class InferenceRules:
    """Configuration for intelligent inference"""

    enabled: List[str] = field(default_factory=lambda: [
        "ceiling_tiles",
        "floor_finishes",
        "sprinklers",
        "lighting",
        "hvac_diffusers",
        "mep_routing"
    ])

    disabled: List[str] = field(default_factory=lambda: [
        "furniture_auto_add"
    ])

    min_confidence_threshold: float = 0.70

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "enabled": self.enabled,
            "disabled": self.disabled,
            "min_confidence_threshold": self.min_confidence_threshold
        }


@dataclass
class Project:
    """Main project data model"""

    name: str
    building_type: str = "Transportation Hub"
    sub_types: List[str] = field(default_factory=lambda: ["Airport Terminal"])
    created: str = field(default_factory=lambda: datetime.now().isoformat())

    # File paths
    dwg_file: Optional[str] = None
    excel_file: Optional[str] = None
    pdf_file: Optional[str] = None
    mep_schedule_file: Optional[str] = None

    # Configuration
    global_defaults: GlobalDefaults = field(default_factory=GlobalDefaults)
    inference_rules: InferenceRules = field(default_factory=InferenceRules)

    # Spaces (populated after parsing)
    spaces: List = field(default_factory=list)  # List of Space objects

    # Statistics
    total_spaces_configured: int = 0
    spaces_from_excel: int = 0
    spaces_from_user: int = 0
    average_confidence: float = 0.0
    elements_flagged_for_review: int = 0
    estimated_total_elements: int = 0

    def add_space(self, space):
        """Add a space to the project"""
        self.spaces.append(space)
        self.update_statistics()

    def update_statistics(self):
        """Recalculate project statistics"""
        self.total_spaces_configured = len(self.spaces)
        self.spaces_from_excel = sum(1 for s in self.spaces if s.source == "excel_space_program")
        self.spaces_from_user = sum(1 for s in self.spaces if s.source == "user_configured")

        if self.spaces:
            self.average_confidence = sum(s.confidence for s in self.spaces) / len(self.spaces)
        else:
            self.average_confidence = 0.0

    def get_spaces_needing_configuration(self) -> List:
        """Get list of spaces that need user input"""
        return [s for s in self.spaces if s.needs_configuration()]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "project": {
                "name": self.name,
                "building_type": self.building_type,
                "sub_types": self.sub_types,
                "created": self.created
            },
            "global_defaults": self.global_defaults.to_dict(),
            "spaces": [s.to_dict() for s in self.spaces],
            "inference_rules": self.inference_rules.to_dict(),
            "validation": {
                "total_spaces_configured": self.total_spaces_configured,
                "spaces_from_excel": self.spaces_from_excel,
                "spaces_from_user": self.spaces_from_user,
                "average_confidence": self.average_confidence,
                "elements_flagged_for_review": self.elements_flagged_for_review,
                "estimated_total_elements": self.estimated_total_elements
            }
        }
