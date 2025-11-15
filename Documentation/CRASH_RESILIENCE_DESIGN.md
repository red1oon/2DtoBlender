=============================================================================
CRASH RESILIENCE & MEMORY MANAGEMENT DESIGN
=============================================================================

Document Type: Technical Design for Long-Running Conversion Process
Created: November 12, 2025
Status: Design Specification (Pre-Implementation)
Purpose: Ensure DWG→BIM conversion can survive crashes and manage memory

=============================================================================
PROBLEM STATEMENT
=============================================================================

The DWG → Database conversion process may take HOURS for large files:
- Parse DXF with millions of entities
- Match each entity against templates
- Generate 3D geometry with tessellation
- Write 49,000+ elements to database

RISKS without resilience:
❌ Power failure after 3 hours → restart from scratch
❌ Out-of-memory crash → lose all progress
❌ Database lock timeout → partial corruption
❌ User interruption (Ctrl+C) → no partial results

SOLUTION: Implement checkpointing, resumption, and memory management

=============================================================================
CORE DESIGN PRINCIPLES
=============================================================================

1. INCREMENTAL PROGRESS
   - Process in batches (e.g., 1000 entities at a time)
   - Commit to database after each batch
   - Track progress in temporary state table

2. RESUMABLE PROCESSING
   - Detect if previous run was interrupted
   - Resume from last checkpoint automatically
   - Option to start fresh if desired

