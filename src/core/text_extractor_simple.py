#!/usr/bin/env python3
"""
Simple Text-Only PDF Extractor (Based on DeepSeek POC)
======================================================
Extracts ONLY text content from PDF, no coordinates.
Follows expert's proven approach: text extraction → classification → coordinate generation.

CRITICAL INSIGHT:
  OCR cannot reliably extract dimension line coordinates from PDF annotations.
  Use GridTruth for dimensions instead.
"""

import sqlite3
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional


class SimpleTextExtractor:
    """
    Minimal text extractor - no coordinate extraction.
    Based on DeepSeek POC proven methodology.
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """Create simple text storage table"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_text (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page INTEGER NOT NULL,
                text TEXT NOT NULL,
                text_type TEXT,
                confidence REAL,

                -- Metadata only (no coordinates needed)
                font_name TEXT,
                font_size REAL,
                extraction_method TEXT DEFAULT 'pdfplumber_text',

                -- Timestamps
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_text_page ON extracted_text(page)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_text_type ON extracted_text(text_type)
        """)

        self.conn.commit()

    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        Extract text from PDF using simple pdfplumber.

        NO coordinate extraction - follows expert POC approach.
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        stats = {
            "pages_processed": 0,
            "text_items_extracted": 0,
            "errors": []
        }

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    # Method 1: Extract as plain text
                    text = page.extract_text()

                    if text:
                        # Split into lines
                        lines = [line.strip() for line in text.split('\n') if line.strip()]

                        for line in lines:
                            self.cursor.execute("""
                                INSERT INTO extracted_text (page, text, extraction_method)
                                VALUES (?, ?, ?)
                            """, (page_num, line, 'pdfplumber_text'))
                            stats["text_items_extracted"] += 1

                    # Method 2: Also try extract_words for richer metadata
                    try:
                        words = page.extract_words()
                        for word in words:
                            # Store unique text with font info
                            self.cursor.execute("""
                                INSERT INTO extracted_text
                                (page, text, font_name, font_size, extraction_method)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                page_num,
                                word.get('text', ''),
                                word.get('fontname', ''),
                                word.get('height', 0.0),
                                'pdfplumber_words'
                            ))
                            stats["text_items_extracted"] += 1
                    except Exception as e:
                        stats["errors"].append(f"Page {page_num} words extraction: {e}")

                    # Method 3: Extract annotations (AutoCAD dimensions often here!)
                    try:
                        if hasattr(page, 'annots') and page.annots:
                            for annot in page.annots:
                                contents = annot.get('contents', '')
                                if contents and contents.strip():
                                    self.cursor.execute("""
                                        INSERT INTO extracted_text
                                        (page, text, text_type, extraction_method)
                                        VALUES (?, ?, ?, ?)
                                    """, (page_num, contents, 'annotation', 'pdfplumber_annots'))
                                    stats["text_items_extracted"] += 1
                    except Exception as e:
                        stats["errors"].append(f"Page {page_num} annotation extraction: {e}")

                    stats["pages_processed"] += 1

                except Exception as e:
                    stats["errors"].append(f"Page {page_num}: {e}")

        self.conn.commit()
        return stats

    def get_all_text(self, page: Optional[int] = None) -> List[Dict]:
        """Retrieve extracted text, optionally filtered by page"""
        if page:
            self.cursor.execute("""
                SELECT page, text, text_type, font_name, font_size, extraction_method
                FROM extracted_text
                WHERE page = ?
                ORDER BY id
            """, (page,))
        else:
            self.cursor.execute("""
                SELECT page, text, text_type, font_name, font_size, extraction_method
                FROM extracted_text
                ORDER BY page, id
            """)

        return [
            {
                "page": row[0],
                "text": row[1],
                "text_type": row[2],
                "font_name": row[3],
                "font_size": row[4],
                "extraction_method": row[5]
            }
            for row in self.cursor.fetchall()
        ]

    def get_unique_tokens(self) -> List[str]:
        """Get unique text tokens for classification"""
        self.cursor.execute("""
            SELECT DISTINCT text
            FROM extracted_text
            WHERE text != ''
            ORDER BY text
        """)
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test extraction on TB-LKTN HOUSE.pdf"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 text_extractor_simple.py <pdf_path>")
        print("\nThis extractor does NOT extract coordinates.")
        print("It follows expert POC approach: text only → classify → generate coords from GridTruth")
        sys.exit(1)

    pdf_path = sys.argv[1]
    db_path = "output_artifacts/simple_text_extraction.db"

    print("=" * 70)
    print("SIMPLE TEXT-ONLY EXTRACTION (DeepSeek POC Approach)")
    print("=" * 70)
    print(f"PDF: {pdf_path}")
    print(f"Output DB: {db_path}")
    print()

    extractor = SimpleTextExtractor(db_path)

    print("Extracting text (no coordinates)...")
    stats = extractor.extract_from_pdf(pdf_path)

    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Pages processed: {stats['pages_processed']}")
    print(f"Text items: {stats['text_items_extracted']}")

    if stats['errors']:
        print(f"\nErrors: {len(stats['errors'])}")
        for err in stats['errors'][:5]:
            print(f"  - {err}")

    print("\nUnique tokens (first 20):")
    tokens = extractor.get_unique_tokens()[:20]
    for token in tokens:
        print(f"  '{token}'")

    print(f"\n✓ Saved to {db_path}")
    print("\nNext step: Run classification against CHEAT_SHEET patterns")
    print("=" * 70)

    extractor.close()


if __name__ == "__main__":
    main()
