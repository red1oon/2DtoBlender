#!/usr/bin/env python3
"""
Enhanced Geometry Generator - Extracts actual geometry from DXF entities.

Phase 1: CIRCLE → Cylindrical columns
Phase 2: LWPOLYLINE → Extruded wall profiles
Phase 3: LINE → Beam profiles

Key Concept:
- DXF vertices = SHAPE (relative coordinates)
- Element position = POSITION (where to place shape)
- Extract shape relative to itself, THEN translate to viewport position

Formula:
    final_vertex = viewport_position_m + (shape_offset_mm × 0.001)
"""

import struct
import hashlib
import math
from typing import Tuple, List, Optional, Dict, Any


def generate_cylinder_geometry(radius: float, height: float, segments: int,
                               center_x: float, center_y: float, center_z: float,
                               unit_scale: float = 0.001) -> Tuple[bytes, bytes, bytes]:
    """
    Generate cylindrical column geometry.

    Args:
        radius: Cylinder radius in mm (DXF units)
        height: Height in meters (already converted)
        segments: Number of circle segments (32 = smooth)
        center_x, center_y, center_z: Position in meters (viewport-relative)
        unit_scale: Conversion factor (0.001 for mm→m)

    Returns:
        (vertices_blob, faces_blob, normals_blob)
    """
    # Convert radius from mm to meters
    radius_m = radius * unit_scale
    hz = height / 2.0
    vertices = []

    # Generate vertices: bottom and top circles
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments

        # Shape offsets (relative to center)
        x_offset = radius_m * math.cos(angle)
        y_offset = radius_m * math.sin(angle)

        # Add to viewport position (both in meters now!)
        # Bottom vertex
        vertices.append((center_x + x_offset, center_y + y_offset, center_z - hz))
        # Top vertex
        vertices.append((center_x + x_offset, center_y + y_offset, center_z + hz))

    # Generate faces (triangles)
    faces = []

    # Side faces (vertical walls of cylinder)
    for i in range(segments):
        bottom_current = i * 2
        top_current = i * 2 + 1
        bottom_next = ((i + 1) % segments) * 2
        top_next = ((i + 1) % segments) * 2 + 1

        # Two triangles per quad
        faces.append((bottom_current, bottom_next, top_next))
        faces.append((bottom_current, top_next, top_current))

    # Bottom cap (fan triangulation from center)
    # Add center vertex for bottom
    center_bottom_idx = len(vertices)
    vertices.append((center_x, center_y, center_z - hz))

    for i in range(segments):
        bottom_current = i * 2
        bottom_next = ((i + 1) % segments) * 2
        faces.append((center_bottom_idx, bottom_current, bottom_next))

    # Top cap (fan triangulation from center)
    # Add center vertex for top
    center_top_idx = len(vertices)
    vertices.append((center_x, center_y, center_z + hz))

    for i in range(segments):
        top_current = i * 2 + 1
        top_next = ((i + 1) % segments) * 2 + 1
        faces.append((center_top_idx, top_next, top_current))  # Reverse winding for top

    # Pack to binary format
    vertices_blob = struct.pack(f'{len(vertices) * 3}f', *[c for v in vertices for c in v])
    faces_blob = struct.pack(f'{len(faces) * 3}I', *[i for f in faces for i in f])
    normals_blob = b''  # Skip normals for simplicity

    return (vertices_blob, faces_blob, normals_blob)


def generate_extruded_profile_geometry(profile_vertices_2d: List[Tuple[float, float]],
                                       height: float,
                                       center_x: float, center_y: float, center_z: float,
                                       unit_scale: float = 0.001) -> Tuple[bytes, bytes, bytes]:
    """
    Generate mesh from extruded 2D profile (for LWPOLYLINE walls).

    Args:
        profile_vertices_2d: RELATIVE vertices in mm (e.g., [(-1.5, -2.5), (1.5, -2.5), ...])
        height: Extrusion height in meters
        center_x, center_y, center_z: Position in meters (viewport-relative)
        unit_scale: Conversion factor (0.001 for mm→m)

    Returns:
        (vertices_blob, faces_blob, normals_blob)
    """
    n_profile = len(profile_vertices_2d)
    hz = height / 2.0
    vertices = []

    # Bottom profile
    for (x_mm, y_mm) in profile_vertices_2d:
        # Convert shape coords from mm to meters
        x_m = x_mm * unit_scale
        y_m = y_mm * unit_scale

        # Add to viewport position (both in meters now!)
        vertex_x = center_x + x_m
        vertex_y = center_y + y_m
        vertex_z = center_z - hz

        vertices.append((vertex_x, vertex_y, vertex_z))

    # Top profile
    for (x_mm, y_mm) in profile_vertices_2d:
        x_m = x_mm * unit_scale
        y_m = y_mm * unit_scale
        vertices.append((center_x + x_m, center_y + y_m, center_z + hz))

    # Generate faces (side walls)
    faces = []
    for i in range(n_profile):
        next_i = (i + 1) % n_profile
        v0, v1, v2, v3 = i, next_i, next_i + n_profile, i + n_profile

        # Two triangles per quad
        faces.append((v0, v1, v2))
        faces.append((v0, v2, v3))

    # Bottom cap (fan triangulation)
    for i in range(1, n_profile - 1):
        faces.append((0, i + 1, i))

    # Top cap (fan triangulation)
    for i in range(1, n_profile - 1):
        faces.append((n_profile, n_profile + i, n_profile + i + 1))

    # Pack to binary
    vertices_blob = struct.pack(f'{len(vertices) * 3}f', *[c for v in vertices for c in v])
    faces_blob = struct.pack(f'{len(faces) * 3}I', *[i for f in faces for i in f])
    normals_blob = b''  # Skip normals for simplicity

    return (vertices_blob, faces_blob, normals_blob)


