# Parametric Array Templates - Smart Element Generation

**Concept:** Instead of mapping individual elements, detect **spatial patterns** and generate arrays based on function/space type.

Based on Phase 1 results showing 91.4% entity coverage, we can now apply intelligent array generation for common repeating elements.

---

## 🎯 The Array Generation Concept

### Traditional Approach (Slow):
```
DXF: 100 individual chair blocks → Map 100 times → Generate 100 IFC elements
```

### Smart Array Approach (Fast):
```
DXF: Detect seating pattern → Recognize "Gate Waiting Area" → Apply Airport Seating Array
     → Generate 100 IfcFurniture elements with proper spacing, orientation, and properties
```

---

## 📐 Array Pattern Library

### 1. 💺 **Airport Seating Arrays**

**Detection Criteria:**
- Layer: `FURNITURE`, `TOILETLOADED`
- Block pattern: Repeating chairs in rows
- Spacing: 0.6m-1.0m apart
- Location: Near gates (proximity to "GATE" text)

**Template Parameters:**
```python
AIRPORT_SEATING = {
  "pattern_type": "linear_array",
  "element_type": "IfcFurniture",
  "variants": {
    "gate_waiting": {
      "rows": "auto_detect",        # Count rows from DXF
      "seats_per_row": "auto_detect",
      "seat_spacing": 0.65,          # meters
      "row_spacing": 1.2,
      "orientation": "perpendicular_to_wall",
      "properties": {
        "material": "Metal frame, plastic seat",
        "load_capacity": "150kg",
        "maintenance": "Quarterly cleaning",
        "fire_rating": "Class 1"
      }
    },

    "food_court": {
      "arrangement": "table_groups",
      "seats_per_table": 4,
      "table_spacing": 1.5,
      "properties": {
        "material": "Laminate top, metal frame",
        "cleanable": true
      }
    },

    "lounge": {
      "arrangement": "scattered",
      "seat_types": ["single", "sofa_2", "sofa_3"],
      "distribution": [0.4, 0.4, 0.2],  # 40% singles, 40% 2-seaters, 20% 3-seaters
    }
  },

  "z_offset": 0.0  # Floor level
}
```

**User Options in Template Engine:**
```
┌─────────────────────────────────────────┐
│ Seating Array Detected (176 seats)      │
├─────────────────────────────────────────┤
│ Area Type:                               │
│ ○ Gate Waiting (recommended)             │
│ ○ Food Court                             │
│ ○ Lounge                                 │
│ ○ Custom...                              │
│                                          │
│ Spacing: [0.65m] ▼                      │
│ Orientation: [Auto] ▼                    │
│ Material: [Standard Airport] ▼           │
│                                          │
│ [Apply] [Preview in 3D] [Skip]          │
└─────────────────────────────────────────┘
```

---

### 2. 🚽 **Toilet Arrays**

**Detection Criteria:**
- Layer: `TOILETLOADED`, `toilet`, `SANI`
- Block pattern: WC, basin, urinal symbols
- Spacing: Standard plumbing grid (1.2m-1.5m)
- Count: Pairs (male/female)

**Template Parameters:**
```python
TOILET_ARRAYS = {
  "pattern_type": "fixture_array",
  "element_types": ["IfcSanitaryTerminal"],

  "variants": {
    "airport_public": {
      "male": {
        "wc_cubicles": "auto_count",      # Count from DXF blocks
        "urinals": "auto_count",
        "basins": "auto_count",
        "spacing": 1.2,
        "accessible_cubicle": 1,          # 1 per toilet
        "properties": {
          "flush_type": "Sensor activated",
          "water_efficient": "6/3L dual flush",
          "maintenance": "Daily cleaning"
        }
      },

      "female": {
        "wc_cubicles": "auto_count * 1.5",  # More cubicles for women
        "basins": "auto_count",
        "spacing": 1.2,
        "accessible_cubicle": 1,
        "baby_change": 1
      },

      "common": {
        "mirror_length": "basin_count * 0.6",
        "hand_dryer_count": "basin_count / 2",
        "lighting": "downlight_per_cubicle"
      }
    },

    "office": {
      "ratio_male_female": 1.0,
      "cubicles_per_gender": [3, 5, 8],  # Options
      "basins": 2,
      "urinals": 2
    },

    "hospital_ward": {
      "ensuite": true,
      "accessible": true,
      "shower": true,
      "grab_bars": true
    }
  }
}
```

