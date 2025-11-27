#!/usr/bin/env python3
"""
Door Swing Detection Script for TB-LKTN House Pipeline

Since OCR cannot detect arc geometry for door swings, this script uses:
1. Room type rules (bathrooms swing OUT per UBBL safety)
2. Wall position detection (perpendicular projection)
3. Door label proximity matching
4. Grid-snapped coordinate alignment

Outputs spec-compliant door objects with:
- wall: NORTH/SOUTH/EAST/WEST
- swing_direction: "inward" or "outward"
- rotation: 0° (N/S walls) or 90° (E/W walls)

Author: BIM Syncro Engineers
Date: 2025-11-27
Spec Reference: TB-LKTN_COMPLETE_SPECIFICATION.md v1.1
"""

import json
import math
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path


# =============================================================================
# CONFIGURATION - From TB-LKTN_COMPLETE_SPECIFICATION.md
# =============================================================================

# Grid coordinates (Section 2.1)
GRID_X = {
    'A': 0.0,
    'B': 1.3,
    'C': 4.4,
    'D': 8.1,
    'E': 11.2
}

GRID_Y = {
    '1': 0.0,
    '2': 2.3,
    '3': 5.4,
    '4': 7.0,
    '5': 8.5
}

# Building envelope (Section 2.2)
BUILDING_BOUNDS = {
    'x_min': 0.0,
    'x_max': 11.2,
    'y_min': -2.3,  # Includes porch
    'y_max': 8.5
}

# Room definitions (Section 3.1)
ROOMS = {
    'BILIK_UTAMA': {'grid': 'D2-E3', 'x': (8.1, 11.2), 'y': (2.3, 5.4), 'type': 'bedroom'},
    'BILIK_2': {'grid': 'B2-C3', 'x': (1.3, 4.4), 'y': (2.3, 5.4), 'type': 'bedroom'},
    'BILIK_3': {'grid': 'C1-D2', 'x': (4.4, 8.1), 'y': (0.0, 2.3), 'type': 'bedroom'},
    'RUANG_TAMU': {'grid': 'A1-C3', 'x': (0.0, 4.4), 'y': (0.0, 5.4), 'type': 'living'},
    'RUANG_MAKAN': {'grid': 'C1-D2', 'x': (4.4, 8.1), 'y': (0.0, 2.3), 'type': 'dining'},
    'DAPUR': {'grid': 'C2-E4', 'x': (4.4, 11.2), 'y': (2.3, 7.0), 'type': 'kitchen'},
    'BILIK_MANDI': {'grid': 'A3-B4', 'x': (0.0, 1.3), 'y': (5.4, 7.0), 'type': 'bathroom'},
    'TANDAS': {'grid': 'A4-B5', 'x': (0.0, 1.3), 'y': (7.0, 8.5), 'type': 'toilet'},
    'RUANG_BASUH': {'grid': 'C3-D4', 'x': (4.4, 8.1), 'y': (5.4, 7.0), 'type': 'utility'},
    'ANJUNG': {'grid': 'B0-C1', 'x': (2.3, 5.5), 'y': (-2.3, 0.0), 'type': 'porch'},
}

# Door schedule from Page 8 (Section 5.1)
DOOR_SCHEDULE = {
    'D1': {'width_mm': 900, 'height_mm': 2100, 'qty': 2, 'locations': ['RUANG_TAMU', 'DAPUR'], 'type': 'external'},
    'D2': {'width_mm': 900, 'height_mm': 2100, 'qty': 3, 'locations': ['BILIK_UTAMA', 'BILIK_2', 'BILIK_3'], 'type': 'bedroom'},
    'D3': {'width_mm': 750, 'height_mm': 2100, 'qty': 2, 'locations': ['BILIK_MANDI', 'TANDAS'], 'type': 'bathroom'},
}

