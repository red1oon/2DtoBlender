#!/usr/bin/env python3
"""
Minimal POC to test PDF extraction hypothesis
Objective: Understand why 31% of text has (0,0) coordinates
"""

import sqlite3
from pathlib import Path

def analyze_current_extraction():
    """Analyze what we currently have in the database"""

    db_path = Path("output_artifacts/TB-LKTN HOUSE_ANNOTATION_FROM_2D.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 70)
    print("CURRENT EXTRACTION ANALYSIS")
    print("=" * 70)

    # 1. Overall statistics
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN x = 0.0 AND y = 0.0 THEN 1 ELSE 0 END) as zero_coords,
            SUM(CASE WHEN x <> 0.0 OR y <> 0.0 THEN 1 ELSE 0 END) as valid_coords
        FROM primitives_text
    """)

    total, zero, valid = cursor.fetchone()
    print(f"\nText Statistics:")
    print(f"  Total items: {total}")
    print(f"  Valid coordinates: {valid} ({valid/total*100:.1f}%)")
    print(f"  Zero coordinates: {zero} ({zero/total*100:.1f}%)")

    # 2. Analyze patterns in zero coordinates
    print("\n Zero Coordinate Patterns:")
    cursor.execute("""
        SELECT text, COUNT(*) as count
        FROM primitives_text
        WHERE x = 0.0 AND y = 0.0
        AND length(text) < 20
        GROUP BY text
        ORDER BY count DESC
        LIMIT 15
    """)

    print("  Most common zero-coord texts:")
    for text, count in cursor.fetchall():
        print(f"    '{text}': {count} instances")

    # 3. Analyze valid coordinates
    print("\nValid Coordinate Patterns:")
    cursor.execute("""
        SELECT text, x, y
        FROM primitives_text
        WHERE x <> 0.0 AND y <> 0.0
        AND (text LIKE '%mm' OR text IN ('A','B','C','D','E') OR text LIKE 'W%' OR text LIKE 'D%')
        ORDER BY text
        LIMIT 15
    """)

    print("  Sample valid coordinates:")
    for text, x, y in cursor.fetchall():
        print(f"    '{text}': ({x:.2f}, {y:.2f})")

    # 4. Check for dimension annotations
    cursor.execute("""
        SELECT DISTINCT text
        FROM primitives_text
        WHERE text GLOB '[0-9]*'
        AND CAST(REPLACE(text, 'mm', '') AS INTEGER) BETWEEN 1000 AND 10000
        AND x = 0.0 AND y = 0.0
        ORDER BY CAST(REPLACE(text, 'mm', '') AS INTEGER)
    """)

    zero_dims = [row[0] for row in cursor.fetchall()]
    if zero_dims:
        print(f"\nDimensions with zero coordinates: {zero_dims}")
        print(f"  These are critical for calibration!")

    # 5. Hypothesis testing
    print("\n" + "=" * 70)
    print("HYPOTHESIS TEST")
    print("=" * 70)

    print("\n1. Text Type Analysis:")

    # Check if certain text patterns correlate with zero coords
    patterns = [
        ("Dimensions", "text GLOB '[0-9]*' AND length(text) = 4"),
        ("Grid labels", "text IN ('A','B','C','D','E','1','2','3','4','5')"),
        ("Room labels", "text LIKE '%ROOM%' OR text LIKE '%BILIK%'"),
        ("Door/Window", "text LIKE 'D[1-9]' OR text LIKE 'W[1-9]'"),
        ("Titles", "text LIKE '%. %'"),
        ("DISCHARGE", "text LIKE '%DISCHARGE%'")
    ]

    for name, condition in patterns:
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN x = 0.0 AND y = 0.0 THEN 1 ELSE 0 END) as zero
            FROM primitives_text
            WHERE {condition}
        """)
        total, zero = cursor.fetchone()
        if total > 0:
            print(f"  {name}: {zero}/{total} ({zero/total*100:.0f}%) have zero coords")

    # 6. Page distribution
    print("\n2. Page Distribution:")
    cursor.execute("""
        SELECT
            page,
            COUNT(*) as total,
            SUM(CASE WHEN x = 0.0 AND y = 0.0 THEN 1 ELSE 0 END) as zero
        FROM primitives_text
        GROUP BY page
        ORDER BY page
        LIMIT 5
    """)

    for page, total, zero in cursor.fetchall():
        print(f"  Page {page}: {zero}/{total} ({zero/total*100:.0f}%) have zero coords")

    conn.close()

    print("\n" + "=" * 70)
    print("CONCLUSIONS")
    print("=" * 70)

    print("""
The data shows:
1. Specific text types (dimensions, DISCHARGE) consistently have (0,0)
2. Regular labels (A, B, C, W3, D1) have valid coordinates
3. This suggests different extraction methods or PDF object types

Next step: Test different extraction methods to recover coordinates
""")

def test_extraction_methods():
    """Test different extraction approaches"""

    print("\n" + "=" * 70)
    print("EXTRACTION METHOD TESTING")
    print("=" * 70)

    print("""
Proposed extraction improvements:

1. For annotations (rect field):
   if 'rect' in annot:
       x, y = annot['rect'][0], annot['rect'][1]

2. For AutoCAD text (direct coordinates):
   x = annot.get('x', annot.get('x0', 0))
   y = annot.get('y', annot.get('y0', 0))

3. For embedded fonts (character extraction):
   chars = page.chars
   # Group chars into words by proximity

4. Validation:
   if x == 0 and y == 0 and text in CRITICAL_LABELS:
       # Try alternative extraction
       # Log warning
       # Mark as needs_review
""")

if __name__ == "__main__":
    analyze_current_extraction()
    test_extraction_methods()