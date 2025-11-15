# Major Expectations Framework - Getting the Important Things Right

**Date:** November 12, 2025
**Philosophy:** Focus on critical accuracy, not perfect detail
**Goal:** 3D shape + crucial disciplines + functional intelligence

---

## Core Principle: The 80/20 Rule

**What Users REALLY Care About:**
```
✅ 20% of elements = 80% of value
   - Correct 3D shape (walls, slabs, structure)
   - Critical MEP systems (sprinklers, HVAC, power)
   - Functional space layouts (toilets, seating, circulation)

❌ 80% of elements = 20% of value
   - Exact ceiling tile count
   - Minor fixtures
   - Decorative elements
```

**Strategy:** Get the 20% absolutely right, guess intelligently on the 80%

---

## The Three Pillars of Major Expectations

### 1. 3D SHAPE (Spatial Correctness)
*"Does it look like a building?"*

### 2. CRUCIAL DISCIPLINES (Life Safety)
*"Can people use it safely?"*

### 3. FUNCTIONAL PURPOSE (Intelligence)
*"Does the space make sense for its use?"*

---

## PILLAR 1: 3D SHAPE - Absolute Critical

### What Must Be Correct

| Element | IFC Class | Why Critical | Accuracy Target |
|---------|-----------|--------------|-----------------|
| **Walls** | IfcWall | Define spaces | 95%+ |
| **Slabs** | IfcSlab | Floor/roof structure | 95%+ |
| **Columns** | IfcColumn | Structural support | 95%+ |
| **Beams** | IfcBeam | Structural support | 90%+ |
| **Stairs** | IfcStair | Vertical circulation | 95%+ |
| **Doors** | IfcDoor | Access/egress | 95%+ |
| **Windows** | IfcWindow | Envelope | 90%+ |
| **Roof** | IfcRoof | Building envelope | 90%+ |

**Why These Matter:**
- Define building geometry
- Required for clash detection
- Foundation for all other systems
- Cannot be "guessed" - must be from DXF

**Validation Rule:**
```python
CRITICAL_STRUCTURAL = [
    'IfcWall', 'IfcSlab', 'IfcColumn', 'IfcBeam',
    'IfcStair', 'IfcDoor', 'IfcWindow', 'IfcRoof'
]

for ifc_class in CRITICAL_STRUCTURAL:
    accuracy = validate_accuracy(ifc_class)
    if accuracy < 90:
        raise CriticalError(f"{ifc_class} accuracy {accuracy}% < 90% - UNACCEPTABLE")
```

---

## PILLAR 2: CRUCIAL DISCIPLINES - Life Safety First

### Fire Protection (FP) - HIGHEST PRIORITY

**Why:** Life safety, building code compliance

```python
CRITICAL_FP_CHAIN:
  1. Detect plumbing fixtures (toilets, sinks) on layer FP-* or PLUMB-*
     → INFER: These are toilets/restrooms

  2. Detect room with toilets
     → INFER: Sprinklers required (building code)
     → GENERATE: Sprinklers @ 3m spacing, ceiling height

  3. Detect sprinklers
     → INFER: Sprinkler pipes must connect them
     → GENERATE: Pipe routing from fixtures to main

  4. Detect corridor > 20m length
     → INFER: Fire hose reel required every 30m
     → GENERATE: Fire hose reels @ 30m intervals
```

**Example: Toilet → Sprinkler Chain**
```python
def infer_fire_protection(room):
    """Critical: Fire protection inference chain."""

    # Step 1: Detect room purpose from fixtures
    fixtures = detect_fixtures(room, layer="FP-FIXTURE")

    if any("WC" in f.name or "TOILET" in f.name for f in fixtures):
        room.purpose = "TOILET"
        room.fire_rating = "HIGH"  # Wet area = high risk

        # Step 2: Generate sprinklers (REQUIRED by code)
        sprinklers = generate_grid(
            room.polygon,
            spacing=3.0,  # 3m code requirement
            z_height=room.ceiling_height - 0.3,
            ifc_class="IfcFireSuppressionTerminal",
            confidence=0.95  # HIGH - building code mandated
        )

        # Step 3: Connect sprinklers with pipes
        pipes = route_sprinkler_pipes(
            sprinklers,
            main_pipe_location="nearest_riser"
        )

        return sprinklers + pipes
```

