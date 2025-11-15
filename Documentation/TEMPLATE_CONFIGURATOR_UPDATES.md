# Template Configurator - Updates from Inference Work

**Date:** November 12, 2025
**Purpose:** Add new features from intelligent inference design
**Integrates with:** TEMPLATE_CONFIGURATOR_DESIGN.md (original 747 lines)

---

## What to Add to Existing Design

The original TEMPLATE_CONFIGURATOR_DESIGN.md is excellent and comprehensive.
These are **additions** to enhance it with today's inference intelligence.

---

## NEW FEATURE 1: Building Type Selector

### Add to Main UI (Top Section)

```
┌──────────────────────────────────────────────────────────────┐
│ Template Configurator v1.0                                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌─ PROJECT CONTEXT ────────────────────────────────────┐   │
│ │                                                        │   │
│ │ Building Type: [▼ Transportation Hub        ]         │   │
│ │                                                        │   │
│ │ ┌─ Preview ────────────────────────────────────────┐  │   │
│ │ │ Transportation Hub                               │  │   │
│ │ │ (Airport / Bus Terminal / Ferry Jetty / Train)   │  │   │
│ │ │                                                   │  │   │
│ │ │ Typical Spaces:                                  │  │   │
│ │ │  • Waiting lobbies (100-5000 m²)                 │  │   │
│ │ │  • High-capacity toilets                         │  │   │
│ │ │  • Retail/F&B spaces                             │  │   │
│ │ │  • Boarding gates                                │  │   │
│ │ │                                                   │  │   │
│ │ │ MEP Standards:                                   │  │   │
│ │ │  • Sprinkler spacing: 3.0m                       │  │   │
│ │ │  • Lighting: 300 lux (public areas)              │  │   │
│ │ │  • HVAC: 8 ACH (high occupancy)                  │  │   │
│ │ └───────────────────────────────────────────────────┘  │   │
│ │                                                        │   │
│ │ [Manage Building Types...] [Import Type...]           │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ TEMPLATE LIBRARY ─────────────────────────────────────┐  │
│ │  📁 Terminal 1 Base (v1.0) - 44 templates              │  │
│ │   ├─ 🏛️ ARC (13)                                      │  │
│ │   ├─ 🔥 FP (9)                                         │  │
│ │   └─ ... (other disciplines)                           │  │
│ └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Building Type Data Structure

```python
class BuildingType:
    """Building type configuration for intelligent inference."""

    def __init__(self, type_id, name, description):
        self.id = type_id
        self.name = name
        self.description = description
        self.signature_spaces = {}  # Room types
        self.mep_standards = {}      # MEP parameters
        self.inference_rules = []    # Automatic inference

# Example: Transportation Hub
transport_hub = BuildingType(
    type_id="transportation_hub",
    name="Transportation Hub",
    description="Airport, Bus Terminal, Ferry Jetty, Train Station"
)

transport_hub.signature_spaces = {
    "waiting_lobby": {
        "area_range": (100, 5000),
        "furniture": "bench_seating_rows",
        "seating_density": 1.5,  # m² per seat
    },
    "toilet": {
        "area_range": (10, 50),
        "fixture_density": "high",
        "mep_chain": "full_inference",
    }
}