# Wall segments (exterior + key interior)
WALL_SEGMENTS = [
    # Exterior walls
    {'id': 'WEST', 'x1': 0.0, 'y1': 0.0, 'x2': 0.0, 'y2': 8.5, 'type': 'exterior'},
    {'id': 'EAST', 'x1': 11.2, 'y1': 0.0, 'x2': 11.2, 'y2': 8.5, 'type': 'exterior'},
    {'id': 'SOUTH', 'x1': 0.0, 'y1': 0.0, 'x2': 11.2, 'y2': 0.0, 'type': 'exterior'},
    {'id': 'NORTH', 'x1': 0.0, 'y1': 8.5, 'x2': 11.2, 'y2': 8.5, 'type': 'exterior'},
    # Key interior walls
    {'id': 'INT_Y2.3', 'x1': 0.0, 'y1': 2.3, 'x2': 11.2, 'y2': 2.3, 'type': 'interior'},
    {'id': 'INT_Y5.4', 'x1': 0.0, 'y1': 5.4, 'x2': 11.2, 'y2': 5.4, 'type': 'interior'},
    {'id': 'INT_Y7.0', 'x1': 0.0, 'y1': 7.0, 'x2': 1.3, 'y2': 7.0, 'type': 'interior'},
    {'id': 'INT_X1.3', 'x1': 1.3, 'y1': 2.3, 'x2': 1.3, 'y2': 8.5, 'type': 'interior'},
    {'id': 'INT_X4.4', 'x1': 4.4, 'y1': 0.0, 'x2': 4.4, 'y2': 7.0, 'type': 'interior'},
    {'id': 'INT_X8.1', 'x1': 8.1, 'y1': 2.3, 'x2': 8.1, 'y2': 7.0, 'type': 'interior'},
]

# Rotation mapping (Section 9.1)
WALL_ROTATION = {
    'NORTH': 0,
    'SOUTH': 0,
    'EAST': 90,
    'WEST': 90,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DoorLabel:
    """Raw door label from PDF extraction"""
    text: str
    x: float
    y: float
    page: int
    confidence: float
    
@dataclass 
class DoorPlacement:
    """Spec-compliant door placement"""
    element_id: str
    name: str
    code: str
    object_type: str
    position: Tuple[float, float, float]
    wall: str
    swing_direction: str
    orientation: float
    room: str
    width_mm: int
    height_mm: int
    confidence: float
    derivation: str


# =============================================================================
# GEOMETRY UTILITIES
# =============================================================================

def point_to_line_distance(px: float, py: float, 
                           x1: float, y1: float, 
                           x2: float, y2: float) -> Tuple[float, float, float]:
    """
    Calculate perpendicular distance from point to line segment.
    Returns: (distance, closest_x, closest_y)
    """
    dx = x2 - x1
    dy = y2 - y1
    
    # Handle zero-length segment
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1)**2 + (py - y1)**2), x1, y1
    
    # Parameter t for projection onto line
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    
    # Closest point on line segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    distance = math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    return distance, closest_x, closest_y


def snap_to_grid(x: float, y: float, tolerance: float = 0.15) -> Tuple[float, float]:
    """
    Snap coordinates to nearest grid line if within tolerance.
    """
    snapped_x = x
    snapped_y = y
    
    # Snap X to grid columns
    for grid_x in GRID_X.values():
        if abs(x - grid_x) < tolerance:
            snapped_x = grid_x
            break
    
    # Snap Y to grid rows
    for grid_y in GRID_Y.values():
        if abs(y - grid_y) < tolerance:
            snapped_y = grid_y
            break
    
    return snapped_x, snapped_y


def find_room_at_position(x: float, y: float) -> Optional[str]:
    """
    Determine which room contains the given position.
    """
    for room_name, room_data in ROOMS.items():
        x_min, x_max = room_data['x']
        y_min, y_max = room_data['y']
        
        # Expand bounds slightly for doors on walls
        if (x_min - 0.2 <= x <= x_max + 0.2 and 
            y_min - 0.2 <= y <= y_max + 0.2):
            return room_name
    
    return None


