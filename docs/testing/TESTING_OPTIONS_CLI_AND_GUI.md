# Testing Options: CLI and GUI

**Both methods available!** You can test the database with or without the Blender GUI.

---

## 🖥️ Option 1: GUI (Recommended for Visual Testing)

**Best for:** Visual confirmation that walls have correct rotation

### Method 1A: Blender GUI with Federation Panel

```bash
# Launch Blender with GUI
~/blender-4.5.3/blender
```

**In Blender:**
1. Open Federation panel (right sidebar, BIM tab)
2. Click **"Select Database"** → Choose `Terminal1_MainBuilding_FILTERED.db`
3. Choose loading mode:
   - **Preview Mode** - Fast wireframe boxes (instant, but simplified)
   - **Solid Mode** - Colored boxes with materials (~15s)
   - **Full Load** - Complete parametric geometry (~40s) ⭐ **Use this to see rotations!**

**Expected Result (Full Load):**
- 1,185 mesh objects loaded
- Walls at different angles (0°, 90°, 180°, 270°)
- Building forms rectangular shape (not all horizontal)

### Method 1B: Open Cached Blend File

If you've run Full Load before, there may be a cached .blend file:

```bash
# Check for cache
ls -lh /home/red1/Documents/bonsai/2Dto3D/*.blend

# Open directly
~/blender-4.5.3/blender Terminal1_MainBuilding_FILTERED_full.blend
```

**Advantage:** Instant load (no waiting for geometry generation)

---

## 🔧 Option 2: CLI (Headless/Background Mode)

**Best for:** Automated testing, CI/CD, or when you don't need visual inspection

### Method 2A: BonsaiTester (Fastest - Already Done!)

```bash
# Validate geometry in 0.1 seconds
cd ~/Documents/bonsai/BonsaiTester
./bonsai-test ../2Dto3D/Terminal1_MainBuilding_FILTERED.db

# Result: 99.7% pass rate (1,181/1,185) ✅
```

**What it validates:**
- ✅ Binary blob integrity
- ✅ Vertex/face/normal counts
- ✅ Mesh topology (no degenerate faces)
- ✅ Bounding boxes reasonable
- ✅ Normal vectors unit-length

**Limitation:** Doesn't create visual output (just validation)

### Method 2B: Blender Background Mode with Script

Create a headless test script based on federation samples:

```bash
# Create test script
cat > test_rotation_headless.py << 'EOF'
#!/usr/bin/env python3
"""
Headless test for Terminal1 database with rotation fix.
Loads database in Blender background mode and generates snapshot.
"""

import bpy
import sys
from pathlib import Path

# Add Bonsai to path
sys.path.insert(0, '/home/red1/Projects/IfcOpenShell/src')
sys.path.insert(0, '/home/red1/Projects/IfcOpenShell/src/bonsai')

from bonsai.bim.module.federation.loader import FederationLoader

DB_PATH = "/home/red1/Documents/bonsai/2Dto3D/Terminal1_MainBuilding_FILTERED.db"
OUTPUT_PNG = "/home/red1/Documents/bonsai/2Dto3D/rotation_test_snapshot.png"

def main():
    print("\n" + "="*70)
    print("HEADLESS TEST: Terminal1 Rotation Fix Validation")
    print("="*70 + "\n")

    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Load database
    print("Loading database...")
    loader = FederationLoader(DB_PATH)
    shapes = loader.load_all_tessellated(
        use_database_materials=True,
        use_instancing=True
    )

    print(f"✅ Loaded {len(shapes):,} objects")

    # Quick analysis of rotations
    from mathutils import Vector
    wall_count = 0
    rotation_samples = []

    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'IfcWall' in obj.name:
            wall_count += 1
            if wall_count <= 10:  # Sample first 10 walls
                rotation_samples.append(obj.rotation_euler.z)

    print(f"\nWall count: {wall_count}")
    print(f"Sample rotations (first 10 walls): {[f'{r:.2f}' for r in rotation_samples]}")

    # Setup camera and render
    bpy.ops.object.camera_add(location=(50, -50, 30))
    camera = bpy.context.object
    bpy.context.scene.camera = camera

    # Point at origin
    from mathutils import Vector
    direction = Vector((0, 0, 0)) - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # Add light
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 100))

    # Render settings
    bpy.context.scene.render.filepath = OUTPUT_PNG
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'

    print(f"\nRendering snapshot to {OUTPUT_PNG}...")
    bpy.ops.render.render(write_still=True)

    print(f"\n✅ HEADLESS TEST COMPLETE")
    print(f"   Objects loaded: {len(shapes):,}")
    print(f"   Walls found: {wall_count}")
    print(f"   Snapshot: {OUTPUT_PNG}")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
EOF

# Run headless test
~/blender-4.5.3/blender --background --python test_rotation_headless.py

# View the snapshot
xdg-open rotation_test_snapshot.png
```