transport_hub.mep_standards = {
    "sprinkler_spacing": 3.0,
    "lighting_lux": 300,
    "hvac_ach": 8,
}
```

### UI Workflow

1. User selects building type from dropdown
2. Preview pane shows type characteristics
3. Template browser filters/highlights relevant templates
4. Inference rules auto-configure based on type
5. Save building type with variant configuration

---

## NEW FEATURE 2: Inference Rule Manager

### Add New Tab: "Inference Rules"

```
┌──────────────────────────────────────────────────────────────┐
│ [Templates] [Variants] [Inference Rules] [Validation]        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Inference Categories:                                        │
│                                                              │
│ ┌─ 1. Boundary-Based Inference ─────────────────────────┐   │
│ │                                                        │   │
│ │ ☑ Ceiling Tiles                                       │   │
│ │    Trigger: [Closed polyline on layer: ARC-CEIL*]    │   │
│ │    Tile size: [0.6] m × [0.6] m                      │   │
│ │    Default Z-height: [18.5] m                         │   │
│ │    Confidence: [90]%                                  │   │
│ │    [Edit Rule...] [Test on DXF...] [Disable]         │   │
│ │                                                        │   │
│ │ ☑ Floor Coverings                                     │   │
│ │    Trigger: [Any room boundary]                       │   │
│ │    Material: [Auto-detect from room type]             │   │
│ │    Z-height: [0.0] m                                  │   │
│ │    Confidence: [70]%                                  │   │
│ │    [Edit Rule...] [Test on DXF...] [Disable]         │   │
│ │                                                        │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ 2. Spacing-Based Inference ──────────────────────────┐   │
│ │                                                        │   │
│ │ ☑ Fire Sprinklers                                     │   │
│ │    Trigger: [Room area > 9 m²]                        │   │
│ │    Spacing: [3.0] m grid                              │   │
│ │    Height: [Ceiling - 0.3] m                          │   │
│ │    Code-required: [✓]                                 │   │
│ │    Confidence: [95]%                                  │   │
│ │    [Edit Rule...] [Test on DXF...] [Disable]         │   │
│ │                                                        │   │
│ │ ☑ Light Fixtures                                      │   │
│ │    Trigger: [All rooms]                               │   │
│ │    Spacing: [4.0] m (office) [3.0] m (corridor)      │   │
│ │    Type: [Based on room type]                         │   │
│ │    Lux level: [500] (office) [200] (corridor)        │   │
│ │    Confidence: [70]%                                  │   │
│ │    [Edit Rule...] [Test on DXF...] [Disable]         │   │
│ │                                                        │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ 3. Cross-Discipline Chains ──────────────────────────┐   │
│ │                                                        │   │
│ │ ☑ Toilet MEP Chain (CRITICAL)                         │   │
│ │    Trigger: [Detect toilet fixtures]                  │   │
│ │    Generates:                                         │   │
│ │      1. ☑ Sprinklers (FP)                             │   │
│ │      2. ☑ Sprinkler pipes (FP)                        │   │
│ │      3. ☑ Water supply (FP)                           │   │
│ │      4. ☑ Drainage (FP)                               │   │
│ │      5. ☑ Extract fans (ACMV)                         │   │
│ │      6. ☑ Extract ducts (ACMV)                        │   │
│ │      7. ☑ Waterproof lights (ELEC)                    │   │
│ │      8. ☑ GFCI outlets (ELEC)                         │   │
│ │      9. ☑ Floor finish (ARC)                          │   │
│ │     10. ☑ Wall finish (ARC)                           │   │
│ │    Overall confidence: [90]%                          │   │
│ │    [Configure Chain...] [Test on DXF...] [Disable]   │   │
│ │                                                        │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ [Test All Rules] [Export Configuration] [Import Rules]       │
└──────────────────────────────────────────────────────────────┘
```

### Inference Rule Editor Dialog

```
┌─ Edit Inference Rule: Ceiling Tiles ──────────────────────┐
│                                                            │
│ Rule Name: [Ceiling Tiles - Boundary Based]               │
│ Category: [Boundary-Based ▼]                              │
│                                                            │
│ ┌─ Trigger Conditions ─────────────────────────────────┐  │
│ │                                                       │  │
│ │ Layer detection:                                     │  │
│ │   Pattern: [ARC-CEIL*, CEILING*, A-CEIL*]           │  │
│ │   Entity type: [POLYLINE, LWPOLYLINE]               │  │
│ │   Must be closed: [✓]                               │  │
│ │                                                       │  │
│ │ Alternative triggers:                                │  │
│ │   [✓] Infer from room boundary if no ceiling layer  │  │
│ │   [ ] Only generate for specific room types          │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                            │
│ ┌─ Generation Parameters ──────────────────────────────┐  │
│ │                                                       │  │
│ │ Tile size:                                           │  │
│ │   Width:  [0.6] m                                    │  │
│ │   Length: [0.6] m                                    │  │
│ │                                                       │  │
│ │ Z-height:                                            │  │
│ │   ( ) Fixed: [18.5] m                                │  │
│ │   (•) From storey data (fallback: 18.5 m)           │  │
│ │   ( ) Calculate: [Floor height + 3.0] m              │  │
│ │                                                       │  │
│ │ IFC Properties:                                      │  │
│ │   IFC Class: [IfcPlate ▼]                           │  │
│ │   Element Type: [Metal Deck:Metal Deck]             │  │
│ │   Material: [Metal Deck]                            │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                            │
│ ┌─ Validation & Confidence ────────────────────────────┐  │
│ │                                                       │  │
│ │ Confidence score: [90]%                              │  │
│ │                                                       │  │
│ │ Validation rules:                                    │  │
│ │   [✓] Skip rooms < 5 m²                             │  │
│ │   [✓] Warn if tile count > 10,000 per room          │  │
│ │   [ ] Require manual review if confidence < 80%      │  │
│ │                                                       │  │
│ │ Mark elements as: [INFERRED_SPATIAL ▼]              │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                            │
│ [Test on Sample DXF] [Save Rule] [Cancel]                 │
└────────────────────────────────────────────────────────────┘
```

---

## NEW FEATURE 3: Room Purpose Editor

### Add New Tab: "Room Types & Purposes"

```
┌──────────────────────────────────────────────────────────────┐
│ [Templates] [Room Types] [Inference Rules] [Validation]      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌─ Room Types (Building: Transportation Hub) ─────────────┐ │
│ │                                                          │ │
│ │ Available Types:                                         │ │
│ │  • Waiting Lobby                                         │ │
│ │  • Toilet                        ← SELECTED             │ │
│ │  • Retail Shop                                           │ │
│ │  • Boarding Gate                                         │ │
│ │  • Corridor                                              │ │
│ │  • Back-of-House                                         │ │
│ │                                                          │ │
│ │ [Add Room Type...] [Delete] [Import Set...]             │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Room Type: Toilet ────────────────────────────────────┐  │
│ │                                                         │  │
│ │ Detection Criteria:                                     │  │
│ │   Layer patterns: [FP-*, TOILET, WC, BATH]             │  │
│ │   Fixture detection: [✓] WC [✓] SINK [✓] URINAL       │  │
│ │   Minimum fixtures: [1]                                 │  │
│ │   Area range: [3] - [50] m²                            │  │
│ │                                                         │  │
│ │ ┌─ Furniture Template ───────────────────────────────┐  │  │
│ │ │ Layout: [Fixtures in rows]                        │  │  │
│ │ │ WC spacing: [1.2] m                               │  │  │
│ │ │ Additional furniture: [None]                       │  │  │
│ │ │ Priority: [HIGH] (functional requirement)         │  │  │
│ │ └────────────────────────────────────────────────────┘  │  │
│ │                                                         │  │
│ │ ┌─ MEP Inference Chain ──────────────────────────────┐  │  │
│ │ │                                                    │  │  │
│ │ │ Fire Protection (FP):                             │  │  │
│ │ │   1. [✓] Sprinklers - 2.5m spacing               │  │  │
│ │ │   2. [✓] Sprinkler pipes - Route to riser        │  │  │
│ │ │   3. [✓] Water supply - 20mm diameter            │  │  │
│ │ │   4. [✓] Drainage - 100mm soil pipe              │  │  │
│ │ │                                                    │  │  │
│ │ │ HVAC (ACMV):                                      │  │  │
│ │ │   5. [✓] Extract fans - 50 m³/h per WC           │  │  │
│ │ │   6. [✓] Extract ducts - 150mm diameter          │  │  │
│ │ │                                                    │  │  │
│ │ │ Electrical (ELEC):                                │  │  │
│ │ │   7. [✓] Waterproof lights - IP65, 200 lux       │  │  │
│ │ │   8. [✓] GFCI outlets - 1.2m height              │  │  │
│ │ │                                                    │  │  │
│ │ │ Architecture (ARC):                               │  │  │
│ │ │   9. [✓] Ceramic floor - Non-slip                │  │  │
│ │ │  10. [✓] Ceramic walls - 2.0m height             │  │  │
│ │ │                                                    │  │  │
│ │ │ [Configure Each Rule...] [Enable/Disable All]    │  │  │
│ │ └────────────────────────────────────────────────────┘  │  │
│ │                                                         │  │
│ │ Confidence: [90]% (HIGH - toilet detection reliable)   │  │
│ │                                                         │  │
│ │ [Test Detection on DXF] [Save] [Revert]                │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Room Type Data Structure

