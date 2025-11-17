# Future Roadmap - Componentized Placement System

**Current Status:** Sprinkler grid generation working
**Vision:** Unified placement system for ALL building elements

---

## 🎯 Where We're Heading

### **Problem:**
Many building elements have the same placement issues as sprinklers:
- Lights (clustered, not evenly distributed)
- HVAC diffusers (random placement)
- Smoke detectors (code compliance issues)
- Emergency lights (spacing violations)
- Electrical outlets (no pattern)

### **Solution:**
**Componentized placement system** that works for ANY element type using engineering standards.

---

## 🏗️ Architecture Vision

### **Phase 1: Current (Sprinklers) ✅**

```python
# Hardcoded for sprinklers
PlacementGenerator.generate_grid_placement(
    room_bounds,
    'sprinkler',
    'FP'
)
```

### **Phase 2: Componentized (Future)**

```python
# Works for ANY element type
PlacementEngine = PlacementFactory.create(
    element_type='light_fixture',
    discipline='ELEC',
    strategy='grid'  # or 'corridor', 'perimeter', 'custom'
)

placements = PlacementEngine.generate(room_bounds)
```

---

## 📦 Componentization Strategy

### **1. Placement Strategies (Patterns)**

```
PlacementStrategy (Base Class)
├── GridPlacement        - Even 2D grid (sprinklers, lights, HVAC)
├── PerimeterPlacement   - Around walls (emergency lights, outlets)
├── CorridorPlacement    - Along corridors (exit signs, smoke detectors)
├── ZonedPlacement       - By room type (task lighting)
└── CustomPlacement      - User-defined patterns
```

### **2. Element Standards Database**

```python
ELEMENT_STANDARDS = {
    ('sprinkler', 'FP'): {
        'strategy': 'grid',
        'spacing': PlacementStandards(...),
        'validator': NFPA13Validator
    },
    ('light_fixture', 'ELEC'): {
        'strategy': 'grid',
        'spacing': PlacementStandards(...),
        'validator': IESValidator
    },
    ('smoke_detector', 'FP'): {
        'strategy': 'corridor',
        'spacing': PlacementStandards(...),
        'validator': NFPA72Validator
    },
    ('emergency_light', 'ELEC'): {
        'strategy': 'perimeter',
        'spacing': PlacementStandards(...),
        'validator': IBC_LifeSafetyValidator
    }
}
```

### **3. Unified Interface**

```python
class PlacementEngine:
    """Unified interface for all element placement."""

    def __init__(self, element_type, discipline):
        self.standards = get_element_standards(element_type, discipline)
        self.strategy = self._create_strategy(self.standards.strategy)
        self.validator = self.standards.validator

    def generate(self, room_bounds):
        """Generate placements using appropriate strategy."""
        placements = self.strategy.generate(room_bounds, self.standards)
        violations = self.validator.validate(placements)
        return placements, violations

    def export_to_database(self, db_path, placements):
        """Export to database (same for all element types)."""
        DatabaseExporter.insert_elements(db_path, placements, self.element_type)
```

---

## 🚀 Implementation Roadmap

### **Phase 1: Foundation (DONE) ✅**
- [x] PlacementStandards dataclass
- [x] PLACEMENT_STANDARDS dictionary
- [x] PlacementGenerator.generate_grid_placement()
- [x] Integration with master_routing.py
- [x] Database export working
- [x] Sprinklers (273 grid) verified

### **Phase 2: Refactor for Reusability (Next)**
- [ ] Extract GridPlacement strategy as separate class
- [ ] Create PlacementStrategy base class
- [ ] Create PlacementFactory for strategy selection
- [ ] Move database export to separate DatabaseExporter class
- [ ] Add PerimeterPlacement strategy (emergency lights, outlets)

### **Phase 3: Additional Element Types (Future)**
- [ ] Lights (ELEC) - grid placement
- [ ] HVAC diffusers (HVAC) - grid placement
- [ ] Smoke detectors (FP) - corridor placement
- [ ] Emergency lights (ELEC) - perimeter placement
- [ ] Exit signs (ELEC) - corridor placement
- [ ] Electrical outlets (ELEC) - perimeter placement

### **Phase 4: GUI Integration (Long-term)**
- [ ] Visual room definition (click to define bounds)
- [ ] Strategy selection UI (grid/perimeter/corridor)
- [ ] Preview placement before export
- [ ] Adjustment tools (add/remove/move elements)
- [ ] Batch placement (all element types at once)

---

## 💡 Key Benefits