3. MEMORY MANAGEMENT
   - Clear entity cache after each batch
   - Stream DXF parsing (don't load entire file at once)
   - Use database for intermediate storage (not RAM)
   - Periodic garbage collection

4. CRASH DETECTION & RECOVERY
   - Write state markers before critical operations
   - Detect incomplete conversions on startup
   - Offer resume or restart options

=============================================================================
IMPLEMENTATION ARCHITECTURE
=============================================================================

COMPONENT 1: Progress Tracking Table
────────────────────────────────────────────────────────────────────────────

Add temporary table to Generated_*.db during conversion:

CREATE TABLE _conversion_progress (
    id INTEGER PRIMARY KEY DEFAULT 1,
    started_at TEXT NOT NULL,
    last_checkpoint_at TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'in_progress', 'completed', 'failed', 'paused'
    dxf_filepath TEXT NOT NULL,
    template_library_path TEXT NOT NULL,

    -- Progress tracking
    total_entities INTEGER,
    entities_processed INTEGER DEFAULT 0,
    entities_matched INTEGER DEFAULT 0,
    entities_skipped INTEGER DEFAULT 0,

    -- Batch tracking
    current_batch_number INTEGER DEFAULT 0,
    batch_size INTEGER DEFAULT 1000,
    last_entity_id TEXT,  -- Resume point

    -- Memory management
    peak_memory_mb REAL,
    cache_cleared_count INTEGER DEFAULT 0,

    -- Error tracking
    error_count INTEGER DEFAULT 0,
    last_error TEXT,

    -- Configuration snapshot
    config_json TEXT,  -- JSON of conversion parameters

    CHECK (id = 1)  -- Only one row allowed
);

This table exists ONLY during conversion. Deleted on successful completion.

COMPONENT 2: Batch Processing Engine
────────────────────────────────────────────────────────────────────────────

Conversion flow with checkpoints:

┌─────────────────────────────────────────────────────────────────────────┐
│ START CONVERSION                                                        │
└─────────────────────────────────────────────────────────────────────────┘
           │
           ├─→ Check if _conversion_progress exists
           │   ├─ YES: Previous run interrupted
           │   │   ├─→ Load state
           │   │   ├─→ Prompt user: [Resume] [Restart] [Cancel]
           │   │   └─→ If Resume: Jump to last_entity_id
           │   └─ NO: Start fresh
           │       └─→ Create _conversion_progress table
           ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ BATCH LOOP (Process N entities at a time)                              │
└─────────────────────────────────────────────────────────────────────────┘
           │
           ├─→ [CHECKPOINT 1] Update status = 'processing_batch_X'
           │
           ├─→ Fetch next batch of entities from DXF
           │   (Stream parsing, not loading entire file)
           │
           ├─→ Match entities to templates
           │   (In-memory matching, fast)
           │
           ├─→ Generate geometry for matched entities
           │   (Compute vertices, tessellation if needed)
           │
           ├─→ [CHECKPOINT 2] Write batch to database
           │   BEGIN TRANSACTION
           │     INSERT INTO elements_meta VALUES (...)
           │     INSERT INTO element_transforms VALUES (...)
           │     INSERT INTO element_geometry VALUES (...)
           │     UPDATE _conversion_progress SET
           │       entities_processed += batch_count,
           │       current_batch_number += 1,
           │       last_entity_id = last_processed_id,
           │       last_checkpoint_at = NOW()
           │   COMMIT TRANSACTION
           │
           ├─→ [CHECKPOINT 3] Clear memory caches
           │   - Clear entity object cache
           │   - Clear geometry buffers
           │   - Python garbage collection (gc.collect())
           │   - Log peak memory usage
           │
           ├─→ [CHECKPOINT 4] Check health
           │   - If memory > threshold (e.g., 2GB): force GC
           │   - If errors > threshold (e.g., 100): pause for review
           │   - If user interrupt signal: graceful pause
           │
           ↓
           └─→ More entities?
               ├─ YES: Continue to next batch
               └─ NO: Finalize
                   ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ FINALIZATION                                                            │
└─────────────────────────────────────────────────────────────────────────┘
           │
           ├─→ Update status = 'completed'
           ├─→ Generate statistics
           ├─→ Create database indexes
           ├─→ VACUUM database (optimize)
           ├─→ Delete _conversion_progress table
           └─→ Generate success report

COMPONENT 3: Memory Management Strategy
────────────────────────────────────────────────────────────────────────────

Problem: Processing 49,000+ entities could consume gigabytes of RAM

Solutions:

1. STREAMING DXF PARSING
   Instead of:
     doc = ezdxf.readfile("large.dxf")  # Loads entire file into memory

   Use:
     for entity in stream_dxf_entities("large.dxf"):  # One at a time
         process(entity)
         del entity  # Free immediately

2. BATCH PROCESSING WITH MEMORY LIMITS
   config = {
       "batch_size": 1000,  # Process 1000 entities, then commit
       "max_memory_mb": 2000,  # If RAM > 2GB, pause and clear cache
       "cache_clear_interval": 10  # Clear cache every 10 batches
   }

3. DATABASE AS TEMPORARY STORAGE
   Instead of:
     all_entities_in_memory = []  # ❌ Out of memory

   Use:
     Write to temporary database table during processing:

     CREATE TABLE _temp_entity_cache (
         entity_id TEXT PRIMARY KEY,
         entity_type TEXT,
         layer TEXT,
         geometry_json TEXT,
         processed INTEGER DEFAULT 0
     );

     Query in batches:
     SELECT * FROM _temp_entity_cache WHERE processed = 0 LIMIT 1000

4. PERIODIC GARBAGE COLLECTION
   import gc

   def process_batch(entities):
       # Process entities
       ...
       # Force garbage collection after each batch
       gc.collect()

       # Log memory usage
       import psutil
       process = psutil.Process()
       memory_mb = process.memory_info().rss / 1024 / 1024
       log(f"Memory: {memory_mb:.1f} MB")

COMPONENT 4: Crash Detection & Recovery
────────────────────────────────────────────────────────────────────────────

On conversion start, check for interrupted previous run:

def check_for_interrupted_conversion(db_path):
    """
    Check if database has incomplete conversion.
    Returns: None if clean, or dict with progress info
    """

    if not os.path.exists(db_path):
        return None  # New conversion

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if progress table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='_conversion_progress'
    """)

    if not cursor.fetchone():
        return None  # Previous conversion completed successfully

    # Load progress info
    cursor.execute("SELECT * FROM _conversion_progress")
    row = cursor.fetchone()

    if row:
        progress = {
            "status": row['status'],
            "started_at": row['started_at'],
            "last_checkpoint_at": row['last_checkpoint_at'],
            "entities_processed": row['entities_processed'],
            "total_entities": row['total_entities'],
            "current_batch": row['current_batch_number'],
            "last_entity_id": row['last_entity_id'],
            "error_count": row['error_count']
        }

        conn.close()

        print("⚠️  INTERRUPTED CONVERSION DETECTED")
        print(f"   Started: {progress['started_at']}")
        print(f"   Last checkpoint: {progress['last_checkpoint_at']}")
        print(f"   Progress: {progress['entities_processed']}/{progress['total_entities']} "
              f"({progress['entities_processed']/progress['total_entities']*100:.1f}%)")
        print(f"   Status: {progress['status']}")

        return progress

    conn.close()
    return None


def prompt_resume_or_restart(progress):
    """
    Ask user what to do with interrupted conversion.
    """

    print("\nOptions:")
    print("  [R] Resume from last checkpoint")
    print("  [S] Start fresh (discard progress)")
    print("  [C] Cancel")

    choice = input("\nYour choice [R/S/C]: ").strip().upper()

    if choice == 'R':
        return 'resume'
    elif choice == 'S':
        return 'restart'
    else:
        return 'cancel'

=============================================================================
CONFIGURATION PARAMETERS (User-Adjustable)
=============================================================================

These should be configurable in dxf_to_database.py or via config file:

# Batch Processing
batch_size = 1000  # Entities per batch (lower = more frequent commits, slower)
                   # Higher = fewer commits, faster, but more lost on crash
                   # Recommended: 500-2000

# Memory Management
max_memory_mb = 2000  # Pause if memory exceeds this (default: 2GB)
cache_clear_interval = 10  # Clear cache every N batches
force_gc_interval = 5  # Force garbage collection every N batches

# Error Handling
max_errors = 100  # Stop if errors exceed this count
error_action = 'skip'  # 'skip' or 'stop' on entity processing error

# Database
db_transaction_mode = 'immediate'  # 'deferred', 'immediate', or 'exclusive'
db_timeout = 30000  # Milliseconds (30 seconds)

# Resumption
auto_resume = False  # If True, automatically resume; if False, prompt user
checkpoint_interval = 1  # Save progress every N batches (1 = every batch)

# Logging
log_level = 'INFO'  # 'DEBUG', 'INFO', 'WARNING', 'ERROR'
log_file = 'conversion_progress.log'
progress_bar = True  # Show progress bar in terminal

=============================================================================
EXAMPLE USAGE WITH RESUMPTION
=============================================================================

Session 1 (Interrupted):
────────────────────────────────────────────────────────────────────────────

$ python3 dxf_to_database.py Terminal1.dxf Generated_Terminal1.db template_library.db

Starting DWG → Database conversion...
Parsing DXF: 100,000 entities found
Processing batch 1/100...   [▓▓░░░░░░░░] 1,000/100,000 (1%)
Processing batch 2/100...   [▓▓▓░░░░░░░] 2,000/100,000 (2%)
Processing batch 3/100...   [▓▓▓▓░░░░░░] 3,000/100,000 (3%)
...
Processing batch 45/100...  [▓▓▓▓▓░░░░░] 45,000/100,000 (45%)
^C  ← USER INTERRUPTION or POWER FAILURE

Session 2 (Resumed):
────────────────────────────────────────────────────────────────────────────

$ python3 dxf_to_database.py Terminal1.dxf Generated_Terminal1.db template_library.db

⚠️  INTERRUPTED CONVERSION DETECTED
   Started: 2025-11-12 14:30:00
   Last checkpoint: 2025-11-12 16:15:23
   Progress: 45,000/100,000 (45.0%)
   Status: in_progress

Options:
  [R] Resume from last checkpoint
  [S] Start fresh (discard progress)
  [C] Cancel

Your choice [R/S/C]: R

Resuming from batch 46...
Processing batch 46/100...  [▓▓▓▓▓░░░░░] 46,000/100,000 (46%)
Processing batch 47/100...  [▓▓▓▓▓▓░░░░] 47,000/100,000 (47%)
...
Processing batch 100/100... [▓▓▓▓▓▓▓▓▓▓] 100,000/100,000 (100%)

✅ Conversion completed successfully!
   Total time: 3h 45m (including interruption)
   Elements generated: 49,059
   Match rate: 92.3%

=============================================================================
IMPLEMENTATION CHECKLIST
=============================================================================

Phase 1: Basic Batch Processing
────────────────────────────────────────────────────────────────────────────
☐ Modify dxf_to_database.py to process in batches
☐ Add batch commit after each batch
☐ Add progress logging

Phase 2: Progress Tracking
────────────────────────────────────────────────────────────────────────────
☐ Create _conversion_progress table schema
☐ Write progress after each batch
☐ Implement progress query function

Phase 3: Crash Detection
────────────────────────────────────────────────────────────────────────────
☐ Implement check_for_interrupted_conversion()
☐ Add resume vs restart prompt
☐ Test resume functionality

Phase 4: Memory Management
────────────────────────────────────────────────────────────────────────────
☐ Add memory monitoring (psutil)
☐ Implement cache clearing
☐ Add garbage collection calls
☐ Test with large DXF file (1M+ entities)

Phase 5: Streaming DXF Parser
────────────────────────────────────────────────────────────────────────────
☐ Implement stream_dxf_entities() generator
☐ Replace bulk load with streaming
☐ Test memory usage improvement

Phase 6: Configuration System
────────────────────────────────────────────────────────────────────────────
☐ Create conversion_config.json
☐ Load config in dxf_to_database.py
☐ Add CLI arguments for common settings

Phase 7: Testing & Validation
────────────────────────────────────────────────────────────────────────────
☐ Test interruption at various points
☐ Test resume accuracy (data matches expected)
☐ Test memory management with large files
☐ Load testing (100K, 1M, 10M entities)

=============================================================================
ADVANCED FEATURES (Post-MVP)
=============================================================================

1. PARALLEL PROCESSING
   - Split DXF into chunks
   - Process chunks in parallel (multiprocessing)
   - Merge results at end
   - Speedup: 4-8x on multi-core systems

2. PROGRESS WEBHOOKS
   - Send progress updates to external system
   - Useful for web UI or monitoring dashboard
   - POST to webhook URL every N batches

3. CLOUD CHECKPOINTING
   - Save checkpoints to cloud storage
   - Enable cross-machine resumption
   - Disaster recovery (local machine fails)

4. SMART BATCH SIZING
   - Dynamically adjust batch size based on:
     * Memory availability
     * Entity complexity
     * Processing speed
   - Start with large batches, reduce if memory pressure

5. ENTITY TYPE PRIORITIZATION
   - Process critical elements first (walls, structure)
   - MEP elements later (can fail without blocking)
   - Allows partial results to be useful

=============================================================================
FAILURE MODES & RECOVERY
=============================================================================

SCENARIO 1: Out of Memory
────────────────────────────────────────────────────────────────────────────
Detection: Monitor memory usage with psutil
Response:
  1. Force garbage collection
  2. Reduce batch size dynamically
  3. If still OOM: Pause, log checkpoint, exit gracefully
  4. User can resume with smaller batch size

SCENARIO 2: Database Lock Timeout
────────────────────────────────────────────────────────────────────────────
Detection: sqlite3.OperationalError: database is locked
Response:
  1. Retry with exponential backoff (1s, 2s, 4s, 8s)
  2. If 5 retries fail: Pause, log checkpoint
  3. User can resume when lock is released

SCENARIO 3: Power Failure / System Crash
────────────────────────────────────────────────────────────────────────────
Detection: Presence of _conversion_progress table on restart
Response:
  1. Automatic detection on next run
  2. Prompt user to resume
  3. Resume from last committed batch

SCENARIO 4: Corrupted DXF File
────────────────────────────────────────────────────────────────────────────
Detection: ezdxf parsing exception
Response:
  1. Log error with entity ID
  2. Skip problematic entity
  3. Continue processing
  4. Generate error report at end

SCENARIO 5: Template Matching Failures
────────────────────────────────────────────────────────────────────────────
Detection: No template matches for entity
Response:
  1. Increment skip counter
  2. Log unmatched entity (layer, type, block name)
  3. Continue processing
  4. Generate match rate report at end

=============================================================================
PERFORMANCE BENCHMARKS (Target)
=============================================================================

Small DXF (10K entities):
  Processing time: ~2 minutes
  Memory usage: <500 MB
  Checkpoint overhead: <5%

Medium DXF (100K entities):
  Processing time: ~20 minutes
  Memory usage: <1 GB
  Checkpoint overhead: <3%

Large DXF (1M entities):
  Processing time: ~3 hours
  Memory usage: <2 GB (with streaming + caching)
  Checkpoint overhead: <2%

Resume overhead:
  Detection: <1 second
  Resume from 50% progress: ~5 seconds

=============================================================================
INTEGRATION WITH TEMPLATE CONFIGURATOR
=============================================================================

The Template Configurator (future Phase 3+) can use progress data:

1. CONVERSION MONITORING TAB
   - Show live progress of active conversions
   - Display entity counts, match rates, memory usage
   - Estimate time remaining

2. HISTORY VIEW
   - List all past conversions
   - Show success/failure rates
   - Identify problematic entity types

3. TEMPLATE EFFECTIVENESS METRICS
   - Track which templates match frequently vs rarely
   - Suggest template improvements based on skip patterns
   - Show correlation: template changes → match rate improvements

=============================================================================
CONCLUSION
=============================================================================

Crash resilience is CRITICAL for production use. Key takeaways:

✅ Batch processing with frequent commits (every 1000 entities)
✅ Progress tracking in temporary database table
✅ Automatic detection and resumption of interrupted conversions
✅ Memory management with streaming, caching, and GC
✅ Configurable parameters for different hardware/use cases

Build incrementally:
  Phase 1 POC: No resilience (acceptable for small test files)
  Phase 2: Add batch processing + progress tracking
  Phase 3: Add resumption capability
  Phase 4: Add memory management

Start simple, enhance based on real-world testing.

=============================================================================
DOCUMENT STATUS
=============================================================================

Status: DESIGN SPECIFICATION
Implementation: Post-POC (after basic conversion works)
Priority: HIGH (required for production use)
Owner: TBD

=============================================================================
REFERENCES
=============================================================================

Related Documents:
- CURRENT_APPROACH.md - Overall conversion strategy
- TEMPLATE_CONFIGURATOR_DESIGN.md - UI integration points
- dxf_to_database.py - Implementation file to modify

=============================================================================
LAST UPDATED: 2025-11-12
=============================================================================