```python
class RoomType:
    """Room functional purpose with inference rules."""

    def __init__(self, name, building_type):
        self.name = name
        self.building_type = building_type
        self.detection_criteria = {}
        self.furniture_template = {}
        self.mep_chain = []
        self.confidence = 0.8

# Example: Toilet room type
toilet = RoomType("Toilet", "transportation_hub")

toilet.detection_criteria = {
    "layers": ["FP-*", "TOILET", "WC", "BATH"],
    "fixtures": ["WC", "SINK", "URINAL"],
    "min_fixtures": 1,
    "area_range": (3, 50),
}

toilet.furniture_template = {
    "layout": "fixtures_in_rows",
    "wc_spacing": 1.2,
    "additional_furniture": None,
}

toilet.mep_chain = [
    {"discipline": "FP", "element": "sprinklers", "spacing": 2.5},
    {"discipline": "FP", "element": "pipes", "diameter": 25},
    {"discipline": "ACMV", "element": "extract_fans", "airflow": 50},
    {"discipline": "ELEC", "element": "lights", "type": "waterproof_IP65"},
    # ... etc
]
```

---

## NEW FEATURE 4: Drag-and-Paint Design Canvas (Future)

### Visual DXF Preview with Room Purpose Painting

```
┌──────────────────────────────────────────────────────────────┐
│ [Templates] [Room Types] [Design Canvas] [Validation]        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌─ DXF Preview ─────────────────────────────────────────┐   │
│ │                                                        │   │
│ │  [Zoom In] [Zoom Out] [Fit] [Pan]                     │   │
│ │                                                        │   │
│ │  ┌──────────────────────────────────────────────────┐ │   │
│ │  │                                                  │ │   │
│ │  │         ┌───────────────────┐                   │ │   │
│ │  │         │                   │                   │ │   │
│ │  │         │  [WAITING LOBBY]  │  (painted blue)   │ │   │
│ │  │         │                   │                   │ │   │
│ │  │         └───────────────────┘                   │ │   │
│ │  │                                                  │ │   │
│ │  │  ┌──┐  ┌──┐                                     │ │   │
│ │  │  │T │  │T │  (painted green = toilets)          │ │   │
│ │  │  └──┘  └──┘                                     │ │   │
│ │  │                                                  │ │   │
│ │  │  [Shop1]  [Shop2]  [Shop3]  (painted yellow)   │ │   │
│ │  │                                                  │ │   │
│ │  └──────────────────────────────────────────────────┘ │   │
│ │                                                        │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Paint Tools ─────────────────────────────────────────┐   │
│ │                                                        │   │
│ │ Room Purpose:                                          │   │
│ │   [Waiting Lobby]  [Toilet]  [Retail]  [Gate]        │   │
│ │   [Corridor]  [Back-of-House]  [Eraser]              │   │
│ │                                                        │   │
│ │ Paint Mode:                                            │   │
│ │   (•) Click room to assign                            │   │
│ │   ( ) Drag to paint multiple                          │   │
│ │   ( ) Select region                                   │   │
│ │                                                        │   │
│ │ Detection Mode:                                        │   │
│ │   [✓] Auto-detect from DXF (show suggestions)         │   │
│ │   [ ] Manual only                                     │   │
│ │                                                        │   │
│ └────────────────────────────────────────────────────────┘   │
│                                                              │
│ ┌─ Detected Spaces ──────────────────────────────────────┐  │
│ │ Room ID │ Area (m²) │ Purpose (Auto) │ Confidence │ ✓ │  │
│ │ ───────────────────────────────────────────────────────│  │
│ │ R001    │ 1,245     │ Waiting Lobby  │ 85%        │ ✓ │  │
│ │ R002    │ 32        │ Toilet (M)     │ 95%        │ ✓ │  │
│ │ R003    │ 28        │ Toilet (F)     │ 95%        │ ✓ │  │
│ │ R004    │ 45        │ Retail         │ 70%        │ ✓ │  │
│ │ R005    │ 52        │ Unknown        │ --         │ → │  │
│ │ R006    │ 890       │ Waiting Lobby  │ 88%        │ ✓ │  │
│ │                                                         │  │
│ │ [Accept All] [Review Uncertain] [Export Assignments]   │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ Workflow:                                                    │
│ 1. Load DXF → Auto-detect room purposes                     │
│ 2. Review/correct uncertain assignments                     │
│ 3. Paint additional purposes as needed                      │
│ 4. Generate with functional intelligence!                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Integration with Existing Features

### Variant Configuration Extended

Add building type and inference rules to variant JSON:

```json
{
  "variant_name": "Terminal2_Transportation_Hub",
  "base_template_version": "terminal_base_v1.0",
  "created": "2025-11-12",

  "building_type": {
    "type_id": "transportation_hub",
    "subtype": "airport",
    "auto_detect": false
  },

  "inference_rules": {
    "enabled_categories": [
      "boundary_based",
      "spacing_based",
      "cross_discipline_chains"
    ],

    "ceiling_tiles": {
      "enabled": true,
      "tile_size": 0.6,
      "default_height": 18.5,
      "confidence": 0.90
    },

    "sprinklers": {
      "enabled": true,
      "spacing": 3.0,
      "confidence": 0.95
    },

    "toilet_mep_chain": {
      "enabled": true,
      "confidence": 0.90
    }
  },

  "room_types": [
    {
      "name": "Waiting Lobby",
      "detection_layers": ["LOBBY", "DEPARTURE", "ARRIVAL"],
      "furniture": "terminal_seating",
      "seating_density": 1.5
    },
    {
      "name": "Toilet",
      "detection_layers": ["FP-*", "TOILET", "WC"],
      "mep_chain": "full_inference",
      "confidence": 0.95
    }
  ],

  "template_overrides": [
    // ... existing template overrides
  ]
}
```

---

## Implementation Priority

### Phase 1: Building Type Selector
**Timeline:** Week 1
**Complexity:** Low
- Add dropdown to main UI
- Load building type definitions
- Display type preview
- Save with variant

### Phase 2: Inference Rule Manager
**Timeline:** Week 2
**Complexity:** Medium
- New "Inference Rules" tab
- List all inference categories
- Enable/disable rules
- Edit parameters
- Test on DXF

### Phase 3: Room Purpose Editor
**Timeline:** Week 2-3
**Complexity:** Medium-High
- New "Room Types" tab
- Define room types
- Configure detection criteria
- Set furniture templates
- Configure MEP chains

### Phase 4: Drag-and-Paint Canvas
**Timeline:** Week 4+
**Complexity:** High
- DXF preview rendering
- Paint tools for room purposes
- Auto-detection + manual override
- Visual feedback
- Export assignments

---

## Data Storage

### Extended Template Database Schema

Add new tables to template_library.db:

```sql
-- Building types
CREATE TABLE building_types (
    id INTEGER PRIMARY KEY,
    type_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    signature_spaces JSON,
    mep_standards JSON
);