**User Options:**
```
┌─────────────────────────────────────────┐
│ Toilet Block Detected                    │
├─────────────────────────────────────────┤
│ Type: ○ Airport Public (recommended)     │
│       ○ Office                           │
│       ○ Hospital                         │
│                                          │
│ Male: 8 WC + 6 Urinals + 6 Basins       │
│ Female: 12 WC + 8 Basins                │
│                                          │
│ Add accessible: ☑                        │
│ Add baby change: ☑                       │
│ Water efficient: ☑                       │
│                                          │
│ [Generate] [Customize] [Skip]           │
└─────────────────────────────────────────┘
```

---

### 3. 🔥 **Sprinkler Arrays**

**Detection Criteria:**
- Layer: `C-BOMBA HATCH`, `z-fire-sprinkler`, `FP-SPRINKLER`
- Pattern: Grid layout (697 detected in Terminal 1)
- Spacing: 3.0m-4.5m (coverage radius)
- Height: Ceiling mounted (z-offset based on ceiling height)

**Template Parameters:**
```python
SPRINKLER_ARRAYS = {
  "pattern_type": "grid_coverage",
  "element_type": "IfcFireSuppressionTerminal",

  "variants": {
    "airport_terminal": {
      "coverage_radius": 4.0,       # meters (NFPA 13 Light Hazard)
      "spacing_max": 3.66,          # 12 feet
      "ceiling_clearance": 0.3,     # Below ceiling
      "z_offset_from_floor": "ceiling_height - clearance",

      "head_types": {
        "main_concourse": "concealed",
        "back_of_house": "pendant",
        "mechanical": "upright"
      },

      "properties": {
        "response_time": "Quick response",
        "k_factor": 5.6,
        "temperature_rating": "68°C (155°F)",
        "finish": "Chrome plated",
        "manufacturer": "Tyco/Viking/Reliable"
      }
    },

    "warehouse_high_rack": {
      "coverage_radius": 2.5,
      "spacing_max": 2.4,
      "head_type": "ESFR",           # Early Suppression Fast Response
      "k_factor": 25.2
    },

    "residential": {
      "coverage_radius": 4.5,
      "spacing_max": 4.0,
      "head_type": "residential",
      "optional": true               # Not mandatory in all areas
    }
  },

  "auto_placement": {
    "avoid_obstacles": true,
    "column_offset": 0.3,            # meters from columns
    "wall_offset": 0.1,
    "adjust_for_beams": true
  }
}
```

**User Options:**
```
┌─────────────────────────────────────────┐
│ Sprinkler Coverage Analysis              │
├─────────────────────────────────────────┤
│ Detected: 697 sprinkler heads            │
│ Coverage: 15,840 m² (main terminal)      │
│                                          │
│ Hazard Class:                            │
│ ● Light Hazard (4.0m radius)            │
│ ○ Ordinary Hazard (3.66m radius)        │
│ ○ High Hazard (2.5m radius)             │
│                                          │
│ Head Type:                               │
│ ● Concealed (public areas)              │
│ ○ Pendant (back of house)               │
│                                          │
│ Auto-optimize spacing: ☑                 │
│ Avoid structural: ☑                      │
│ Check coverage gaps: ☑                   │
│                                          │
│ [Generate] [Show Coverage Map] [Skip]   │
└─────────────────────────────────────────┘
```

---

### 4. 💡 **Lighting Arrays**

**Detection Criteria:**
- Layer: `EL`, `ELEC`, `z-light`
- Pattern: Grid or track layout (354 fixtures in Terminal 1)
- Spacing: 2.0m-3.0m typical
- Height: Ceiling mounted

