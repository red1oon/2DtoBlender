#!/usr/bin/env python3
"""
Enhanced Primitive Extractor - Exhaustive Multi-Method Extraction

Enhancements over primitive_extractor.py:
1. Multiple text extraction methods (standard, layout, font-filtered)
2. Targeted area extraction for buried/occluded text
3. Page-specific extraction masks (avoid duplicates)
4. Bilingual label support (English/Malay)
5. Fragment reconstruction (combines "BILIK" + "1" → "BILIK 1")
"""

import pdfplumber
import json
import sqlite3
from datetime import datetime
from pathlib import Path


# ============================================================================
# PAGE-SPECIFIC EXTRACTION MASKS
# ============================================================================
PAGE_EXTRACTION_RULES = {
    1: {  # Floor Plan
        "extract": ["room_labels", "doors", "windows", "walls", "furniture"],
        "skip_symbols": [],  # Extract all for now, will filter later
        "priority": "structural"
    },
    2: {  # Electrical Plan
        "extract": ["electrical_symbols"],
        "skip_symbols": ["D1", "D2", "D3", "W1", "W2", "W3"],  # Duplicates from page 1
        "priority": "electrical"
    },
    3: {  # Roof Plan
        "extract": ["roof_elements"],
        "skip_symbols": [],
        "priority": "roof"
    },
    # Pages 4-7: Elevations
    # Page 8: Legend/Details
}

# ============================================================================
# BILINGUAL ROOM LABEL VOCABULARY
# ============================================================================
ROOM_LABELS_BILINGUAL = {
    # English
    'LIVING ROOM': ('living_room', None),
    'LIVING': ('living_room', None),
    'KITCHEN': ('kitchen', None),
    'DINING ROOM': ('dining_room', None),
    'DINING': ('dining_room', None),
    'MASTER BEDROOM': ('bedroom', 'master'),
    'BEDROOM 1': ('bedroom', 'bedroom_1'),
    'BEDROOM 2': ('bedroom', 'bedroom_2'),
    'BEDROOM 3': ('bedroom', 'bedroom_3'),
    'BEDROOM': ('bedroom', None),
    'BATHROOM': ('washroom', None),
    'TOILET': ('washroom', None),
    'UTILITY': ('utility_room', None),
    'WASH ROOM': ('utility_room', None),

    # Malay
    'RUANG TAMU': ('living_room', None),
    'DAPUR': ('kitchen', None),
    'RUANG MAKAN': ('dining_room', None),
    'BILIK UTAMA': ('bedroom', 'master'),
    'BILIK 1': ('bedroom', 'bedroom_1'),
    'BILIK 2': ('bedroom', 'bedroom_2'),
    'BILIK 3': ('bedroom', 'bedroom_3'),
    'BILIK TIDUR': ('bedroom', None),
    'BILIK': ('bedroom', None),
    'BILIK MANDI': ('washroom', None),
    'TANDAS': ('washroom', None),
    'RUANG BASUH': ('utility_room', None),
}

# ============================================================================
# TARGETED EXTRACTION AREAS (for buried text)
# ============================================================================
TARGETED_SEARCH_AREAS = {
    1: {  # Page 1 - Floor Plan
        'BILIK_1_area': {
            'bbox': (380, 200, 420, 350),  # Based on BILIK 2 (393,290), BILIK 3 (393,376)
            'target_label': 'BILIK 1',
            'reason': 'Missing from standard extraction - likely buried under furniture'
        }
    }
}


