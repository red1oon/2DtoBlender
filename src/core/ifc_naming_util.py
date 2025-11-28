"""
IFC Naming Layer Utility
========================
Minimal patch to apply IFC naming and discipline grouping to output objects.

Usage:
    from ifc_naming_util import IfcNamingLayer, apply_naming_to_output
    
    naming = IfcNamingLayer("ifc_naming_layer.json")
    
    # Get IFC properties for an object type
    props = naming.get_properties("door_single_900_lod300")
    # Returns: {ifc_class: "IfcDoor", discipline: "ARC", group: "Doors", ...}
    
    # Apply to entire output JSON
    output = apply_naming_to_output(output_data, naming)
"""

import json
from typing import Dict, Optional, List, Any
from pathlib import Path


class IfcNamingLayer:
    """
    IFC Naming and Discipline Layer.
    
    Maps object_type to:
    - ifc_class (IfcDoor, IfcWall, IfcSlab, etc.)
    - ifc_predefined_type (DOOR, ROOF, FLOOR, etc.)
    - discipline (ARC, MEP, STR, PLUM)
    - group (Envelope, Kitchen, Electrical, etc.)
    - blender_name template
    """
    
    def __init__(self, config_path: str = None):
        self.items: Dict[str, Dict] = {}
        self.disciplines: Dict[str, Dict] = {}
        self.groups: Dict[str, Dict] = {}
        
        if config_path:
            self.load(config_path)
        else:
            self._load_defaults()
    
    def load(self, config_path: str):
        """Load naming layer from JSON file."""
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        self.disciplines = data.get('disciplines', {})
        self.groups = data.get('groups', {})
        
        for item in data.get('items', []):
            if 'object_type' in item:
                self.items[item['object_type']] = item
    
    def _load_defaults(self):
        """Load minimal defaults if no config file."""
        self.disciplines = {
            "ARC": {"name": "Architectural", "order": 1},
            "STR": {"name": "Structural", "order": 2},
            "MEP": {"name": "Mechanical/Electrical", "order": 3},
            "PLUM": {"name": "Plumbing", "order": 4}
        }
        
        # Minimal defaults
        self.items = {
            "roof_slab": {"ifc_class": "IfcSlab", "ifc_predefined_type": "ROOF", "discipline": "STR", "group": "Roofing"},
            "floor_slab": {"ifc_class": "IfcSlab", "ifc_predefined_type": "FLOOR", "discipline": "STR", "group": "Floor"},
            "ceiling": {"ifc_class": "IfcCovering", "ifc_predefined_type": "CEILING", "discipline": "ARC", "group": "Envelope"},
            "wall_exterior": {"ifc_class": "IfcWall", "ifc_predefined_type": "SOLIDWALL", "discipline": "ARC", "group": "Walls"},
            "wall_interior": {"ifc_class": "IfcWall", "ifc_predefined_type": "PARTITIONING", "discipline": "ARC", "group": "Walls"},
        }
    
    def get_properties(self, object_type: str) -> Dict:
        """Get IFC properties for an object type (excludes object_type to avoid overwriting)."""
        # Direct match
        if object_type in self.items:
            props = self.items[object_type].copy()
            props.pop('object_type', None)  # Don't overwrite original object_type
            return props

        # Partial match (e.g., "door_ruang_tamu" matches "door_single_900_lod300")
        for key, props in self.items.items():
            if object_type.startswith(key.split('_')[0]):
                result = props.copy()
                result.pop('object_type', None)  # Don't overwrite original object_type
                result['_matched_from'] = key
                return result

        # Infer from object_type name
        return self._infer_properties(object_type)
    
    def _infer_properties(self, object_type: str) -> Dict:
        """Infer IFC properties from object_type name."""
        ot_lower = object_type.lower()
        
        # Plumbing (check FIRST - before "floor" matches floor_slab)
        if 'toilet' in ot_lower or 'wc' in ot_lower or 'tandas' in ot_lower:
            return {"ifc_class": "IfcSanitaryTerminal", "ifc_predefined_type": "TOILETPAN", "discipline": "PLUM", "group": "Fixtures"}
        if 'basin' in ot_lower or 'sinki' in ot_lower:
            return {"ifc_class": "IfcSanitaryTerminal", "ifc_predefined_type": "WASHHANDBASIN", "discipline": "PLUM", "group": "Fixtures"}
        if 'sink' in ot_lower:
            return {"ifc_class": "IfcSanitaryTerminal", "ifc_predefined_type": "SINK", "discipline": "PLUM", "group": "Fixtures"}
        if 'floor_drain' in ot_lower or 'floordrain' in ot_lower:
            return {"ifc_class": "IfcWasteTerminal", "ifc_predefined_type": "FLOORTRAP", "discipline": "PLUM", "group": "Drainage"}
        if 'drain' in ot_lower or 'saliran' in ot_lower or 'discharge' in ot_lower or 'gutter' in ot_lower:
            return {"ifc_class": "IfcPipeSegment", "ifc_predefined_type": "GUTTER", "discipline": "PLUM", "group": "Drainage"}

        # Structural
        if 'roof' in ot_lower:
            return {"ifc_class": "IfcSlab", "ifc_predefined_type": "ROOF", "discipline": "STR", "group": "Roofing"}
        if 'floor' in ot_lower or 'slab' in ot_lower:
            return {"ifc_class": "IfcSlab", "ifc_predefined_type": "FLOOR", "discipline": "STR", "group": "Floor"}
        if 'ceiling' in ot_lower:
            return {"ifc_class": "IfcCovering", "ifc_predefined_type": "CEILING", "discipline": "ARC", "group": "Envelope"}
        
        # Walls
        if 'wall' in ot_lower:
            if 'ext' in ot_lower or 'exterior' in ot_lower:
                return {"ifc_class": "IfcWall", "ifc_predefined_type": "SOLIDWALL", "discipline": "ARC", "group": "Walls"}
            return {"ifc_class": "IfcWall", "ifc_predefined_type": "PARTITIONING", "discipline": "ARC", "group": "Walls"}
        
        # Doors
        if 'door' in ot_lower or 'pintu' in ot_lower:
            return {"ifc_class": "IfcDoor", "ifc_predefined_type": "DOOR", "discipline": "ARC", "group": "Doors"}
        
        # Windows
        if 'window' in ot_lower or 'tingkap' in ot_lower:
            return {"ifc_class": "IfcWindow", "ifc_predefined_type": "WINDOW", "discipline": "ARC", "group": "Windows"}
        
        # MEP - Electrical
        if 'switch' in ot_lower or 'suis' in ot_lower:
            return {"ifc_class": "IfcSwitchingDevice", "ifc_predefined_type": "TOGGLESWITCH", "discipline": "MEP", "group": "Electrical"}
        if 'outlet' in ot_lower or 'socket' in ot_lower or 'soket' in ot_lower:
            return {"ifc_class": "IfcOutlet", "ifc_predefined_type": "POWEROUTLET", "discipline": "MEP", "group": "Electrical"}
        if 'light' in ot_lower or 'lampu' in ot_lower:
            return {"ifc_class": "IfcLightFixture", "ifc_predefined_type": "POINTSOURCE", "discipline": "MEP", "group": "Lighting"}
        if 'fan' in ot_lower or 'kipas' in ot_lower:
            return {"ifc_class": "IfcFan", "ifc_predefined_type": "NOTDEFINED", "discipline": "MEP", "group": "Electrical"}
        
        # Furniture
        if 'sofa' in ot_lower or 'table' in ot_lower or 'bed' in ot_lower or 'chair' in ot_lower:
            return {"ifc_class": "IfcFurniture", "ifc_predefined_type": "NOTDEFINED", "discipline": "ARC", "group": "Furniture"}
        if 'fridge' in ot_lower or 'stove' in ot_lower or 'washer' in ot_lower or 'washing' in ot_lower:
            return {"ifc_class": "IfcElectricAppliance", "ifc_predefined_type": "NOTDEFINED", "discipline": "MEP", "group": "Kitchen"}
        if 'canopy' in ot_lower or 'porch' in ot_lower:
            return {"ifc_class": "IfcSlab", "ifc_predefined_type": "ROOF", "discipline": "ARC", "group": "Envelope"}
        
        # Default
        return {"ifc_class": "IfcBuildingElementProxy", "ifc_predefined_type": "NOTDEFINED", "discipline": "ARC", "group": "Misc"}
    
    def get_blender_name(self, object_type: str, **kwargs) -> str:
        """
        Generate Blender-friendly name.
        
        Args:
            object_type: The object type
            **kwargs: Variables for template (room, label, index, direction)
        
        Returns:
            Name like "ARC_Door_D1" or "MEP_Switch_Kitchen"
        """
        props = self.get_properties(object_type)
        discipline = props.get('discipline', 'ARC')
        
        # Use template if available
        if 'blender_name' in props:
            template = props['blender_name']
            try:
                return template.format(**kwargs)
            except KeyError:
                pass
        
        # Generate default name
        base = object_type.split('_')[0].capitalize()
        room = kwargs.get('room', '')
        label = kwargs.get('label', '')
        
        if label:
            return f"{discipline}_{base}_{label}"
        elif room:
            return f"{discipline}_{base}_{room}"
        else:
            return f"{discipline}_{base}"
    
    def get_collection_hierarchy(self, object_type: str) -> List[str]:
        """
        Get Blender collection hierarchy for an object.
        
        Returns: ["ARC", "Doors"] or ["MEP", "Electrical"]
        """
        props = self.get_properties(object_type)
        discipline = props.get('discipline', 'ARC')
        group = props.get('group', 'Misc')
        return [discipline, group]