def find_nearest_wall(x: float, y: float, max_distance: float = 0.3) -> Optional[Dict]:
    """
    Find the wall segment nearest to the given position.
    Returns wall info with distance.
    """
    nearest_wall = None
    min_distance = float('inf')
    
    for wall in WALL_SEGMENTS:
        dist, cx, cy = point_to_line_distance(
            x, y, 
            wall['x1'], wall['y1'], 
            wall['x2'], wall['y2']
        )
        
        if dist < min_distance and dist < max_distance:
            min_distance = dist
            nearest_wall = {
                **wall,
                'distance': dist,
                'closest_point': (cx, cy)
            }
    
    return nearest_wall


def determine_wall_direction(wall_segment: Dict, door_x: float, door_y: float) -> str:
    """
    Determine cardinal direction (NORTH/SOUTH/EAST/WEST) of wall relative to building.
    """
    x1, y1 = wall_segment['x1'], wall_segment['y1']
    x2, y2 = wall_segment['x2'], wall_segment['y2']
    
    # Check if horizontal or vertical wall
    is_horizontal = abs(y1 - y2) < 0.1
    is_vertical = abs(x1 - x2) < 0.1
    
    if is_horizontal:
        # Horizontal wall - determine if NORTH or SOUTH
        wall_y = (y1 + y2) / 2
        building_center_y = (BUILDING_BOUNDS['y_min'] + BUILDING_BOUNDS['y_max']) / 2
        
        # Also consider door position relative to wall
        if wall_y >= 7.0:
            return 'NORTH'
        elif wall_y <= 1.0:
            return 'SOUTH'
        else:
            # Interior horizontal wall - determine by room position
            room = find_room_at_position(door_x, door_y)
            if room:
                room_data = ROOMS.get(room, {})
                room_center_y = sum(room_data.get('y', (0, 0))) / 2
                return 'NORTH' if door_y > room_center_y else 'SOUTH'
            return 'SOUTH'  # Default
    
    elif is_vertical:
        # Vertical wall - determine if EAST or WEST
        wall_x = (x1 + x2) / 2
        
        if wall_x >= 10.0:
            return 'EAST'
        elif wall_x <= 1.5:
            return 'WEST'
        else:
            # Interior vertical wall
            room = find_room_at_position(door_x, door_y)
            if room:
                room_data = ROOMS.get(room, {})
                room_center_x = sum(room_data.get('x', (0, 0))) / 2
                return 'EAST' if door_x > room_center_x else 'WEST'
            return 'WEST'  # Default
    
    return 'SOUTH'  # Default fallback


# =============================================================================
# SWING DIRECTION INFERENCE
# =============================================================================

def infer_swing_direction(room_name: str, room_type: str, door_code: str) -> str:
    """
    Infer door swing direction based on room type and UBBL safety rules.
    
    Per TB-LKTN_COMPLETE_SPECIFICATION.md Section 9.2:
    - Bathrooms/Toilets: OUTWARD (safety - unconscious person can't block)
    - All others: INWARD
    """
    # UBBL Safety Rule: Bathroom doors MUST swing outward
    if room_type in ['bathroom', 'toilet']:
        return 'outward'
    
    # D3 doors are bathroom doors by schedule
    if door_code == 'D3':
        return 'outward'
    
    # All other doors swing inward
    return 'inward'


def get_room_type(room_name: str) -> str:
    """Get the type of a room from its name."""
    room_data = ROOMS.get(room_name, {})
    return room_data.get('type', 'unknown')


# =============================================================================
# DOOR PLACEMENT GENERATION
# =============================================================================