**Crucial FP Elements:**
- ✅ Sprinklers (code required)
- ✅ Fire hose reels (code required)
- ✅ Sprinkler pipes (connect system)
- ⚠️ Fire alarms (medium priority)
- ⚠️ Smoke detectors (medium priority)

---

### Electrical (ELEC) - Power & Safety

**Why:** Building functionality, safety systems

```python
CRITICAL_ELEC_CHAIN:
  1. Detect room purpose
     → INFER: Power requirements

  2. Detect walls
     → INFER: Outlets every 3m (code)
     → GENERATE: Wall outlets @ 0.3m height

  3. Detect ceiling
     → INFER: Lighting required
     → GENERATE: Lights based on room type:
        - Office: 4m spacing, recessed LED
        - Corridor: 3m spacing, linear fixtures
        - Toilet: 2m spacing, waterproof
        - Warehouse: 6m spacing, high bay

  4. Detect critical equipment (servers, pumps)
     → INFER: Dedicated circuits needed
     → GENERATE: Conduits from equipment to panel
```

**Example: Room Type → Lighting**
```python
def infer_electrical(room):
    """Critical: Electrical system inference."""

    # Detect room purpose
    purpose = detect_room_purpose(room)

    # Generate appropriate lighting
    if purpose == "OFFICE":
        lights = generate_grid(
            room.polygon,
            spacing=4.0,
            fixture_type="LED Panel 600x600",
            z_height=room.ceiling_height - 0.5,
            lux_level=500  # Office standard
        )

    elif purpose == "CORRIDOR":
        lights = generate_linear(
            room.centerline,
            spacing=3.0,
            fixture_type="Linear LED",
            lux_level=200  # Circulation standard
        )

    elif purpose == "TOILET":
        lights = generate_grid(
            room.polygon,
            spacing=2.0,
            fixture_type="Waterproof LED",
            z_height=room.ceiling_height - 0.3,
            ip_rating="IP65"  # Wet area rated
        )

    # Generate outlets along walls
    outlets = generate_perimeter(
        room.polygon,
        spacing=3.0,  # Building code
        height=0.3,
        ifc_class="IfcOutlet"
    )

    return lights + outlets
```

---

### HVAC (ACMV) - Comfort & Air Quality

**Why:** Building comfort, air quality

```python
CRITICAL_ACMV_CHAIN:
  1. Detect room size & purpose
     → CALCULATE: Required air changes per hour (ACH)
        - Toilet: 10-15 ACH
        - Office: 4-6 ACH
        - Kitchen: 15-20 ACH

  2. Calculate required airflow
     → INFER: Number of diffusers needed
     → GENERATE: Air terminals @ appropriate spacing

  3. Detect diffusers
     → INFER: Ducts must supply them
     → GENERATE: Duct routing from AHU to terminals
```

**Example: Room → HVAC Sizing**
```python
def infer_hvac(room):
    """Critical: HVAC system sizing and placement."""

    purpose = detect_room_purpose(room)
    volume = room.area * room.height

    # Determine air changes per hour (ACH)
    ACH_REQUIREMENTS = {
        "TOILET": 15,      # High extraction needed
        "KITCHEN": 20,     # Highest ventilation
        "OFFICE": 6,       # Moderate
        "CORRIDOR": 4,     # Low
        "LOBBY": 8,        # Moderate-high
    }

    ach = ACH_REQUIREMENTS.get(purpose, 6)  # Default office

    # Calculate required airflow (m³/h)
    required_airflow = volume * ach

    # Size diffusers (typical: 250 m³/h per diffuser)
    diffuser_capacity = 250
    diffuser_count = ceil(required_airflow / diffuser_capacity)

    # Generate diffusers
    diffusers = distribute_evenly(
        room.polygon,
        count=diffuser_count,
        z_height=room.ceiling_height - 0.2,
        ifc_class="IfcAirTerminal",
        size="300x300",
        airflow=diffuser_capacity
    )

    return diffusers
```