### **Current Approach (Hardcoded):**
- ❌ Separate code for each element type
- ❌ Duplication of placement logic
- ❌ Hard to maintain
- ❌ Adding new element types requires code changes

### **Componentized Approach (Future):**
- ✅ Single, reusable codebase
- ✅ Add new element types via configuration (not code)
- ✅ Mix strategies (grid + perimeter + corridor)
- ✅ Easy to test and maintain
- ✅ User-friendly (select strategy, not write code)

---

## 🔧 Example Usage (Future)

### **Scenario: Complete MEP Layout for a Room**

```python
# Define room once
room = {
    'min_x': 0, 'max_x': 20,
    'min_y': 0, 'max_y': 15,
    'height': 3.0
}

# Place ALL element types with one workflow
placement_config = {
    'sprinklers': {'type': 'sprinkler', 'discipline': 'FP', 'strategy': 'grid'},
    'lights': {'type': 'light_fixture', 'discipline': 'ELEC', 'strategy': 'grid'},
    'hvac': {'type': 'hvac_diffuser', 'discipline': 'HVAC', 'strategy': 'grid'},
    'smoke_detectors': {'type': 'smoke_detector', 'discipline': 'FP', 'strategy': 'corridor'},
    'emergency_lights': {'type': 'emergency_light', 'discipline': 'ELEC', 'strategy': 'perimeter'},
    'outlets': {'type': 'outlet', 'discipline': 'ELEC', 'strategy': 'perimeter'}
}

# Generate all placements
all_placements = PlacementBatchEngine.generate_all(room, placement_config)

# Validate against codes
validation_report = CodeComplianceEngine.validate_all(all_placements)

# Export to database
DatabaseExporter.export_all(db_path, all_placements)
```

**Result:** Complete MEP layout (6 element types) in one command!

---

## 📐 Standards Database Expansion

### **Current (3 element types):**
```python
PLACEMENT_STANDARDS = {
    ('sprinkler', 'FP'): PlacementStandards(...),
    ('light_fixture', 'ELEC'): PlacementStandards(...),
    ('hvac_diffuser', 'HVAC'): PlacementStandards(...)
}
```

### **Future (20+ element types):**
```python
PLACEMENT_STANDARDS = {
    # Fire Protection
    ('sprinkler', 'FP'): {...},
    ('smoke_detector', 'FP'): {...},
    ('fire_alarm', 'FP'): {...},
    ('fire_extinguisher', 'FP'): {...},

    # Electrical
    ('light_fixture', 'ELEC'): {...},
    ('emergency_light', 'ELEC'): {...},
    ('exit_sign', 'ELEC'): {...},
    ('outlet', 'ELEC'): {...},
    ('junction_box', 'ELEC'): {...},

    # HVAC
    ('hvac_diffuser', 'HVAC'): {...},
    ('return_grille', 'HVAC'): {...},
    ('thermostat', 'HVAC'): {...},

    # Plumbing
    ('water_closet', 'PLB'): {...},
    ('lavatory', 'PLB'): {...},
    ('floor_drain', 'PLB'): {...},

    # ... and more
}
```

---

## 🎨 Interface Patterns

### **Pattern 1: Declarative Configuration**
```json
{
  "room": {"bounds": [0, 0, 20, 15], "height": 3.0},
  "elements": [
    {"type": "sprinkler", "strategy": "grid", "spacing": "auto"},
    {"type": "light_fixture", "strategy": "grid", "spacing": "auto"},
    {"type": "emergency_light", "strategy": "perimeter", "spacing": 15.0}
  ]
}
```

### **Pattern 2: Builder Pattern**
```python
PlacementBuilder(room_bounds) \
    .add_grid('sprinkler', 'FP') \
    .add_grid('light_fixture', 'ELEC') \
    .add_perimeter('emergency_light', 'ELEC') \
    .validate() \
    .export(db_path)
```

### **Pattern 3: CLI Interface**
```bash
python3 Scripts/place_elements.py \
    --room "0,0,20,15" \
    --add-grid sprinkler,FP \
    --add-grid light_fixture,ELEC \
    --add-perimeter emergency_light,ELEC \
    --output Terminal1.db
```

---

## 📊 Success Metrics

**Current (Sprinklers only):**
- 1 element type working
- 273 placements in grid
- Manual workflow

**Target (Componentized):**
- 20+ element types supported
- 1000s of placements automatically
- Single command workflow
- GUI integration

---

**Status:** Foundation complete, ready for componentization
**Next Step:** Refactor GridPlacement as strategy class
**Timeline:** Phase 2 (next session), Phase 3 (future sessions)