**Template Parameters:**
```python
LIGHTING_ARRAYS = {
  "pattern_type": "grid_or_track",
  "element_type": "IfcLightFixture",

  "variants": {
    "airport_concourse": {
      "layout": "linear_rows",
      "spacing": 2.5,
      "fixture_type": "LED downlight",
      "lux_level": 500,              # Target illuminance
      "color_temp": "4000K",         # Neutral white
      "dimming": true,
      "emergency_backup": "10%",

      "zones": {
        "gate_waiting": {
          "lux": 300,
          "dimming_zones": true
        },
        "circulation": {
          "lux": 200,
          "sensor_control": "motion"
        },
        "retail": {
          "lux": 750,
          "accent_lighting": true
        }
      }
    },

    "office_open_plan": {
      "layout": "grid",
      "spacing": 3.0,
      "fixture_type": "LED panel 600x600",
      "lux_level": 400,
      "daylight_harvesting": true
    },

    "warehouse": {
      "layout": "high_bay",
      "spacing": 6.0,
      "fixture_type": "LED high bay",
      "lux_level": 200,
      "mounting_height": 8.0
    }
  },

  "energy_compliance": {
    "lpd_limit": 6.0,                # W/m² (MS 1525)
    "controls_required": true,
    "occupancy_sensors": true
  }
}
```

**User Options:**
```
┌─────────────────────────────────────────┐
│ Lighting Design Assistant                │
├─────────────────────────────────────────┤
│ Area: Main Concourse (3,200 m²)         │
│ Detected: 354 light points               │
│                                          │
│ Fixture Type:                            │
│ ● LED Downlight (12W)                   │
│ ○ LED Panel 600x600 (40W)               │
│ ○ High Bay (150W)                        │
│                                          │
│ Target Lux: [500] ▼                     │
│ Current: 487 lux (within spec ✓)       │
│                                          │
│ Controls:                                │
│ ☑ Daylight harvesting                    │
│ ☑ Occupancy sensors                      │
│ ☑ Time schedule                          │
│                                          │
│ Energy: 5.2 W/m² (compliant ✓)          │
│                                          │
│ [Generate] [Lux Calculation] [Skip]     │
└─────────────────────────────────────────┘
```

---

### 5. 🔌 **Electrical Outlet Arrays**

**Detection Criteria:**
- Layer: `EL`, `ELEC`, `power`
- Pattern: Wall-mounted points
- Spacing: 3.0m-6.0m (code requirement)
- Height: 0.3m-0.45m above floor

**Template Parameters:**
```python
ELECTRICAL_ARRAYS = {
  "pattern_type": "perimeter_points",
  "element_type": "IfcElectricDistributionBoard",

  "variants": {
    "airport_public": {
      "socket_type": "USB charging station",
      "outlets_per_station": 4,
      "usb_ports": 2,
      "spacing": 6.0,               # Every 6m
      "mounting_height": 0.4,

      "locations": {
        "seating_areas": "high_density",
        "circulation": "standard",
        "retail": "per_tenant"
      }
    },

    "office": {
      "socket_type": "double_socket_13A",
      "spacing": 3.0,
      "desk_clusters": true,
      "floor_boxes": "every_6m"
    },

    "hospital_ward": {
      "socket_type": "medical_grade",
      "per_bed": 8,
      "emergency_power": 4,
      "isolated_ground": true
    }
  }
}
```

---

### 6. 🌀 **ACMV Diffuser Arrays**

**Detection Criteria:**
- Layer: `z-ac-griille`, `ACMV`, `diffuser`
- Pattern: Grid layout (125 grilles in Terminal 1)
- Spacing: 3.0m-4.5m
- Type: Supply/return/exhaust

**Template Parameters:**
```python
ACMV_DIFFUSER_ARRAYS = {
  "pattern_type": "air_distribution",
  "element_type": "IfcAirTerminal",

  "variants": {
    "airport_terminal": {
      "diffuser_types": {
        "supply": {
          "type": "swirl_diffuser",
          "size": "350mm",
          "cfm": 500,
          "throw": 4.0,              # meters
          "spacing": 3.5
        },
        "return": {
          "type": "grille",
          "size": "600x300",
          "cfm": 800,
          "spacing": 6.0
        },
        "exhaust": {
          "locations": ["toilets", "pantries", "back_of_house"],
          "cfm_per_toilet": 150,
          "cfm_per_pantry": 300
        }
      },

      "ratio": "supply:return = 1.2:1",  # Slight positive pressure

      "zoning": {
        "public": "VAV with CO2 sensors",
        "retail": "tenant_controlled",
        "back_of_house": "CAV"
      }
    }
  }
}
```

---

## 🎨 Template Swapping UI Concept

**The Power of Parametric Choice:**