---

## PILLAR 3: FUNCTIONAL PURPOSE - Intelligence Layer

### Room Purpose Detection (THE KEY!)

**The Critical Insight:**
Room purpose determines EVERYTHING else:
- Sprinkler requirements
- Lighting type/spacing
- HVAC sizing
- Furniture layout
- Electrical loads

```python
def detect_room_purpose(room):
    """
    Detect room functional purpose from DXF clues.
    This drives ALL downstream inference!
    """

    # Strategy 1: Layer name analysis
    if "TOILET" in room.layer or "WC" in room.layer:
        return "TOILET"
    elif "KITCHEN" in room.layer or "PANTRY" in room.layer:
        return "KITCHEN"
    elif "CORRIDOR" in room.layer or "PASSAGE" in room.layer:
        return "CORRIDOR"

    # Strategy 2: Detect fixtures in room
    fixtures = get_fixtures_in_room(room)

    toilet_fixtures = [f for f in fixtures if
                       "WC" in f.name or "TOILET" in f.name or
                       "URINAL" in f.name or "SINK" in f.name]

    if len(toilet_fixtures) > 2:
        return "TOILET"  # Multiple plumbing = toilet

    kitchen_fixtures = [f for f in fixtures if
                        "SINK" in f.name and "COUNTER" in f.name]

    if kitchen_fixtures:
        return "KITCHEN"

    # Strategy 3: Room geometry analysis
    aspect_ratio = room.width / room.length

    if aspect_ratio < 0.3:  # Very narrow
        return "CORRIDOR"

    if room.area > 200:  # Very large
        if room.has_windows:
            return "LOBBY"
        else:
            return "WAREHOUSE"

    # Strategy 4: Building type context
    if building_type == "AIRPORT":
        if room.area > 500:
            return "DEPARTURE_HALL"  # Large open space
        elif 20 < room.area < 100:
            return "GATE_LOUNGE"

    elif building_type == "HOSPITAL":
        if room.area > 30:
            return "WARD"
        elif 15 < room.area < 25:
            return "CONSULTATION_ROOM"

    # Default: Office/Generic
    return "OFFICE"
```

---

### Functional Purpose Templates

**Transportation Hub Template (Airport/Port/Bus Terminal)**

```python
TRANSPORTATION_HUB_RULES = {
    "DEPARTURE_HALL": {
        "area_range": (500, 5000),
        "furniture": {
            "seating_rows": True,
            "spacing": 2.0,  # 2m between rows
            "orientation": "facing_boarding_gates",
            "density": 1.5,  # 1.5 m² per seat
        },
        "lighting": {
            "type": "High bay LED",
            "spacing": 6.0,
            "lux": 300,
        },
        "hvac": {
            "ach": 8,  # High occupancy
            "diffuser_spacing": 4.0,
        },
        "fire_protection": {
            "sprinkler_spacing": 3.0,
            "hose_reel_spacing": 30.0,
        },
        "electrical": {
            "charging_stations": True,
            "station_spacing": 10.0,  # USB charging every 10m
        }
    },

    "GATE_LOUNGE": {
        "area_range": (30, 100),
        "furniture": {
            "seating_type": "bench_seating",
            "layout": "perimeter_and_center",
            "capacity": "1_per_1.2m2",  # High density
        },
        "lighting": {
            "type": "Recessed LED",
            "spacing": 3.0,
            "lux": 400,
        },
        "signage": {
            "type": "Flight_information_display",
            "location": "visible_from_entrance",
        }
    },

    "RETAIL": {
        "area_range": (20, 200),
        "furniture": {
            "counters": True,
            "shelving": True,
            "checkout": True,
        },
        "lighting": {
            "type": "Track lighting",
            "lux": 750,  # High for retail
        },
        "electrical": {
            "outlet_density": "high",  # Every 2m
        }
    },

    "TOILET": {
        "indicators": ["WC fixtures", "tiled floor", "wet area"],
        "layout": "fixtures_in_rows",
        "fixture_spacing": 1.2,  # 1.2m between WC
        "furniture": None,  # No furniture in toilets!
        "fire_protection": {
            "sprinkler_spacing": 2.5,  # Closer in wet areas
        },
        "hvac": {
            "ach": 15,  # High extraction
            "extract_grilles": True,
        },
        "lighting": {
            "type": "Waterproof IP65",
            "spacing": 2.0,
        }
    }
}
```