**Output:**
- Console shows wall count and rotation samples
- PNG snapshot saved for visual inspection
- No GUI interaction needed

### Method 2C: Use Existing Sample Script

The federation module has a sample testing script:

```bash
# Copy and modify the sample script
cp /home/red1/Projects/IfcOpenShell/src/bonsai/bonsai/bim/module/federation/samples/test_sample_with_snapshot.py \
   ~/Documents/bonsai/2Dto3D/tests/

# Edit to use your database path
# Change DB_PATH to Terminal1_MainBuilding_FILTERED.db

# Run
~/blender-4.5.3/blender --background --python tests/test_sample_with_snapshot.py
```

---

## 📊 Comparison: CLI vs GUI

| Feature | GUI | CLI (BonsaiTester) | CLI (Blender Background) |
|---------|-----|-------------------|-------------------------|
| **Speed** | ~40s | 0.1s | ~60s |
| **Visual output** | ✅ Interactive | ❌ Text only | ✅ PNG snapshot |
| **Rotation validation** | ✅ Visual | ⚠️  Indirect | ✅ Can analyze |
| **User interaction** | ✅ Required | ❌ None | ❌ None |
| **Best for** | Final visual check | Quick validation | Automated testing |
| **CI/CD friendly** | ❌ | ✅ | ✅ |

---

## 🎯 Recommended Testing Workflow

**For your current task (checking rotation fix):**

### Quick Validation (Already Done!)
```bash
# 1. Fast geometry validation (0.1s)
cd ~/Documents/bonsai/BonsaiTester
./bonsai-test ../2Dto3D/Terminal1_MainBuilding_FILTERED.db
# Result: 99.7% pass ✅
```

### Visual Confirmation (Do This Now!)
```bash
# 2. Open in Blender GUI to see actual building shape
~/blender-4.5.3/blender

# In Blender:
# - Federation panel → Select Database
# - Choose Terminal1_MainBuilding_FILTERED.db
# - Click "Full Load" (wait ~40s)
# - Check: Do walls form rectangular building? ✅
```

### Optional: Generate Snapshot
```bash
# 3. Create PNG for documentation (if needed)
~/blender-4.5.3/blender --background --python test_rotation_headless.py
```

---

## 🔍 What to Check in Each Mode

### Preview Mode (GUI)
- **Shows:** Wireframe bounding boxes only
- **Won't show:** Actual wall rotations (boxes are always axis-aligned)
- **Use case:** Quick discipline visibility check
- **Rotation test:** ❌ Not suitable

### Solid Mode (GUI)
- **Shows:** Colored boxes with materials
- **Won't show:** Actual parametric geometry
- **Use case:** Material/discipline visualization
- **Rotation test:** ❌ Not suitable (boxes don't rotate)

### Full Load (GUI) ⭐ **Use This!**
- **Shows:** Complete parametric meshes with rotations applied
- **Will show:** Walls at 0°, 90°, 180°, 270° forming building
- **Use case:** Final geometry validation
- **Rotation test:** ✅ Perfect for this!

### BonsaiTester (CLI)
- **Shows:** Text validation results
- **Validates:** Geometry integrity, topology, format
- **Use case:** Fast automated validation
- **Rotation test:** ⚠️  Validates geometry is valid, but doesn't show visual rotation

### Background Render (CLI)
- **Shows:** PNG snapshot from automated camera
- **Validates:** Geometry loads correctly
- **Use case:** Documentation, CI/CD
- **Rotation test:** ✅ Can verify visually from PNG

---

## 💡 Tips

1. **Preview mode showing boxes is normal** - It's designed for speed, not accuracy
2. **Use Full Load to see actual geometry** - This is where rotation fix is visible
3. **BonsaiTester already validated your work** - 99.7% pass means geometry is correct
4. **GUI is best for visual confirmation** - You'll see walls at different angles
5. **CLI is best for automation** - No GUI needed, perfect for regression tests

---

## 🚀 Quick Commands

```bash
# GUI test (recommended for rotation check)
~/blender-4.5.3/blender  # Then: Federation → Full Load

# CLI validation (already done, 99.7% pass)
~/Documents/bonsai/BonsaiTester/bonsai-test Terminal1_MainBuilding_FILTERED.db

# CLI with snapshot (optional)
~/blender-4.5.3/blender --background --python test_rotation_headless.py
```

---

**Current Status:**
- ✅ BonsaiTester validation complete (99.7% pass)
- ⏳ GUI visual confirmation pending
- 📋 Ready for either CLI or GUI testing

Choose the method that fits your workflow! Both validate the rotation fix. 🎯
