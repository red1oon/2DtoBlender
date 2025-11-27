#!/usr/bin/env python3
"""
Cheat-Sheet Text Classifier (From DeepSeek POC)
================================================
Classifies extracted text using pattern matching.
NO AI/ML - pure deterministic pattern recognition (Rule 0 compliant).

Based on poc_pipeline.py lines 86-323.
"""

import re
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional


# Cheat sheet patterns (from poc_pipeline.py:89-101)
CHEAT_SHEET = {
    "grid_horizontal": ["A", "B", "C", "D", "E"],
    "grid_vertical": ["1", "2", "3", "4", "5"],
    "dimensions_mm": [500, 600, 750, 900, 1000, 1200, 1300, 1500, 1600, 1800, 2100, 2300, 3100, 3700],
    "markers": ["DISCHARGE", "FFL", "CEILING", "LINTEL", "SILL", "GRD", "FLOOR PLAN", "ELEVATION", "ROOF", "NTS", "SECTION"],
    "door_codes": ["D1", "D2", "D3"],
    "window_codes": ["W1", "W2", "W3", "W4"],
    "room_names_malay": [
        "RUANG TAMU", "DAPUR", "BILIK UTAMA", "BILIK 2", "BILIK 3",
        "BILIK MANDI", "TANDAS", "RUANG BASUH", "CORRIDOR", "OUTDOOR"
    ],
    "plumbing": ["WC", "SINK", "BASIN", "TAP", "SEPTIC", "MH1", "FD", "FLOOR DRAIN"],
    "electrical": ["FP1", "FP", "LC", "SW", "SP"],
    "furniture": ["BED", "KATIL", "WARDROBE", "ALMARI", "SOFA", "MEJA", "TABLE"],
}