**Hospitality Template (Hotel/Hostel)**

```python
HOSPITALITY_RULES = {
    "LOBBY": {
        "area_range": (50, 300),
        "furniture": {
            "reception_desk": True,
            "desk_location": "visible_from_entrance",
            "seating_groups": True,
            "group_spacing": 3.0,
            "sofa_count": "1_per_20m2",
            "coffee_tables": True,
        },
        "lighting": {
            "type": "Decorative + ambient",
            "lux": 200,  # Lower for ambiance
        },
        "ceiling": {
            "type": "feature_ceiling",
            "height": "double_height_if_area>100",
        }
    },

    "GUEST_ROOM": {
        "area_range": (15, 40),
        "furniture": {
            "bed": {
                "type": "queen_or_king",
                "location": "against_wall",
                "count": 1,
            },
            "nightstands": 2,
            "desk": 1,
            "chair": 1,
            "tv_console": 1,
        },
        "electrical": {
            "bedside_outlets": 2,
            "desk_outlet": 1,
            "tv_outlet": 1,
        },
        "lighting": {
            "bedside_lamps": 2,
            "ceiling_light": 1,
            "desk_lamp": 1,
        }
    }
}
```

**Food Service Template (Cafeteria/Restaurant)**

```python
FOOD_SERVICE_RULES = {
    "DINING_AREA": {
        "furniture": {
            "tables": "4_seater_or_6_seater",
            "table_spacing": 1.5,  # 1.5m between tables
            "chairs_per_table": "auto",  # Based on table size
            "capacity": "1_seat_per_2m2",
        },
        "layout_patterns": [
            "grid_aligned",  # Formal dining
            "scattered",      # Casual café
            "booth_seating",  # Fast food
        ],
        "hvac": {
            "ach": 10,  # Higher for food service
        },
        "fire_protection": {
            "sprinkler_spacing": 3.0,
        }
    },

    "KITCHEN": {
        "equipment": {
            "cooking_ranges": True,
            "prep_tables": True,
            "sinks": True,
            "cold_storage": True,
        },
        "hvac": {
            "ach": 20,  # Very high extraction
            "hood_extract": True,  # Over cooking
        },
        "fire_protection": {
            "sprinkler_spacing": 2.5,
            "suppression_system": "wet_chemical",  # Kitchen specific
        },
        "lighting": {
            "lux": 500,  # High for food prep
            "type": "Waterproof",
        }
    }
}
```

---

## Cross-Discipline Inference Chains

### Chain 1: Toilet Detection → Full MEP System

