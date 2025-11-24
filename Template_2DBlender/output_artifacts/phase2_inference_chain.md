# Inference Chain

## Phase 1B

### drain_perimeter_calibration
- **Source:** discharge_plan_page7
- **Inference:** Calibrated scale: 0.035285
- **Confidence:** 95%
- **Validated by:** drain_perimeter

## Phase 1C

### vector_wall_detection
- **Source:** floor_plan_page1
- **Inference:** Detected 109 internal wall candidates
- **Confidence:** 85%
- **Validated by:** vector_line_filtering, deduplication

## Phase 2

### schedule_extraction
- **Source:** page8_tables
- **Inference:** Extracted 3 door types, 3 window types
- **Confidence:** 95%
- **Validated by:** table_extraction

### opening_position_extraction
- **Source:** floor_plan_labels
- **Inference:** Found 7 doors, 10 windows on floor plan
- **Confidence:** 90%
- **Validated by:** label_matching, calibrated_coordinates

### progressive_validation_with_openings
- **Source:** wall_validator
- **Inference:** Filtered 109 → 17 walls using connection + opening proximity
- **Confidence:** 92%
- **Validated by:** connection_scoring, opening_proximity

### room_boundary_filtering
- **Source:** room_boundary_detector
- **Inference:** Filtered to 7 walls that form room boundaries
- **Confidence:** 95%
- **Validated by:** room_enclosure_logic, wall_connectivity

