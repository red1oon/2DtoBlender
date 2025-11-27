# Automated Element Placement Algorithm

## Objective
Generate initial door/window placements from 2D drawing data with ~80% accuracy, leaving 20% for GUI refinement.

---

## Building Code Compliance (Malaysia UBBL 1984 + International)

### Room Requirements (UBBL By-Law 42-44)

| Room Type | Min Area | Min Width | Min Height |
|-----------|----------|-----------|------------|
| Habitable room (bedroom/living) | 6.5 m² | 2.0 m | 2.5 m |
| Kitchen | - | - | 2.25 m |
| Bathroom | 1.5 m² | 0.75 m | 2.0 m |
| Bathroom + WC | 2.0 m² | 0.75 m | 2.0 m |
| WC (pedestal) | 1.5 × 0.75 m | 0.75 m | 2.0 m |
| WC (squat) | 1.25 × 0.75 m | 0.75 m | 2.0 m |

### Natural Light & Ventilation (UBBL By-Law 39)

| Building Type | Window Area | Openable Area |
|---------------|-------------|---------------|
| Residential/Commercial | ≥10% floor area | ≥5% floor area (half of 10%) |
| Bathroom/WC | ≥0.2 m² per unit | Must allow free unimpeded passage of air |

### Door Requirements

| Type | Min Width | Min Height | Notes |
|------|-----------|------------|-------|
| Main entrance | 900 mm | 2100 mm | Single leaf, exterior |
| Bedroom | 800-900 mm | 2100 mm | Interior, swing into room |
| Bathroom/WC | 700-750 mm | 2100 mm | Swing outward (safety) |
| Accessible (MS 1184) | 900 mm clear | 2100 mm | 32" (813mm) clear opening |

### Window Requirements