```python
def toilet_room_full_inference(room):
    """
    CRITICAL CHAIN: Toilet detection triggers complete MEP inference.
    This is a perfect example of functional intelligence!
    """

    # 1. DETECT: Toilet fixtures (FP discipline)
    fixtures = detect_fixtures(room)
    wc_count = count_fixtures(fixtures, type="WC")
    sink_count = count_fixtures(fixtures, type="SINK")

    if wc_count == 0:
        return None  # Not a toilet

    # 2. INFER: Room purpose = TOILET
    room.purpose = "TOILET"
    room.occupancy = wc_count * 2  # 2 people per WC

    # 3. GENERATE: Sprinklers (FP - CRITICAL)
    sprinklers = generate_grid(
        room.polygon,
        spacing=2.5,  # Tighter spacing in wet areas
        z_height=room.ceiling_height - 0.3,
        ifc_class="IfcFireSuppressionTerminal",
        confidence=0.95
    )

    # 4. GENERATE: Sprinkler pipes (FP)
    sprinkler_pipes = route_pipes(
        sprinklers,
        pipe_type="sprinkler",
        diameter=25,  # 25mm typical
        material="Steel"
    )

    # 5. GENERATE: Water supply pipes (FP)
    water_supply = route_to_fixtures(
        fixtures,
        pipe_type="cold_water",
        diameter=20,
        connection_type="bottom_feed"
    )

    # 6. GENERATE: Drainage pipes (FP - CRITICAL)
    drainage = route_from_fixtures(
        fixtures,
        pipe_type="soil_pipe",
        diameter=100,  # 100mm soil pipe
        slope=0.01,  # 1% slope required
        connection="nearest_stack"
    )

    # 7. GENERATE: Extract fans (ACMV - CRITICAL)
    extract_fans = generate_grid(
        room.polygon,
        spacing=3.0,
        z_height=room.ceiling_height - 0.2,
        ifc_class="IfcFan",
        airflow=wc_count * 50,  # 50 m³/h per WC
        confidence=0.9
    )

    # 8. GENERATE: Extract ducts (ACMV)
    extract_ducts = route_ducts(
        extract_fans,
        duct_type="extract",
        diameter=150,
        destination="nearest_riser"
    )

    # 9. GENERATE: Lighting (ELEC - waterproof required)
    lights = generate_grid(
        room.polygon,
        spacing=2.0,
        fixture_type="Waterproof_LED_IP65",
        z_height=room.ceiling_height - 0.3,
        lux_level=200,
        confidence=0.85
    )

    # 10. GENERATE: Electrical outlets (ELEC - GFCI required)
    outlets = generate_perimeter(
        room.polygon,
        spacing=4.0,  # Wider spacing in toilet
        height=1.2,  # Higher for wet area
        outlet_type="GFCI",  # Ground fault protection
        confidence=0.8
    )

    # 11. INFER: Floor finish (ARC)
    floor_covering = create_covering(
        room.polygon,
        z_height=0.0,
        material="Ceramic_Tile",  # Always tiled
        finish="Non_slip",
        confidence=0.9
    )

    # 12. INFER: Wall finish (ARC)
    wall_covering = create_wall_covering(
        room.walls,
        height=2.0,  # 2m tiling height
        material="Ceramic_Tile",
        confidence=0.85
    )

    return {
        'FP': sprinklers + sprinkler_pipes + water_supply + drainage,
        'ACMV': extract_fans + extract_ducts,
        'ELEC': lights + outlets,
        'ARC': floor_covering + wall_covering,
        'confidence': 0.9,  # HIGH - toilet detection is reliable
        'element_count': len(sprinklers) + len(pipes) + ... # ~50-100 elements per toilet!
    }
```

**Impact:** Single toilet room detection → 50-100 elements generated across 4 disciplines!

---

### Chain 2: Open Space Detection → Functional Furniture

```python
def open_space_furniture_inference(room, building_type):
    """
    INTELLIGENT CHAIN: Large open space → Functional furniture layout.
    Based on building type and spatial analysis.
    """

    if room.area < 100:
        return None  # Not an open space

    # Detect building context
    if building_type == "AIRPORT":
        return generate_airport_seating(room)

    elif building_type == "HOTEL":
        return generate_lobby_furniture(room)

    elif building_type == "CAFETERIA":
        return generate_dining_furniture(room)

def generate_airport_seating(room):
    """Airport departure hall seating inference."""

    # Analyze room geometry
    main_axis = calculate_primary_axis(room.polygon)
    circulation_zones = identify_circulation(room)

    # Seating in rows facing boarding gates
    seating_zones = subtract_zones(room.polygon, circulation_zones)

    furniture = []

    for zone in seating_zones:
        # Generate rows of seating
        rows = generate_rows(
            zone,
            row_orientation="facing_gates",
            seat_spacing=0.6,  # 600mm per seat
            row_spacing=2.0,   # 2m between rows
            seat_type="Bench_Seating_3seat"
        )

        for row in rows:
            furniture.append({
                'ifc_class': 'IfcFurniture',
                'type': 'Seating_Bench',
                'position': row.position,
                'orientation': row.angle,
                'seats': 3,
                'confidence': 0.75  # MEDIUM - layout is assumption
            })

    # Add charging stations
    charging_points = generate_grid(
        seating_zones,
        spacing=10.0,  # Every 10m
        furniture_type="Charging_Station_USB",
        confidence=0.7
    )

    return furniture + charging_points
```

