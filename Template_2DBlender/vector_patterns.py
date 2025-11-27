#!/usr/bin/env python3
"""
Vector Pattern Dictionary - Low-level execution primitives for OCR extraction

Architecture: Two-tier system
  - Tier 1: master_reference_template.json (high-level instructions)
  - Tier 2: vector_patterns.py (low-level execution) ← THIS FILE

Think: Java bytecode → C implementation
"""

# =============================================================================
# VECTOR PATTERN EXECUTION PRIMITIVES
# =============================================================================

VECTOR_PATTERNS = {

    # =========================================================================
    # PHASE 1B: CALIBRATION
    # =========================================================================

    "CALIBRATION_DRAIN_PERIMETER": {
        "description": "Extract bounding box from closed shape near page edges",
        "method": "vector_bounding_box",
        "execution": {
            "step_1_text_search": {
                "search_for": "text_contains",
                "keywords": ["DISCHARGE"],
                "case_sensitive": False,
                "get_page_number": True
            },
            "step_2_vector_extraction": {
                "from_page": "result_of_step_1",
                "extract": "all_lines",
                "filter_by": {
                    "line_type": ["rect", "closed_polygon"],
                    "min_lines": 4  # Rectangle needs 4 lines minimum
                }
            },
            "step_3_selection": {
                "method": "nearest_to_page_edge",
                "calculate_distance": "min(distance_to_top, distance_to_left, distance_to_right, distance_to_bottom)",
                "select": "shape_with_minimum_distance"
            },
            "step_4_bounding_box": {
                "extract_from": "selected_shape_lines",
                "calculate": {
                    "pdf_min_x": "min([line['x0'], line['x1']] for all lines)",
                    "pdf_max_x": "max([line['x0'], line['x1']] for all lines)",
                    "pdf_min_y": "min([line['y0'], line['y1']] for all lines)",
                    "pdf_max_y": "max([line['y0'], line['y1']] for all lines)"
                }
            },
            "step_5_calibration": {
                "scale_x": "building_width / (pdf_max_x - pdf_min_x)",
                "scale_y": "building_length / (pdf_max_y - pdf_min_y)",
                "offset_x": "pdf_min_x",
                "offset_y": "pdf_min_y",
                "confidence": "95 if abs(scale_x - scale_y)/scale_x < 0.05 else 85"
            }
        },
        "output_format": {
            "scale_x": "float",
            "scale_y": "float",
            "offset_x": "float",
            "offset_y": "float",
            "confidence": "int (percentage)",
            "method": "drain_perimeter"
        }
    },

    # =========================================================================
    # PHASE 1D: ELEVATIONS
    # =========================================================================

    "ELEVATION_TEXT_REGEX": {
        "description": "Extract dimension values from elevation text using regex",
        "method": "regex_pattern_matching",
        "execution": {
            "step_1": {
                "extract_text": "from_page",
                "get": "all_text_content"
            },
            "step_2": {
                "apply_regex": "patterns_from_master_template",
                "match_groups": 1,  # Extract first capture group
                "convert_units": {
                    "if_unit_mm": "divide_by_1000",
                    "if_unit_m": "as_is"
                }
            },
            "step_3": {
                "validate": {
                    "min_value": 0.0,
                    "max_value": 10.0,  # Reasonable building height limit
                    "return_null_if_invalid": True
                }
            }
        },
        "output_format": {
            "value": "float (meters)",
            "confidence": "int (90-95)"
        }
    },

    # =========================================================================
    # PHASE 1A: SCHEDULES
    # =========================================================================

    "SCHEDULE_TABLE_EXTRACTION": {
        "description": "Extract structured data from tables (door/window schedules)",
        "method": "table_parsing",
        "execution": {
            "step_1_text_search": {
                "search_for": "header_keyword",
                "keywords_from_template": True,
                "get_bounding_box": True
            },
            "step_2_table_detection": {
                "method": "pdfplumber.extract_tables()",
                "within_bbox": "result_of_step_1 + margin_50px",
                "table_settings": {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "intersection_tolerance": 5
                }
            },
            "step_3_parse_rows": {
                "headers": "first_row",
                "data_rows": "remaining_rows",
                "create_dict": {
                    "key": "TYPE_column",
                    "value": {
                        "width": "WIDTH_or_SIZE_column",
                        "height": "HEIGHT_column",
                        "quantity": "QUANTITY_column"
                    }
                }
            }
        },
        "output_format": {
            "schedule_dict": {
                "D1": {"width": 0.9, "height": 2.1, "quantity": 1},
                "D2": {"width": 0.9, "height": 2.1, "quantity": 1}
            }
        }
    },

    # =========================================================================
    # PHASE 1C: WALLS
    # =========================================================================

    "WALL_VECTOR_LINES": {
        "description": "Detect walls from continuous line vectors",
        "method": "vector_line_detection",
        "execution": {
            "step_1": {
                "extract": "all_lines_from_page",
                "filter_by": {
                    "min_length": 0.5,  # meters (after calibration)
                    "line_weight": ">= 1.0",  # Thick lines
                    "exclude_curves": True
                }
            },
            "step_2": {
                "group_collinear": {
                    "method": "slope_clustering",
                    "tolerance": 5  # degrees
                },
                "merge_continuous": {
                    "max_gap": 0.1  # meters
                }
            },
            "step_3": {
                "classify": {
                    "horizontal": "abs(angle) < 10 OR abs(angle - 180) < 10",
                    "vertical": "abs(angle - 90) < 10 OR abs(angle - 270) < 10"
                }
            }
        },
        "output_format": {
            "walls": [
                {
                    "start": "list[x1, y1]",
                    "end": "list[x2, y2]",
                    "height": "from_elevation_data",
                    "thickness": 0.1,
                    "wall_type": "interior"
                }
            ]
        }
    },

    "BUILDING_PERIMETER": {
        "description": "Generate outer walls from building envelope",
        "method": "geometric_calculation",
        "execution": {
            "calculate_from_dimensions": {
                "north_wall": {"start": "list[0, 0]", "end": "list[building_width, 0]"},
                "south_wall": {"start": "list[0, building_length]", "end": "list[building_width, building_length]"},
                "east_wall": {"start": "list[0, 0]", "end": "list[0, building_length]"},
                "west_wall": {"start": "list[building_width, 0]", "end": "list[building_width, building_length]"}
            },
            "add_properties": {
                "height": "from_elevation_data",
                "thickness": 0.3,
                "wall_type": "exterior"
            }
        }
    },

    # =========================================================================
    # PHASE 2: OPENINGS
    # =========================================================================

    "TEXT_LABEL_SEARCH": {
        "description": "Search for text labels (D1, W1, etc.) and extract position",
        "method": "text_coordinate_extraction",
        "execution": {
            "step_1": {
                "extract": "all_words_from_page",
                "method": "pdfplumber.extract_words()",
                "get_properties": ["text", "x0", "top", "x1", "bottom"]
            },
            "step_2": {
                "filter": {
                    "text_in": "search_text_from_template",
                    "case_transform": "upper"
                }
            },
            "step_3": {
                "transform_coordinates": {
                    "method": "apply_calibration",
                    "building_x": "(word['x0'] - offset_x) * scale_x",
                    "building_y": "(word['top'] - offset_y) * scale_y",
                    "building_z": "from_height_rules"
                }
            },
            "step_4": {
                "validate_position": {
                    "within_building_bounds": True,
                    "margin": 1.0  # meters tolerance
                }
            },
            "step_5": {
                "lookup_dimensions": {
                    "from": "schedule_data",
                    "key": "matched_text"
                }
            }
        },
        "output_format": {
            "objects": [
                {
                    "name": "D1",
                    "object_type": "from_template",
                    "position": "list[x, y, z]",
                    "width": "from_schedule",
                    "height": "from_schedule",
                    "confidence": 90
                }
            ]
        }
    },

    # =========================================================================
    # PHASE 3: ELECTRICAL
    # =========================================================================

    "TEXT_MARKER_WITH_SYMBOL": {
        "description": "Find text marker with optional vector symbol nearby",
        "method": "text_plus_optional_symbol",
        "execution": {
            "step_1": {
                "search": "text_markers_from_template",
                "method": "extract_words()",
                "transform_coordinates": "apply_calibration"
            },
            "step_2": {
                "optional_symbol_detection": {
                    "search_radius": 0.3,  # meters around text
                    "vector_patterns": {
                        "circle": "curves with closure",
                        "square": "4 lines forming closed shape"
                    },
                    "if_not_found": "use_text_position_only"
                }
            },
            "step_3": {
                "apply_height_rule": {
                    "method": "lookup_from_template",
                    "rules": {
                        "1.2m_from_floor": 1.2,
                        "0.3m_from_floor": 0.3,
                        "ceiling_height": "use_ceiling_level_from_elevation"
                    }
                }
            },
            "step_4": {
                "snap_to_wall": {
                    "method": "find_nearest_wall",
                    "max_distance": 0.5,  # meters
                    "adjust_position": "perpendicular_to_wall_surface"
                }
            }
        },
        "output_format": {
            "objects": [
                {
                    "name": "auto_generated",
                    "object_type": "from_template",
                    "position": "list[x, y, z]",
                    "orientation": "perpendicular_to_wall",
                    "confidence": 85
                }
            ]
        }
    },

    # =========================================================================
    # PHASE 4: PLUMBING
    # =========================================================================

    "TOILET_BOWL_COMBO": {
        "description": "Detect toilet by ellipse (bowl) + trapezoid (tank) + WC text correlation",
        "method": "multi_shape_correlation",
        "execution": {
            "step_1_text_search": {
                "search_for": "text_markers",
                "keywords": ["WC", "wc", "TOILET"],
                "get_positions": True,
                "create_correlation_zones": {
                    "radius": 5.0  # meters
                }
            },
            "step_2_vector_detection": {
                "find_ellipses": {
                    "method": "detect_curves_with_closure",
                    "aspect_ratio": [1.2, 1.8],
                    "size_range": [0.4, 0.6],  # meters
                    "filter_by": "major_axis_orientation"
                },
                "find_trapezoids": {
                    "method": "detect_4_line_shapes",
                    "size": "smaller_than_ellipse",
                    "spatial_relation": "behind_ellipse"
                }
            },
            "step_3_correlation": {
                "require": "ellipse AND trapezoid AND text_marker_within_zone",
                "validation": {
                    "fail_if_no_text_marker": True,
                    "confidence_penalty": "if_text_marker_far"
                }
            },
            "step_4_position": {
                "use": "ellipse_centroid",
                "orientation": "tank_to_wall_direction"
            }
        },
        "validation_rules": {
            "must_have_WC_text_in_room": True,
            "fail_if_missing": "text_correlation"
        },
        "output_format": {
            "objects": [
                {
                    "name": "TOILET_auto",
                    "object_type": "floor_mounted_toilet_lod300",
                    "position": "list[x, y, 0.0]",
                    "orientation": "angle_to_wall",
                    "confidence": 80,
                    "validation_passed": True
                }
            ]
        }
    },

    "BASIN_SYMBOL": {
        "description": "Detect basin from circle/oval with faucet mark",
        "method": "shape_with_appendage",
        "execution": {
            "step_1": {
                "find_circles_or_ovals": {
                    "method": "curve_detection",
                    "size_range": [0.3, 0.6],  # meters
                    "aspect_ratio": [0.8, 1.5]
                }
            },
            "step_2": {
                "find_faucet_mark": {
                    "search_for": "small_line_at_edge",
                    "optional": True
                }
            },
            "step_3": {
                "room_correlation": {
                    "prefer_in_washroom": True,
                    "text_markers": ["BASIN", "WASH"]
                }
            }
        },
        "smart_selection": {
            "prefer_round_for_washroom": {
                "if_room_type": "washroom",
                "object_type": "basin_round_residential_lod300"
            }
        }
    },

    "SINK_SYMBOL": {
        "description": "Detect kitchen sink from rectangle with divider line",
        "method": "divided_rectangle",
        "execution": {
            "step_1": {
                "find_rectangles": {
                    "size_range": [0.8, 1.5],  # meters length
                    "aspect_ratio": [1.5, 3.0]
                }
            },
            "step_2": {
                "check_divider": {
                    "look_for": "internal_line",
                    "orientation": "parallel_to_short_edge"
                }
            },
            "step_3": {
                "room_constraint": {
                    "must_be_in_kitchen": True,
                    "validation": "check_room_boundary"
                }
            }
        },
        "smart_selection": {
            "prefer_sink_with_drainboard": {
                "object_type": "kitchen_sink_single_bowl_with_drainboard_lod300",
                "reason": "residential_kitchen_benefit"
            }
        }
    },

    "SHOWER_SYMBOL": {
        "description": "Detect shower from circle with spray lines",
        "method": "symbol_with_radiating_lines",
        "execution": {
            "step_1": {
                "find_circles": {
                    "size_range": [0.1, 0.3]  # meters
                }
            },
            "step_2": {
                "check_spray_lines": {
                    "look_for": "short_lines_radiating_from_circle",
                    "count": ">= 3",
                    "optional": True
                }
            },
            "step_3": {
                "room_constraint": {
                    "must_be_in_washroom": True
                }
            }
        }
    },

    "DRAIN_SYMBOL": {
        "description": "Detect floor drain from small circle with cross",
        "method": "circle_with_cross",
        "execution": {
            "step_1": {
                "find_small_circles": {
                    "size_range": [0.05, 0.15]  # meters
                }
            },
            "step_2": {
                "check_cross_mark": {
                    "look_for": "two_perpendicular_lines_through_center",
                    "optional": True
                }
            }
        }
    },

    # =========================================================================
    # PHASE 5: BUILT-INS
    # =========================================================================

    "CABINET_VECTOR_PATTERN": {
        "description": "Detect cabinets from continuous rectangles along wall",
        "method": "aligned_rectangles",
        "execution": {
            "step_1": {
                "find_rectangles": {
                    "along_wall": True,
                    "parallel_to_wall": "within_5_degrees",
                    "size_range": [0.6, 1.2]  # meters per unit
                }
            },
            "step_2": {
                "group_continuous": {
                    "max_gap": 0.1,  # meters
                    "same_alignment": True
                }
            },
            "step_3": {
                "classify_type": {
                    "base_cabinet": "solid_line_pattern",
                    "wall_cabinet": "dashed_line_pattern"
                }
            },
            "step_4": {
                "apply_height": {
                    "base_cabinet": 0.9,  # meters from floor
                    "wall_cabinet": 2.0   # meters from floor
                }
            }
        }
    },

    # =========================================================================
    # PHASE 6: FURNITURE
    # =========================================================================

    "FURNITURE_RECTANGLE_WITH_TEXT": {
        "description": "Detect furniture from rectangles with text labels",
        "method": "labeled_rectangle",
        "execution": {
            "step_1": {
                "search_text": "from_template",
                "get_position": True
            },
            "step_2": {
                "find_rectangle_nearby": {
                    "search_radius": 1.0,  # meters
                    "size_constraints": "from_furniture_type",
                    "use_rectangle_center_as_position": True
                }
            },
            "step_3": {
                "room_constraint": {
                    "check": "from_template",
                    "validate_room_boundary": True
                }
            },
            "step_4": {
                "smart_selection": {
                    "apply_rules": "from_template",
                    "examples": {
                        "bed_queen_for_master": "if master_bedroom",
                        "bed_single_for_secondary": "if secondary_bedroom"
                    }
                }
            }
        }
    },

    "APPLIANCE_RECTANGLE_WITH_TEXT": {
        "description": "Detect kitchen appliances from rectangles with text",
        "method": "labeled_rectangle_in_kitchen",
        "execution": {
            "inherit_from": "FURNITURE_RECTANGLE_WITH_TEXT",
            "additional_constraint": {
                "room": "must_be_kitchen"
            }
        }
    },

    "APPLIANCE_SYMBOL": {
        "description": "Detect stove from square with burner circles",
        "method": "symbol_with_internal_pattern",
        "execution": {
            "step_1": {
                "find_squares": {
                    "size_range": [0.5, 0.8]  # meters
                }
            },
            "step_2": {
                "check_burner_pattern": {
                    "look_for": "small_circles_inside",
                    "count": [2, 4],
                    "arranged_in": "grid_pattern"
                }
            },
            "step_3": {
                "room_constraint": {
                    "must_be_in_kitchen": True
                }
            }
        }
    }
}


