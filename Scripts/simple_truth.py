#!/usr/bin/env python3
"""
The Simple Truth - One query to prove if Preview mode should work
"""

import sqlite3

DB_PATH = "/home/red1/Documents/bonsai/2Dto3D/Terminal1_3D_FINAL.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# The EXACT query that Preview mode uses
cursor.execute("""
    SELECT m.discipline, r.minX, r.minY, r.minZ, r.maxX, r.maxY, r.maxZ, m.guid
    FROM elements_meta m
    JOIN elements_rtree r ON m.id = r.id
    LIMIT 1
""")

row = cursor.fetchone()

if row:
    discipline, minX, minY, minZ, maxX, maxY, maxZ, guid = row
    width = maxX - minX
    print(f"✅ THE QUERY WORKS")
    print(f"   Element: {discipline}")
    print(f"   BBox: ({minX:.1f}, {minY:.1f}, {minZ:.1f}) to ({maxX:.1f}, {maxY:.1f}, {maxZ:.1f})")
    print(f"   Size: {width:.1f}m wide")
    print(f"\n   This element WILL render in Preview mode.")
else:
    print(f"❌ THE QUERY FAILS")
    print(f"   Preview mode will NOT work.")

conn.close()
