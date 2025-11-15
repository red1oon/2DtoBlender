"""
Data model for a configured space (room/hall/area)
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class Space:
    """Represents a single space/room in the building"""

    id: str
    name: str
    functional_type: str  # waiting_area, restaurant, office, toilet, etc.
    area_m2: float
    source: str  # "excel_space_program", "dwg_detected", "user_configured"

    # Optional furniture configuration
    furniture: Optional[Dict] = None

    # Optional overrides for this specific space
    overrides: Optional[Dict] = None

    # Confidence score (0.0-1.0)
    confidence: float = 0.0

    # Inference chain (list of what will be auto-generated)
    inference_chain: List[str] = field(default_factory=list)

    # Bounding box (for visualization)
    bounds: Optional[Dict] = None  # {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100}

    def __post_init__(self):
        """Validate data after initialization"""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

        if self.area_m2 <= 0:
            raise ValueError(f"Area must be positive, got {self.area_m2}")

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "id": self.id,
            "name": self.name,
            "functional_type": self.functional_type,
            "area_m2": self.area_m2,
            "source": self.source,
            "furniture": self.furniture,
            "overrides": self.overrides,
            "confidence": self.confidence,
            "inference_chain": self.inference_chain,
            "bounds": self.bounds
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Space':
        """Create Space from dictionary"""
        return cls(
            id=data["id"],
            name=data["name"],
            functional_type=data["functional_type"],
            area_m2=data["area_m2"],
            source=data["source"],
            furniture=data.get("furniture"),
            overrides=data.get("overrides"),
            confidence=data.get("confidence", 0.0),
            inference_chain=data.get("inference_chain", []),
            bounds=data.get("bounds")
        )

    def get_status_color(self) -> str:
        """Get color for UI display based on source"""
        colors = {
            "excel_space_program": "green",
            "dwg_detected": "green",
            "user_configured": "blue",
            "unknown": "yellow"
        }
        return colors.get(self.source, "yellow")

    def needs_configuration(self) -> bool:
        """Check if space needs user configuration"""
        return self.functional_type == "unknown" or self.confidence < 0.5
