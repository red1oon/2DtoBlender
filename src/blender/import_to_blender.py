#!/usr/bin/env python3
"""
Blender LOD300 Import - Enhanced with IFC Organization
VERSION: 2025-11-29-IFC-ORGANIZED

Imports extraction output JSON to Blender with:
- IFC discipline collections (ARC, MEP, PLUM, STR)
- Sub-collections by group (Doors, Walls, Lighting, etc.)
- Custom properties for IFC class, discipline, room
- Comprehensive geometry debug logging
- Pre-flight validation
- Post-import verification

Flow:
1. Load extraction output JSON
2. Validate geometry (pre-flight checks)
3. Create discipline collections
4. Fetch LOD300 geometries from database
5. Create meshes with proper organization
6. Assign IFC custom properties
7. Position objects at extracted coordinates
8. Verify and report results

Usage:
    blender --python blender_lod300_import_v2.py -- <input.json> <database.db> [output.blend]
"""

import bpy
import json
import sys
import os
import math
import numpy as np
from mathutils import Vector, Euler
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Add core directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'core'))

try:
    from database_geometry_fetcher import DatabaseGeometryFetcher
    from geometry_validator import GeometryValidator
    VALIDATORS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Optional imports not available: {e}")
    VALIDATORS_AVAILABLE = False


#===============================================================================
# CONFIGURATION
#===============================================================================

# Discipline colors for viewport display
DISCIPLINE_COLORS = {
    'ARC': (0.29, 0.56, 0.85, 1.0),   # Blue - Architecture
    'MEP': (0.96, 0.65, 0.14, 1.0),   # Orange - MEP
    'PLUM': (0.49, 0.83, 0.13, 1.0),  # Green - Plumbing
    'STR': (0.61, 0.35, 0.71, 1.0),   # Purple - Structure
    'UNKNOWN': (0.5, 0.5, 0.5, 1.0),  # Gray - Unknown
}

# Default heights if not in JSON
DEFAULT_WALL_HEIGHT = 3.0
DEFAULT_WALL_THICKNESS = 0.1
DEFAULT_CEILING_HEIGHT = 3.0

# Geometry validation thresholds
MAX_OBJECT_DIMENSION = 50.0  # meters - flag objects larger than this
MIN_OBJECT_DIMENSION = 0.01  # meters - flag objects smaller than this


#===============================================================================
# DEBUG LOGGING
#===============================================================================