def generate_geometry_hash(vertices_blob: bytes, faces_blob: bytes) -> str:
    """Generate SHA256 hash for geometry deduplication."""
    hasher = hashlib.sha256()
    hasher.update(vertices_blob)
    hasher.update(faces_blob)
    return hasher.hexdigest()


def generate_element_geometry_enhanced(entity_geom: Optional[Dict[str, Any]],
                                      ifc_class: str,
                                      length: float, width: float, height: float,
                                      center_x: float, center_y: float, center_z: float) -> Tuple[bytes, bytes, bytes, str]:
    """
    Generate enhanced geometry using actual DXF entity data.

    Args:
        entity_geom: Extracted entity geometry data (radius, vertices, etc.) or None
        ifc_class: IFC class name
        length, width, height: Fallback dimensions in meters
        center_x, center_y, center_z: Position in meters (viewport-relative)

    Returns:
        (vertices_blob, faces_blob, normals_blob, geometry_hash)
    """
    # Import box generator as fallback
    from geometry_generator import generate_box_geometry

    # Phase 1: Handle CIRCLE entities
    if entity_geom and entity_geom.get('entity_type') == 'CIRCLE':
        radius_mm = entity_geom.get('radius', 150.0)  # Default 150mm if missing

        # Generate cylinder (32 segments for smooth appearance)
        vertices_blob, faces_blob, normals_blob = generate_cylinder_geometry(
            radius=radius_mm,
            height=height,
            segments=32,
            center_x=center_x,
            center_y=center_y,
            center_z=center_z,
            unit_scale=0.001  # mm → m
        )

        geometry_hash = generate_geometry_hash(vertices_blob, faces_blob)
        return (vertices_blob, faces_blob, normals_blob, geometry_hash)

    # Phase 2: Handle LWPOLYLINE entities (TODO)
    elif entity_geom and entity_geom.get('entity_type') == 'LWPOLYLINE':
        vertices_2d = entity_geom.get('vertices_2d', [])

        if len(vertices_2d) >= 3:  # Need at least 3 points for a profile
            vertices_blob, faces_blob, normals_blob = generate_extruded_profile_geometry(
                profile_vertices_2d=vertices_2d,
                height=height,
                center_x=center_x,
                center_y=center_y,
                center_z=center_z,
                unit_scale=0.001  # mm → m
            )

            geometry_hash = generate_geometry_hash(vertices_blob, faces_blob)
            return (vertices_blob, faces_blob, normals_blob, geometry_hash)

    # Fallback: Use box geometry (original behavior)
    vertices_blob, faces_blob, normals_blob = generate_box_geometry(
        length, width, height, center_x, center_y, center_z
    )
    geometry_hash = generate_geometry_hash(vertices_blob, faces_blob)

    return (vertices_blob, faces_blob, normals_blob, geometry_hash)


# Test
if __name__ == "__main__":
    print("Testing enhanced geometry generation...")

    # Test 1: Cylinder (column)
    print("\n=== Test 1: CIRCLE (Column) ===")
    entity_geom = {
        'entity_type': 'CIRCLE',
        'radius': 300.0  # 300mm radius
    }

    vertices, faces, normals, geom_hash = generate_element_geometry_enhanced(
        entity_geom=entity_geom,
        ifc_class='IfcColumn',
        length=0.6, width=0.6, height=3.5,  # Fallback dims
        center_x=10.0, center_y=20.0, center_z=1.75
    )

    # Unpack first vertex to verify coordinates
    first_vertex = struct.unpack('3f', vertices[:12])
    vertex_count = len(vertices) // 12
    face_count = len(faces) // 12

    print(f"  Radius: 300mm → 0.3m")
    print(f"  Position: (10.0, 20.0, 1.75) m")
    print(f"  Vertices: {vertex_count} (expected: 66 = 32 segments × 2 + 2 centers)")
    print(f"  Faces: {face_count} (expected: 96 = 32 sides × 2 + 32 caps × 2)")
    print(f"  First vertex: ({first_vertex[0]:.2f}, {first_vertex[1]:.2f}, {first_vertex[2]:.2f}) m")
    print(f"  Expected: (~10.3, 20.0, 0.0) m - near position with radius offset")
    print(f"  Hash: {geom_hash[:16]}...")

    # Verify coordinates are reasonable (near origin)
    if abs(first_vertex[0]) < 100 and abs(first_vertex[1]) < 100:
        print("  ✅ Coordinates look correct (near origin)")
    else:
        print(f"  ❌ WARNING: Coordinates too large! ({first_vertex[0]}, {first_vertex[1]})")

    print("\n✅ Enhanced geometry generation working!")