---

## Implementation Priority: Critical Path

### Phase 1: Structural Integrity (MUST BE RIGHT)
```
Week 1: Validate 3D shape accuracy
  - Walls: 95%+
  - Slabs: 95%+
  - Columns: 95%+
  - Doors: 95%+

  If any < 90%: STOP and fix template matching
```

### Phase 2: Life Safety Systems (CRITICAL)
```
Week 2: Fire Protection inference
  - Toilet detection → Sprinkler generation
  - Corridor detection → Hose reel placement
  - Sprinkler pipe routing

  Target: FP discipline 85%+ accuracy
```

### Phase 3: Functional Intelligence (HIGH VALUE)
```
Week 3: Room purpose detection + furniture
  - Implement purpose detection algorithm
  - Airport seating templates
  - Toilet MEP chain
  - Cafeteria dining layouts

  Target: Overall 90%+ accuracy
```

### Phase 4: Complete MEP (NICE TO HAVE)
```
Week 4: Remaining MEP systems
  - Electrical outlets/lighting
  - HVAC diffusers/ducts
  - Remaining pipe fittings

  Target: 95%+ accuracy
```

---

## Validation: What Success Looks Like

```python
MAJOR_EXPECTATIONS_VALIDATION = {
    "3D_SHAPE": {
        "walls": {"accuracy": 0.96, "status": "✅ PASS"},
        "slabs": {"accuracy": 0.95, "status": "✅ PASS"},
        "columns": {"accuracy": 0.94, "status": "✅ PASS"},
        "doors": {"accuracy": 0.97, "status": "✅ PASS"},
    },

    "CRITICAL_DISCIPLINES": {
        "FP": {
            "sprinklers": {"accuracy": 0.88, "status": "✅ PASS"},
            "pipes": {"accuracy": 0.82, "status": "✅ PASS"},
            "hose_reels": {"accuracy": 0.90, "status": "✅ PASS"},
        },
        "ELEC": {
            "lights": {"accuracy": 0.85, "status": "✅ PASS"},
            "outlets": {"accuracy": 0.78, "status": "⚠️ ACCEPTABLE"},
        },
        "ACMV": {
            "diffusers": {"accuracy": 0.81, "status": "✅ PASS"},
            "ducts": {"accuracy": 0.75, "status": "⚠️ ACCEPTABLE"},
        }
    },

    "FUNCTIONAL_PURPOSE": {
        "toilet_detection": {"accuracy": 0.95, "status": "✅ EXCELLENT"},
        "furniture_generation": {"accuracy": 0.72, "status": "✅ ACCEPTABLE"},
        "mep_chain_inference": {"accuracy": 0.85, "status": "✅ EXCELLENT"},
    },

    "OVERALL": {
        "total_accuracy": 0.92,
        "status": "✅ MAJOR EXPECTATIONS MET",
        "ready_for_production": True
    }
}
```

---

## Bottom Line: The Major Expectations Checklist

### ✅ What MUST Be Right (90%+)
- [ ] Walls, slabs, columns (3D shape)
- [ ] Doors and windows (openings)
- [ ] Structural elements (beams, stairs)
- [ ] Fire sprinklers (life safety)
- [ ] Toilet detection and fixtures

### ✅ What Should Be Good (80%+)
- [ ] Lighting fixtures (functional)
- [ ] HVAC diffusers (comfort)
- [ ] Electrical outlets (usability)
- [ ] Pipe/duct routing (connectivity)

### ⚠️ What Can Be Approximate (70%+)
- [ ] Furniture layouts (refinable)
- [ ] Ceiling tiles (decorative)
- [ ] Minor fixtures (non-critical)
- [ ] Decorative elements (aesthetic)

---

**Philosophy:**
> "Get the bones right (structure), the blood right (MEP), and the brain right (functional purpose). Everything else can be refined."

**Next:** Implement functional purpose detection when DXF files arrive!

**Last Updated:** November 12, 2025
