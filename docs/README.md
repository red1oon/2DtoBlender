# 2D to 3D BIM Federation System

**Location:** `/home/red1/Documents/bonsai/2Dto3D/`
**Last Updated:** November 18, 2025

---

## 🚀 Quick Start

### **New to this project?**

**Read this first:** [`../2Dto3D_ROADMAP.md`](../2Dto3D_ROADMAP.md)

This roadmap explains:
- The big picture vision (Mini Bonsai Tree GUI)
- Why we're building this
- Current stage and priorities
- How it fits into the Bonsai ecosystem

### **Working on current tasks?**

**Check current status:** `~/Documents/bonsai/prompt.txt`

Updated every session with:
- What's working now
- What's the next priority
- Known issues and fixes
- File locations and references

---

## 📁 Project Structure

```
2Dto3D/
├── 2Dto3D_ROADMAP.md           ← START HERE (big picture vision)
│
├── SourceFiles/                 ← DXF/DWG source files
│   └── TERMINAL1DXF/
│       ├── 01 ARCHITECT/
│       └── 02 STRUCTURE/
│
├── Scripts/                     ← Python generation scripts
│   ├── generate_base_arc_str_multifloor.py
│   ├── master_routing.py
│   └── [Other scripts]
│
├── BASE_ARC_STR.db             ← Current working database
├── building_config.json        ← Building configuration
│
├── Archive_SessionNotes_Nov2025/  ← Historical session notes
└── docs/                       ← This folder
```

---

## 🎯 What This Does

**Converts 2D DXF files → Federated 3D BIM database**

Input: DXF floor plans (architects/engineers use these)
Output: Blender-compatible federated database (same format as 8_IFC/)

**Why:**
- Prove DXF → realistic 3D database is viable
- Build baseline for future GUI tool
- Enable BIM coordination from 2D sources

**Current focus:**
Extracting actual geometry from DXF entities (walls, columns, beams) to replace placeholder boxes

---

## 📚 Key Documentation

**Strategic (big picture):**
- [`2Dto3D_ROADMAP.md`](../2Dto3D_ROADMAP.md) - Vision, goals, architecture

**Tactical (current work):**
- `~/Documents/bonsai/prompt.txt` - Current status and priorities
- `~/Documents/bonsai/StandingInstructions.txt` - Development protocols

**Historical (reference):**
- `Archive_SessionNotes_Nov2025/` - Session-specific notes from Nov 2025

---

## 🔗 Related Projects

**Federation Module:**
- Location: `~/Projects/IfcOpenShell/src/bonsai/bonsai/tool/federation/`
- Features: Clash detection, routing, BOQ, structural works
- Integration: 2Dto3D output feeds into federation database

**Reference Database:**
- Location: `~/Documents/bonsai/8_IFC/enhanced_federation.db`
- Purpose: Quality target (what generated geometry should look like)
- Size: 327 MB, 49,059 elements with detailed tessellated meshes

---

## 💡 Philosophy

**This project is NOT:**
- ❌ One-time Terminal 1 conversion
- ❌ Manual BIM modeling
- ❌ Perfect geometry extraction

**This project IS:**
- ✅ Automation to eliminate 90% of grunt work
- ✅ Reusable templates across all projects
- ✅ Foundation for Mini Bonsai Tree GUI
- ✅ Proof that DXF → BIM workflow is viable

---

## 📧 Questions?

1. **What's the big picture?** → Read [`2Dto3D_ROADMAP.md`](../2Dto3D_ROADMAP.md)
2. **What should I work on?** → Read `~/Documents/bonsai/prompt.txt`
3. **How do I run X?** → Check script comments or session notes archive

---

**Remember:** The baseline we're building now proves the approach. Once proven, the GUI becomes the force multiplier.

**Last Updated:** 2025-11-18