| Type | Typical Size | Sill Height | Notes |
|------|--------------|-------------|-------|
| Bedroom egress | ≥1200×1000 mm | ≤1118 mm (44") | Emergency escape |
| Living room | 1800×1000 mm | 900 mm | Viewing |
| Bathroom (high) | 600×500 mm | 1500 mm | Privacy + ventilation |
| Kitchen | 1200×1000 mm | 900 mm | Above counter |

### Egress Requirements (International/IRC)

- **Bedroom windows**: Min 5.7 sq ft (0.53 m²) clear opening
- **Min dimensions**: 20" (508mm) wide × 24" (610mm) high
- **Max sill height**: 44" (1118mm) from floor
- **Purpose**: Emergency escape and rescue

### Safety Glazing (UBBL + International)

Required locations for tempered/safety glass:
- Within 450mm of door edges
- Within 300mm of floor level
- Adjacent to bathtub/shower (within 1500mm)
- Staircase glazing

---

## Inputs

| Source | Data | Format |
|--------|------|--------|
| GridTruth | Grid labels, dimensions, origin | JSON |
| Schedule OCR | Element→Room assignments, sizes | Text/JSON |
| Constraints | Room shapes (square/rectangle) | Rules |

---

## Algorithm

### Phase 1: Room Boundary Inference

```
FOR each room in ROOM_LIST:
    IF room.type == "bedroom":
        room.shape = SQUARE
        room.size = 3.1m × 3.1m  # from grid segment
    ELIF room.type == "washroom":
        room.shape = RECTANGLE
        room.size = 1.3m × 1.6m  # A-B column width
    
    room.bounds = assign_to_grid_cells(room, GridTruth)
```

**Grid Cell Assignment Heuristic:**
- Bedrooms occupy D-E or C-D columns (3.1m width)
- Washrooms occupy A-B column (1.3m width)
- Vertical stacking based on row count

### Phase 2: Door Placement Rules

```
FOR each door in SCHEDULE:
    room = door.assigned_room
    
    # Determine wall selection
    IF room.is_interior:
        wall = select_wall_adjacent_to(CORRIDOR or LIVING)
    ELIF room.is_exterior:
        wall = select_exterior_wall()
    
    # Position on wall
    door.position = wall.center - (door.width / 2)
    door.position.z = 0  # floor level
    
    # Swing direction
    door.swing = infer_swing(room, wall)
```

**Wall Selection Priority:**
1. Wall shared with circulation space (hallway/living)
2. Shorter wall if rectangular room
3. Wall without windows

### Phase 3: Window Placement Rules

```
FOR each window in SCHEDULE:
    room = window.assigned_room
    
    # Exterior walls only
    wall = select_exterior_wall(room)
    
    # Sill height by type
    IF window.size.height >= 1000mm:
        window.sill = 900mm  # viewing window
    ELSE:
        window.sill = 1500mm  # high ventilation
    
    # Center on wall, avoid corners
    window.position = wall.center - (window.width / 2)
    window.position = clamp(window.position, 
                            wall.start + 300mm, 
                            wall.end - 300mm)
```

### Phase 4: Collision Detection

```
FOR each element in PLACED_ELEMENTS:
    FOR each other in PLACED_ELEMENTS:
        IF overlap(element, other):
            # Shift along wall
            element.position += shift_increment
            RECHECK collision
```

---

## Output Schema

```json
{
  "placements": [
    {
      "element_id": "D1_1",
      "type": "door",
      "code": "D1",
      "room": "RUANG_TAMU",
      "wall": "north",
      "position": {"x": 5.2, "y": 2.3, "z": 0},
      "size": {"width": 0.9, "height": 2.1},
      "confidence": 0.75,
      "requires_review": true
    }
  ]
}
```

---

## Confidence Scoring

| Factor | Score Impact |
|--------|--------------|
| Room boundary derived from grid | +0.3 |
| Single valid wall for element | +0.2 |
| Multiple wall options | -0.1 |
| Collision resolved by shift | -0.15 |
| Schedule explicitly states room | +0.2 |

`confidence < 0.6` → Flag for GUI review

---

## GUI Refinement Hooks

Elements flagged for review:
- Click-drag repositioning on wall
- Wall reassignment dropdown
- Swing direction toggle
- Size override from dropdown

---

## Constraints Table

| Room Type | Shape | Door Wall | Window Wall | Door Swing |
|-----------|-------|-----------|-------------|------------|
| Bedroom (BILIK) | Square 3.1×3.1 | Interior (to corridor) | Exterior | Into room |
| Living (RUANG_TAMU) | L-shape/Rectangle | Exterior (main entry) | Exterior | Into house |
| Kitchen (DAPUR) | Rectangle | Interior (from living) | Exterior | Into kitchen |
| Bathroom (BILIK_MANDI) | Rectangle ≤2m² | Interior | High vent (1500mm sill) | **Outward** |
| Toilet (TANDAS) | Rectangle ≤1.5m² | Interior | High vent (1500mm sill) | **Outward** |

### Architectural Placement Rules

#### Door Placement
1. **Clear swing arc**: Door must have unobstructed 90° swing
2. **Wall clearance**: Min 100mm from perpendicular wall to door frame
3. **Furniture clearance**: Consider bed/furniture placement in bedrooms
4. **Bathroom doors swing OUT**: Safety requirement (unconscious person blocks inward swing)
5. **Entry doors swing IN**: Security and weather protection
6. **Adjacent doors**: Min 600mm between door edges when both open

#### Window Placement  
1. **Center on wall**: Default position unless obstruction
2. **Corner clearance**: Min 300mm from wall corners
3. **Above furniture**: Living/bedroom windows at 900mm sill (above sofa/bed)
4. **Kitchen windows**: Above counter height (900mm sill)
5. **Bathroom windows**: High placement (1500mm sill) for privacy
6. **Egress windows**: Max 1118mm sill height in bedrooms

#### Room-Specific Rules
1. **Bedrooms**: One door + min one egress window on exterior wall
2. **Bathrooms**: Door opposite to WC, window away from shower
3. **Kitchen**: Window above sink area preferred
4. **Living room**: Main entry door + largest windows for daylight

---

## Rule 0 Compliance

All inputs derived from:
- OCR extraction (Tesseract/existing .txt files)
- GridTruth JSON (grid system)
- Geometric constraints (defined above)

No manual coordinate entry required for initial placement.