class EnhancedPrimitiveExtractor:
    """
    Exhaustive primitive extraction with multiple methods and validation
    """

    def __init__(self, db_path):
        """Initialize with SQLite database path"""
        self.db_path = db_path
        self.conn = None
        self.extraction_stats = {
            'methods_used': [],
            'labels_found': [],
            'labels_reconstructed': [],
            'labels_targeted': [],
            'duplicates_removed': 0
        }

    def _create_tables(self, cursor):
        """Create database schema if tables don't exist"""
        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Text primitives
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS primitives_text (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER,
                text TEXT,
                x REAL,
                y REAL,
                x0 REAL,
                y0 REAL,
                x1 REAL,
                y1 REAL,
                fontname TEXT,
                size REAL,
                method TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_text_page ON primitives_text(page)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_text_xy ON primitives_text(x, y)")

        # Line primitives
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS primitives_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER,
                x0 REAL,
                y0 REAL,
                x1 REAL,
                y1 REAL,
                linewidth REAL,
                length REAL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lines_page ON primitives_lines(page)")

        # Curve primitives
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS primitives_curves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER,
                x0 REAL,
                y0 REAL,
                x1 REAL,
                y1 REAL,
                pts_json TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_curves_page ON primitives_curves(page)")

        # Rectangle primitives
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS primitives_rects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER,
                x0 REAL,
                y0 REAL,
                x1 REAL,
                y1 REAL,
                width REAL,
                height REAL,
                area REAL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rects_page ON primitives_rects(page)")

        # Page dimensions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_dimensions (
                page INTEGER PRIMARY KEY,
                width REAL,
                height REAL
            )
        """)

        # Context dimensions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_dimensions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER,
                x REAL,
                y REAL,
                text TEXT,
                dimension_type TEXT
            )
        """)

    def extract_to_database(self, pdf_path):
        """
        Extract ALL primitives to SQLite database
        Using multiple methods for exhaustiveness
        """
        print(f"=" * 80)
        print(f"ENHANCED PRIMITIVE EXTRACTION")
        print(f"=" * 80)
        print(f"PDF: {pdf_path}")
        print(f"Database: {self.db_path}")
        print()

        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        # Create tables if they don't exist
        print("Initializing database schema...")
        self._create_tables(cursor)

        # Clear existing primitives (fresh extraction)
        print("Clearing existing primitives...")
        cursor.execute("DELETE FROM primitives_text")
        cursor.execute("DELETE FROM primitives_lines")
        cursor.execute("DELETE FROM primitives_curves")
        cursor.execute("DELETE FROM primitives_rects")
        self.conn.commit()

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Total pages: {total_pages}")
            print()

            for page_num, page in enumerate(pdf.pages, 1):
                print(f"Processing Page {page_num}/{total_pages}...")

                # Extract primitives with multiple methods
                self._extract_page_exhaustive(page, page_num, cursor)

                print()

        # Post-processing: Remove duplicates
        print("Post-processing: Removing duplicates...")
        self._remove_duplicates(cursor)

        # Update metadata
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value) VALUES
            ('extraction_method', 'enhanced_multi_method'),
            ('extracted_at', ?),
            ('pdf_source', ?)
        """, (datetime.now().isoformat(), pdf_path))

        self.conn.commit()

        # Print statistics
        self._print_extraction_stats(cursor)

        self.conn.close()
        print()
        print(f"✅ Extraction complete!")

    def _extract_page_exhaustive(self, page, page_num, cursor):
        """
        Extract from single page using ALL methods
        """
        all_text_items = []

        # Method 1: Standard extraction
        print(f"  Method 1: Standard extraction...")
        words_standard = page.extract_words()
        for word in words_standard:
            all_text_items.append({
                'text': word['text'],
                'x': word['x0'],
                'y': word['top'],
                'bbox': (word['x0'], word['top'], word['x1'], word['bottom']),
                'method': 'standard',
                'confidence': 0.95
            })
        print(f"    Found: {len(words_standard)} text items")

        # Method 2: Layout-preserving extraction (SKIP if not supported)
        print(f"  Method 2: Layout-preserving extraction...")
        print(f"    Skipped (not supported in pdfplumber 0.11.8)")

        # Method 3: Font-filtered extraction (architectural labels)
        print(f"  Method 3: Font-filtered extraction...")
        try:
            words_fonts = page.extract_words(extra_attrs=['fontname', 'size'])
            # Filter for architectural label fonts (typically 10-14pt)
            words_filtered = [w for w in words_fonts if w.get('size', 0) >= 10]
            font_new = 0
            for word in words_filtered:
                if not self._is_duplicate_text(word['text'], word['x0'], word['top'], all_text_items):
                    all_text_items.append({
                        'text': word['text'],
                        'x': word['x0'],
                        'y': word['top'],
                        'bbox': (word['x0'], word['top'], word['x1'], word['bottom']),
                        'method': 'font_filtered',
                        'confidence': 0.92,
                        'font_size': word.get('size', 0)
                    })
                    font_new += 1
            print(f"    Found: {font_new} new text items (font size >= 10pt)")
        except Exception as e:
            print(f"    Warning: Font-filtered extraction failed: {e}")

        # Method 4: Annotation extraction (AutoCAD SHX)
        print(f"  Method 4: Annotation extraction...")
        annots = page.annots if hasattr(page, 'annots') else []
        annot_count = 0
        for annot in annots:
            contents = annot.get('contents', '')
            if contents:
                # Try multiple ways to get coordinates
                x, y, x1, y1 = 0, 0, 0, 0

                # Method 1: Try rect field (most common)
                if 'rect' in annot and annot['rect']:
                    rect = annot['rect']
                    if len(rect) >= 4:
                        x, y, x1, y1 = rect[0], rect[1], rect[2], rect[3]

                # Method 2: Try x0/y0/x1/y1 fields (AutoCAD format)
                if x == 0 and y == 0:
                    x = annot.get('x0', 0)
                    y = annot.get('y0', 0)
                    x1 = annot.get('x1', x)
                    y1 = annot.get('y1', y)

                # Method 3: Try page coordinates if available
                if x == 0 and y == 0 and 'page_x' in annot:
                    x = annot.get('page_x', 0)
                    y = annot.get('page_y', 0)
                    x1 = x + 50  # Default width
                    y1 = y + 10  # Default height
                if not self._is_duplicate_text(contents, x, y, all_text_items):
                    all_text_items.append({
                        'text': contents,
                        'x': x,
                        'y': y,
                        'bbox': (x, y, x1, y1),
                        'method': 'annotation',
                        'confidence': 0.95
                    })
                    annot_count += 1
        print(f"    Found: {annot_count} annotation text items")

        # Method 5: Targeted area extraction (for missing labels)
        if page_num in TARGETED_SEARCH_AREAS:
            print(f"  Method 5: Targeted area extraction...")
            for area_name, area_config in TARGETED_SEARCH_AREAS[page_num].items():
                bbox = area_config['bbox']
                target = area_config['target_label']
                print(f"    Searching for '{target}' in {bbox}...")

                cropped = page.crop(bbox)
                words_targeted = cropped.extract_words()
                targeted_found = 0
                for word in words_targeted:
                    # Adjust coordinates back to full page
                    abs_x = word['x0']
                    abs_y = word['top']
                    if not self._is_duplicate_text(word['text'], abs_x, abs_y, all_text_items):
                        all_text_items.append({
                            'text': word['text'],
                            'x': abs_x,
                            'y': abs_y,
                            'bbox': (abs_x, abs_y, word['x1'], word['bottom']),
                            'method': 'targeted',
                            'confidence': 0.85,
                            'target_area': area_name
                        })
                        targeted_found += 1
                        if target in word['text']:
                            print(f"      ✅ FOUND: '{word['text']}' at ({abs_x:.1f}, {abs_y:.1f})")
                print(f"    Found: {targeted_found} text items in targeted area")

        # Method 6: Fragment reconstruction (combine "BILIK" + "1")
        print(f"  Method 6: Fragment reconstruction...")
        reconstructed = self._reconstruct_fragments(all_text_items)
        if reconstructed:
            print(f"    Reconstructed: {len(reconstructed)} labels")
            for item in reconstructed:
                all_text_items.append(item)
                print(f"      '{item['text']}' at ({item['x']:.1f}, {item['y']:.1f})")

        # Store all text in database
        print(f"  Storing {len(all_text_items)} text primitives to database...")
        for idx, item in enumerate(all_text_items):
            bbox = item['bbox']
            cursor.execute("""
                INSERT INTO primitives_text (page, text, x, y, x0, y0, x1, y1)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                page_num,
                item['text'],
                item['x'],
                item['y'],
                bbox[0], bbox[1], bbox[2], bbox[3]
            ))

        # Extract other primitives (lines, curves, rects) - use standard method
        # (These are less prone to occlusion issues)
        self._extract_geometric_primitives(page, page_num, cursor)

        self.conn.commit()

    def _is_duplicate_text(self, text, x, y, existing_items, tolerance=5.0):
        """Check if text already exists at similar position"""
        for item in existing_items:
            if item['text'] == text:
                dx = abs(item['x'] - x)
                dy = abs(item['y'] - y)
                if dx < tolerance and dy < tolerance:
                    return True
        return False

    def _reconstruct_fragments(self, text_items):
        """
        Reconstruct fragmented labels like "BILIK" + "1" → "BILIK 1"
        """
        reconstructed = []

        # Find potential prefixes (BILIK, RUANG, BEDROOM)
        prefixes = [item for item in text_items if item['text'] in ['BILIK', 'RUANG', 'BEDROOM']]

        # Find potential suffixes (numbers, TAMU, MAKAN, etc.)
        suffixes = [item for item in text_items if item['text'] in ['1', '2', '3', 'TAMU', 'MAKAN', 'MANDI', 'BASUH', 'UTAMA']]

        for prefix in prefixes:
            for suffix in suffixes:
                # Check if on same Y-coordinate (±5pt) and nearby X (within 50pt)
                dy = abs(prefix['y'] - suffix['y'])
                dx = abs(prefix['x'] - suffix['x'])

                if dy < 5.0 and 0 < dx < 50:
                    # Combine fragments
                    combined_text = f"{prefix['text']} {suffix['text']}"

                    # Check if this is a valid room label
                    if combined_text in ROOM_LABELS_BILINGUAL:
                        # Use prefix position as anchor
                        reconstructed.append({
                            'text': combined_text,
                            'x': prefix['x'],
                            'y': prefix['y'],
                            'bbox': (prefix['bbox'][0], prefix['bbox'][1], suffix['bbox'][2], suffix['bbox'][3]),
                            'method': 'reconstructed',
                            'confidence': 0.80,
                            'fragments': [prefix['text'], suffix['text']]
                        })

        return reconstructed

    def _extract_geometric_primitives(self, page, page_num, cursor):
        """Extract lines, curves, rectangles (standard method)"""

        # Lines
        lines = page.lines if hasattr(page, 'lines') else []
        for idx, line in enumerate(lines):
            length = ((line['x1'] - line['x0'])**2 + (line['y1'] - line['y0'])**2)**0.5
            if length > 5.0:  # Filter very short lines
                cursor.execute("""
                    INSERT INTO primitives_lines (page, x0, y0, x1, y1, linewidth, length)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    page_num,
                    line['x0'], line['y0'],
                    line['x1'], line['y1'],
                    line.get('linewidth', 1.0),
                    length
                ))

        # Curves
        curves = page.curves if hasattr(page, 'curves') else []
        for curve in curves:
            pts = curve.get('pts', [])
            if pts:
                cursor.execute("""
                    INSERT INTO primitives_curves (page, x0, y0, x1, y1, pts_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    page_num,
                    curve['x0'], curve['y0'],
                    curve['x1'], curve['y1'],
                    json.dumps(pts)
                ))

        # Rectangles
        rects = page.rects if hasattr(page, 'rects') else []
        for rect in rects:
            width = rect['x1'] - rect['x0']
            height = rect['y1'] - rect['y0']
            area = width * height
            if area > 10.0:  # Filter tiny rects
                cursor.execute("""
                    INSERT INTO primitives_rects (page, x0, y0, x1, y1, width, height, area)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    page_num,
                    rect['x0'], rect['y0'],
                    rect['x1'], rect['y1'],
                    width, height, area
                ))

    def _remove_duplicates(self, cursor):
        """Remove duplicate text primitives across pages (keep page 1 priority)"""

        # For door/window labels: Keep only from page 1
        priority_labels = ['D1', 'D2', 'D3', 'W1', 'W2', 'W3']
        for label in priority_labels:
            # Delete from other pages
            cursor.execute("""
                DELETE FROM primitives_text
                WHERE text = ? AND page != 1
            """, (label,))
            removed = cursor.rowcount
            if removed > 0:
                print(f"  Removed {removed} duplicate '{label}' from pages 2-8")
                self.extraction_stats['duplicates_removed'] += removed

    def _print_extraction_stats(self, cursor):
        """Print extraction statistics"""
        print()
        print(f"=" * 80)
        print(f"EXTRACTION STATISTICS")
        print(f"=" * 80)

        # Text primitives by page
        cursor.execute("""
            SELECT page, COUNT(*) as count
            FROM primitives_text
            GROUP BY page
            ORDER BY page
        """)
        print(f"\nText primitives by page:")
        for row in cursor.fetchall():
            print(f"  Page {row[0]}: {row[1]} items")

        # Total counts
        cursor.execute("SELECT COUNT(*) FROM primitives_text")
        text_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM primitives_lines")
        line_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM primitives_curves")
        curve_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM primitives_rects")
        rect_count = cursor.fetchone()[0]

        print(f"\nTotal primitives:")
        print(f"  Text: {text_count}")
        print(f"  Lines: {line_count}")
        print(f"  Curves: {curve_count}")
        print(f"  Rectangles: {rect_count}")
        print(f"  TOTAL: {text_count + line_count + curve_count + rect_count}")

        # Room labels found
        cursor.execute("""
            SELECT text FROM primitives_text
            WHERE page=1
            AND (text LIKE '%RUANG%' OR text LIKE '%DAPUR%' OR text LIKE '%BILIK%')
            ORDER BY text
        """)
        room_labels = cursor.fetchall()
        print(f"\nRoom labels found (page 1): {len(room_labels)}")
        for label in room_labels:
            print(f"  ✓ {label[0]}")

        print(f"\nDuplicates removed: {self.extraction_stats['duplicates_removed']}")
        print(f"=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python3 primitive_extractor_enhanced.py <pdf_path> <database_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    db_path = sys.argv[2]

    extractor = EnhancedPrimitiveExtractor(db_path)
    extractor.extract_to_database(pdf_path)
