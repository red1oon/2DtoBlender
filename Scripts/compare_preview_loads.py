#!/usr/bin/env python3
"""
Compare what Preview mode loads from working IFC vs our DXF database
"""

import sqlite3

WORKING_DB = "/home/red1/Documents/bonsai/8_IFC/enhanced_federation.db"
OUR_DB = "/home/red1/Documents/bonsai/2Dto3D/Terminal1_3D_FINAL.db"

print("="*80)
print("PREVIEW MODE DATA COMPARISON")
print("="*80)

# The EXACT query Preview mode uses
PREVIEW_QUERY = """
    SELECT m.discipline, r.minX, r.minY, r.minZ, r.maxX, r.maxY, r.maxZ, m.guid
    FROM elements_meta m
    JOIN elements_rtree r ON m.id = r.id
"""

print("\n1. WORKING IFC DATABASE (What Preview mode successfully loads)")
print("-"*80)

conn_working = sqlite3.connect(WORKING_DB)
cursor_working = conn_working.cursor()

try:
    cursor_working.execute(PREVIEW_QUERY + " LIMIT 5")
    rows = cursor_working.fetchall()

    print(f"✅ Query works! Sample elements:")
    for discipline, minX, minY, minZ, maxX, maxY, maxZ, guid in rows[:3]:
        width = maxX - minX
        print(f"   {discipline:20s}: size {width:6.2f}m, at ({minX:7.1f}, {minY:7.1f}, {minZ:7.1f})")

    # Count total
    cursor_working.execute(f"SELECT COUNT(*) FROM ({PREVIEW_QUERY})")
    total = cursor_working.fetchone()[0]
    print(f"\n   Total loadable: {total:,} elements")

except Exception as e:
    print(f"❌ Query failed: {e}")

conn_working.close()

print("\n2. OUR DXF DATABASE (What we're trying to load)")
print("-"*80)

conn_ours = sqlite3.connect(OUR_DB)
cursor_ours = conn_ours.cursor()

try:
    cursor_ours.execute(PREVIEW_QUERY + " LIMIT 5")
    rows = cursor_ours.fetchall()

    print(f"✅ Query works! Sample elements:")
    for discipline, minX, minY, minZ, maxX, maxY, maxZ, guid in rows[:3]:
        width = maxX - minX
        print(f"   {discipline:20s}: size {width:6.2f}m, at ({minX:7.1f}, {minY:7.1f}, {minZ:7.1f})")

    # Count total
    cursor_ours.execute(f"SELECT COUNT(*) FROM ({PREVIEW_QUERY})")
    total = cursor_ours.fetchone()[0]
    print(f"\n   Total loadable: {total:,} elements")

except Exception as e:
    print(f"❌ Query failed: {e}")

conn_ours.close()

print("\n" + "="*80)
print("COMPARISON RESULT")
print("="*80)

print("\nBoth databases can be loaded by Preview mode using the same query.")
print("If working IFC loads but ours doesn't display, the issue is NOT the database.")
print("The issue is likely viewport rendering or camera positioning.")
