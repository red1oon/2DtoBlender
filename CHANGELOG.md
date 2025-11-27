# Changelog

All notable changes to the 2DtoBlender project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.1.0] - 2025-11-28

### Fixed
- Objects scattered in Blender (placed at PDF label positions instead of room geometry)
- Root cause: placement_engine.py and room_inference/ not integrated into pipeline
- Migrated: src/standards/, src/room_inference/ directories with proper PYTHONPATH
- Pipeline now correctly calls placement engine for grid-based object positioning
- Objects now assigned to rooms with proper heights (e.g., towel_rack at 1.2m)

### Added
- src/room_inference/integrate_room_templates.py - Room template integration
- src/room_inference/room_inference_engine.py - Room detection logic
- src/LocalLibrary/room_templates.json - Room furniture/fixture templates
- docs/room_inference/ROOM_INFERENCE_ENGINE_SPEC.md - Room inference specification
- docs/room_inference/ROOF_CANOPY_INFERENCE_SPEC.md - Roof extraction specification

### Changed
- bin/RUN_COMPLETE_PIPELINE.sh - Updated paths from core/ to src/core/
- bin/RUN_COMPLETE_PIPELINE.sh - Added PYTHONPATH for room_inference module
- docs/TB-LKTN_COMPLETE_SPECIFICATION.md - Updated Section 8 (Pipeline Architecture)
- docs/TB-LKTN_COMPLETE_SPECIFICATION.md - Added Error 4 to Section 12 (Known Issues)
- docs/TB-LKTN_COMPLETE_SPECIFICATION.md - Updated Section 14 (Spec Maintenance)

## [1.0.0] - 2025-11-26

### Added
- Initial release with 2-stage extraction pipeline
- Grid-based coordinate system (GridTruth)
- Master reference template for object detection
- UBBL 1984 compliance validation
- TB-LKTN House complete specification
