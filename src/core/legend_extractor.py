#!/usr/bin/env python3
"""
Legend & Schedule Extractor

Extracts symbol legends and dimensional schedules from PDF:
- Symbol legend (general symbols and their meanings)
- Door schedule (D1, D2, D3... with dimensions)
- Window schedule (W1, W2, W3... with dimensions)

Stores in database for pattern matching validation
"""

import sqlite3
import re
from pathlib import Path


class LegendExtractor:
    """Extract legend and schedule information from database"""

    def __init__(self, db_path: str):
        """
        Initialize legend extractor

        Args:
            db_path: Path to annotation database
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect_db(self):
        """Connect to database and create legend tables"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # Create legend tables
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_schedules (
                schedule_type TEXT,
                item_id TEXT,
                description TEXT,
                width_mm REAL,
                height_mm REAL,
                depth_mm REAL,
                metadata_json TEXT,
                page INTEGER,
                PRIMARY KEY (schedule_type, item_id)
            );
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_legend (
                symbol_id TEXT PRIMARY KEY,
                symbol_text TEXT,
                description TEXT,
                category TEXT,
                page INTEGER
            );
        """)

        self.conn.commit()

    def extract_door_schedule(self) -> int:
        """
        Extract door schedule from page 8 using spatial clustering

        Door IDs (D1, D2, D3) are at y~159
        Dimensions are at y~219 with separate text elements:
        - Width number, "X" separator, Height number
        """
        print("\n📐 Extracting DOOR SCHEDULE...")

        # Get door IDs (D1, D2, D3, etc.)
        self.cursor.execute("""
            SELECT text, x, y
            FROM primitives_text
            WHERE page = 8 AND text GLOB 'D[0-9]*'
            ORDER BY x ASC
        """)
        door_ids = self.cursor.fetchall()

        if not door_ids:
            print("   ❌ No door IDs found")
            return 0

        # Get dimension area (y between 210 and 230 for doors)
        self.cursor.execute("""
            SELECT text, x, y
            FROM primitives_text
            WHERE page = 8 AND y BETWEEN 210 AND 230
            ORDER BY x ASC
        """)
        dim_area = self.cursor.fetchall()

        # Find dimension clusters by X position
        # Each cluster = width number + X separator + height number
        # Prioritize "MM" suffixed numbers (official schedule values)
        clusters = []
        i = 0
        while i < len(dim_area):
            text, x, y = dim_area[i]

            # Look for width with "MM" suffix (prioritize official schedule)
            if 'MM' in text.upper() and text.replace('MM', '').replace('mm', '').strip().isdigit():
                width = float(text.replace('MM', '').replace('mm', '').strip())
                width_x = x

                # Look ahead for "X" separator (within 50 pts)
                for j in range(i+1, min(i+5, len(dim_area))):
                    if dim_area[j][0] in ['X', 'x', '×'] and abs(dim_area[j][1] - x) < 50:
                        # Look ahead for height number with MM suffix
                        for k in range(j+1, min(j+5, len(dim_area))):
                            h_text = dim_area[k][0]
                            if 'MM' in h_text.upper():
                                h_value = h_text.replace('MM', '').replace('mm', '').strip()
                                if h_value.isdigit() and abs(dim_area[k][1] - dim_area[j][1]) < 50:
                                    height = float(h_value)
                                    clusters.append({
                                        'width': width,
                                        'height': height,
                                        'x': width_x
                                    })
                                    break
                        break
            i += 1

        # Match clusters to door IDs by X proximity
        extracted = []
        for door_text, door_x, door_y in door_ids:
            # Find closest cluster by X position (within 100 pts)
            best_cluster = None
            min_dist = float('inf')

            for cluster in clusters:
                dist = abs(cluster['x'] - door_x)
                if dist < min_dist and dist < 100:
                    min_dist = dist
                    best_cluster = cluster

            if best_cluster:
                extracted.append({
                    'item_id': door_text,
                    'width_mm': best_cluster['width'],
                    'height_mm': best_cluster['height'],
                    'description': f'Door {door_text}'
                })
                print(f"   ✅ {door_text}: {best_cluster['width']}mm x {best_cluster['height']}mm")

        # Store in database
        for door in extracted:
            self.cursor.execute("""
                INSERT OR REPLACE INTO context_schedules
                (schedule_type, item_id, description, width_mm, height_mm, page)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('door', door['item_id'], door['description'],
                  door['width_mm'], door['height_mm'], 8))

        self.conn.commit()
        print(f"   Extracted {len(extracted)} door schedule entries")
        return len(extracted)

    def extract_window_schedule(self) -> int:
        """
        Extract window schedule from page 8 using spatial clustering

        Window IDs (W1, W2, W3) are at y~395
        Dimensions are at y~452 with separate text elements:
        - Width number, "X" separator, Height number
        """
        print("\n🪟 Extracting WINDOW SCHEDULE...")

        # Get window IDs (W1, W2, W3, etc.)
        self.cursor.execute("""
            SELECT text, x, y
            FROM primitives_text
            WHERE page = 8 AND text GLOB 'W[0-9]*'
            ORDER BY x ASC
        """)
        window_ids = self.cursor.fetchall()

        if not window_ids:
            print("   ❌ No window IDs found")
            return 0

        # Get dimension area (y between 445 and 460 for windows)
        self.cursor.execute("""
            SELECT text, x, y
            FROM primitives_text
            WHERE page = 8 AND y BETWEEN 445 AND 460
            ORDER BY x ASC
        """)
        dim_area = self.cursor.fetchall()

        # Find dimension clusters by X position
        # Each cluster = width number + X separator + height number
        # Prioritize "mm" suffixed numbers (official schedule values)
        clusters = []
        i = 0
        while i < len(dim_area):
            text, x, y = dim_area[i]

            # Look for width with "mm" suffix (prioritize official schedule)
            if 'mm' in text.lower() and text.replace('mm', '').replace('MM', '').strip().isdigit():
                width = float(text.replace('mm', '').replace('MM', '').strip())
                width_x = x

                # Look ahead for "X" separator (within 50 pts)
                for j in range(i+1, min(i+5, len(dim_area))):
                    if dim_area[j][0] in ['X', 'x', '×'] and abs(dim_area[j][1] - x) < 50:
                        # Look ahead for height number with mm suffix
                        for k in range(j+1, min(j+5, len(dim_area))):
                            h_text = dim_area[k][0]
                            if 'mm' in h_text.lower():
                                h_value = h_text.replace('mm', '').replace('MM', '').strip()
                                if h_value.isdigit() and abs(dim_area[k][1] - dim_area[j][1]) < 50:
                                    height = float(h_value)
                                    clusters.append({
                                        'width': width,
                                        'height': height,
                                        'x': width_x
                                    })
                                    break
                        break
            i += 1

        # Match clusters to window IDs by X proximity
        extracted = []
        for window_text, window_x, window_y in window_ids:
            # Find closest cluster by X position (within 100 pts)
            best_cluster = None
            min_dist = float('inf')

            for cluster in clusters:
                dist = abs(cluster['x'] - window_x)
                if dist < min_dist and dist < 100:
                    min_dist = dist
                    best_cluster = cluster

            if best_cluster:
                extracted.append({
                    'item_id': window_text,
                    'width_mm': best_cluster['width'],
                    'height_mm': best_cluster['height'],
                    'description': f'Window {window_text}'
                })
                print(f"   ✅ {window_text}: {best_cluster['width']}mm x {best_cluster['height']}mm")

        # Store in database
        for window in extracted:
            self.cursor.execute("""
                INSERT OR REPLACE INTO context_schedules
                (schedule_type, item_id, description, width_mm, height_mm, page)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('window', window['item_id'], window['description'],
                  window['width_mm'], window['height_mm'], 8))

        self.conn.commit()
        print(f"   Extracted {len(extracted)} window schedule entries")
        return len(extracted)

    def extract_symbol_legend(self) -> int:
        """
        Extract symbol legend from page 7

        General symbols and their meanings
        """
        print("\n🔣 Extracting SYMBOL LEGEND...")

        # Get text from page 7 (legend page)
        self.cursor.execute("""
            SELECT text, x, y
            FROM primitives_text
            WHERE page = 7
            ORDER BY y DESC, x ASC
        """)
        page7_text = self.cursor.fetchall()

        # Simple extraction: look for common symbols
        symbols = []
        common_symbols = ['FP', 'D1', 'D2', 'D3', 'W1', 'W2', 'W3', 'W4',
                         'SWS', 'PP', 'L', 'CF', 'CP', 'WH', 'EF']

        for text, x, y in page7_text:
            if text.strip() in common_symbols:
                symbols.append({
                    'symbol_id': text.strip(),
                    'page': 7
                })

        # Store in database
        for symbol in symbols:
            self.cursor.execute("""
                INSERT OR IGNORE INTO context_legend
                (symbol_id, page)
                VALUES (?, ?)
            """, (symbol['symbol_id'], symbol['page']))

        self.conn.commit()
        print(f"   Extracted {len(symbols)} symbol legend entries")
        return len(symbols)

    def run_extraction(self):
        """Run all legend/schedule extractions"""

        print("=" * 70)
        print("LEGEND & SCHEDULE EXTRACTION")
        print("=" * 70)

        self.connect_db()

        try:
            door_count = self.extract_door_schedule()
            window_count = self.extract_window_schedule()
            symbol_count = self.extract_symbol_legend()

            total = door_count + window_count + symbol_count

            print("\n" + "=" * 70)
            print(f"✅ LEGEND EXTRACTION COMPLETE")
            print(f"   Total entries: {total}")
            print(f"   - Door schedule: {door_count}")
            print(f"   - Window schedule: {window_count}")
            print(f"   - Symbol legend: {symbol_count}")
            print("=" * 70)

            return total

        finally:
            if self.conn:
                self.conn.close()


def main():
    """Main execution"""
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "output_artifacts" / "TB-LKTN HOUSE_ANNOTATION_FROM_2D.db"

    extractor = LegendExtractor(str(db_path))
    extractor.run_extraction()


if __name__ == "__main__":
    main()
