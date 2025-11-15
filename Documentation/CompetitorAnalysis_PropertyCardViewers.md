# Who Else Has 2D-to-3D Property Card Configurators?

**Date:** November 12, 2025
**Question:** Who has built property card overlays that show 2D information on hover in 3D BIM viewers?

---

## Direct Competitors (Have This Feature)

### 1. **Autodesk Forge Viewer** (Web-based)
**Implementation:**
- Uses `OBJECT_UNDER_MOUSE_CHANGED` event to detect hover
- Displays property cards as DOM overlays on 3D canvas
- `viewer.getProperties(dbId)` retrieves element properties
- Custom overlays via `viewer.impl.createOverlayScene()`

**Technical Approach:**
```javascript
viewer.addEventListener(Autodesk.Viewing.OBJECT_UNDER_MOUSE_CHANGED, function(e) {
    viewer.getProperties(e.dbId, function(props) {
        // Display property card at mouse position
        showPropertyCard(props.name, props.properties);
    });
});
```

**Platform:** Web browser (WebGL-based)
**Cost:** Part of Autodesk Platform Services (APS), requires subscription

---

### 2. **BIMcollab Zoom** (Desktop IFC Viewer)
**Implementation:**
- Hover over element → tooltip appears with basic properties
- Right-click → full property panel slides in from side
- "Smart Properties" feature adds custom property overlays
- Color-codes elements based on property values

**Technical Approach:**
- Native desktop application
- Direct IFC property parsing
- Qt-based UI framework (likely)

**Platform:** Windows desktop
**Cost:** Free (freemium model, upsell to BIMcollab cloud services)

**Unique Feature:** Smart Views - filter/color objects based on properties in 3D view

---

### 3. **xBIM Viewer** (Web Component)
**Implementation:**
- `hoverpick` event triggers on mouse hover
- `hoverpicked` event used for tooltips/context menus
- Lightweight WebGL viewer for IFC models
- Open-source (MIT license)

**Technical Approach:**
```javascript
viewer.on('hoverpicked', function(args) {
    // args contains element ID and properties
    displayTooltip(args.id, args.properties);
});
```

**Platform:** Web browser (JavaScript/TypeScript)
**Cost:** Free and open-source
**GitHub:** https://github.com/xBimTeam/XbimWebUI

---

### 4. **Autodesk Tandem** (Cloud Digital Twin)
**Implementation:**
- Asset property cards appear in 3D/2D views
- Lightweight cards (not full property panel)
- Shows KPIs, sensor data, maintenance info
- Can pin cards to viewport

**Technical Approach:**
- Proprietary cloud platform
- Real-time IoT data integration
- Mobile-friendly responsive cards

**Platform:** Web browser + mobile apps
**Cost:** $1,800-2,500/year per building

**Unique Feature:** Live IoT sensor data overlaid on 3D model

---

### 5. **Solibri Anywhere** (Web Viewer)
**Implementation:**
- Click element → property panel slides in
- Hover → tooltip with basic info (name, type)
- Rule-based color coding in 3D view
- Issue markers with property cards

**Platform:** Web browser
**Cost:** Part of Solibri Office subscription ($3,400/year)

**Note:** Less emphasis on hover cards, more on issue management

---

## Partial Competitors (Similar But Different)

### 6. **Navisworks**
**What They Have:**
- Properties panel (side panel, not overlay)
- Selection Tree view
- **NO hover tooltips** - must click to see properties

**Why Not a Direct Competitor:**
- Desktop-only (not web)
- Properties are in separate panel, not overlaid on viewport
- Old-school UI (pre-dates modern overlay UX)

---

### 7. **Revit**
**What They Have:**
- Properties palette (docked panel)
- Element tooltips on hover (very basic - just element name/type)
- **NO rich property cards**

**Why Not a Direct Competitor:**
- Authoring tool, not viewer
- Properties UI designed for editing, not viewing

---

## Open-Source Alternatives

### 8. **BlenderBIM (Bonsai)**
**Current State:**
- Properties panel in Blender UI (right sidebar)
- **NO viewport overlay cards** (yet!)
- Click element → properties in side panel

**Opportunity:** This is the gap Mini Bonsai Tree fills!

---

### 9. **IFC.js Viewer**
**Implementation:**
- Web-based IFC viewer
- Click element → property table appears
- Open-source (MIT license)

**Platform:** Web browser (Three.js based)
**GitHub:** https://github.com/IFCjs/web-ifc-viewer

**Limitations:** No hover tooltips, only click-to-view

---

## Summary Table