class DebugLogger:
    """Comprehensive debug logger for geometry import"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.info = []
        self.geometry_issues = []
        
    def error(self, msg):
        self.errors.append(msg)
        print(f"❌ ERROR: {msg}")
        
    def warn(self, msg):
        self.warnings.append(msg)
        if self.verbose:
            print(f"⚠️  WARN: {msg}")
            
    def log(self, msg):
        self.info.append(msg)
        if self.verbose:
            print(f"   {msg}")
            
    def geometry(self, obj_name, issue):
        """Log geometry-specific issue"""
        self.geometry_issues.append((obj_name, issue))
        print(f"🔺 GEOMETRY [{obj_name}]: {issue}")
        
    def section(self, title):
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
        
    def subsection(self, title):
        print(f"\n--- {title} ---")
        
    def summary(self):
        """Print summary of all issues"""
        self.section("IMPORT SUMMARY")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Geometry Issues: {len(self.geometry_issues)}")
        
        if self.errors:
            print(f"\n   ERRORS:")
            for e in self.errors[:10]:
                print(f"      - {e}")
            if len(self.errors) > 10:
                print(f"      ... and {len(self.errors) - 10} more")
                
        if self.geometry_issues:
            print(f"\n   GEOMETRY ISSUES:")
            for name, issue in self.geometry_issues[:10]:
                print(f"      - {name}: {issue}")
            if len(self.geometry_issues) > 10:
                print(f"      ... and {len(self.geometry_issues) - 10} more")


# Global logger
LOG = DebugLogger(verbose=True)


#===============================================================================
# COLLECTION MANAGEMENT (Blender Outliner Organization)
#===============================================================================

def create_discipline_collections() -> Dict[str, bpy.types.Collection]:
    """
    Create organized collection hierarchy by discipline
    
    Structure:
        Scene Collection
        ├── ARC_Architecture
        │   ├── Doors
        │   ├── Walls
        │   ├── Furniture
        │   └── ...
        ├── MEP_Electrical
        │   ├── Lighting
        │   ├── Switches
        │   └── ...
        ├── PLUM_Plumbing
        │   ├── Fixtures
        │   ├── Drainage
        │   └── ...
        └── STR_Structure
            ├── Slabs
            ├── Roofs
            └── ...
    
    Returns:
        Dict mapping "DISCIPLINE/Group" to collection
    """
    LOG.subsection("Creating Collection Hierarchy")
    
    scene_collection = bpy.context.scene.collection
    collections = {}
    
    # Define hierarchy
    hierarchy = {
        'ARC': {
            'name': 'ARC_Architecture',
            'groups': ['Doors', 'Windows', 'Walls', 'Furniture', 'Bedroom', 'Kitchen', 'Bathroom']
        },
        'MEP': {
            'name': 'MEP_Electrical', 
            'groups': ['Lighting', 'Electrical', 'Switches', 'Outlets', 'Fans']
        },
        'PLUM': {
            'name': 'PLUM_Plumbing',
            'groups': ['Fixtures', 'Drainage', 'Sanitary']
        },
        'STR': {
            'name': 'STR_Structure',
            'groups': ['Slabs', 'Roofs', 'Ceilings', 'Foundations']
        },
        'UNKNOWN': {
            'name': 'UNKNOWN_Uncategorized',
            'groups': ['Other']
        }
    }
    
    for discipline, config in hierarchy.items():
        # Create discipline collection
        disc_coll = bpy.data.collections.new(config['name'])
        scene_collection.children.link(disc_coll)
        collections[discipline] = disc_coll
        
        # Create group sub-collections
        for group in config['groups']:
            group_coll = bpy.data.collections.new(f"{discipline}_{group}")
            disc_coll.children.link(group_coll)
            collections[f"{discipline}/{group}"] = group_coll
            
        LOG.log(f"Created {config['name']} with {len(config['groups'])} groups")
    
    return collections


def get_collection_for_object(collections: Dict, obj_data: Dict) -> bpy.types.Collection:
    """
    Get appropriate collection for an object based on discipline and group
    
    Args:
        collections: Collection hierarchy dict
        obj_data: Object data from JSON
        
    Returns:
        Target collection for this object
    """
    discipline = obj_data.get('discipline', 'UNKNOWN')
    group = obj_data.get('group', 'Other')
    
    # Try specific group first
    key = f"{discipline}/{group}"
    if key in collections:
        return collections[key]
    
    # Fall back to discipline
    if discipline in collections:
        return collections[discipline]
    
    # Ultimate fallback
    return collections.get('UNKNOWN', bpy.context.scene.collection)


#===============================================================================
# IFC PROPERTY ASSIGNMENT
#===============================================================================

def assign_ifc_properties(obj: bpy.types.Object, obj_data: Dict):
    """
    Assign IFC-related custom properties to Blender object
    
    Properties assigned:
        - ifc_class: IfcDoor, IfcWall, etc.
        - ifc_predefined_type: DOOR, SOLIDWALL, etc.
        - discipline: ARC, MEP, PLUM, STR
        - group: Doors, Walls, Lighting, etc.
        - room: Room assignment
        - room_id: Room identifier
        - phase: Construction phase
        - blender_name: Naming convention
    
    Args:
        obj: Blender object
        obj_data: Object data from JSON
    """
    # Core IFC properties
    obj['ifc_class'] = obj_data.get('ifc_class', 'IfcBuildingElement')
    obj['ifc_predefined_type'] = obj_data.get('ifc_predefined_type', 'NOTDEFINED')
    
    # Organization properties
    obj['discipline'] = obj_data.get('discipline', 'UNKNOWN')
    obj['group'] = obj_data.get('group', 'Other')
    
    # Spatial properties
    obj['room'] = obj_data.get('room', 'unknown')
    obj['room_id'] = obj_data.get('room_id', '')
    
    # Phase and naming
    obj['phase'] = obj_data.get('phase', obj_data.get('_phase', ''))
    obj['blender_name'] = obj_data.get('blender_name', obj.name)
    
    # Source tracking
    obj['object_type'] = obj_data.get('object_type', '')
    obj['source'] = obj_data.get('source', obj_data.get('_generation_method', 'unknown'))
    
    # Dimensions if available
    if 'width' in obj_data:
        obj['width'] = obj_data['width']
    if 'height' in obj_data:
        obj['height'] = obj_data['height']
    if 'length' in obj_data:
        obj['length'] = obj_data['length']


def set_object_color_by_discipline(obj: bpy.types.Object, discipline: str):
    """
    Set viewport display color based on discipline
    
    Args:
        obj: Blender object
        discipline: ARC, MEP, PLUM, STR
    """
    color = DISCIPLINE_COLORS.get(discipline, DISCIPLINE_COLORS['UNKNOWN'])
    
    # Create or get material
    mat_name = f"MAT_{discipline}"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.diffuse_color = color
        mat.use_nodes = False
    else:
        mat = bpy.data.materials[mat_name]
    
    # Assign to object
    if obj.data and hasattr(obj.data, 'materials'):
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat


#===============================================================================
# GEOMETRY VALIDATION (Pre-flight)
#===============================================================================

def validate_object_geometry(obj_data: Dict, building_envelope: Dict) -> List[str]:
    """
    Validate object geometry before import
    
    Checks:
        1. Position within building bounds
        2. Reasonable dimensions
        3. Valid rotation values
        4. Required fields present
    
    Args:
        obj_data: Object data from JSON
        building_envelope: Building bounds
        
    Returns:
        List of warning/error messages
    """
    issues = []
    name = obj_data.get('name', 'unnamed')
    
    # Check position
    pos = obj_data.get('position', [0, 0, 0])
    if len(pos) != 3:
        issues.append(f"Invalid position format: {pos}")
        return issues
    
    x, y, z = pos
    
    # Check bounds (with margin for porch, etc.)
    margin = 5.0
    x_min = building_envelope.get('x_min', 0) - margin
    x_max = building_envelope.get('x_max', 20) + margin
    y_min = building_envelope.get('y_min', 0) - margin
    y_max = building_envelope.get('y_max', 20) + margin
    
    if not (x_min <= x <= x_max):
        issues.append(f"X position {x:.2f} outside bounds [{x_min:.2f}, {x_max:.2f}]")
    if not (y_min <= y <= y_max):
        issues.append(f"Y position {y:.2f} outside bounds [{y_min:.2f}, {y_max:.2f}]")
    if z < -1.0 or z > 10.0:
        issues.append(f"Z position {z:.2f} unusual (expected 0-10m)")
    
    # Check rotation
    orientation = obj_data.get('orientation', 0)
    if not isinstance(orientation, (int, float)):
        issues.append(f"Invalid orientation type: {type(orientation)}")
    elif orientation < 0 or orientation > 360:
        issues.append(f"Orientation {orientation}° outside 0-360 range")
    
    # Check for walls with end_point
    if 'wall' in obj_data.get('object_type', '').lower():
        if 'end_point' not in obj_data:
            issues.append("Wall missing end_point")
        else:
            end = obj_data['end_point']
            if len(end) != 3:
                issues.append(f"Invalid end_point format: {end}")
            else:
                # Check wall length
                length = math.sqrt((end[0]-x)**2 + (end[1]-y)**2 + (end[2]-z)**2)
                if length < 0.1:
                    issues.append(f"Wall too short: {length:.3f}m")
                if length > 20.0:
                    issues.append(f"Wall unusually long: {length:.2f}m")
    
    return issues


def preflight_validation(data: Dict) -> Tuple[bool, Dict]:
    """
    Run pre-flight validation on all objects
    
    Args:
        data: Full JSON data
        
    Returns:
        (success, stats) - Whether to proceed and validation statistics
    """
    LOG.section("PRE-FLIGHT VALIDATION")
    
    objects = data.get('objects', [])
    envelope = data.get('building_envelope', {})
    
    stats = {
        'total': len(objects),
        'valid': 0,
        'warnings': 0,
        'errors': 0,
        'by_discipline': {},
        'by_group': {},
        'missing_geometry_types': set()
    }
    
    for obj_data in objects:
        name = obj_data.get('name', 'unnamed')
        discipline = obj_data.get('discipline', 'UNKNOWN')
        group = obj_data.get('group', 'Other')
        
        # Count by category
        stats['by_discipline'][discipline] = stats['by_discipline'].get(discipline, 0) + 1
        stats['by_group'][group] = stats['by_group'].get(group, 0) + 1
        
        # Validate geometry
        issues = validate_object_geometry(obj_data, envelope)
        
        if issues:
            for issue in issues:
                LOG.geometry(name, issue)
            stats['warnings'] += len(issues)
        else:
            stats['valid'] += 1
    
    # Report statistics
    LOG.subsection("Object Distribution")
    print(f"   Total objects: {stats['total']}")
    print(f"   Valid: {stats['valid']}")
    print(f"   With warnings: {stats['total'] - stats['valid']}")
    
    print(f"\n   By Discipline:")
    for disc, count in sorted(stats['by_discipline'].items()):
        print(f"      {disc}: {count}")
    
    print(f"\n   By Group:")
    for group, count in sorted(stats['by_group'].items()):
        print(f"      {group}: {count}")
    
    # Proceed if no critical errors
    success = stats['errors'] == 0
    return success, stats


#===============================================================================
# GEOMETRY CREATION
#===============================================================================

def create_mesh_from_geometry(name: str, geometry_data: Dict, 
                              base_rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> bpy.types.Mesh:
    """
    Create Blender mesh from geometry data with debug logging
    
    Args:
        name: Object name
        geometry_data: Dict with 'vertices', 'faces', 'normals'
        base_rotation: (rx, ry, rz) in radians
        
    Returns:
        bpy.types.Mesh object
    """
    vertices = geometry_data['vertices'].copy()
    faces = geometry_data['faces']
    
    # Debug: Log geometry stats
    LOG.log(f"Creating mesh '{name}': {len(vertices)} verts, {len(faces)} faces")
    
    # Validate geometry
    if len(vertices) == 0:
        LOG.error(f"Mesh '{name}' has no vertices!")
        return None
    if len(faces) == 0:
        LOG.warn(f"Mesh '{name}' has no faces (point cloud?)")
    
    # Apply base rotation if needed
    if any(r != 0.0 for r in base_rotation):
        LOG.log(f"   Applying base rotation: ({math.degrees(base_rotation[0]):.0f}°, "
                f"{math.degrees(base_rotation[1]):.0f}°, {math.degrees(base_rotation[2]):.0f}°)")
        vertices = apply_rotation_to_vertices(vertices, base_rotation)
    
    # Create mesh
    mesh = bpy.data.meshes.new(name=f"{name}_mesh")
    verts = [tuple(v) for v in vertices]
    face_indices = [tuple(f) for f in faces]
    
    mesh.from_pydata(verts, [], face_indices)
    mesh.update()
    mesh.validate()
    
    # Debug: Verify mesh dimensions
    if mesh.vertices:
        xs = [v.co.x for v in mesh.vertices]
        ys = [v.co.y for v in mesh.vertices]
        zs = [v.co.z for v in mesh.vertices]
        
        dims = (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
        
        # Flag unusual dimensions
        if max(dims) > MAX_OBJECT_DIMENSION:
            LOG.geometry(name, f"Very large: {dims[0]:.2f} x {dims[1]:.2f} x {dims[2]:.2f}m")
        if max(dims) < MIN_OBJECT_DIMENSION and max(dims) > 0:
            LOG.geometry(name, f"Very small: {dims[0]:.4f} x {dims[1]:.4f} x {dims[2]:.4f}m")
    
    return mesh


def apply_rotation_to_vertices(vertices: List, rotation: Tuple[float, float, float]) -> List:
    """Apply rotation to vertices using numpy"""
    verts_array = np.array(vertices)
    rx, ry, rz = rotation
    
    # X-axis rotation
    if rx != 0.0:
        c, s = math.cos(rx), math.sin(rx)
        rot = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        verts_array = verts_array @ rot.T
    
    # Y-axis rotation
    if ry != 0.0:
        c, s = math.cos(ry), math.sin(ry)
        rot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        verts_array = verts_array @ rot.T
    
    # Z-axis rotation
    if rz != 0.0:
        c, s = math.cos(rz), math.sin(rz)
        rot = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        verts_array = verts_array @ rot.T
    
    return verts_array.tolist()


def create_geometry_from_bounding_box(name: str, position: List, bounding_box: Dict,
                                      facing: str = '+Z', pivot: str = 'center') -> bpy.types.Object:
    """
    GENERIC: Create box geometry directly from JSON bounding_box data.

    This is the UNIVERSAL translator: JSON bounding_box → Blender mesh
    No database needed! All data comes from annotations.

    Args:
        name: Object name
        position: [x, y, z] from JSON
        bounding_box: {'length', 'width', 'height'} from JSON
        facing: Direction object faces ('+X', '+Y', '+Z', etc.)
        pivot: 'center' or 'base'

    Returns:
        Blender object with baked geometry
    """
    from mathutils import Vector, Euler

    # Extract dimensions from bounding_box
    length = bounding_box.get('length', 1.0)
    width = bounding_box.get('width', 1.0)
    height = bounding_box.get('height', 1.0)

    # Adjust position based on pivot point
    pos = Vector(position)
    if pivot == 'base':
        # Pivot at base means position is bottom center, move up by height/2
        pos.z += height / 2

    # Create cube at position
    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos.x, pos.y, pos.z))
    obj = bpy.context.active_object
    obj.name = name

    # Scale to match bounding_box dimensions
    obj.scale = (length, width, height)

    # Rotate based on facing direction (if needed)
    # '+Y' = default (front faces +Y), '+X' = rotate 90° around Z, etc.
    rotation_map = {
        '+X': (0, 0, math.pi/2),
        '-X': (0, 0, -math.pi/2),
        '+Y': (0, 0, 0),           # Default
        '-Y': (0, 0, math.pi),
        '+Z': (math.pi/2, 0, 0),   # Horizontal plane
        '-Z': (-math.pi/2, 0, 0),
    }

    if facing in rotation_map:
        obj.rotation_euler = Euler(rotation_map[facing], 'XYZ')

    # CRITICAL: Apply scale transform to bake geometry
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    LOG.log(f"Created '{name}': {length:.2f}m × {width:.2f}m × {height:.2f}m at ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")

    return obj


def create_roof_slope_geometry(name: str, position: List, end_point: List,
                               bounding_box: Dict) -> bpy.types.Object:
    """
    Create gable roof slope as plane stretched between eave and ridge

    Args:
        name: Roof slope name
        position: Start point (eave) [x, y, z]
        end_point: Ridge point [x, y, z]
        bounding_box: Dict with 'length', 'width', 'height'

    Returns:
        Blender object (sloped plane)
    """
    from mathutils import Vector

    start = Vector(position)
    ridge = Vector(end_point)

    # Roof dimensions
    roof_length = bounding_box.get('length', 10.0)  # Along building width
    slope_width = bounding_box.get('width', 5.0)    # Slope distance
    thickness = bounding_box.get('height', 0.02)    # Sheet thickness

    # Create plane and scale to roof dimensions
    bpy.ops.mesh.primitive_plane_add(size=1, location=(start.x, start.y, start.z))
    obj = bpy.context.active_object
    obj.name = name

    # Scale plane: X=length (building width), Y=slope width
    obj.scale = (roof_length, slope_width, 1.0)

    # Calculate rotation to slope from eave to ridge
    slope_direction = ridge - start
    slope_angle_x = math.atan2(slope_direction.z, slope_direction.y)  # Pitch angle

    # Rotate plane to match slope
    obj.rotation_euler = Euler((slope_angle_x, 0, 0), 'XYZ')

    # Apply scale transform so geometry is baked
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Move to midpoint between eave and ridge
    mid_y = (start.y + ridge.y) / 2
    mid_z = (start.z + ridge.z) / 2
    obj.location = (start.x, mid_y, mid_z)

    LOG.log(f"Roof '{name}': {roof_length:.2f}m × {slope_width:.2f}m, pitch={math.degrees(slope_angle_x):.1f}°")

    return obj


def create_wall_geometry(name: str, position: List, end_point: List,
                        thickness: float, height: float) -> bpy.types.Object:
    """
    Create wall as box stretched between two points
    
    Args:
        name: Wall name
        position: Start point [x, y, z]
        end_point: End point [x, y, z]
        thickness: Wall thickness in meters
        height: Wall height in meters
        
    Returns:
        Blender object
    """
    start = Vector(position)
    end = Vector(end_point)
    direction = end - start
    length = direction.length
    
    if length < 0.01:
        LOG.error(f"Wall '{name}' has zero length!")
        return None
    
    mid_point = (start + end) / 2
    
    # Create cube at correct size (not using scale transforms)
    # Position at midpoint, but Z should place bottom at 0
    bpy.ops.mesh.primitive_cube_add(size=1, location=(mid_point[0], mid_point[1], height / 2))
    obj = bpy.context.active_object
    obj.name = name

    # Scale: X=length, Y=thickness, Z=height (cube size=1 extends ±0.5, so scale directly)
    obj.scale = (length, thickness, height)

    # Rotate to align with wall direction
    angle = math.atan2(direction[1], direction[0])
    obj.rotation_euler = Euler((0, 0, angle), 'XYZ')

    # CRITICAL FIX: Apply scale transform so geometry is baked, not object-level
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    LOG.log(f"Wall '{name}': {length:.2f}m long, {height:.2f}m high, angle={math.degrees(angle):.0f}°")

    return obj


def create_object_from_geometry(name: str, geometry_data: Dict, obj_data: Dict) -> Optional[bpy.types.Object]:
    """
    Create Blender object from geometry data
    
    Handles:
        - Regular objects (from database geometry)
        - Walls (from position + end_point)
        - Scaled objects (gutters, etc.)
    
    Args:
        name: Object name
        geometry_data: Geometry from database (or None for walls)
        obj_data: Full object data from JSON
        
    Returns:
        Blender object or None if failed
    """
    obj_type = obj_data.get('object_type', '')
    position = obj_data.get('position', [0, 0, 0])
    orientation = obj_data.get('orientation', 0.0)
    
    # Special case: Walls with end_point
    if 'wall' in obj_type.lower() and 'end_point' in obj_data:
        thickness = obj_data.get('thickness', DEFAULT_WALL_THICKNESS)
        height = obj_data.get('height', DEFAULT_WALL_HEIGHT)
        return create_wall_geometry(name, position, obj_data['end_point'], thickness, height)

    # Special case: Roof slopes with end_point and bounding_box
    if 'roof' in obj_type.lower() and 'end_point' in obj_data and 'bounding_box' in obj_data:
        return create_roof_slope_geometry(name, position, obj_data['end_point'], obj_data['bounding_box'])

    # UNIVERSAL FALLBACK: If no database geometry BUT JSON has bounding_box → create from JSON!
    # This is the key insight: JSON already contains complete geometry specs
    if not geometry_data and 'bounding_box' in obj_data:
        facing = obj_data.get('facing', '+Y')
        pivot = obj_data.get('pivot', 'center')
        return create_geometry_from_bounding_box(name, position, obj_data['bounding_box'], facing, pivot)

    # Only fail if BOTH database AND JSON bounding_box are missing
    if not geometry_data:
        LOG.warn(f"No geometry for '{name}' ({obj_type}) - no database entry and no bounding_box in JSON")
        return None
    
    # Get base rotation from geometry (inherent orientation)
    base_rotation = geometry_data.get('base_rotation', (0.0, 0.0, 0.0))
    
    # Create mesh
    mesh = create_mesh_from_geometry(name, geometry_data, base_rotation)
    if not mesh:
        return None
    
    # Create object
    obj = bpy.data.objects.new(name, mesh)
    
    # Position
    obj.location = (position[0], position[1], position[2])
    
    # Rotation (Z-axis only, base already applied to vertices)
    if orientation != 0:
        obj.rotation_euler = Euler((0, 0, math.radians(orientation)), 'XYZ')
    
    # Scale for objects with length parameter (gutters, etc.)
    if 'length' in obj_data:
        geo_dims = geometry_data.get('dimensions', {})
        base_width = geo_dims.get('width', 1.0)
        if base_width > 0:
            scale_x = obj_data['length'] / base_width
            obj.scale = (scale_x, 1.0, 1.0)

    # Scale for objects with dimensions dict (slabs, roofs, etc.)
    elif 'dimensions' in obj_data and geometry_data:
        target_dims = obj_data['dimensions']
        geo_dims = geometry_data.get('dimensions', {})

        # Handle both dict and list formats for dimensions
        if isinstance(target_dims, list):
            # List format: [length, width, thickness]
            target_length = target_dims[0] if len(target_dims) > 0 else None
            target_width = target_dims[1] if len(target_dims) > 1 else None
            target_thickness = target_dims[2] if len(target_dims) > 2 else None
        elif isinstance(target_dims, dict):
            # Dict format: {"length": 9.7, "width": 7.0, "thickness": 0.15}
            target_length = target_dims.get('length', target_dims.get('width', None))
            target_width = target_dims.get('width', target_dims.get('depth', None))
            target_thickness = target_dims.get('thickness', target_dims.get('height', None))
        else:
            LOG.warn(f"Unknown dimensions format for {name}: {type(target_dims)}")
            return obj

        # Get base dimensions from database geometry
        # Note: Geometry may have 90° Y rotation applied, swapping X/Z axes
        base_width_db = geo_dims.get('width', 1.0)
        base_depth_db = geo_dims.get('depth', 1.0)
        base_height_db = geo_dims.get('height', 1.0)

        # Check for base rotation to determine axis mapping
        base_rotation = geometry_data.get('base_rotation', (0.0, 0.0, 0.0))
        has_y_rotation = abs(base_rotation[1]) > 0.1  # 90° Y rotation?

        if has_y_rotation:
            # After 90° Y rotation: X←height, Y←depth, Z←width
            # Target: length(9.7m) × width(7.0m) × thickness(0.15m)
            # Maps to: Z × Y × X in rotated mesh
            scale_x = target_thickness / base_height_db if target_thickness and base_height_db > 0 else 1.0
            scale_y = target_width / base_depth_db if target_width and base_depth_db > 0 else 1.0
            scale_z = target_length / base_width_db if target_length and base_width_db > 0 else 1.0
        else:
            # No rotation: Standard mapping
            scale_x = target_length / base_width_db if target_length and base_width_db > 0 else 1.0
            scale_y = target_width / base_depth_db if target_width and base_depth_db > 0 else 1.0
            scale_z = target_thickness / base_height_db if target_thickness and base_height_db > 0 else 1.0

        obj.scale = (scale_x, scale_y, scale_z)
        LOG.log(f"   Scaled {name}: ({scale_x:.2f}, {scale_y:.2f}, {scale_z:.2f}) to match {target_length}m × {target_width}m × {target_thickness}m")

    return obj


#===============================================================================
# MAIN IMPORT FUNCTION
#===============================================================================

def clear_scene():
    """Clear all objects and collections from scene"""
    # Delete all objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Remove non-default collections
    scene_collection = bpy.context.scene.collection
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    
    LOG.log("Scene cleared")


def import_lod300_geometry(json_file: str, database_path: str) -> Dict:
    """
    Main import function with full IFC organization
    
    Args:
        json_file: Path to extraction output JSON
        database_path: Path to Ifc_Object_Library.db
        
    Returns:
        Import statistics dict
    """
    LOG.section("LOD300 IMPORT WITH IFC ORGANIZATION")
    LOG.log(f"Input JSON: {json_file}")
    LOG.log(f"Database: {database_path}")
    
    # Load JSON
    with open(json_file) as f:
        data = json.load(f)
    
    objects = data.get('objects', [])
    summary = data.get('summary', {})
    envelope = data.get('building_envelope', {})
    rooms = data.get('rooms', {})
    
    LOG.log(f"Loaded {len(objects)} objects from JSON")
    LOG.log(f"Building envelope: {envelope.get('width', '?')}m x {envelope.get('depth', '?')}m")
    LOG.log(f"Rooms defined: {len(rooms)}")
    
    # Pre-flight validation
    valid, validation_stats = preflight_validation(data)
    if not valid:
        LOG.error("Pre-flight validation failed - aborting import")
        return {'success': False, 'error': 'validation_failed'}
    
    # Get unique object types
    object_types = list(set(obj.get('object_type') for obj in objects if obj.get('object_type')))
    LOG.log(f"Unique object types: {len(object_types)}")
    
    # Fetch geometries from database
    LOG.subsection("Fetching Geometries from Database")
    geometries = {}
    missing_types = []
    
    if os.path.exists(database_path):
        try:
            fetcher = DatabaseGeometryFetcher(database_path)
            geometries = fetcher.fetch_all_geometries(object_types)
            fetcher.close()
            LOG.log(f"Fetched {len(geometries)} geometries from database")
        except Exception as e:
            LOG.error(f"Database error: {e}")
    else:
        LOG.error(f"Database not found: {database_path}")
    
    # Check for missing geometries
    for obj_type in object_types:
        if obj_type and obj_type not in geometries:
            # Walls don't need database geometry
            if 'wall' not in obj_type.lower():
                missing_types.append(obj_type)
    
    if missing_types:
        LOG.warn(f"Missing geometries for {len(missing_types)} types:")
        for t in missing_types[:10]:
            LOG.log(f"   - {t}")
        if len(missing_types) > 10:
            LOG.log(f"   ... and {len(missing_types) - 10} more")
    
    # Clear scene and create collections
    clear_scene()
    collections = create_discipline_collections()
    
    # Import statistics
    stats = {
        'success': True,
        'total': len(objects),
        'placed': 0,
        'skipped': 0,
        'by_discipline': {},
        'by_group': {},
        'errors': []
    }
    
    # Create objects
    LOG.section("CREATING OBJECTS IN BLENDER")
    
    for i, obj_data in enumerate(objects, 1):
        name = obj_data.get('name', f'object_{i}')
        obj_type = obj_data.get('object_type', '')
        discipline = obj_data.get('discipline', 'UNKNOWN')
        group = obj_data.get('group', 'Other')
        
        try:
            # Get geometry (None for walls, they're created procedurally)
            geometry = geometries.get(obj_type)
            
            # Create object
            obj = create_object_from_geometry(name, geometry, obj_data)
            
            if obj:
                # Assign IFC properties
                assign_ifc_properties(obj, obj_data)
                
                # Set color by discipline
                set_object_color_by_discipline(obj, discipline)
                
                # Link to appropriate collection
                target_collection = get_collection_for_object(collections, obj_data)
                
                # Unlink from default collection if linked there
                if obj.name in bpy.context.scene.collection.objects:
                    bpy.context.scene.collection.objects.unlink(obj)
                
                # Link to target collection
                target_collection.objects.link(obj)
                
                # Update stats
                stats['placed'] += 1
                stats['by_discipline'][discipline] = stats['by_discipline'].get(discipline, 0) + 1
                stats['by_group'][group] = stats['by_group'].get(group, 0) + 1
            else:
                stats['skipped'] += 1
                
        except Exception as e:
            LOG.error(f"Failed to create {name}: {e}")
            stats['errors'].append((name, str(e)))
            stats['skipped'] += 1
        
        # Progress
        if i % 20 == 0:
            LOG.log(f"Progress: {i}/{len(objects)} ({stats['placed']} placed)")
    
    # Final report
    LOG.section("IMPORT COMPLETE")
    print(f"   Total objects: {stats['total']}")
    print(f"   Placed: {stats['placed']}")
    print(f"   Skipped: {stats['skipped']}")
    
    print(f"\n   By Discipline:")
    for disc, count in sorted(stats['by_discipline'].items()):
        print(f"      {disc}: {count}")
    
    print(f"\n   By Group:")
    for group, count in sorted(stats['by_group'].items(), key=lambda x: -x[1])[:10]:
        print(f"      {group}: {count}")
    
    # Verification
    expected = summary.get('total_objects', len(objects))
    if stats['placed'] == expected:
        print(f"\n✅ Hash total verified: {stats['placed']}/{expected}")
    else:
        print(f"\n⚠️  Hash total mismatch: {stats['placed']}/{expected}")
        print(f"   Missing: {expected - stats['placed']} objects")
    
    # Log any issues
    LOG.summary()
    
    return stats


#===============================================================================
# MAIN ENTRY POINT
#===============================================================================

if __name__ == "__main__":
    argv = sys.argv
    
    # Blender arguments come after "--"
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    
    if len(argv) < 2:
        print("""
Usage: blender --python blender_lod300_import_v2.py -- <input.json> <database.db> [output.blend]

Arguments:
    input.json      Extraction output JSON file
    database.db     Path to Ifc_Object_Library.db
    output.blend    Output Blender file (optional, default: output.blend)

Example:
    blender --python blender_lod300_import_v2.py -- \\
        output_artifacts/TB-LKTN_HOUSE_OUTPUT_20251129_125842_FINAL.json \\
        DatabaseFiles/Ifc_Object_Library.db \\
        terrace_house.blend
        """)
        sys.exit(1)
    
    json_file = argv[0]
    database_path = argv[1]
    output_file = argv[2] if len(argv) > 2 else 'output.blend'
    
    # Run import
    stats = import_lod300_geometry(json_file, database_path)
    
    if stats.get('success', False):
        # Save Blender file
        bpy.ops.wm.save_as_mainfile(filepath=output_file)
        print(f"\n✅ Blender file saved: {output_file}")
    else:
        print(f"\n❌ Import failed - file not saved")
        sys.exit(1)