# =============================================================================
# HELPER FUNCTIONS (Low-level geometric operations)
# =============================================================================

def calculate_distance_to_page_edge(shape_bbox, page_bbox):
    """Calculate minimum distance from shape to any page edge"""
    distances = [
        shape_bbox['y0'] - page_bbox['y0'],  # Distance to top
        page_bbox['y1'] - shape_bbox['y1'],  # Distance to bottom
        shape_bbox['x0'] - page_bbox['x0'],  # Distance to left
        page_bbox['x1'] - shape_bbox['x1']   # Distance to right
    ]
    return min(distances)


def is_collinear(line1, line2, angle_tolerance=5):
    """Check if two lines are collinear within tolerance"""
    import math
    angle1 = math.atan2(line1['y1'] - line1['y0'], line1['x1'] - line1['x0'])
    angle2 = math.atan2(line2['y1'] - line2['y0'], line2['x1'] - line2['x0'])
    angle_diff = abs(math.degrees(angle1 - angle2))
    return angle_diff < angle_tolerance or angle_diff > (180 - angle_tolerance)


def detect_closed_shape(lines, closure_tolerance=5):
    """Detect if lines form a closed shape"""
    # Implementation: Check if end points connect back to start
    pass


def find_nearest_wall(position, walls, max_distance=0.5):
    """
    Find nearest wall to a given position

    Args:
        position: [x, y, z] coordinates
        walls: List of wall dicts with start_point, end_point
        max_distance: Maximum distance to consider (meters)

    Returns:
        dict: {wall: wall_dict, distance: float, orientation: float (degrees)}
              or None if no wall within max_distance
    """
    import math

    if not walls:
        return None

    nearest_wall = None
    min_distance = float('inf')
    best_orientation = 0.0

    for wall in walls:
        # Get wall endpoints
        x1, y1 = wall['start_point'][0], wall['start_point'][1]
        x2, y2 = wall['end_point'][0], wall['end_point'][1]

        # Calculate perpendicular distance from point to line
        px, py = position[0], position[1]

        # Line vector
        dx = x2 - x1
        dy = y2 - y1
        line_length_sq = dx*dx + dy*dy

        if line_length_sq == 0:
            continue

        # Projection parameter
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / line_length_sq))

        # Closest point on line segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Distance to closest point
        distance = math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

        if distance < min_distance:
            min_distance = distance
            nearest_wall = wall

            # Calculate orientation perpendicular to wall
            wall_angle = math.degrees(math.atan2(dy, dx))
            # Perpendicular is +90 degrees from wall angle
            best_orientation = (wall_angle + 90) % 360

    if min_distance <= max_distance:
        return {
            'wall': nearest_wall,
            'distance': min_distance,
            'orientation': best_orientation
        }

    return None