def process_door_label(label: DoorLabel, instance_counter: Dict[str, int]) -> Optional[DoorPlacement]:
    """
    Process a single door label and generate spec-compliant placement.
    """
    code = label.text.upper().strip()
    
    # Validate door code
    if code not in DOOR_SCHEDULE:
        print(f"  ⚠️ Unknown door code: {code}")
        return None
    
    schedule = DOOR_SCHEDULE[code]
    
    # Convert PDF coordinates to building coordinates (already done in extraction)
    door_x = label.x
    door_y = label.y
    
    # Snap to grid
    snapped_x, snapped_y = snap_to_grid(door_x, door_y)
    
    # Find room
    room_name = find_room_at_position(snapped_x, snapped_y)
    if not room_name:
        # Try to infer from schedule locations
        for loc in schedule['locations']:
            room_data = ROOMS.get(loc, {})
            x_range = room_data.get('x', (0, 0))
            y_range = room_data.get('y', (0, 0))
            if (x_range[0] - 0.5 <= snapped_x <= x_range[1] + 0.5 and
                y_range[0] - 0.5 <= snapped_y <= y_range[1] + 0.5):
                room_name = loc
                break
    
    if not room_name:
        room_name = 'unknown'
    
    room_type = get_room_type(room_name)
    
    # Find nearest wall
    wall_info = find_nearest_wall(snapped_x, snapped_y, max_distance=0.5)
    
    if wall_info:
        wall_direction = determine_wall_direction(wall_info, snapped_x, snapped_y)
        wall_distance = wall_info['distance']
    else:
        # Infer wall from position on grid
        if abs(snapped_y - 2.3) < 0.2:
            wall_direction = 'SOUTH' if room_type == 'bedroom' else 'NORTH'
        elif abs(snapped_y - 5.4) < 0.2:
            wall_direction = 'NORTH' if snapped_y < 5.4 else 'SOUTH'
        elif abs(snapped_x - 1.3) < 0.2:
            wall_direction = 'EAST'
        elif abs(snapped_x - 4.4) < 0.2:
            wall_direction = 'WEST' if room_name in ['BILIK_2', 'RUANG_TAMU'] else 'EAST'
        else:
            wall_direction = 'SOUTH'
        wall_distance = 0.1
    
    # Determine swing direction
    swing_direction = infer_swing_direction(room_name, room_type, code)
    
    # Calculate rotation from wall direction
    rotation = WALL_ROTATION.get(wall_direction, 0)
    
    # Generate element ID
    instance_counter[code] = instance_counter.get(code, 0) + 1
    element_id = f"{code}_{instance_counter[code]}"
    
    # Generate object name (coordinate-based for traceability)
    name = f"{code}_x{int(snapped_x*10)}_y{int(snapped_y*10)}"
    
    # Generate object_type
    object_type = f"door_{schedule['width_mm']}x{schedule['height_mm']}_lod300"
    
    # Calculate confidence
    confidence = 0.8
    if wall_distance > 0.2:
        confidence -= 0.1
    if room_name == 'unknown':
        confidence -= 0.2
    
    return DoorPlacement(
        element_id=element_id,
        name=name,
        code=code,
        object_type=object_type,
        position=(snapped_x, snapped_y, 0.0),
        wall=wall_direction,
        swing_direction=swing_direction,
        orientation=rotation,
        room=room_name,
        width_mm=schedule['width_mm'],
        height_mm=schedule['height_mm'],
        confidence=confidence,
        derivation=f"Label at ({label.x:.2f}, {label.y:.2f}) → Room {room_name} → Wall {wall_direction} → Swing {swing_direction}"
    )


def deduplicate_doors(doors: List[DoorPlacement], threshold: float = 0.5) -> List[DoorPlacement]:
    """
    Remove duplicate doors within threshold distance.
    Keep the one with higher confidence.
    """
    unique = []
    
    for door in doors:
        is_duplicate = False
        for i, existing in enumerate(unique):
            # Check if same code and within threshold
            if door.code == existing.code:
                dist = math.sqrt(
                    (door.position[0] - existing.position[0])**2 +
                    (door.position[1] - existing.position[1])**2
                )
                if dist < threshold:
                    is_duplicate = True
                    # Keep higher confidence
                    if door.confidence > existing.confidence:
                        unique[i] = door
                    break
        
        if not is_duplicate:
            unique.append(door)
    
    return unique


# =============================================================================
# DATABASE QUERIES
# =============================================================================