```
User clicks on seating area in 3D:

┌─────────────────────────────────────────────────────────┐
│ 176 Seats Detected - Choose Configuration               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │▓▓▓▓▓▓│  │░░░░░░│  │░░░░░░│  │░░░░░░│               │
│  │▓Gate▓│  │ Food │  │Lounge│  │Custom│               │
│  │▓Wait▓│  │Court │  │      │  │      │               │
│  └──────┘  └──────┘  └──────┘  └──────┘               │
│  Selected   Preview   Preview   Advanced               │
│                                                          │
│  Preview in 3D: [Gate seating in rows] ▼               │
│                                                          │
│  Properties:                                             │
│  • Seats per row: 8                                     │
│  • Number of rows: 22                                   │
│  • Spacing: 0.65m                                       │
│  • Material: Metal/plastic                              │
│  • Accessible seats: 4 (ADA compliant)                 │
│                                                          │
│  Cost Estimate: RM 52,800 (176 seats @ RM 300/each)    │
│  Maintenance: Quarterly cleaning                        │
│                                                          │
│  [◄ Previous Array] [Apply] [Next Array ►]             │
└─────────────────────────────────────────────────────────┘
```

**One Click Swap:**
- Click "Food Court" → Instantly rearranges to table groups
- Click "Lounge" → Scatters sofas and armchairs
- See 3D preview in real-time
- Cost updates automatically

---

## 💰 Business Value: Array Intelligence

**Traditional Manual Modeling:**
- 176 seats × 2 minutes each = 352 minutes (5.9 hours)
- 697 sprinklers × 3 minutes each = 2,091 minutes (34.8 hours)
- 354 lights × 2 minutes each = 708 minutes (11.8 hours)
- **Total: 52.5 hours for repetitive elements**

**Smart Array Generation:**
- Detect pattern: 30 seconds
- Choose template: 30 seconds
- Adjust parameters: 2 minutes
- Generate all: 10 seconds
- **Total: 3.5 minutes per array type**
- **Time saved: 52 hours → 20 minutes (99.4% faster!)**

---

## 🔄 Template Engine Workflow

### Step 1: Auto-Detection
```python
detected_arrays = analyze_dxf_patterns(dxf_file)
# Returns:
# [
#   {'type': 'seating', 'count': 176, 'pattern': 'rows', 'confidence': 0.92},
#   {'type': 'sprinklers', 'count': 697, 'pattern': 'grid', 'confidence': 0.95},
#   {'type': 'toilets', 'count': 24, 'pattern': 'fixtures', 'confidence': 0.88}
# ]
```

### Step 2: User Review & Selection
```python
for array in detected_arrays:
    template_options = get_template_variants(array['type'], building_type='airport')
    user_choice = show_template_picker(template_options)

    if user_choice == 'customize':
        params = custom_parameter_editor(template_options[0])
    else:
        params = template_options[user_choice]
```

### Step 3: Generate Elements
```python
elements = generate_array_elements(
    pattern=array['pattern'],
    template=params,
    positions=array['positions']
)

database.insert_elements(elements)
```

### Step 4: Preview & Refine
```python
blender.load_elements(elements, collection=f"Array_{array['type']}")
blender.focus_camera(elements.bbox)

if not user_approves():
    revert_and_retry()
```

---

## 📊 Summary: Parametric Power

**What We Discovered from Phase 1:**
- 91.4% of entities covered by smart mapping
- 135/166 layers automatically classified
- Clear repeating patterns (seating, toilets, sprinklers, lights)

**What We're Building:**
- Template library for common arrays
- Building-type specific variants
- One-click parameter swapping
- Visual preview in Blender Outliner
- 99%+ time savings on repetitive elements

**User Experience:**
1. Smart detection finds 176 seats
2. User picks "Airport Gate Waiting" template
3. Previews in 3D → looks good
4. Clicks Apply → 176 IfcFurniture elements generated in 10 seconds
5. Repeat for toilets, sprinklers, lights
6. **Total time: 5 minutes instead of 50+ hours!**

---

**Next Implementation:**
Would you like me to integrate this smart mapping into the conversion pipeline and re-run the test? We should get much better results now!

---

**Date:** November 15, 2025
**Coverage:** 91.4% entities with smart patterns
**Time Savings:** 99.4% for array-based elements