def calculate_orientation_from_walls(position, walls):
    """
    Calculate orientation for an object based on nearest wall

    Args:
        position: [x, y, z] coordinates
        walls: List of wall dicts

    Returns:
        float: Orientation in degrees (0-360), or 0.0 if no walls available
    """
    nearest = find_nearest_wall(position, walls, max_distance=0.5)

    if nearest:
        return nearest['orientation']

    return 0.0  # Default if no wall found


# =============================================================================
# EXECUTION ENGINE
# =============================================================================

class VectorPatternExecutor:
    """
    Executes vector pattern matching based on detection_id from master template

    Usage:
        executor = VectorPatternExecutor(pdf, calibration_engine)
        result = executor.execute("TEXT_LABEL_SEARCH", search_text=["D1", "D2"], context={})
    """

    def __init__(self, pdf, calibration_engine=None):
        self.pdf = pdf
        self.calibration_engine = calibration_engine
        self.calibration = None  # Will be set after calibration extraction

    def execute(self, detection_id, search_text=None, pages=None, object_type=None, context=None):
        """
        Execute pattern matching for given detection_id

        Args:
            detection_id: Pattern identifier from master template
            search_text: Text keywords to search for
            pages: Page numbers to search (0-indexed)
            object_type: IFC object type from library
            context: Shared extraction context (calibration, schedules, etc.)

        Returns:
            Result depends on detection type (dict, list, or None)
        """
        if detection_id not in VECTOR_PATTERNS:
            raise ValueError(f"Unknown detection_id: {detection_id}")

        pattern = VECTOR_PATTERNS[detection_id]
        method = pattern['method']
        context = context or {}

        # Update calibration if available in context
        if 'calibration' in context:
            self.calibration = context['calibration']

        # Route to appropriate method
        if method == "vector_bounding_box":
            return self._execute_calibration(pattern, pages or [6], context)

        elif method == "regex_pattern_matching":
            return self._execute_regex_search(pattern, search_text, pages or [2, 3])

        elif method == "table_parsing":
            return self._execute_schedule_extraction(pattern, search_text, pages or [7])

        elif method == "text_coordinate_extraction":
            return self._execute_text_label_search(pattern, search_text, pages or [0], object_type, context)

        elif method == "text_plus_optional_symbol":
            return self._execute_text_marker_with_symbol(pattern, search_text, pages or [0], object_type, context)

        elif method in ["vector_line_detection", "geometric_calculation"]:
            # Wall detection - not implemented in POC
            return None

        elif method in ["multi_shape_correlation", "shape_with_appendage", "divided_rectangle",
                       "symbol_with_radiating_lines", "circle_with_cross"]:
            # Complex vector patterns - use text fallback for POC
            return self._execute_text_fallback(pattern, search_text, pages or [0], object_type, context)

        elif method in ["aligned_rectangles", "labeled_rectangle", "labeled_rectangle_in_kitchen",
                       "symbol_with_internal_pattern"]:
            # Furniture/cabinet patterns - use text fallback for POC
            return self._execute_text_fallback(pattern, search_text, pages or [0], object_type, context)

        else:
            raise NotImplementedError(f"Method {method} not implemented in POC")

    def _execute_calibration(self, pattern, pages, context):
        """Execute CALIBRATION_DRAIN_PERIMETER pattern"""
        # Use existing CalibrationEngine
        if not self.calibration_engine:
            return None

        # Try each page to find calibration
        for page_num in pages:
            try:
                calibration_data = self.calibration_engine.extract_drain_perimeter(page_num)
                if calibration_data and calibration_data.get('confidence', 0) > 60:
                    return calibration_data
            except:
                continue

        return None

    def _execute_regex_search(self, pattern, search_text, pages):
        """Execute ELEVATION_TEXT_REGEX pattern"""
        import re

        for page_num in pages:
            if page_num >= len(self.pdf.pages):
                continue

            page = self.pdf.pages[page_num]
            text = page.extract_text() or ""

            # Try each search text keyword
            for keyword in (search_text or []):
                # Common regex patterns for dimensions
                patterns = [
                    (rf'{keyword}\s*\+?\s*(\d+\.?\d*)\s*m(?!m)', 1.0),  # "FFL +0.150m"
                    (rf'{keyword}\s*\+?\s*(\d+)\s*mm', 0.001),           # "FFL +150mm"
                    (rf'{keyword}.*?(\d+\.?\d*)\s*m(?!m)', 1.0),        # "FFL LEVEL 0.150m"
                    (rf'{keyword}.*?(\d+)\s*mm', 0.001)                  # "FFL LEVEL 150mm"
                ]

                for regex_pattern, multiplier in patterns:
                    match = re.search(regex_pattern, text, re.IGNORECASE)
                    if match:
                        value = float(match.group(1)) * multiplier
                        # Validate reasonable range (0 to 10 meters)
                        if 0.0 <= value <= 10.0:
                            return value

        return None

    def _execute_schedule_extraction(self, pattern, search_text, pages):
        """Execute SCHEDULE_TABLE_EXTRACTION pattern"""
        # POC: Use existing ScheduleExtractor from extraction_engine
        # In production, this would be reimplemented here
        from extraction_engine import ScheduleExtractor

        schedule_extractor = ScheduleExtractor(self.pdf)

        # Determine if door or window schedule
        if search_text and any('DOOR' in text.upper() or 'PINTU' in text.upper() for text in search_text):
            return schedule_extractor.extract_door_schedule(pages[0] if pages else 7)
        elif search_text and any('WINDOW' in text.upper() or 'TINGKAP' in text.upper() for text in search_text):
            return schedule_extractor.extract_window_schedule(pages[0] if pages else 7)

        return {}

    def _execute_text_label_search(self, pattern, search_text, pages, object_type, context):
        """Execute TEXT_LABEL_SEARCH pattern

        NEW: Now captures OCR annotations as ground truth for validation
        """
        if not self.calibration:
            raise RuntimeError("Calibration required before TEXT_LABEL_SEARCH. Run calibration first.")

        # Initialize annotations in context if not present
        if 'annotations' not in context:
            context['annotations'] = {
                'doors': [],
                'windows': [],
                'rooms': [],
                'dimensions': [],
                'other': []
            }

        results = []
        for page_num in pages:
            if page_num >= len(self.pdf.pages):
                continue

            page = self.pdf.pages[page_num]
            words = page.extract_words()

            for word in words:
                text_upper = word['text'].upper().strip()

                # Match search text
                if text_upper in [s.upper() for s in (search_text or [])]:
                    # Transform coordinates using calibration
                    x = (word['x0'] - self.calibration['offset_x']) * self.calibration['scale_x']
                    y = (word['top'] - self.calibration['offset_y']) * self.calibration['scale_y']

                    # Get dimensions from schedule if available
                    width = None
                    height = None
                    room = "unknown"

                    # Check door schedule
                    door_schedule = context.get('door_schedule', {})
                    is_door = text_upper in door_schedule
                    if is_door:
                        width = door_schedule[text_upper].get('width')
                        height = door_schedule[text_upper].get('height')

                    # Check window schedule
                    window_schedule = context.get('window_schedule', {})
                    is_window = text_upper in window_schedule
                    if is_window:
                        width = window_schedule[text_upper].get('width')
                        height = window_schedule[text_upper].get('height')

                    # Calculate orientation from nearest wall
                    walls = context.get('walls', [])
                    orientation = calculate_orientation_from_walls([x, y, 0.0], walls)

                    # Generate object name
                    object_name = f"{text_upper}_x{int(x*10)}_y{int(y*10)}"
                    print(f"        [ANNOTATION DEBUG] Generating annotation for {text_upper} → {object_name}")

                    # NEW: Capture annotation as ground truth
                    annotation = {
                        'text': text_upper,
                        'pdf_position': {
                            'x': word['x0'],
                            'y': word['top'],
                            'page': page_num
                        },
                        'building_position': [x, y, 0.0],
                        'bbox_pdf': {
                            'x0': word['x0'],
                            'y0': word['top'],
                            'x1': word['x1'],
                            'y1': word['bottom']
                        },
                        'confidence': 90,
                        'associated_object': object_name,
                        'extracted_from': 'floor_plan_label'
                    }

                    # Store annotation in appropriate category
                    if is_door:
                        context['annotations']['doors'].append(annotation)
                    elif is_window:
                        context['annotations']['windows'].append(annotation)
                    else:
                        context['annotations']['other'].append(annotation)

                    # Build object dict
                    obj = {
                        'name': object_name,
                        'object_type': object_type,
                        'position': [x, y, 0.0],
                        'orientation': orientation,
                        'room': room,
                        '_annotation_captured': True  # Mark that annotation exists
                    }

                    if width:
                        obj['width'] = width
                    if height:
                        obj['height'] = height

                    results.append(obj)

        return results if results else None

    def _execute_text_marker_with_symbol(self, pattern, search_text, pages, object_type, context):
        """Execute TEXT_MARKER_WITH_SYMBOL pattern (switches, outlets, lights, fans)

        NEW: Now captures OCR annotations as ground truth for validation
        """
        if not self.calibration:
            raise RuntimeError("Calibration required before TEXT_MARKER_WITH_SYMBOL.")

        # Initialize annotations in context if not present
        if 'annotations' not in context:
            context['annotations'] = {
                'doors': [],
                'windows': [],
                'rooms': [],
                'dimensions': [],
                'other': []
            }

        results = []
        for page_num in pages:
            if page_num >= len(self.pdf.pages):
                continue

            page = self.pdf.pages[page_num]
            words = page.extract_words()

            for word in words:
                text_upper = word['text'].upper().strip()

                # Match search text
                if any(text_upper.startswith(s.upper()) for s in (search_text or [])):
                    # Transform coordinates
                    x = (word['x0'] - self.calibration['offset_x']) * self.calibration['scale_x']
                    y = (word['top'] - self.calibration['offset_y']) * self.calibration['scale_y']

                    # Generate unique name
                    name = f"{text_upper}_{len(results)+1}"

                    # NEW: Capture annotation as ground truth
                    annotation = {
                        'text': text_upper,
                        'pdf_position': {
                            'x': word['x0'],
                            'y': word['top'],
                            'page': page_num
                        },
                        'building_position': [x, y, 0.0],
                        'bbox_pdf': {
                            'x0': word['x0'],
                            'y0': word['top'],
                            'x1': word['x1'],
                            'y1': word['bottom']
                        },
                        'confidence': 85,
                        'associated_object': name,
                        'extracted_from': 'floor_plan_label',
                        'category': 'electrical'
                    }
                    context['annotations']['other'].append(annotation)

                    # Calculate orientation from nearest wall
                    walls = context.get('walls', [])
                    orientation = calculate_orientation_from_walls([x, y, 0.0], walls)

                    obj = {
                        'name': name,
                        'object_type': object_type,
                        'position': [x, y, 0.0],
                        'orientation': orientation,
                        'room': "unknown",
                        '_annotation_captured': True  # Mark that annotation exists
                    }

                    results.append(obj)

        return results if results else None

    def _execute_text_fallback(self, pattern, search_text, pages, object_type, context):
        """
        Text-based fallback for complex vector patterns (POC)

        Used when vector pattern detection is not implemented.
        Simply searches for text labels and extracts positions.

        NEW: Now captures OCR annotations as ground truth for validation
        """
        if not self.calibration:
            return None

        if not search_text:
            return None

        # Initialize annotations in context if not present
        if 'annotations' not in context:
            context['annotations'] = {
                'doors': [],
                'windows': [],
                'rooms': [],
                'dimensions': [],
                'other': []
            }

        results = []
        for page_num in pages:
            if page_num >= len(self.pdf.pages):
                continue

            page = self.pdf.pages[page_num]
            words = page.extract_words()

            for word in words:
                text_upper = word['text'].upper().strip()

                # Match any of the search texts
                if any(s.upper() in text_upper for s in search_text):
                    # Transform coordinates
                    x = (word['x0'] - self.calibration['offset_x']) * self.calibration['scale_x']
                    y = (word['top'] - self.calibration['offset_y']) * self.calibration['scale_y']

                    # Generate name
                    name = f"{text_upper}_{len(results)+1}"

                    # NEW: Capture annotation as ground truth
                    annotation = {
                        'text': text_upper,
                        'pdf_position': {
                            'x': word['x0'],
                            'y': word['top'],
                            'page': page_num
                        },
                        'building_position': [x, y, 0.0],
                        'bbox_pdf': {
                            'x0': word['x0'],
                            'y0': word['top'],
                            'x1': word['x1'],
                            'y1': word['bottom']
                        },
                        'confidence': 80,
                        'associated_object': name,
                        'extracted_from': 'floor_plan_label',
                        'category': 'furniture_or_fixture'
                    }
                    context['annotations']['other'].append(annotation)

                    # Calculate orientation from nearest wall
                    walls = context.get('walls', [])
                    orientation = calculate_orientation_from_walls([x, y, 0.0], walls)

                    obj = {
                        'name': name,
                        'object_type': object_type,
                        'position': [x, y, 0.0],
                        'orientation': orientation,
                        'room': "unknown",
                        '_annotation_captured': True  # Mark that annotation exists
                    }

                    results.append(obj)

        return results if results else None