def load_door_labels_from_db(db_path: str) -> List[DoorLabel]:
    """
    Load door labels from primitives_text table.
    """
    labels = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query door labels (D1, D2, D3)
        cursor.execute("""
            SELECT text, x, y, page, 
                   COALESCE(confidence, 90) as confidence
            FROM primitives_text
            WHERE text IN ('D1', 'D2', 'D3')
               OR text LIKE 'D1%' OR text LIKE 'D2%' OR text LIKE 'D3%'
            ORDER BY text, y, x
        """)
        
        for row in cursor.fetchall():
            text = row[0].strip().upper()
            # Clean up text (take only D1, D2, or D3)
            if text.startswith('D1'):
                text = 'D1'
            elif text.startswith('D2'):
                text = 'D2'
            elif text.startswith('D3'):
                text = 'D3'
            else:
                continue
                
            labels.append(DoorLabel(
                text=text,
                x=float(row[1]),
                y=float(row[2]),
                page=int(row[3]) if row[3] else 0,
                confidence=float(row[4])
            ))
        
        conn.close()
        print(f"✓ Loaded {len(labels)} door labels from database")
        
    except Exception as e:
        print(f"⚠️ Database error: {e}")
        print("  Falling back to extraction JSON...")
    
    return labels


def load_door_labels_from_json(json_path: str) -> List[DoorLabel]:
    """
    Load door labels from extraction JSON output.
    """
    labels = []
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Check annotations.doors
        annotations = data.get('annotations', {})
        doors = annotations.get('doors', [])
        
        for door in doors:
            text = door.get('text', '').strip().upper()
            if text not in ['D1', 'D2', 'D3']:
                continue
            
            # Get building position (already transformed)
            pos = door.get('building_position', [0, 0, 0])
            
            labels.append(DoorLabel(
                text=text,
                x=float(pos[0]),
                y=float(pos[1]),
                page=door.get('pdf_position', {}).get('page', 0),
                confidence=float(door.get('confidence', 90))
            ))
        
        print(f"✓ Loaded {len(labels)} door labels from JSON")
        
    except Exception as e:
        print(f"⚠️ JSON error: {e}")
    
    return labels


# =============================================================================
# OUTPUT GENERATION
# =============================================================================

def generate_spec_compliant_output(doors: List[DoorPlacement]) -> Dict:
    """
    Generate spec-compliant JSON output matching TB-LKTN_COMPLETE_SPECIFICATION.md Section 10.2
    """
    output = {
        "metadata": {
            "version": "1.0",
            "generator": "door_swing_detector.py",
            "spec_reference": "TB-LKTN_COMPLETE_SPECIFICATION.md v1.1",
            "rule_0_compliant": True,
            "total_doors": len(doors)
        },
        "door_placements": []
    }
    
    for door in doors:
        placement = {
            "element_id": door.element_id,
            "name": door.name,
            "type": "door",
            "code": door.code,
            "object_type": door.object_type,
            "position": {
                "x": door.position[0],
                "y": door.position[1],
                "z": door.position[2]
            },
            "size": {
                "width": door.width_mm / 1000.0,
                "height": door.height_mm / 1000.0
            },
            "width_mm": door.width_mm,
            "height_mm": door.height_mm,
            "wall": door.wall,
            "swing_direction": door.swing_direction,
            "orientation": door.orientation,
            "room": door.room,
            "confidence": door.confidence,
            "requires_review": door.confidence < 0.6,
            "derivation": door.derivation
        }
        output["door_placements"].append(placement)
    
    return output


