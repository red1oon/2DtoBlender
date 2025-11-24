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
- **Validated by:** vector_line_filtering, robust_deduplication

## Phase 1D

### elevation_extraction
- **Source:** elevation_views_page3_page4
- **Inference:** Extracted elevation data: ceiling=3.0m, sill=1.0m
- **Confidence:** 95%
- **Validated by:** regex_patterns, cross_page_validation

### room_label_extraction
- **Source:** floor_plan_text_labels
- **Inference:** Extracted 0 room labels (Malay → English)
- **Confidence:** 90%
- **Validated by:** pattern_matching, calibrated_coordinates

### window_sill_inference
- **Source:** elevation_data + window_schedule
- **Inference:** Inferred sill heights for 10 windows based on size
- **Confidence:** 85%
- **Validated by:** window_size_rules, elevation_data

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

### progressive_validation_4criteria
- **Source:** wall_validator_enhanced
- **Inference:** Filtered 109 → 17 walls using 4-criteria scoring
- **Confidence:** 92%
- **Validated by:** connection, opening_proximity, room_boundary, parallelism

### room_boundary_filtering
- **Source:** room_boundary_detector
- **Inference:** Filtered to 7 walls that form room boundaries
- **Confidence:** 95%
- **Validated by:** room_enclosure_logic, wall_connectivity