def apply_naming_to_output(output_data: Dict, naming: IfcNamingLayer) -> Dict:
    """
    Apply IFC naming layer to output JSON.
    
    Adds ifc_class, ifc_predefined_type, discipline, group to each object.
    """
    if 'objects' not in output_data:
        return output_data
    
    for obj in output_data['objects']:
        object_type = obj.get('object_type', '')
        props = naming.get_properties(object_type)
        
        # Add IFC properties
        obj['ifc_class'] = props.get('ifc_class', 'IfcBuildingElementProxy')
        obj['ifc_predefined_type'] = props.get('ifc_predefined_type', 'NOTDEFINED')
        obj['discipline'] = props.get('discipline', 'ARC')
        obj['group'] = props.get('group', 'Misc')
        
        # Generate blender_name
        obj['blender_name'] = naming.get_blender_name(
            object_type,
            room=obj.get('room', ''),
            label=obj.get('name', '').split('_')[-1] if obj.get('name') else '',
            index=obj.get('index', 0)
        )
        
        # Collection hierarchy
        obj['collection_path'] = naming.get_collection_hierarchy(object_type)
    
    return output_data


def group_by_discipline(output_data: Dict) -> Dict[str, List[Dict]]:
    """
    Group objects by discipline for Blender collection creation.
    
    Returns:
        {
            "ARC": {"Doors": [...], "Walls": [...]},
            "MEP": {"Electrical": [...], "Lighting": [...]},
            ...
        }
    """
    grouped = {}
    
    for obj in output_data.get('objects', []):
        discipline = obj.get('discipline', 'ARC')
        group = obj.get('group', 'Misc')
        
        if discipline not in grouped:
            grouped[discipline] = {}
        if group not in grouped[discipline]:
            grouped[discipline][group] = []
        
        grouped[discipline][group].append(obj)
    
    return grouped


# =============================================================================
# CLI / TEST
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("IFC NAMING LAYER TEST")
    print("=" * 60)
    
    # Load naming layer
    naming = IfcNamingLayer()  # Uses defaults
    
    # Test various object types
    test_types = [
        "roof_slab",
        "floor_slab", 
        "ceiling_main",
        "wall_exterior_north",
        "wall_interior_kitchen",
        "door_single_900_lod300",
        "door_ruang_tamu",
        "switch_1gang_lod300",
        "outlet_13a_twin_lod300",
        "toilet_floor_lod300",
        "discharge_perimeter_1",
        "sofa_3seat",
        "unknown_object"
    ]
    
    print("\nObject Type → IFC Class / Discipline / Group")
    print("-" * 60)
    
    for ot in test_types:
        props = naming.get_properties(ot)
        print(f"{ot:30} → {props.get('ifc_class', '?'):20} {props.get('discipline', '?'):5} {props.get('group', '?')}")
    
    print("\n" + "=" * 60)
    print("BLENDER NAMES")
    print("=" * 60)
    
    for ot in test_types[:6]:
        name = naming.get_blender_name(ot, room="Kitchen", label="D1")
        print(f"{ot:30} → {name}")
    
    print("\n✅ IFC Naming Layer test complete!")