class CheatSheetClassifier:
    """
    Classify text tokens using deterministic pattern matching.
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """Create classification results table"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS classified_text (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER NOT NULL,
                token TEXT NOT NULL,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL NOT NULL,
                classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_classified_category ON classified_text(category)
        """)

        self.conn.commit()

    def classify_token(self, token: str) -> List[Dict]:
        """
        Classify a single token against cheat sheet patterns.
        Based on poc_pipeline.py:255-323
        """
        upper = token.upper().strip()
        classifications = []

        # Grid labels
        if upper in CHEAT_SHEET["grid_horizontal"]:
            classifications.append({
                "category": "grid_h",
                "value": upper,
                "confidence": 1.0
            })

        if upper in CHEAT_SHEET["grid_vertical"]:
            classifications.append({
                "category": "grid_v",
                "value": upper,
                "confidence": 1.0
            })

        # Door/window codes
        if upper in CHEAT_SHEET["door_codes"]:
            classifications.append({
                "category": "door",
                "value": upper,
                "confidence": 1.0
            })

        if upper in CHEAT_SHEET["window_codes"]:
            classifications.append({
                "category": "window",
                "value": upper,
                "confidence": 1.0
            })

        # Dimensions
        dim_match = re.match(r'^(\d{3,4})(MM)?$', upper)
        if dim_match:
            num = int(dim_match.group(1))
            cat = "dimension_known" if num in CHEAT_SHEET["dimensions_mm"] else "dimension_unknown"
            classifications.append({
                "category": cat,
                "value": str(num),
                "confidence": 0.9 if cat == "dimension_known" else 0.6
            })

        # Size pattern (WxH)
        size_match = re.search(r'(\d{3,4})MM?\s*X\s*(\d{3,4})MM?', upper)
        if size_match:
            w, h = int(size_match.group(1)), int(size_match.group(2))
            classifications.append({
                "category": "size_wxh",
                "value": json.dumps({"width": w, "height": h}),
                "confidence": 1.0
            })

        # Room names
        for room in CHEAT_SHEET["room_names_malay"]:
            if room in upper or upper in room.split():
                classifications.append({
                    "category": "room",
                    "value": room,
                    "confidence": 0.9
                })
                break

        # Markers
        for marker in CHEAT_SHEET["markers"]:
            if marker in upper:
                classifications.append({
                    "category": "marker",
                    "value": marker,
                    "confidence": 1.0
                })
                break

        # Plumbing
        for plumb in CHEAT_SHEET["plumbing"]:
            if plumb in upper:
                classifications.append({
                    "category": "plumbing",
                    "value": plumb,
                    "confidence": 0.9
                })
                break

        # Electrical
        for elec in CHEAT_SHEET["electrical"]:
            if elec in upper:
                classifications.append({
                    "category": "electrical",
                    "value": elec,
                    "confidence": 0.9
                })
                break

        # Furniture
        for furn in CHEAT_SHEET["furniture"]:
            if furn in upper:
                classifications.append({
                    "category": "furniture",
                    "value": furn,
                    "confidence": 0.8
                })
                break

        # Scale notation
        if re.search(r'1\s*:\s*100', token):
            classifications.append({
                "category": "scale",
                "value": "1:100",
                "confidence": 1.0
            })

        # Quantity (N NOS)
        qty_match = re.search(r'(\d+)\s*NOS', upper)
        if qty_match:
            classifications.append({
                "category": "quantity",
                "value": str(int(qty_match.group(1))),
                "confidence": 1.0
            })

        # Angle (roof)
        angle_match = re.search(r'(\d+)°', token)
        if angle_match:
            classifications.append({
                "category": "angle",
                "value": str(int(angle_match.group(1))),
                "confidence": 1.0
            })

        return classifications

    def classify_all(self, source_db: str):
        """
        Classify all text from source database.
        """
        source_conn = sqlite3.connect(source_db)
        source_cursor = source_conn.cursor()

        # Get all extracted text
        source_cursor.execute("""
            SELECT page, text
            FROM extracted_text
            WHERE text != ''
        """)

        stats = {
            "total_tokens": 0,
            "classified_tokens": 0,
            "by_category": {}
        }

        for page, token in source_cursor.fetchall():
            stats["total_tokens"] += 1
            classifications = self.classify_token(token)

            if classifications:
                stats["classified_tokens"] += 1

                for cls in classifications:
                    self.cursor.execute("""
                        INSERT INTO classified_text (page, token, category, value, confidence)
                        VALUES (?, ?, ?, ?, ?)
                    """, (page, token, cls["category"], cls["value"], cls["confidence"]))

                    # Update stats
                    cat = cls["category"]
                    stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        self.conn.commit()
        source_conn.close()

        return stats

    def get_by_category(self, category: str) -> List[Dict]:
        """Get all items of a specific category"""
        self.cursor.execute("""
            SELECT DISTINCT token, value, confidence
            FROM classified_text
            WHERE category = ?
            ORDER BY value
        """, (category,))

        return [
            {"token": row[0], "value": row[1], "confidence": row[2]}
            for row in self.cursor.fetchall()
        ]

    def get_summary(self) -> Dict:
        """Get classification summary"""
        self.cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM classified_text
            GROUP BY category
            ORDER BY count DESC
        """)

        return {row[0]: row[1] for row in self.cursor.fetchall()}

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test classification"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 cheatsheet_classifier.py <source_db>")
        sys.exit(1)

    source_db = sys.argv[1]
    output_db = "output_artifacts/classified_text.db"

    print("=" * 70)
    print("CHEAT-SHEET TEXT CLASSIFICATION")
    print("=" * 70)
    print(f"Source: {source_db}")
    print(f"Output: {output_db}")
    print()

    classifier = CheatSheetClassifier(output_db)

    print("Classifying tokens...")
    stats = classifier.classify_all(source_db)

    print("\n" + "=" * 70)
    print("CLASSIFICATION COMPLETE")
    print("=" * 70)
    print(f"Total tokens: {stats['total_tokens']}")
    print(f"Classified: {stats['classified_tokens']} ({stats['classified_tokens']/stats['total_tokens']*100:.1f}%)")
    print(f"\nBy category:")

    summary = classifier.get_summary()
    for cat, count in sorted(summary.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

    # Show samples
    print("\nSample classifications:")
    for cat in ["grid_h", "grid_v", "door", "window", "room"]:
        items = classifier.get_by_category(cat)[:5]
        if items:
            print(f"\n  {cat}:")
            for item in items:
                print(f"    '{item['token']}' → {item['value']} (conf: {item['confidence']})")

    print(f"\n✓ Saved to {output_db}")
    print("=" * 70)

    classifier.close()


if __name__ == "__main__":
    main()
