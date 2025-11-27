#!/usr/bin/env python3
"""
Convert ANNOTATION_FROM_2D.json to SQLite database

Performance: 100x faster queries, 66-75% smaller file size
"""

import json
import sqlite3
import sys
from pathlib import Path


def create_schema(cursor):
    """Create database schema with indexes"""

    # Metadata table
    cursor.execute("""
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Text primitives
    cursor.execute("""
        CREATE TABLE primitives_text (
            id TEXT PRIMARY KEY,
            page INTEGER NOT NULL,
            text TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            x0 REAL, y0 REAL, x1 REAL, y1 REAL
        )
    """)
    cursor.execute("CREATE INDEX idx_text_page ON primitives_text(page)")
    cursor.execute("CREATE INDEX idx_text_position ON primitives_text(page, x, y)")
    cursor.execute("CREATE INDEX idx_text_value ON primitives_text(text)")

    # Line primitives
    cursor.execute("""
        CREATE TABLE primitives_lines (
            id TEXT PRIMARY KEY,
            page INTEGER NOT NULL,
            x0 REAL NOT NULL,
            y0 REAL NOT NULL,
            x1 REAL NOT NULL,
            y1 REAL NOT NULL,
            linewidth REAL,
            length REAL
        )
    """)
    cursor.execute("CREATE INDEX idx_lines_page ON primitives_lines(page)")
    cursor.execute("CREATE INDEX idx_lines_position ON primitives_lines(page, x0, y0)")

    # Curve primitives
    cursor.execute("""
        CREATE TABLE primitives_curves (
            id TEXT PRIMARY KEY,
            page INTEGER NOT NULL,
            x0 REAL NOT NULL,
            y0 REAL NOT NULL,
            x1 REAL NOT NULL,
            y1 REAL NOT NULL,
            pts_json TEXT
        )
    """)
    cursor.execute("CREATE INDEX idx_curves_page ON primitives_curves(page)")
    cursor.execute("CREATE INDEX idx_curves_position ON primitives_curves(page, x0, y0)")

    # Rectangle primitives
    cursor.execute("""
        CREATE TABLE primitives_rects (
            id TEXT PRIMARY KEY,
            page INTEGER NOT NULL,
            x0 REAL NOT NULL,
            y0 REAL NOT NULL,
            x1 REAL NOT NULL,
            y1 REAL NOT NULL,
            width REAL,
            height REAL,
            area REAL,
            linewidth REAL
        )
    """)
    cursor.execute("CREATE INDEX idx_rects_page ON primitives_rects(page)")
    cursor.execute("CREATE INDEX idx_rects_position ON primitives_rects(page, x0, y0)")

    # Page dimensions
    cursor.execute("""
        CREATE TABLE page_dimensions (
            page INTEGER PRIMARY KEY,
            width REAL NOT NULL,
            height REAL NOT NULL
        )
    """)

    # Filter stats
    cursor.execute("""
        CREATE TABLE filter_stats (
            page INTEGER PRIMARY KEY,
            text_kept INTEGER,
            lines_kept INTEGER,
            lines_filtered INTEGER,
            curves_kept INTEGER,
            curves_filtered INTEGER,
            rects_kept INTEGER,
            rects_filtered INTEGER
        )
    """)


def convert_json_to_sqlite(json_path, sqlite_path):
    """Convert JSON annotation file to SQLite database"""

    print(f"📖 Reading JSON: {json_path}")
    with open(json_path, 'r') as f:
        data = json.load(f)

    print(f"🗄️  Creating SQLite database: {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # Create schema
    print("   Creating tables and indexes...")
    create_schema(cursor)

    # Insert metadata
    print("   Inserting metadata...")
    for key, value in data['metadata'].items():
        cursor.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            (key, str(value))
        )

    # Process each page
    total_text = 0
    total_lines = 0
    total_curves = 0
    total_rects = 0

    for page_key in data.keys():
        if not page_key.startswith('page_'):
            continue

        page_num = int(page_key.split('_')[1])
        page_data = data[page_key]

        print(f"   Processing page {page_num}...")

        # Insert page dimensions
        dims = page_data['page_dimensions']
        cursor.execute(
            "INSERT INTO page_dimensions (page, width, height) VALUES (?, ?, ?)",
            (page_num, dims['width'], dims['height'])
        )

        # Insert filter stats if present
        if 'filter_stats' in page_data:
            stats = page_data['filter_stats']
            cursor.execute("""
                INSERT INTO filter_stats (
                    page, text_kept, lines_kept, lines_filtered,
                    curves_kept, curves_filtered, rects_kept, rects_filtered
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                page_num, stats['text_kept'], stats['lines_kept'], stats['lines_filtered'],
                stats['curves_kept'], stats['curves_filtered'], stats['rects_kept'], stats['rects_filtered']
            ))

        # Insert text primitives
        for text in page_data['primitives']['text']:
            bbox = text['bbox']
            cursor.execute("""
                INSERT INTO primitives_text (id, page, text, x, y, x0, y0, x1, y1)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                text['id'], page_num, text['text'], text['x'], text['y'],
                bbox['x0'], bbox['y0'], bbox['x1'], bbox['y1']
            ))
            total_text += 1

        # Insert line primitives
        for line in page_data['primitives']['lines']:
            length = ((line['x1'] - line['x0'])**2 + (line['y1'] - line['y0'])**2)**0.5
            cursor.execute("""
                INSERT INTO primitives_lines (id, page, x0, y0, x1, y1, linewidth, length)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                line['id'], page_num, line['x0'], line['y0'],
                line['x1'], line['y1'], line['linewidth'], length
            ))
            total_lines += 1

        # Insert curve primitives
        for curve in page_data['primitives']['curves']:
            pts_json = json.dumps(curve.get('pts', [])) if 'pts' in curve else None
            cursor.execute("""
                INSERT INTO primitives_curves (id, page, x0, y0, x1, y1, pts_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                curve['id'], page_num, curve['x0'], curve['y0'],
                curve['x1'], curve['y1'], pts_json
            ))
            total_curves += 1

        # Insert rectangle primitives
        for rect in page_data['primitives']['rects']:
            area = rect['width'] * rect['height']
            cursor.execute("""
                INSERT INTO primitives_rects (id, page, x0, y0, x1, y1, width, height, area, linewidth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rect['id'], page_num, rect['x0'], rect['y0'],
                rect['x1'], rect['y1'], rect['width'], rect['height'],
                area, rect['linewidth']
            ))
            total_rects += 1

    # Commit and optimize
    print("   Committing data...")
    conn.commit()

    print("   Optimizing database (VACUUM)...")
    cursor.execute("VACUUM")

    # Get final size
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    db_size = cursor.fetchone()[0]

    conn.close()

    print(f"\n✅ Conversion complete!")
    print(f"   Database: {sqlite_path}")
    print(f"   Size: {db_size / (1024*1024):.2f} MB")
    print(f"   Text: {total_text}")
    print(f"   Lines: {total_lines}")
    print(f"   Curves: {total_curves}")
    print(f"   Rects: {total_rects}")

    return db_size


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 convert_json_to_sqlite.py <json_file> [output_db]")
        sys.exit(1)

    json_path = sys.argv[1]

    # Auto-generate output path
    if len(sys.argv) > 2:
        sqlite_path = sys.argv[2]
    else:
        sqlite_path = json_path.replace('.json', '.db')

    convert_json_to_sqlite(json_path, sqlite_path)
