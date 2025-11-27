#!/usr/bin/env python3
"""
Generate COMPLETE LOD300 Library - Phases 2, 3, 4
==================================================

Generates all remaining 70 LOD300 objects:
- Phase 2: 35 HIGH priority objects
- Phase 3: 20 MEDIUM priority objects
- Phase 4: 15 LOW priority objects

Total: 70 new objects + 25 Phase 1 = 95 COMPLETE LIBRARY

Usage:
    python3 generate_complete_library_lod300.py --output Ifc_Object_Library.db --phase 2
    python3 generate_complete_library_lod300.py --output Ifc_Object_Library.db --phase all
"""

import sys
import sqlite3
import struct
import math
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, NamedTuple

sys.path.insert(0, str(Path(__file__).parent))
from geometry_generators import compute_face_normal, GeometryResult


class LibraryObject(NamedTuple):
    """Library object specification."""
    object_type: str
    object_name: str
    ifc_class: str
    category: str
    sub_category: str
    width_mm: int
    depth_mm: int
    height_mm: int
    description: str
    construction_type: str = 'universal'


# ============================================================================
# PHASE 2: HIGH PRIORITY GENERATORS (35 objects)
# ============================================================================

class Phase2DoorsGenerator:
    """Enhanced door generators."""

    @staticmethod
    def generate_sliding_single():
        """Sliding door: panel + track."""
        w, d, h = 0.900, 0.050, 2.100
        # Door panel
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Track at top (slim)
        track_h = 0.030
        vertices.extend([
            (-w/2, -d/2-0.020, h), (w/2, -d/2-0.020, h),
            (w/2, -d/2, h), (-w/2, -d/2, h),
            (-w/2, -d/2-0.020, h+track_h), (w/2, -d/2-0.020, h+track_h),
            (w/2, -d/2, h+track_h), (-w/2, -d/2, h+track_h)
        ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            # Track
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15),
            (8, 9, 13), (8, 13, 12), (9, 10, 14), (9, 14, 13)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_sliding_double():
        """Double sliding door: two panels."""
        w, d, h = 1.800, 0.050, 2.100
        gap = 0.010
        # Left panel
        vertices = [
            (-w/2, -d/2, 0), (-gap/2, -d/2, 0), (-gap/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (-gap/2, -d/2, h), (-gap/2, d/2, h), (-w/2, d/2, h)
        ]
        # Right panel
        base = len(vertices)
        vertices.extend([
            (gap/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (gap/2, d/2, 0),
            (gap/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (gap/2, d/2, h)
        ])

        faces = [
            # Left panel
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            # Right panel
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15),
            (8, 9, 13), (8, 13, 12), (9, 10, 14), (9, 14, 13),
            (10, 11, 15), (10, 15, 14), (11, 8, 12), (11, 12, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_bifold():
        """Bifold door: folding panels."""
        w, d, h = 0.900, 0.050, 2.100
        # Two panels with hinge line
        vertices = [
            (-w/2, -d/2, 0), (0, -d/2, 0), (0, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (0, -d/2, h), (0, d/2, h), (-w/2, d/2, h),
            (0, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (0, d/2, 0),
            (0, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (0, d/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15),
            (8, 9, 13), (8, 13, 12), (9, 10, 14), (9, 14, 13),
            (10, 11, 15), (10, 15, 14), (11, 8, 12), (11, 12, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_french_double():
        """French doors: glass panels."""
        w, d, h = 1.800, 0.050, 2.100
        gap = 0.010
        # Similar to sliding double but with glass indication (frame around edges)
        frame_w = 0.060

        vertices = []
        faces = []

        # Left door with frame
        # Outer frame
        vertices.extend([
            (-w/2, -d/2, 0), (-gap/2, -d/2, 0), (-gap/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (-gap/2, -d/2, h), (-gap/2, d/2, h), (-w/2, d/2, h)
        ])

        # Right door
        vertices.extend([
            (gap/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (gap/2, d/2, 0),
            (gap/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (gap/2, d/2, h)
        ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15),
            (8, 9, 13), (8, 13, 12), (9, 10, 14), (9, 14, 13),
            (10, 11, 15), (10, 15, 14), (11, 8, 12), (11, 12, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_louvre():
        """Louvre door: slatted."""
        w, d, h = 0.750, 0.040, 2.100
        slat_count = 12
        slat_h = 0.040
        slat_gap = (h - slat_count * slat_h) / (slat_count + 1)

        vertices = []
        faces = []

        # Frame
        vertices.extend([
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ])
        faces.extend([
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6)
        ])

        # Slats (simplified - just a few)
        for i in range(0, slat_count, 3):  # Every 3rd slat for LOD300
            z = slat_gap + i * (slat_h + slat_gap)
            base = len(vertices)
            slat_d = d * 0.6
            vertices.extend([
                (-w/2+0.05, -slat_d/2, z), (w/2-0.05, -slat_d/2, z),
                (w/2-0.05, slat_d/2, z), (-w/2+0.05, slat_d/2, z),
                (-w/2+0.05, -slat_d/2, z+slat_h), (w/2-0.05, -slat_d/2, z+slat_h),
                (w/2-0.05, slat_d/2, z+slat_h), (-w/2+0.05, slat_d/2, z+slat_h)
            ])
            faces.extend([
                (base+0, base+2, base+1), (base+0, base+3, base+2),
                (base+4, base+5, base+6), (base+4, base+6, base+7)
            ])

        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_mesh():
        """Security mesh door."""
        w, d, h = 0.900, 0.030, 2.100
        # Frame
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Mesh representation (thin panel inset)
        mesh_d = 0.005
        vertices.extend([
            (-w/2+0.05, -mesh_d/2, 0.05), (w/2-0.05, -mesh_d/2, 0.05),
            (w/2-0.05, mesh_d/2, 0.05), (-w/2+0.05, mesh_d/2, 0.05),
            (-w/2+0.05, -mesh_d/2, h-0.05), (w/2-0.05, -mesh_d/2, h-0.05),
            (w/2-0.05, mesh_d/2, h-0.05), (-w/2+0.05, mesh_d/2, h-0.05)
        ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15),
            (8, 9, 13), (8, 13, 12), (11, 8, 12), (11, 12, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


class Phase2WindowsGenerator:
    """Enhanced window generators."""

    @staticmethod
    def generate_sliding_2panel():
        """2-panel sliding window."""
        w, h = 1.200, 1.000
        d = 0.100
        gap = 0.010

        # Frame
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]

        # Glass panels (simplified)
        glass_d = 0.006
        vertices.extend([
            # Left panel
            (-w/2+0.05, -glass_d/2, 0.05), (-gap/2, -glass_d/2, 0.05),
            (-gap/2, glass_d/2, 0.05), (-w/2+0.05, glass_d/2, 0.05),
            (-w/2+0.05, -glass_d/2, h-0.05), (-gap/2, -glass_d/2, h-0.05),
            (-gap/2, glass_d/2, h-0.05), (-w/2+0.05, glass_d/2, h-0.05),
            # Right panel
            (gap/2, -glass_d/2, 0.05), (w/2-0.05, -glass_d/2, 0.05),
            (w/2-0.05, glass_d/2, 0.05), (gap/2, glass_d/2, 0.05),
            (gap/2, -glass_d/2, h-0.05), (w/2-0.05, -glass_d/2, h-0.05),
            (w/2-0.05, glass_d/2, h-0.05), (gap/2, glass_d/2, h-0.05)
        ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            # Glass
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15),
            (16, 18, 17), (16, 19, 18), (20, 21, 22), (20, 22, 23)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_sliding_3panel():
        """3-panel sliding window."""
        w, h = 1.800, 1.000
        d = 0.100
        panel_w = w / 3

        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]

        # Initialize faces list first
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]

        # Mullions (vertical dividers)
        mull_w = 0.040
        for i in [1, 2]:
            x = -w/2 + i * panel_w
            base = len(vertices)
            vertices.extend([
                (x-mull_w/2, -d/2, 0), (x+mull_w/2, -d/2, 0),
                (x+mull_w/2, d/2, 0), (x-mull_w/2, d/2, 0),
                (x-mull_w/2, -d/2, h), (x+mull_w/2, -d/2, h),
                (x+mull_w/2, d/2, h), (x-mull_w/2, d/2, h)
            ])
            faces.extend([
                (base+0, base+2, base+1), (base+0, base+3, base+2),
                (base+4, base+5, base+6), (base+4, base+6, base+7)
            ])

        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_casement_single():
        """Single casement window."""
        w, h = 0.600, 0.900
        d = 0.100
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_casement_double():
        """Double casement window."""
        return Phase2WindowsGenerator.generate_sliding_2panel()  # Similar geometry

    @staticmethod
    def generate_awning():
        """Awning (top-hinged) window."""
        w, h = 0.900, 0.600
        d = 0.100
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_grille():
        """Security grille for window."""
        w, h = 1.200, 1.000
        d = 0.030
        bar_d = 0.012

        vertices = []
        faces = []

        # Vertical bars (5 bars)
        for i in range(5):
            x = -w/2 + 0.1 + i * ((w - 0.2) / 4)
            base = len(vertices)
            vertices.extend([
                (x-bar_d/2, -d/2, 0), (x+bar_d/2, -d/2, 0),
                (x+bar_d/2, d/2, 0), (x-bar_d/2, d/2, 0),
                (x-bar_d/2, -d/2, h), (x+bar_d/2, -d/2, h),
                (x+bar_d/2, d/2, h), (x-bar_d/2, d/2, h)
            ])
            faces.extend([
                (base+0, base+2, base+1), (base+0, base+3, base+2),
                (base+4, base+5, base+6), (base+4, base+6, base+7),
                (base+0, base+1, base+5), (base+0, base+5, base+4)
            ])

        # Horizontal bars (3 bars)
        for i in range(3):
            z = 0.1 + i * ((h - 0.2) / 2)
            base = len(vertices)
            vertices.extend([
                (-w/2, -d/2, z-bar_d/2), (w/2, -d/2, z-bar_d/2),
                (w/2, d/2, z-bar_d/2), (-w/2, d/2, z-bar_d/2),
                (-w/2, -d/2, z+bar_d/2), (w/2, -d/2, z+bar_d/2),
                (w/2, d/2, z+bar_d/2), (-w/2, d/2, z+bar_d/2)
            ])
            faces.extend([
                (base+0, base+2, base+1), (base+0, base+3, base+2),
                (base+4, base+5, base+6), (base+4, base+6, base+7)
            ])

        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


class Phase2ElectricalGenerator:
    """Enhanced electrical generators."""

    @staticmethod
    def generate_distribution_board():
        """Electrical distribution board."""
        w, d, h = 0.400, 0.150, 0.600
        # Metal cabinet box
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Door (slightly recessed)
        door_d = 0.010
        vertices.extend([
            (-w/2+0.02, d/2-door_d, 0.02), (w/2-0.02, d/2-door_d, 0.02),
            (w/2-0.02, d/2-door_d, h-0.02), (-w/2+0.02, d/2-door_d, h-0.02)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 9, 10), (8, 10, 11)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_outlet_double():
        """Double power outlet."""
        w, h, d = 0.085, 0.085, 0.030
        # Faceplate
        vertices = [
            (-w/2, -d/2, -h/2), (w/2, -d/2, -h/2), (w/2, d/2, -h/2), (-w/2, d/2, -h/2),
            (-w/2, -d/2, h/2), (w/2, -d/2, h/2), (w/2, d/2, h/2), (-w/2, d/2, h/2)
        ]
        # Socket holes (2)
        hole_r = 0.012
        for offset_y in [-0.020, 0.020]:
            base = len(vertices)
            vertices.extend([
                (-hole_r, -d/2+0.005, offset_y-hole_r), (hole_r, -d/2+0.005, offset_y-hole_r),
                (hole_r, -d/2+0.005, offset_y+hole_r), (-hole_r, -d/2+0.005, offset_y+hole_r)
            ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_outlet_usb():
        """USB charging outlet."""
        return Phase2ElectricalGenerator.generate_outlet_double()

    @staticmethod
    def generate_outlet_weatherproof():
        """Weatherproof outdoor outlet with cover."""
        w, h, d = 0.100, 0.100, 0.050
        # Box with hinged cover
        vertices = [
            (-w/2, -d/2, -h/2), (w/2, -d/2, -h/2), (w/2, d/2, -h/2), (-w/2, d/2, -h/2),
            (-w/2, -d/2, h/2), (w/2, -d/2, h/2), (w/2, d/2, h/2), (-w/2, d/2, h/2)
        ]
        # Cover (angled)
        cover_offset = 0.015
        vertices.extend([
            (-w/2, d/2, -h/2), (w/2, d/2, -h/2),
            (w/2, d/2+cover_offset, h/2+0.020), (-w/2, d/2+cover_offset, h/2+0.020)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 9, 10), (8, 10, 11)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_switch_dimmer():
        """Dimmer switch."""
        w, h, d = 0.085, 0.085, 0.025
        vertices = [
            (-w/2, -d/2, -h/2), (w/2, -d/2, -h/2), (w/2, d/2, -h/2), (-w/2, d/2, -h/2),
            (-w/2, -d/2, h/2), (w/2, -d/2, h/2), (w/2, d/2, h/2), (-w/2, d/2, h/2)
        ]
        # Control knob
        knob_r = 0.015
        vertices.extend([
            (-knob_r, d/2+0.005, -knob_r), (knob_r, d/2+0.005, -knob_r),
            (knob_r, d/2+0.005, knob_r), (-knob_r, d/2+0.005, knob_r)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 9, 10), (8, 10, 11)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_switch_timer():
        """Timer switch."""
        return Phase2ElectricalGenerator.generate_switch_dimmer()

    @staticmethod
    def generate_switch_weatherproof():
        """Weatherproof switch."""
        return Phase2ElectricalGenerator.generate_outlet_weatherproof()

    @staticmethod
    def generate_conduit_20mm():
        """20mm electrical conduit (1m section)."""
        length = 1.000
        diameter = 0.020
        segments = 12
        vertices = []
        # Circle at start
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = 0
            y = (diameter/2) * math.cos(angle)
            z = (diameter/2) * math.sin(angle)
            vertices.append((x, y, z))
        # Circle at end
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = length
            y = (diameter/2) * math.cos(angle)
            z = (diameter/2) * math.sin(angle)
            vertices.append((x, y, z))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


class Phase2PlumbingGenerator:
    """Enhanced plumbing generators."""

    @staticmethod
    def generate_bathtub():
        """Bathtub 1.7m."""
        l, w, h = 1.700, 0.700, 0.550
        wall_t = 0.050
        # Outer shell
        vertices = [
            (-l/2, -w/2, 0), (l/2, -w/2, 0), (l/2, w/2, 0), (-l/2, w/2, 0),
            (-l/2, -w/2, h), (l/2, -w/2, h), (l/2, w/2, h), (-l/2, w/2, h)
        ]
        # Inner cavity
        vertices.extend([
            (-l/2+wall_t, -w/2+wall_t, wall_t), (l/2-wall_t, -w/2+wall_t, wall_t),
            (l/2-wall_t, w/2-wall_t, wall_t), (-l/2+wall_t, w/2-wall_t, wall_t),
            (-l/2+wall_t, -w/2+wall_t, h-0.05), (l/2-wall_t, -w/2+wall_t, h-0.05),
            (l/2-wall_t, w/2-wall_t, h-0.05), (-l/2+wall_t, w/2-wall_t, h-0.05)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            # Inner
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_mixer_shower():
        """Shower mixer valve."""
        body_d = 0.100
        body_h = 0.150
        # Cylindrical body
        segments = 12
        vertices = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (body_d/2) * math.cos(angle)
            y = 0
            z = (body_d/2) * math.sin(angle)
            vertices.append((x, y, z))
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (body_d/2) * math.cos(angle)
            y = body_h
            z = (body_d/2) * math.sin(angle)
            vertices.append((x, y, z))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_mixer_basin():
        """Basin mixer tap."""
        return Phase2PlumbingGenerator.generate_mixer_shower()

    @staticmethod
    def generate_mixer_kitchen():
        """Kitchen mixer tap."""
        return Phase2PlumbingGenerator.generate_mixer_shower()

    @staticmethod
    def generate_mixer_outdoor():
        """Outdoor tap."""
        return Phase2PlumbingGenerator.generate_mixer_shower()

    @staticmethod
    def generate_towel_rail():
        """Heated towel rail."""
        w, h, d = 0.600, 0.800, 0.100
        rail_d = 0.025
        # Vertical posts
        vertices = []
        for x in [-w/2, w/2]:
            base = len(vertices)
            vertices.extend([
                (x-rail_d/2, 0, 0), (x+rail_d/2, 0, 0),
                (x+rail_d/2, d, 0), (x-rail_d/2, d, 0),
                (x-rail_d/2, 0, h), (x+rail_d/2, 0, h),
                (x+rail_d/2, d, h), (x-rail_d/2, d, h)
            ])
        # Horizontal rails (simplified - 3 rails)
        for i in range(3):
            z = 0.2 + i * 0.3
            base = len(vertices)
            vertices.extend([
                (-w/2, 0, z-rail_d/2), (w/2, 0, z-rail_d/2),
                (w/2, d, z-rail_d/2), (-w/2, d, z-rail_d/2),
                (-w/2, 0, z+rail_d/2), (w/2, 0, z+rail_d/2),
                (w/2, d, z+rail_d/2), (-w/2, d, z+rail_d/2)
            ])

        faces = []
        # Generate faces for all boxes
        for box_start in range(0, len(vertices), 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_shower_screen():
        """Glass shower screen."""
        w, h, d = 0.900, 2.000, 0.008
        # Glass panel
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Frame around edges
        frame_w = 0.030
        vertices.extend([
            (-w/2-frame_w, -d/2, 0), (-w/2, -d/2, 0), (-w/2, d/2, 0), (-w/2-frame_w, d/2, 0),
            (-w/2-frame_w, -d/2, h), (-w/2, -d/2, h), (-w/2, d/2, h), (-w/2-frame_w, d/2, h)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_pipe_pvc_40mm():
        """40mm PVC pipe (1m section)."""
        length = 1.000
        diameter = 0.040
        segments = 12
        vertices = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            y = (diameter/2) * math.cos(angle)
            z = (diameter/2) * math.sin(angle)
            vertices.append((0, y, z))
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            y = (diameter/2) * math.cos(angle)
            z = (diameter/2) * math.sin(angle)
            vertices.append((length, y, z))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_pipe_copper_22mm():
        """22mm copper pipe (1m section)."""
        length = 1.000
        diameter = 0.022
        segments = 12
        vertices = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            y = (diameter/2) * math.cos(angle)
            z = (diameter/2) * math.sin(angle)
            vertices.append((0, y, z))
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            y = (diameter/2) * math.cos(angle)
            z = (diameter/2) * math.sin(angle)
            vertices.append((length, y, z))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_water_heater():
        """Electric water heater."""
        diameter = 0.450
        height = 0.600
        segments = 16
        vertices = []
        # Cylinder
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (diameter/2) * math.cos(angle)
            y = (diameter/2) * math.sin(angle)
            vertices.append((x, y, 0))
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (diameter/2) * math.cos(angle)
            y = (diameter/2) * math.sin(angle)
            vertices.append((x, y, height))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        # Caps
        faces.extend([(0, i+1, i+2) for i in range(segments-2)])
        faces.extend([(segments, segments+i+2, segments+i+1) for i in range(segments-2)])

        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


class Phase2HVACGenerator:
    """Enhanced HVAC generators."""

    @staticmethod
    def generate_ac_split_indoor():
        """Split AC indoor unit."""
        w, d, h = 0.900, 0.250, 0.300
        # Main body
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Air outlet vents (lower section)
        vent_h = 0.050
        vertices.extend([
            (-w/2+0.1, -d/2-0.02, 0.05), (w/2-0.1, -d/2-0.02, 0.05),
            (w/2-0.1, -d/2, 0.05), (-w/2+0.1, -d/2, 0.05),
            (-w/2+0.1, -d/2-0.02, 0.05+vent_h), (w/2-0.1, -d/2-0.02, 0.05+vent_h),
            (w/2-0.1, -d/2, 0.05+vent_h), (-w/2+0.1, -d/2, 0.05+vent_h)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_ac_split_outdoor():
        """Split AC outdoor compressor."""
        w, d, h = 0.800, 0.300, 0.550
        # Main body with grille
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Fan grille (side)
        grille_d = 0.010
        vertices.extend([
            (-w/2+0.1, -d/2-grille_d, 0.1), (w/2-0.1, -d/2-grille_d, 0.1),
            (w/2-0.1, -d/2, 0.1), (-w/2+0.1, -d/2, 0.1),
            (-w/2+0.1, -d/2-grille_d, h-0.1), (w/2-0.1, -d/2-grille_d, h-0.1),
            (w/2-0.1, -d/2, h-0.1), (-w/2+0.1, -d/2, h-0.1)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_duct_rectangular():
        """Rectangular air duct (1m section)."""
        length = 1.000
        w, h = 0.300, 0.150
        vertices = [
            (-w/2, 0, -h/2), (w/2, 0, -h/2), (w/2, 0, h/2), (-w/2, 0, h/2),
            (-w/2, length, -h/2), (w/2, length, -h/2), (w/2, length, h/2), (-w/2, length, h/2)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_vent_supply():
        """Supply air vent/diffuser."""
        w, h, d = 0.300, 0.300, 0.050
        # Grille
        vertices = [
            (-w/2, -d/2, -h/2), (w/2, -d/2, -h/2), (w/2, d/2, -h/2), (-w/2, d/2, -h/2),
            (-w/2, -d/2, h/2), (w/2, -d/2, h/2), (w/2, d/2, h/2), (-w/2, d/2, h/2)
        ]
        # Slats (3 horizontal)
        slat_h = 0.010
        for i in range(3):
            z = -h/2 + 0.05 + i * 0.10
            base = len(vertices)
            vertices.extend([
                (-w/2+0.02, -d/2, z), (w/2-0.02, -d/2, z),
                (w/2-0.02, d/2, z), (-w/2+0.02, d/2, z),
                (-w/2+0.02, -d/2, z+slat_h), (w/2-0.02, -d/2, z+slat_h),
                (w/2-0.02, d/2, z+slat_h), (-w/2+0.02, d/2, z+slat_h)
            ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_louver():
        """Air louver."""
        return Phase2HVACGenerator.generate_vent_supply()


# ============================================================================
# PHASE 3: MEDIUM PRIORITY GENERATORS (20 objects)
# ============================================================================

class Phase3StructuralGenerator:
    """Structural element generators."""

    @staticmethod
    def generate_column_concrete_300():
        """300×300mm concrete column (1m section)."""
        w = 0.300
        h = 1.000
        vertices = [
            (-w/2, -w/2, 0), (w/2, -w/2, 0), (w/2, w/2, 0), (-w/2, w/2, 0),
            (-w/2, -w/2, h), (w/2, -w/2, h), (w/2, w/2, h), (-w/2, w/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_column_steel_150():
        """150×150mm steel column (1m section)."""
        w = 0.150
        h = 1.000
        vertices = [
            (-w/2, -w/2, 0), (w/2, -w/2, 0), (w/2, w/2, 0), (-w/2, w/2, 0),
            (-w/2, -w/2, h), (w/2, -w/2, h), (w/2, w/2, h), (-w/2, w/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_beam_concrete_300x500():
        """300×500mm concrete beam (1m section)."""
        w, h = 0.300, 0.500
        length = 1.000
        vertices = [
            (-w/2, 0, -h/2), (w/2, 0, -h/2), (w/2, 0, h/2), (-w/2, 0, h/2),
            (-w/2, length, -h/2), (w/2, length, -h/2), (w/2, length, h/2), (-w/2, length, h/2)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_beam_steel_200():
        """200mm steel I-beam (1m section)."""
        # Simplified I-beam as H-shape
        flange_w = 0.200
        web_w = 0.010
        h = 0.200
        length = 1.000

        vertices = []
        # Top flange
        vertices.extend([
            (-flange_w/2, 0, h/2-0.015), (flange_w/2, 0, h/2-0.015),
            (flange_w/2, length, h/2-0.015), (-flange_w/2, length, h/2-0.015),
            (-flange_w/2, 0, h/2), (flange_w/2, 0, h/2),
            (flange_w/2, length, h/2), (-flange_w/2, length, h/2)
        ])
        # Web
        vertices.extend([
            (-web_w/2, 0, -h/2), (web_w/2, 0, -h/2),
            (web_w/2, length, -h/2), (-web_w/2, length, -h/2),
            (-web_w/2, 0, h/2), (web_w/2, 0, h/2),
            (web_w/2, length, h/2), (-web_w/2, length, h/2)
        ])
        # Bottom flange
        vertices.extend([
            (-flange_w/2, 0, -h/2), (flange_w/2, 0, -h/2),
            (flange_w/2, length, -h/2), (-flange_w/2, length, -h/2),
            (-flange_w/2, 0, -h/2+0.015), (flange_w/2, 0, -h/2+0.015),
            (flange_w/2, length, -h/2+0.015), (-flange_w/2, length, -h/2+0.015)
        ])

        faces = []
        for box_start in range(0, 24, 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_foundation_strip():
        """Strip foundation (1m section)."""
        w, h = 0.600, 0.300
        length = 1.000
        vertices = [
            (-w/2, 0, -h), (w/2, 0, -h), (w/2, 0, 0), (-w/2, 0, 0),
            (-w/2, length, -h), (w/2, length, -h), (w/2, length, 0), (-w/2, length, 0)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_foundation_pad():
        """Pad foundation 1.5×1.5m."""
        w = 1.500
        h = 0.500
        vertices = [
            (-w/2, -w/2, -h), (w/2, -w/2, -h), (w/2, w/2, -h), (-w/2, w/2, -h),
            (-w/2, -w/2, 0), (w/2, -w/2, 0), (w/2, w/2, 0), (-w/2, w/2, 0)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_tie_beam():
        """Tie beam 200×300mm (1m section)."""
        w, h = 0.200, 0.300
        length = 1.000
        vertices = [
            (-w/2, 0, -h/2), (w/2, 0, -h/2), (w/2, 0, h/2), (-w/2, 0, h/2),
            (-w/2, length, -h/2), (w/2, length, -h/2), (w/2, length, h/2), (-w/2, length, h/2)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


class Phase3FurnitureGenerator:
    """Basic furniture generators."""

    @staticmethod
    def generate_chair_dining():
        """Dining chair."""
        seat_w, seat_d, seat_h = 0.450, 0.450, 0.450
        back_h = 0.900

        vertices = []
        # Seat
        vertices.extend([
            (-seat_w/2, -seat_d/2, seat_h), (seat_w/2, -seat_d/2, seat_h),
            (seat_w/2, seat_d/2, seat_h), (-seat_w/2, seat_d/2, seat_h),
            (-seat_w/2, -seat_d/2, seat_h+0.05), (seat_w/2, -seat_d/2, seat_h+0.05),
            (seat_w/2, seat_d/2, seat_h+0.05), (-seat_w/2, seat_d/2, seat_h+0.05)
        ])
        # Back
        back_t = 0.05
        vertices.extend([
            (-seat_w/2, seat_d/2-back_t, seat_h), (seat_w/2, seat_d/2-back_t, seat_h),
            (seat_w/2, seat_d/2, seat_h), (-seat_w/2, seat_d/2, seat_h),
            (-seat_w/2, seat_d/2-back_t, back_h), (seat_w/2, seat_d/2-back_t, back_h),
            (seat_w/2, seat_d/2, back_h), (-seat_w/2, seat_d/2, back_h)
        ])
        # 4 legs (simplified as boxes)
        leg_w = 0.04
        for x_sign in [-1, 1]:
            for y_sign in [-1, 1]:
                x = x_sign * (seat_w/2 - 0.05)
                y = y_sign * (seat_d/2 - 0.05)
                base = len(vertices)
                vertices.extend([
                    (x-leg_w/2, y-leg_w/2, 0), (x+leg_w/2, y-leg_w/2, 0),
                    (x+leg_w/2, y+leg_w/2, 0), (x-leg_w/2, y+leg_w/2, 0),
                    (x-leg_w/2, y-leg_w/2, seat_h), (x+leg_w/2, y-leg_w/2, seat_h),
                    (x+leg_w/2, y+leg_w/2, seat_h), (x-leg_w/2, y+leg_w/2, seat_h)
                ])

        faces = []
        for box_start in range(0, len(vertices), 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7),
                (box_start+0, box_start+1, box_start+5), (box_start+0, box_start+5, box_start+4)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_table_dining():
        """Dining table 1.5×0.9m."""
        w, d, h = 1.500, 0.900, 0.750
        top_t = 0.040

        vertices = []
        # Tabletop
        vertices.extend([
            (-w/2, -d/2, h-top_t), (w/2, -d/2, h-top_t),
            (w/2, d/2, h-top_t), (-w/2, d/2, h-top_t),
            (-w/2, -d/2, h), (w/2, -d/2, h),
            (w/2, d/2, h), (-w/2, d/2, h)
        ])
        # 4 legs
        leg_w = 0.06
        for x_sign in [-1, 1]:
            for y_sign in [-1, 1]:
                x = x_sign * (w/2 - 0.1)
                y = y_sign * (d/2 - 0.1)
                base = len(vertices)
                vertices.extend([
                    (x-leg_w/2, y-leg_w/2, 0), (x+leg_w/2, y-leg_w/2, 0),
                    (x+leg_w/2, y+leg_w/2, 0), (x-leg_w/2, y+leg_w/2, 0),
                    (x-leg_w/2, y-leg_w/2, h-top_t), (x+leg_w/2, y-leg_w/2, h-top_t),
                    (x+leg_w/2, y+leg_w/2, h-top_t), (x-leg_w/2, y+leg_w/2, h-top_t)
                ])

        faces = []
        for box_start in range(0, len(vertices), 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_bed_single():
        """Single bed 1.0×2.0m."""
        w, l, h = 1.000, 2.000, 0.500
        mattress_h = 0.200

        vertices = []
        # Mattress
        vertices.extend([
            (-w/2, -l/2, h-mattress_h), (w/2, -l/2, h-mattress_h),
            (w/2, l/2, h-mattress_h), (-w/2, l/2, h-mattress_h),
            (-w/2, -l/2, h), (w/2, -l/2, h),
            (w/2, l/2, h), (-w/2, l/2, h)
        ])
        # Frame (simplified)
        frame_h = h - mattress_h
        frame_t = 0.05
        vertices.extend([
            (-w/2-frame_t, -l/2-frame_t, 0), (w/2+frame_t, -l/2-frame_t, 0),
            (w/2+frame_t, l/2+frame_t, 0), (-w/2-frame_t, l/2+frame_t, 0),
            (-w/2-frame_t, -l/2-frame_t, frame_h), (w/2+frame_t, -l/2-frame_t, frame_h),
            (w/2+frame_t, l/2+frame_t, frame_h), (-w/2-frame_t, l/2+frame_t, frame_h)
        ])

        faces = []
        for box_start in range(0, 16, 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_bed_queen():
        """Queen bed 1.5×2.0m."""
        w, l, h = 1.500, 2.000, 0.500
        mattress_h = 0.200

        vertices = []
        vertices.extend([
            (-w/2, -l/2, h-mattress_h), (w/2, -l/2, h-mattress_h),
            (w/2, l/2, h-mattress_h), (-w/2, l/2, h-mattress_h),
            (-w/2, -l/2, h), (w/2, -l/2, h),
            (w/2, l/2, h), (-w/2, l/2, h)
        ])
        frame_t = 0.05
        vertices.extend([
            (-w/2-frame_t, -l/2-frame_t, 0), (w/2+frame_t, -l/2-frame_t, 0),
            (w/2+frame_t, l/2+frame_t, 0), (-w/2-frame_t, l/2+frame_t, 0),
            (-w/2-frame_t, -l/2-frame_t, h-mattress_h), (w/2+frame_t, -l/2-frame_t, h-mattress_h),
            (w/2+frame_t, l/2+frame_t, h-mattress_h), (-w/2-frame_t, l/2+frame_t, h-mattress_h)
        ])

        faces = []
        for box_start in range(0, 16, 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_wardrobe():
        """Wardrobe 1.2m×0.6m×2.0m."""
        w, d, h = 1.200, 0.600, 2.000
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Doors (2 panels)
        door_t = 0.020
        gap = 0.010
        vertices.extend([
            (-w/2, d/2, 0), (-gap/2, d/2, 0),
            (-gap/2, d/2+door_t, 0), (-w/2, d/2+door_t, 0),
            (-w/2, d/2, h), (-gap/2, d/2, h),
            (-gap/2, d/2+door_t, h), (-w/2, d/2+door_t, h)
        ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_desk():
        """Office desk 1.2m×0.6m."""
        w, d, h = 1.200, 0.600, 0.750
        top_t = 0.025

        vertices = []
        # Desktop
        vertices.extend([
            (-w/2, -d/2, h-top_t), (w/2, -d/2, h-top_t),
            (w/2, d/2, h-top_t), (-w/2, d/2, h-top_t),
            (-w/2, -d/2, h), (w/2, -d/2, h),
            (w/2, d/2, h), (-w/2, d/2, h)
        ])
        # 4 legs
        leg_w = 0.04
        for x_sign in [-1, 1]:
            for y_sign in [-1, 1]:
                x = x_sign * (w/2 - 0.05)
                y = y_sign * (d/2 - 0.05)
                base = len(vertices)
                vertices.extend([
                    (x-leg_w/2, y-leg_w/2, 0), (x+leg_w/2, y-leg_w/2, 0),
                    (x+leg_w/2, y+leg_w/2, 0), (x-leg_w/2, y+leg_w/2, 0),
                    (x-leg_w/2, y-leg_w/2, h-top_t), (x+leg_w/2, y-leg_w/2, h-top_t),
                    (x+leg_w/2, y+leg_w/2, h-top_t), (x-leg_w/2, y+leg_w/2, h-top_t)
                ])

        faces = []
        for box_start in range(0, len(vertices), 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_sofa_2seater():
        """2-seater sofa."""
        w, d, h = 1.500, 0.800, 0.850
        seat_h = 0.450

        vertices = []
        # Seat
        vertices.extend([
            (-w/2, -d/2, seat_h-0.1), (w/2, -d/2, seat_h-0.1),
            (w/2, d/2-0.2, seat_h-0.1), (-w/2, d/2-0.2, seat_h-0.1),
            (-w/2, -d/2, seat_h), (w/2, -d/2, seat_h),
            (w/2, d/2-0.2, seat_h), (-w/2, d/2-0.2, seat_h)
        ])
        # Back
        vertices.extend([
            (-w/2, d/2-0.2, seat_h), (w/2, d/2-0.2, seat_h),
            (w/2, d/2, seat_h), (-w/2, d/2, seat_h),
            (-w/2, d/2-0.2, h), (w/2, d/2-0.2, h),
            (w/2, d/2, h), (-w/2, d/2, h)
        ])

        faces = []
        for box_start in range(0, 16, 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_cabinet_kitchen():
        """Kitchen cabinet 0.6m."""
        w, d, h = 0.600, 0.600, 0.850
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_shelf_wall():
        """Wall shelf."""
        w, d, h = 0.900, 0.250, 0.030
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_coffee_table():
        """Coffee table."""
        w, d, h = 1.000, 0.600, 0.400
        top_t = 0.030

        vertices = []
        # Top
        vertices.extend([
            (-w/2, -d/2, h-top_t), (w/2, -d/2, h-top_t),
            (w/2, d/2, h-top_t), (-w/2, d/2, h-top_t),
            (-w/2, -d/2, h), (w/2, -d/2, h),
            (w/2, d/2, h), (-w/2, d/2, h)
        ])
        # 4 legs
        leg_w = 0.05
        for x_sign in [-1, 1]:
            for y_sign in [-1, 1]:
                x = x_sign * (w/2 - 0.08)
                y = y_sign * (d/2 - 0.08)
                base = len(vertices)
                vertices.extend([
                    (x-leg_w/2, y-leg_w/2, 0), (x+leg_w/2, y-leg_w/2, 0),
                    (x+leg_w/2, y+leg_w/2, 0), (x-leg_w/2, y+leg_w/2, 0),
                    (x-leg_w/2, y-leg_w/2, h-top_t), (x+leg_w/2, y-leg_w/2, h-top_t),
                    (x+leg_w/2, y+leg_w/2, h-top_t), (x-leg_w/2, y+leg_w/2, h-top_t)
                ])

        faces = []
        for box_start in range(0, len(vertices), 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


class Phase3FireProtectionGenerator:
    """Fire protection generators."""

    @staticmethod
    def generate_smoke_detector():
        """Smoke detector."""
        diameter = 0.150
        height = 0.050
        segments = 16

        vertices = []
        # Cylinder
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (diameter/2) * math.cos(angle)
            y = (diameter/2) * math.sin(angle)
            vertices.append((x, y, 0))
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (diameter/2) * math.cos(angle)
            y = (diameter/2) * math.sin(angle)
            vertices.append((x, y, height))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_fire_extinguisher():
        """Fire extinguisher."""
        diameter = 0.150
        height = 0.450
        segments = 12

        vertices = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (diameter/2) * math.cos(angle)
            y = (diameter/2) * math.sin(angle)
            vertices.append((x, y, 0))
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (diameter/2) * math.cos(angle)
            y = (diameter/2) * math.sin(angle)
            vertices.append((x, y, height))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_exit_sign():
        """Emergency exit sign."""
        w, h, d = 0.350, 0.150, 0.050
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


# ============================================================================
# PHASE 4: LOW PRIORITY GENERATORS (15 objects)
# ============================================================================

class Phase4ICTGenerator:
    """ICT and smart home generators."""

    @staticmethod
    def generate_data_point():
        """Data point/ethernet socket."""
        w, h, d = 0.085, 0.045, 0.030
        vertices = [
            (-w/2, -d/2, -h/2), (w/2, -d/2, -h/2), (w/2, d/2, -h/2), (-w/2, d/2, -h/2),
            (-w/2, -d/2, h/2), (w/2, -d/2, h/2), (w/2, d/2, h/2), (-w/2, d/2, h/2)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_telephone_point():
        """Telephone point."""
        return Phase4ICTGenerator.generate_data_point()

    @staticmethod
    def generate_tv_point():
        """TV aerial/coax point."""
        return Phase4ICTGenerator.generate_data_point()

    @staticmethod
    def generate_cctv_camera():
        """CCTV camera."""
        body_d = 0.080
        body_l = 0.150

        # Cylindrical camera body
        segments = 12
        vertices = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            y = (body_d/2) * math.cos(angle)
            z = (body_d/2) * math.sin(angle)
            vertices.append((0, y, z))
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            y = (body_d/2) * math.cos(angle)
            z = (body_d/2) * math.sin(angle)
            vertices.append((body_l, y, z))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_doorbell():
        """Doorbell button."""
        w, h, d = 0.080, 0.080, 0.025
        vertices = [
            (-w/2, -d/2, -h/2), (w/2, -d/2, -h/2), (w/2, d/2, -h/2), (-w/2, d/2, -h/2),
            (-w/2, -d/2, h/2), (w/2, -d/2, h/2), (w/2, d/2, h/2), (-w/2, d/2, h/2)
        ]
        # Button
        button_r = 0.020
        vertices.extend([
            (-button_r, d/2+0.005, -button_r), (button_r, d/2+0.005, -button_r),
            (button_r, d/2+0.005, button_r), (-button_r, d/2+0.005, button_r)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 9, 10), (8, 10, 11)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_smart_thermostat():
        """Smart thermostat."""
        w, h, d = 0.100, 0.100, 0.025
        vertices = [
            (-w/2, -d/2, -h/2), (w/2, -d/2, -h/2), (w/2, d/2, -h/2), (-w/2, d/2, -h/2),
            (-w/2, -d/2, h/2), (w/2, -d/2, h/2), (w/2, d/2, h/2), (-w/2, d/2, h/2)
        ]
        # Display screen
        screen_w, screen_h = 0.070, 0.070
        vertices.extend([
            (-screen_w/2, d/2+0.001, -screen_h/2), (screen_w/2, d/2+0.001, -screen_h/2),
            (screen_w/2, d/2+0.001, screen_h/2), (-screen_w/2, d/2+0.001, screen_h/2)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 9, 10), (8, 10, 11)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_motion_sensor():
        """Motion sensor."""
        diameter = 0.100
        height = 0.040
        segments = 12

        vertices = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (diameter/2) * math.cos(angle)
            y = (diameter/2) * math.sin(angle)
            vertices.append((x, y, 0))
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = (diameter/2) * math.cos(angle)
            y = (diameter/2) * math.sin(angle)
            vertices.append((x, y, height))

        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.extend([
                (i, next_i, segments + next_i),
                (i, segments + next_i, segments + i)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


class Phase4ExternalGenerator:
    """External and landscaping generators."""

    @staticmethod
    def generate_fence_panel():
        """Fence panel 2m."""
        w, h, d = 2.000, 1.500, 0.100
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_gate_swing():
        """Swing gate."""
        w, h, d = 1.200, 1.500, 0.050
        # Gate panel
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Frame
        frame_w = 0.060
        vertices.extend([
            (-w/2-frame_w, -d/2, 0), (-w/2, -d/2, 0), (-w/2, d/2, 0), (-w/2-frame_w, d/2, 0),
            (-w/2-frame_w, -d/2, h), (-w/2, -d/2, h), (-w/2, d/2, h), (-w/2-frame_w, d/2, h)
        ])
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10), (12, 13, 14), (12, 14, 15)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_porch_canopy():
        """Porch canopy."""
        w, d, h = 2.000, 1.200, 0.100
        # Sloped canopy
        vertices = [
            (-w/2, -d, 0), (w/2, -d, 0), (w/2, 0, h), (-w/2, 0, h),
            (-w/2, -d, 0.05), (w/2, -d, 0.05), (w/2, 0, h+0.05), (-w/2, 0, h+0.05)
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_planter_box():
        """Planter box."""
        w, d, h = 0.800, 0.400, 0.400
        wall_t = 0.050

        # Outer box
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Inner cavity
        vertices.extend([
            (-w/2+wall_t, -d/2+wall_t, wall_t), (w/2-wall_t, -d/2+wall_t, wall_t),
            (w/2-wall_t, d/2-wall_t, wall_t), (-w/2+wall_t, d/2-wall_t, wall_t),
            (-w/2+wall_t, -d/2+wall_t, h-0.02), (w/2-wall_t, -d/2+wall_t, h-0.02),
            (w/2-wall_t, d/2-wall_t, h-0.02), (-w/2+wall_t, d/2-wall_t, h-0.02)
        ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_outdoor_steps():
        """Outdoor steps (3 steps)."""
        step_w = 1.000
        step_d = 0.300
        step_h = 0.150

        vertices = []
        faces = []

        for i in range(3):
            z = i * step_h
            base = len(vertices)
            vertices.extend([
                (-step_w/2, -step_d*(3-i), z), (step_w/2, -step_d*(3-i), z),
                (step_w/2, -step_d*(2-i), z), (-step_w/2, -step_d*(2-i), z),
                (-step_w/2, -step_d*(3-i), z+step_h), (step_w/2, -step_d*(3-i), z+step_h),
                (step_w/2, -step_d*(2-i), z+step_h), (-step_w/2, -step_d*(2-i), z+step_h)
            ])
            faces.extend([
                (base+0, base+2, base+1), (base+0, base+3, base+2),
                (base+4, base+5, base+6), (base+4, base+6, base+7),
                (base+0, base+1, base+5), (base+0, base+5, base+4)
            ])

        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


class Phase4AdditionalGenerator:
    """Additional generators."""

    @staticmethod
    def generate_kitchen_sink():
        """Kitchen sink."""
        w, d, h = 0.800, 0.500, 0.200
        wall_t = 0.040

        # Outer shell
        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        # Basin cavity
        vertices.extend([
            (-w/2+wall_t, -d/2+wall_t, wall_t), (w/2-wall_t, -d/2+wall_t, wall_t),
            (w/2-wall_t, d/2-wall_t, wall_t), (-w/2+wall_t, d/2-wall_t, wall_t),
            (-w/2+wall_t, -d/2+wall_t, h-0.02), (w/2-wall_t, -d/2+wall_t, h-0.02),
            (w/2-wall_t, d/2-wall_t, h-0.02), (-w/2+wall_t, d/2-wall_t, h-0.02)
        ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
            (8, 10, 9), (8, 11, 10)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_basin_wall():
        """Wall-mounted basin."""
        w, d, h = 0.500, 0.400, 0.150
        wall_t = 0.030

        vertices = [
            (-w/2, -d/2, 0), (w/2, -d/2, 0), (w/2, d/2, 0), (-w/2, d/2, 0),
            (-w/2, -d/2, h), (w/2, -d/2, h), (w/2, d/2, h), (-w/2, d/2, h)
        ]
        vertices.extend([
            (-w/2+wall_t, -d/2+wall_t, wall_t), (w/2-wall_t, -d/2+wall_t, wall_t),
            (w/2-wall_t, d/2-wall_t, wall_t), (-w/2+wall_t, d/2-wall_t, wall_t),
            (-w/2+wall_t, -d/2+wall_t, h-0.02), (w/2-wall_t, -d/2+wall_t, h-0.02),
            (w/2-wall_t, d/2-wall_t, h-0.02), (-w/2+wall_t, d/2-wall_t, h-0.02)
        ])

        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)
        ]
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)

    @staticmethod
    def generate_wc_toilet():
        """WC toilet."""
        # Simplified as two boxes (bowl + tank)
        bowl_w, bowl_d, bowl_h = 0.400, 0.500, 0.400
        tank_w, tank_d, tank_h = 0.350, 0.200, 0.400

        vertices = []
        # Bowl
        vertices.extend([
            (-bowl_w/2, -bowl_d/2, 0), (bowl_w/2, -bowl_d/2, 0),
            (bowl_w/2, bowl_d/2, 0), (-bowl_w/2, bowl_d/2, 0),
            (-bowl_w/2, -bowl_d/2, bowl_h), (bowl_w/2, -bowl_d/2, bowl_h),
            (bowl_w/2, bowl_d/2, bowl_h), (-bowl_w/2, bowl_d/2, bowl_h)
        ])
        # Tank (behind bowl)
        tank_y = bowl_d/2 - tank_d/2
        vertices.extend([
            (-tank_w/2, tank_y-tank_d/2, bowl_h), (tank_w/2, tank_y-tank_d/2, bowl_h),
            (tank_w/2, tank_y+tank_d/2, bowl_h), (-tank_w/2, tank_y+tank_d/2, bowl_h),
            (-tank_w/2, tank_y-tank_d/2, bowl_h+tank_h), (tank_w/2, tank_y-tank_d/2, bowl_h+tank_h),
            (tank_w/2, tank_y+tank_d/2, bowl_h+tank_h), (-tank_w/2, tank_y+tank_d/2, bowl_h+tank_h)
        ])

        faces = []
        for box_start in range(0, 16, 8):
            faces.extend([
                (box_start+0, box_start+2, box_start+1), (box_start+0, box_start+3, box_start+2),
                (box_start+4, box_start+5, box_start+6), (box_start+4, box_start+6, box_start+7),
                (box_start+0, box_start+1, box_start+5), (box_start+0, box_start+5, box_start+4)
            ])
        normals = [compute_face_normal(vertices[f[0]], vertices[f[1]], vertices[f[2]]) for f in faces]
        return GeometryResult(vertices, faces, normals)


# ============================================================================
# OBJECT DEFINITIONS - ALL 70 OBJECTS
# ============================================================================

PHASE2_OBJECTS = [
    # Doors (6)
    LibraryObject('door_sliding_single_900', 'Sliding Door Single 900mm', 'IfcDoor', 'Residential', 'Doors', 900, 50, 2100, 'Single panel sliding door with track'),
    LibraryObject('door_sliding_double_1800', 'Sliding Door Double 1800mm', 'IfcDoor', 'Residential', 'Doors', 1800, 50, 2100, 'Double panel sliding door'),
    LibraryObject('door_bifold_900', 'Bifold Door 900mm', 'IfcDoor', 'Residential', 'Doors', 900, 50, 2100, 'Folding panel door'),
    LibraryObject('door_french_double_1800', 'French Door Double 1800mm', 'IfcDoor', 'Residential', 'Doors', 1800, 50, 2100, 'French glass doors'),
    LibraryObject('door_louvre_750', 'Louvre Door 750mm', 'IfcDoor', 'Residential', 'Doors', 750, 40, 2100, 'Slatted louvre door'),
    LibraryObject('door_mesh_900', 'Security Mesh Door 900mm', 'IfcDoor', 'Residential', 'Doors', 900, 30, 2100, 'Security mesh door'),

    # Windows (6)
    LibraryObject('window_sliding_2panel_1200', 'Window Sliding 2-Panel 1200mm', 'IfcWindow', 'Residential', 'Windows', 1200, 100, 1000, 'Two panel sliding window'),
    LibraryObject('window_sliding_3panel_1800', 'Window Sliding 3-Panel 1800mm', 'IfcWindow', 'Residential', 'Windows', 1800, 100, 1000, 'Three panel sliding window'),
    LibraryObject('window_casement_single_600', 'Window Casement Single 600mm', 'IfcWindow', 'Residential', 'Windows', 600, 100, 900, 'Single casement window'),
    LibraryObject('window_casement_double_1200', 'Window Casement Double 1200mm', 'IfcWindow', 'Residential', 'Windows', 1200, 100, 1000, 'Double casement window'),
    LibraryObject('window_awning_900', 'Window Awning 900mm', 'IfcWindow', 'Residential', 'Windows', 900, 100, 600, 'Top-hinged awning window'),
    LibraryObject('window_grille_1200', 'Window Security Grille 1200mm', 'IfcWindow', 'Residential', 'Windows', 1200, 30, 1000, 'Security grille for window'),

    # Electrical (8)
    LibraryObject('electrical_distribution_board', 'Distribution Board', 'IfcElectricDistributionBoard', 'MEP_Electrical', 'Distribution', 400, 150, 600, 'Main electrical distribution board'),
    LibraryObject('electrical_outlet_double', 'Power Outlet Double', 'IfcOutlet', 'MEP_Electrical', 'Outlets', 85, 30, 85, 'Standard double power socket'),
    LibraryObject('electrical_outlet_usb', 'Power Outlet USB', 'IfcOutlet', 'MEP_Electrical', 'Outlets', 85, 30, 85, 'USB charging outlet'),
    LibraryObject('electrical_outlet_weatherproof', 'Power Outlet Weatherproof', 'IfcOutlet', 'MEP_Electrical', 'Outlets', 100, 50, 100, 'Outdoor weatherproof outlet'),
    LibraryObject('electrical_switch_dimmer', 'Dimmer Switch', 'IfcSwitchingDevice', 'MEP_Electrical', 'Switches', 85, 25, 85, 'Light dimmer switch'),
    LibraryObject('electrical_switch_timer', 'Timer Switch', 'IfcSwitchingDevice', 'MEP_Electrical', 'Switches', 85, 25, 85, 'Programmable timer switch'),
    LibraryObject('electrical_switch_weatherproof', 'Weatherproof Switch', 'IfcSwitchingDevice', 'MEP_Electrical', 'Switches', 100, 50, 100, 'Outdoor weatherproof switch'),
    LibraryObject('electrical_conduit_20mm', 'Electrical Conduit 20mm', 'IfcCableCarrierSegment', 'MEP_Electrical', 'Conduit', 1000, 20, 20, 'Electrical conduit 1m section'),

    # Plumbing (10)
    LibraryObject('plumbing_bathtub_1700', 'Bathtub 1700mm', 'IfcSanitaryTerminal', 'MEP_Plumbing', 'Fixtures', 1700, 700, 550, 'Standard bathtub'),
    LibraryObject('plumbing_mixer_shower', 'Shower Mixer', 'IfcValve', 'MEP_Plumbing', 'Fixtures', 100, 150, 100, 'Shower mixer valve'),
    LibraryObject('plumbing_mixer_basin', 'Basin Mixer Tap', 'IfcValve', 'MEP_Plumbing', 'Fixtures', 100, 150, 100, 'Basin mixer tap'),
    LibraryObject('plumbing_mixer_kitchen', 'Kitchen Mixer Tap', 'IfcValve', 'MEP_Plumbing', 'Fixtures', 100, 150, 100, 'Kitchen mixer tap'),
    LibraryObject('plumbing_mixer_outdoor', 'Outdoor Tap', 'IfcValve', 'MEP_Plumbing', 'Fixtures', 100, 150, 100, 'Outdoor water tap'),
    LibraryObject('plumbing_towel_rail', 'Heated Towel Rail', 'IfcSanitaryTerminal', 'MEP_Plumbing', 'Accessories', 600, 100, 800, 'Heated towel rail'),
    LibraryObject('plumbing_shower_screen', 'Shower Screen Glass', 'IfcBuildingElementProxy', 'Residential', 'Bathroom', 900, 8, 2000, 'Glass shower screen'),
    LibraryObject('plumbing_pipe_pvc_40mm', 'PVC Pipe 40mm', 'IfcPipeSegment', 'MEP_Plumbing', 'Piping', 1000, 40, 40, 'PVC drainage pipe 1m section'),
    LibraryObject('plumbing_pipe_copper_22mm', 'Copper Pipe 22mm', 'IfcPipeSegment', 'MEP_Plumbing', 'Piping', 1000, 22, 22, 'Copper water pipe 1m section'),
    LibraryObject('plumbing_water_heater', 'Electric Water Heater', 'IfcFlowTerminal', 'MEP_Plumbing', 'Equipment', 450, 450, 600, 'Electric storage water heater'),

    # HVAC (5)
    LibraryObject('hvac_ac_split_indoor', 'AC Split Unit Indoor', 'IfcUnitaryEquipment', 'MEP_HVAC', 'AC_Units', 900, 250, 300, 'Split AC indoor unit'),
    LibraryObject('hvac_ac_split_outdoor', 'AC Split Unit Outdoor', 'IfcUnitaryEquipment', 'MEP_HVAC', 'AC_Units', 800, 300, 550, 'Split AC outdoor compressor'),
    LibraryObject('hvac_duct_rectangular', 'Rectangular Air Duct', 'IfcDuctSegment', 'MEP_HVAC', 'Ducting', 1000, 300, 150, 'Rectangular duct 1m section'),
    LibraryObject('hvac_vent_supply', 'Supply Air Vent', 'IfcAirTerminal', 'MEP_HVAC', 'Vents', 300, 50, 300, 'Supply air diffuser'),
    LibraryObject('hvac_louver', 'Air Louver', 'IfcAirTerminal', 'MEP_HVAC', 'Vents', 300, 50, 300, 'Air louver vent'),
]

PHASE3_OBJECTS = [
    # Structural (7)
    LibraryObject('structural_column_concrete_300', 'Concrete Column 300×300mm', 'IfcColumn', 'Structural', 'Columns', 300, 300, 1000, 'Concrete column 1m section'),
    LibraryObject('structural_column_steel_150', 'Steel Column 150×150mm', 'IfcColumn', 'Structural', 'Columns', 150, 150, 1000, 'Steel column 1m section'),
    LibraryObject('structural_beam_concrete_300x500', 'Concrete Beam 300×500mm', 'IfcBeam', 'Structural', 'Beams', 300, 1000, 500, 'Concrete beam 1m section'),
    LibraryObject('structural_beam_steel_200', 'Steel I-Beam 200mm', 'IfcBeam', 'Structural', 'Beams', 200, 1000, 200, 'Steel I-beam 1m section'),
    LibraryObject('structural_foundation_strip', 'Strip Foundation', 'IfcFooting', 'Structural', 'Foundations', 600, 1000, 300, 'Strip foundation 1m section'),
    LibraryObject('structural_foundation_pad', 'Pad Foundation 1.5m', 'IfcFooting', 'Structural', 'Foundations', 1500, 1500, 500, 'Pad foundation 1.5×1.5m'),
    LibraryObject('structural_tie_beam', 'Tie Beam 200×300mm', 'IfcBeam', 'Structural', 'Beams', 200, 1000, 300, 'Tie beam 1m section'),

    # Furniture (10)
    LibraryObject('furniture_chair_dining', 'Dining Chair', 'IfcFurniture', 'Residential_Furniture', 'Dining', 450, 450, 900, 'Standard dining chair'),
    LibraryObject('furniture_table_dining', 'Dining Table 1.5m', 'IfcFurniture', 'Residential_Furniture', 'Dining', 1500, 900, 750, 'Dining table 1.5×0.9m'),
    LibraryObject('furniture_bed_single', 'Single Bed', 'IfcFurniture', 'Residential_Furniture', 'Bedroom', 1000, 2000, 500, 'Single bed 1.0×2.0m'),
    LibraryObject('furniture_bed_queen', 'Queen Bed', 'IfcFurniture', 'Residential_Furniture', 'Bedroom', 1500, 2000, 500, 'Queen bed 1.5×2.0m'),
    LibraryObject('furniture_wardrobe', 'Wardrobe', 'IfcFurniture', 'Residential_Furniture', 'Bedroom', 1200, 600, 2000, 'Wardrobe 1.2×0.6×2.0m'),
    LibraryObject('furniture_desk', 'Office Desk', 'IfcFurniture', 'Residential_Furniture', 'Study', 1200, 600, 750, 'Office desk 1.2×0.6m'),
    LibraryObject('furniture_sofa_2seater', '2-Seater Sofa', 'IfcFurniture', 'Residential_Furniture', 'Living', 1500, 800, 850, '2-seater sofa'),
    LibraryObject('furniture_cabinet_kitchen', 'Kitchen Cabinet', 'IfcFurniture', 'Residential_Furniture', 'Kitchen', 600, 600, 850, 'Kitchen base cabinet'),
    LibraryObject('furniture_shelf_wall', 'Wall Shelf', 'IfcFurniture', 'Residential_Furniture', 'General', 900, 250, 30, 'Wall-mounted shelf'),
    LibraryObject('furniture_coffee_table', 'Coffee Table', 'IfcFurniture', 'Residential_Furniture', 'Living', 1000, 600, 400, 'Coffee table'),

    # Fire Protection (3)
    LibraryObject('fire_smoke_detector', 'Smoke Detector', 'IfcFireSuppressionTerminal', 'Fire_Protection', 'Detection', 150, 150, 50, 'Ceiling smoke detector'),
    LibraryObject('fire_extinguisher', 'Fire Extinguisher', 'IfcFireSuppressionTerminal', 'Fire_Protection', 'Suppression', 150, 150, 450, 'Portable fire extinguisher'),
    LibraryObject('fire_exit_sign', 'Emergency Exit Sign', 'IfcLightFixture', 'Fire_Protection', 'Signage', 350, 50, 150, 'Illuminated exit sign'),
]

PHASE4_OBJECTS = [
    # ICT (7)
    LibraryObject('ict_data_point', 'Data Point RJ45', 'IfcCommunicationsAppliance', 'ICT', 'Data', 85, 30, 45, 'Ethernet data point'),
    LibraryObject('ict_telephone_point', 'Telephone Point', 'IfcCommunicationsAppliance', 'ICT', 'Telephony', 85, 30, 45, 'Telephone socket'),
    LibraryObject('ict_tv_point', 'TV Aerial Point', 'IfcCommunicationsAppliance', 'ICT', 'Entertainment', 85, 30, 45, 'TV coaxial socket'),
    LibraryObject('ict_cctv_camera', 'CCTV Camera', 'IfcCommunicationsAppliance', 'ICT', 'Security', 80, 150, 80, 'Security camera'),
    LibraryObject('ict_doorbell', 'Doorbell', 'IfcCommunicationsAppliance', 'ICT', 'Entry', 80, 25, 80, 'Doorbell button'),
    LibraryObject('ict_smart_thermostat', 'Smart Thermostat', 'IfcController', 'ICT', 'Smart_Home', 100, 25, 100, 'Smart thermostat'),
    LibraryObject('ict_motion_sensor', 'Motion Sensor', 'IfcSensor', 'ICT', 'Security', 100, 100, 40, 'PIR motion sensor'),

    # External/Landscaping (5)
    LibraryObject('external_fence_panel_2000', 'Fence Panel 2m', 'IfcBuildingElementProxy', 'External', 'Fencing', 2000, 100, 1500, 'Fence panel 2m wide'),
    LibraryObject('external_gate_swing_1200', 'Swing Gate 1.2m', 'IfcDoor', 'External', 'Gates', 1200, 50, 1500, 'Swing gate'),
    LibraryObject('external_porch_canopy', 'Porch Canopy', 'IfcRoof', 'External', 'Canopies', 2000, 1200, 100, 'Entrance porch canopy'),
    LibraryObject('external_planter_box', 'Planter Box', 'IfcBuildingElementProxy', 'External', 'Landscaping', 800, 400, 400, 'Planter box'),
    LibraryObject('external_outdoor_steps', 'Outdoor Steps (3)', 'IfcStair', 'External', 'Steps', 1000, 900, 450, 'Three outdoor steps'),

    # Additional (3)
    LibraryObject('additional_kitchen_sink', 'Kitchen Sink', 'IfcSanitaryTerminal', 'MEP_Plumbing', 'Fixtures', 800, 500, 200, 'Kitchen sink'),
    LibraryObject('additional_basin_wall', 'Wall Basin', 'IfcSanitaryTerminal', 'MEP_Plumbing', 'Fixtures', 500, 400, 150, 'Wall-mounted basin'),
    LibraryObject('additional_wc_toilet', 'WC Toilet', 'IfcSanitaryTerminal', 'MEP_Plumbing', 'Fixtures', 400, 500, 800, 'Water closet toilet'),
]


# ============================================================================
# GENERATOR MAPPING
# ============================================================================

GENERATOR_MAP = {
    # Phase 2 - Doors
    'door_sliding_single_900': Phase2DoorsGenerator.generate_sliding_single,
    'door_sliding_double_1800': Phase2DoorsGenerator.generate_sliding_double,
    'door_bifold_900': Phase2DoorsGenerator.generate_bifold,
    'door_french_double_1800': Phase2DoorsGenerator.generate_french_double,
    'door_louvre_750': Phase2DoorsGenerator.generate_louvre,
    'door_mesh_900': Phase2DoorsGenerator.generate_mesh,

    # Phase 2 - Windows
    'window_sliding_2panel_1200': Phase2WindowsGenerator.generate_sliding_2panel,
    'window_sliding_3panel_1800': Phase2WindowsGenerator.generate_sliding_3panel,
    'window_casement_single_600': Phase2WindowsGenerator.generate_casement_single,
    'window_casement_double_1200': Phase2WindowsGenerator.generate_casement_double,
    'window_awning_900': Phase2WindowsGenerator.generate_awning,
    'window_grille_1200': Phase2WindowsGenerator.generate_grille,

    # Phase 2 - Electrical
    'electrical_distribution_board': Phase2ElectricalGenerator.generate_distribution_board,
    'electrical_outlet_double': Phase2ElectricalGenerator.generate_outlet_double,
    'electrical_outlet_usb': Phase2ElectricalGenerator.generate_outlet_usb,
    'electrical_outlet_weatherproof': Phase2ElectricalGenerator.generate_outlet_weatherproof,
    'electrical_switch_dimmer': Phase2ElectricalGenerator.generate_switch_dimmer,
    'electrical_switch_timer': Phase2ElectricalGenerator.generate_switch_timer,
    'electrical_switch_weatherproof': Phase2ElectricalGenerator.generate_switch_weatherproof,
    'electrical_conduit_20mm': Phase2ElectricalGenerator.generate_conduit_20mm,

    # Phase 2 - Plumbing
    'plumbing_bathtub_1700': Phase2PlumbingGenerator.generate_bathtub,
    'plumbing_mixer_shower': Phase2PlumbingGenerator.generate_mixer_shower,
    'plumbing_mixer_basin': Phase2PlumbingGenerator.generate_mixer_basin,
    'plumbing_mixer_kitchen': Phase2PlumbingGenerator.generate_mixer_kitchen,
    'plumbing_mixer_outdoor': Phase2PlumbingGenerator.generate_mixer_outdoor,
    'plumbing_towel_rail': Phase2PlumbingGenerator.generate_towel_rail,
    'plumbing_shower_screen': Phase2PlumbingGenerator.generate_shower_screen,
    'plumbing_pipe_pvc_40mm': Phase2PlumbingGenerator.generate_pipe_pvc_40mm,
    'plumbing_pipe_copper_22mm': Phase2PlumbingGenerator.generate_pipe_copper_22mm,
    'plumbing_water_heater': Phase2PlumbingGenerator.generate_water_heater,

    # Phase 2 - HVAC
    'hvac_ac_split_indoor': Phase2HVACGenerator.generate_ac_split_indoor,
    'hvac_ac_split_outdoor': Phase2HVACGenerator.generate_ac_split_outdoor,
    'hvac_duct_rectangular': Phase2HVACGenerator.generate_duct_rectangular,
    'hvac_vent_supply': Phase2HVACGenerator.generate_vent_supply,
    'hvac_louver': Phase2HVACGenerator.generate_louver,

    # Phase 3 - Structural
    'structural_column_concrete_300': Phase3StructuralGenerator.generate_column_concrete_300,
    'structural_column_steel_150': Phase3StructuralGenerator.generate_column_steel_150,
    'structural_beam_concrete_300x500': Phase3StructuralGenerator.generate_beam_concrete_300x500,
    'structural_beam_steel_200': Phase3StructuralGenerator.generate_beam_steel_200,
    'structural_foundation_strip': Phase3StructuralGenerator.generate_foundation_strip,
    'structural_foundation_pad': Phase3StructuralGenerator.generate_foundation_pad,
    'structural_tie_beam': Phase3StructuralGenerator.generate_tie_beam,

    # Phase 3 - Furniture
    'furniture_chair_dining': Phase3FurnitureGenerator.generate_chair_dining,
    'furniture_table_dining': Phase3FurnitureGenerator.generate_table_dining,
    'furniture_bed_single': Phase3FurnitureGenerator.generate_bed_single,
    'furniture_bed_queen': Phase3FurnitureGenerator.generate_bed_queen,
    'furniture_wardrobe': Phase3FurnitureGenerator.generate_wardrobe,
    'furniture_desk': Phase3FurnitureGenerator.generate_desk,
    'furniture_sofa_2seater': Phase3FurnitureGenerator.generate_sofa_2seater,
    'furniture_cabinet_kitchen': Phase3FurnitureGenerator.generate_cabinet_kitchen,
    'furniture_shelf_wall': Phase3FurnitureGenerator.generate_shelf_wall,
    'furniture_coffee_table': Phase3FurnitureGenerator.generate_coffee_table,

    # Phase 3 - Fire Protection
    'fire_smoke_detector': Phase3FireProtectionGenerator.generate_smoke_detector,
    'fire_extinguisher': Phase3FireProtectionGenerator.generate_fire_extinguisher,
    'fire_exit_sign': Phase3FireProtectionGenerator.generate_exit_sign,

    # Phase 4 - ICT
    'ict_data_point': Phase4ICTGenerator.generate_data_point,
    'ict_telephone_point': Phase4ICTGenerator.generate_telephone_point,
    'ict_tv_point': Phase4ICTGenerator.generate_tv_point,
    'ict_cctv_camera': Phase4ICTGenerator.generate_cctv_camera,
    'ict_doorbell': Phase4ICTGenerator.generate_doorbell,
    'ict_smart_thermostat': Phase4ICTGenerator.generate_smart_thermostat,
    'ict_motion_sensor': Phase4ICTGenerator.generate_motion_sensor,

    # Phase 4 - External
    'external_fence_panel_2000': Phase4ExternalGenerator.generate_fence_panel,
    'external_gate_swing_1200': Phase4ExternalGenerator.generate_gate_swing,
    'external_porch_canopy': Phase4ExternalGenerator.generate_porch_canopy,
    'external_planter_box': Phase4ExternalGenerator.generate_planter_box,
    'external_outdoor_steps': Phase4ExternalGenerator.generate_outdoor_steps,

    # Phase 4 - Additional
    'additional_kitchen_sink': Phase4AdditionalGenerator.generate_kitchen_sink,
    'additional_basin_wall': Phase4AdditionalGenerator.generate_basin_wall,
    'additional_wc_toilet': Phase4AdditionalGenerator.generate_wc_toilet,
}


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def compute_geometry_hash(vertices: List[Tuple[float, float, float]],
                          faces: List[Tuple[int, int, int]]) -> str:
    """Compute SHA-256 hash of geometry."""
    import hashlib
    content = f"{vertices}{faces}".encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def serialize_geometry(geom: GeometryResult) -> Tuple[bytes, bytes, bytes]:
    """Serialize vertices, faces, and normals to binary."""
    vertices_data = struct.pack(f'<{len(geom.vertices) * 3}f',
                                *[coord for v in geom.vertices for coord in v])
    faces_data = struct.pack(f'<{len(geom.faces) * 3}I',
                            *[idx for f in geom.faces for idx in f])
    normals_data = struct.pack(f'<{len(geom.normals) * 3}f',
                              *[coord for n in geom.normals for coord in n])
    return vertices_data, faces_data, normals_data


def insert_library_object(db_path: str, obj: LibraryObject, dry_run: bool = False):
    """Insert object into library database."""

    # Generate geometry
    if obj.object_type not in GENERATOR_MAP:
        print(f"  ⚠️  No generator for {obj.object_type}")
        return

    generator_func = GENERATOR_MAP[obj.object_type]
    geom = generator_func()

    # Compute hash
    geom_hash = compute_geometry_hash(geom.vertices, geom.faces)

    # Serialize
    vertices_blob, faces_blob, normals_blob = serialize_geometry(geom)

    vertex_count = len(geom.vertices)
    face_count = len(geom.faces)

    print(f"  ✅ {obj.object_name}: {vertex_count} vertices, {face_count} faces")

    if dry_run:
        print(f"     [DRY RUN - Not writing to database]")
        return

    # Insert into database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Insert geometry
        cursor.execute("""
            INSERT OR IGNORE INTO base_geometries (geometry_hash, vertices, faces, normals)
            VALUES (?, ?, ?, ?)
        """, (geom_hash, vertices_blob, faces_blob, normals_blob))

        # Insert object
        cursor.execute("""
            INSERT OR REPLACE INTO object_catalog
            (object_type, object_name, ifc_class, category, sub_category,
             width_mm, depth_mm, height_mm, description, construction_type, geometry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (obj.object_type, obj.object_name, obj.ifc_class, obj.category, obj.sub_category,
              obj.width_mm, obj.depth_mm, obj.height_mm, obj.description,
              obj.construction_type, geom_hash))

        conn.commit()
    except Exception as e:
        print(f"     ❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()


def ensure_database_schema(db_path: str):
    """Ensure database has correct schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create base_geometries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS base_geometries (
            geometry_hash TEXT PRIMARY KEY,
            vertices BLOB NOT NULL,
            faces BLOB NOT NULL,
            normals BLOB NOT NULL
        )
    """)

    # Create object_catalog table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS object_catalog (
            object_type TEXT PRIMARY KEY,
            object_name TEXT NOT NULL,
            ifc_class TEXT NOT NULL,
            category TEXT NOT NULL,
            sub_category TEXT,
            width_mm INTEGER NOT NULL,
            depth_mm INTEGER NOT NULL,
            height_mm INTEGER NOT NULL,
            description TEXT,
            construction_type TEXT DEFAULT 'universal',
            geometry_hash TEXT NOT NULL,
            FOREIGN KEY (geometry_hash) REFERENCES base_geometries(geometry_hash)
        )
    """)

    conn.commit()
    conn.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Generate complete LOD300 library (Phases 2-4)')
    parser.add_argument('--output', required=True, help='Output database path')
    parser.add_argument('--phase', choices=['2', '3', '4', 'all'], default='all',
                       help='Which phase to generate (2, 3, 4, or all)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Test generation without writing to database')

    args = parser.parse_args()

    # Select objects based on phase
    objects_to_generate = []
    if args.phase == '2':
        objects_to_generate = PHASE2_OBJECTS
        phase_name = "Phase 2 (35 HIGH priority)"
    elif args.phase == '3':
        objects_to_generate = PHASE3_OBJECTS
        phase_name = "Phase 3 (20 MEDIUM priority)"
    elif args.phase == '4':
        objects_to_generate = PHASE4_OBJECTS
        phase_name = "Phase 4 (15 LOW priority)"
    else:  # all
        objects_to_generate = PHASE2_OBJECTS + PHASE3_OBJECTS + PHASE4_OBJECTS
        phase_name = "ALL PHASES (70 objects)"

    print(f"\n{'='*70}")
    print(f"COMPLETE LOD300 LIBRARY GENERATOR - {phase_name}")
    print(f"{'='*70}\n")

    if args.dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made\n")
    else:
        # Ensure database exists and has schema
        db_path = Path(args.output)
        if not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"📁 Database: {args.output}")
        ensure_database_schema(args.output)
        print(f"✅ Database schema verified\n")

    print(f"🏗️  Generating {len(objects_to_generate)} LOD300 objects...\n")

    # Generate all objects
    success_count = 0
    for obj in objects_to_generate:
        try:
            insert_library_object(args.output, obj, dry_run=args.dry_run)
            success_count += 1
        except Exception as e:
            print(f"  ❌ FAILED: {obj.object_name} - {e}")

    # Summary
    print(f"\n{'='*70}")
    print(f"GENERATION COMPLETE")
    print(f"{'='*70}")
    print(f"✅ Successfully generated: {success_count}/{len(objects_to_generate)} objects")

    if not args.dry_run:
        # Count total objects in database
        conn = sqlite3.connect(args.output)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM object_catalog")
        total_count = cursor.fetchone()[0]
        conn.close()

        print(f"📊 Total objects in library: {total_count}")

    print(f"\n🎉 {phase_name} generation complete!")
    print(f"\nNext steps:")
    if args.phase != 'all':
        print(f"  1. Review generated objects")
        print(f"  2. Run with --phase all to generate remaining phases")
        print(f"  3. Test objects in design workflow")
    else:
        print(f"  1. Review all generated objects")
        print(f"  2. Test objects in Design #001")
        print(f"  3. Create quality report for complete library")

    return 0


if __name__ == '__main__':
    sys.exit(main())