def validate_against_schedule(doors: List[DoorPlacement]) -> Dict[str, any]:
    """
    Validate extracted doors against Page 8 schedule.
    """
    validation = {
        "schedule_match": True,
        "issues": [],
        "counts": {}
    }
    
    # Count doors by code
    counts = {}
    for door in doors:
        counts[door.code] = counts.get(door.code, 0) + 1
    
    validation["counts"] = counts
    
    # Compare with schedule
    for code, schedule in DOOR_SCHEDULE.items():
        expected = schedule['qty']
        actual = counts.get(code, 0)
        
        if actual != expected:
            validation["schedule_match"] = False
            validation["issues"].append(
                f"{code}: Expected {expected}, got {actual}"
            )
    
    # Check swing directions for bathroom doors
    for door in doors:
        if door.code == 'D3' and door.swing_direction != 'outward':
            validation["issues"].append(
                f"{door.element_id}: D3 (bathroom) should swing OUTWARD"
            )
    
    return validation


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main execution - process doors and generate spec-compliant output.
    """
    print("=" * 60)
    print("Door Swing Detection for TB-LKTN House")
    print("=" * 60)
    
    # Try to load from JSON first (most recent extraction)
    json_path = None
    possible_paths = [
        "TB-LKTN_HOUSE_OUTPUT_20251127_161631_FINAL.json",
        "/mnt/project/TB-LKTN_HOUSE_OUTPUT_20251127_161631_FINAL.json",
        "TB-LKTN_HOUSE_OUTPUT_20251127_154049_FINAL.json",
        "/mnt/project/TB-LKTN_HOUSE_OUTPUT_20251127_154049_FINAL.json",
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            json_path = path
            break
    
    labels = []
    
    if json_path:
        print(f"\n📄 Loading from: {json_path}")
        labels = load_door_labels_from_json(json_path)
    
    # Fallback to database if no labels found
    if not labels:
        db_path = "TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"
        if Path(db_path).exists():
            print(f"\n📊 Loading from database: {db_path}")
            labels = load_door_labels_from_db(db_path)
    
    if not labels:
        print("\n❌ No door labels found. Creating from schedule...")
        # Generate doors from schedule as fallback
        labels = generate_doors_from_schedule()
    
    print(f"\n📍 Processing {len(labels)} door labels...")
    
    # Process each label
    instance_counter = {}
    doors = []
    
    for label in labels:
        print(f"  Processing {label.text} at ({label.x:.2f}, {label.y:.2f})...")
        door = process_door_label(label, instance_counter)
        if door:
            doors.append(door)
            print(f"    → {door.element_id}: Wall={door.wall}, Swing={door.swing_direction}, Room={door.room}")
    
    # Deduplicate
    print(f"\n🔄 Deduplicating {len(doors)} doors...")
    doors = deduplicate_doors(doors)
    print(f"   → {len(doors)} unique doors")
    
    # Validate against schedule
    print("\n📋 Validating against Page 8 schedule...")
    validation = validate_against_schedule(doors)
    
    if validation["schedule_match"]:
        print("   ✅ Schedule match: PASS")
    else:
        print("   ⚠️ Schedule match: ISSUES FOUND")
        for issue in validation["issues"]:
            print(f"      - {issue}")
    
    print(f"   Counts: {validation['counts']}")
    
    # Generate output
    output = generate_spec_compliant_output(doors)
    output["validation"] = validation
    
    # Save output
    output_path = "door_placements_spec_compliant.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Output saved to: {output_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total doors: {len(doors)}")
    print("\nDoor Details:")
    for door in doors:
        swing_icon = "↗️" if door.swing_direction == "outward" else "↙️"
        print(f"  {door.element_id}: {door.room} | Wall: {door.wall} | Swing: {swing_icon} {door.swing_direction} | Rotation: {door.orientation}°")
    
    return output


def generate_doors_from_schedule() -> List[DoorLabel]:
    """
    Generate door labels from schedule when extraction fails.
    Uses room centers as approximate positions.
    """
    labels = []
    
    for code, schedule in DOOR_SCHEDULE.items():
        for location in schedule['locations']:
            room = ROOMS.get(location, {})
            if room:
                # Place at room entry (typically on interior wall)
                x_range = room.get('x', (0, 0))
                y_range = room.get('y', (0, 0))
                
                # Approximate door position based on room type
                room_type = room.get('type', '')
                
                if room_type in ['bathroom', 'toilet']:
                    # Bathroom doors on east wall (facing corridor)
                    x = x_range[1]  # East edge
                    y = (y_range[0] + y_range[1]) / 2
                elif room_type == 'bedroom':
                    # Bedroom doors on south wall (facing corridor)
                    x = (x_range[0] + x_range[1]) / 2
                    y = y_range[0]  # South edge
                else:
                    # Default to center
                    x = (x_range[0] + x_range[1]) / 2
                    y = (y_range[0] + y_range[1]) / 2
                
                labels.append(DoorLabel(
                    text=code,
                    x=x,
                    y=y,
                    page=1,
                    confidence=70  # Lower confidence for inferred positions
                ))
    
    return labels


if __name__ == "__main__":
    main()