| Software | Hover Cards | Click Cards | 3D Overlay | Platform | Cost | Open Source |
|----------|-------------|-------------|------------|----------|------|-------------|
| **Autodesk Forge Viewer** | ✅ Yes | ✅ Yes | ✅ Yes | Web | $$ | ❌ No |
| **BIMcollab Zoom** | ✅ Yes | ✅ Yes | ✅ Yes | Desktop | Free | ❌ No |
| **xBIM Viewer** | ✅ Yes | ✅ Yes | ✅ Yes | Web | Free | ✅ Yes |
| **Autodesk Tandem** | ✅ Yes | ✅ Yes | ✅ Yes | Web/Mobile | $$$ | ❌ No |
| **Solibri Anywhere** | ⚠️ Basic | ✅ Yes | ✅ Yes | Web | $$$ | ❌ No |
| **Navisworks** | ❌ No | ✅ Panel only | ❌ No | Desktop | $$$ | ❌ No |
| **Revit** | ⚠️ Name only | ✅ Panel only | ❌ No | Desktop | $$$ | ❌ No |
| **BlenderBIM/Bonsai** | ❌ No | ✅ Panel only | ❌ No | Desktop | Free | ✅ Yes |
| **IFC.js Viewer** | ❌ No | ✅ Yes | ⚠️ Table | Web | Free | ✅ Yes |

**Legend:**
- ✅ Yes = Full feature
- ⚠️ Basic = Limited implementation
- ❌ No = Feature not present
- $$ = Paid subscription
- $$$ = Expensive ($2,000+/year)

---

## Key Insights

### What's Common:
1. **Web viewers** (Forge, xBIM, IFC.js) have hover cards - it's easier with DOM overlays
2. **Desktop apps** (BIMcollab, Navisworks, Revit) mostly use side panels, not overlays
3. **Cloud platforms** (Tandem) have the most polished overlay UX

### What's Rare:
1. **Desktop overlay cards** - Only BIMcollab Zoom does this well
2. **Blender-based overlays** - Nobody has done this! (Mini Bonsai Tree is unique)
3. **Maintenance-aware property cards** - Only Tandem, but for operations not design

### Bonsai's Competitive Position:
- **Only open-source desktop app** with 3D viewport property cards
- **Only Blender-based BIM tool** with overlay UI
- **Only design-phase tool** with maintenance property display

---

## Technical Implementation Notes

### Web-Based Approach (Forge, xBIM, IFC.js):
```javascript
// 1. Detect hover via mouse events
canvas.addEventListener('mousemove', (e) => {
    let intersection = raycaster.intersectObjects(scene.children);
    if (intersection.length > 0) {
        let elementId = intersection[0].object.userData.id;
        showPropertyCard(elementId, e.clientX, e.clientY);
    }
});

// 2. Create DOM overlay positioned over canvas
function showPropertyCard(id, x, y) {
    let card = document.createElement('div');
    card.style.position = 'absolute';
    card.style.left = x + 'px';
    card.style.top = y + 'px';
    card.innerHTML = getProperties(id);
    document.body.appendChild(card);
}
```

### Desktop Approach (BIMcollab, Bonsai's Goal):
```python
# Blender GPU overlay approach
import bpy
import blf

def draw_property_card(self, context):
    # Get mouse position
    mouse_x, mouse_y = context.window.mouse_x, context.window.mouse_y

    # Raycast to find element under mouse
    hit_object = raycast_from_mouse(context, mouse_x, mouse_y)

    if hit_object:
        props = get_properties_from_sqlite(hit_object.name)

        # Draw card using Blender font library
        font_id = 0
        blf.position(font_id, mouse_x + 10, mouse_y - 50, 0)
        blf.size(font_id, 12)
        blf.draw(font_id, f"Type: {props['ifc_class']}")
        # ... more properties
```

### Performance Considerations:
- **Web:** 60fps possible with DOM caching, batch property queries
- **Desktop (Blender):** GPU draw handlers run every frame, must cache database queries
- **Best Practice:** Only query on hover change, not every frame (TTL cache)

---

## Answer to Your Question

**Who else has 2D-to-3D property card configurators?**

**Web Platforms:**
1. ✅ **Autodesk Forge Viewer** - Full implementation, proprietary
2. ✅ **xBIM Viewer** - Open-source, basic hover tooltips
3. ✅ **Autodesk Tandem** - Most polished, cloud-only

**Desktop Apps:**
1. ✅ **BIMcollab Zoom** - Only desktop app with good overlay cards (but proprietary)
2. ⚠️ **Navisworks/Revit** - Side panels only, no overlays

**Open-Source Desktop:**
1. ❌ **Nobody!** - This is the gap Bonsai fills

**Mini Bonsai Tree's Unique Position:**
- **First open-source desktop BIM tool** with 3D viewport property cards
- **Only Blender-based implementation** (leverages GPU draw handlers)
- **Only design tool** combining clash resolution + maintenance properties in overlays

---

**Conclusion:** The feature exists in web viewers (easy with DOM) and one desktop app (BIMcollab). **No open-source desktop implementation exists** - Bonsai would be the first.

**Technical Feasibility:** Proven by BIMcollab Zoom (desktop) and xBIM (open-source web). Blender's GPU overlay system (`bpy.types.SpaceView3D.draw_handler_add()`) makes this achievable.

---

**Last Updated:** November 12, 2025
**Research Sources:** Web search, GitHub repos, community forums (OSArch, buildingSMART)