-- Inference rules
CREATE TABLE inference_rules (
    id INTEGER PRIMARY KEY,
    rule_name TEXT NOT NULL,
    category TEXT,
    trigger_conditions JSON,
    generation_params JSON,
    confidence REAL,
    enabled INTEGER DEFAULT 1
);

-- Room types
CREATE TABLE room_types (
    id INTEGER PRIMARY KEY,
    room_name TEXT NOT NULL,
    building_type_id INTEGER,
    detection_criteria JSON,
    furniture_template JSON,
    mep_chain JSON,
    confidence REAL,
    FOREIGN KEY (building_type_id) REFERENCES building_types(id)
);

-- Room assignments (for drag-and-paint)
CREATE TABLE room_assignments (
    id INTEGER PRIMARY KEY,
    room_id TEXT,  -- From DXF analysis
    room_type_id INTEGER,
    confidence REAL,
    manually_assigned INTEGER DEFAULT 0,
    FOREIGN KEY (room_type_id) REFERENCES room_types(id)
);
```

---

## Testing Strategy

### Test 1: Building Type Selection
1. Load configurator
2. Select "Transportation Hub"
3. Verify preview shows correct information
4. Save variant with building type
5. Load variant and verify type persists

### Test 2: Inference Rule Configuration
1. Open "Inference Rules" tab
2. Edit "Ceiling Tiles" spacing to 0.5m
3. Test on sample DXF
4. Verify generated element count changes
5. Revert to 0.6m and verify count returns

### Test 3: Room Purpose Detection
1. Define "Toilet" room type
2. Load Terminal 1 DXF
3. Run auto-detection
4. Verify 12 toilets detected (matches actual)
5. Check MEP chain inference triggers

### Test 4: End-to-End Workflow
1. Create new variant: "Terminal2_Custom"
2. Select building type: "Transportation Hub"
3. Configure inference rules (enable ceiling, sprinklers)
4. Define room types (toilet, lobby)
5. Save variant
6. Run conversion with variant
7. Validate accuracy improvement (71% → 90%+)

---

## Documentation Updates

Update TEMPLATE_CONFIGURATOR_DESIGN.md sections:

1. **OVERVIEW** - Add building type selection
2. **PROPERTY 5** - Add Inference Rule Manager
3. **PROPERTY 6** - Add Room Purpose Editor
4. **PROPERTY 7** - Add Drag-and-Paint Canvas
5. **USER WORKFLOWS** - Add inference configuration workflow
6. **CONFIGURATION FILE FORMAT** - Extend JSON schema

---

## Bottom Line

### New Capabilities Added:
1. ✅ **Building Type Selector** - Context-aware inference
2. ✅ **Inference Rule Manager** - Configure automatic generation
3. ✅ **Room Purpose Editor** - Functional intelligence
4. ✅ **Drag-and-Paint Canvas** - Visual design tool (future)

### Integration Strategy:
- Extends existing TEMPLATE_CONFIGURATOR_DESIGN.md
- Adds new tabs and dialogs to UI
- Extends variant configuration format
- Backward compatible with existing templates

### Expected Impact:
```
Without these features: 71% accuracy, generic layouts
With these features:     92% accuracy, functional intelligence

Result: Professional, adaptable template system! 🎯
```

---

**Last Updated:** November 12, 2025
**Status:** Design additions ready for implementation
**Integration:** Merge with TEMPLATE_CONFIGURATOR_DESIGN.md
