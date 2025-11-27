#!/usr/bin/env python3
"""
Complete Legend Extractor - Extract all symbols from PDF legend + standards

Extracts symbol legend from TB-LKTN HOUSE.pdf page 1
Format: Two columns - SYMBOLS (x~500) | DESCRIPTIONS (x~530-650)

Merges with architectural_symbol_standards.json for missing symbols

Populates context_legend table with:
- symbol_id (e.g., "GB", "CP", "SWS")
- symbol_text (the actual text)
- description (e.g., "Aluminium Kitchen Sink")
- category (plumbing, electrical, etc.)
- page
- source ("pdf_legend" or "standards")

Author: Claude Code
Date: 2025-11-25
Status: Stage 1 completion
"""

import sqlite3
import sys
import json
from pathlib import Path


def load_standards():
    """Load architectural symbol standards reference"""
    standards_path = Path(__file__).parent / "architectural_symbol_standards.json"

    if not standards_path.exists():
        print("⚠️  Standards reference not found, using PDF legend only")
        return {}

    with open(standards_path, 'r') as f:
        return json.load(f)


def extract_legend_from_page1(db_path: str):
    """Extract complete symbol legend from page 1 + merge with standards"""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 70)
    print("COMPLETE LEGEND EXTRACTION - Page 1 + Standards")
    print("=" * 70)

    # Get all text in legend area (y: 300-490, x: symbols~500, descriptions~530-650)
    cursor.execute("""
        SELECT text, x, y
        FROM primitives_text
        WHERE page = 1
          AND y BETWEEN 300 AND 490
        ORDER BY y DESC, x
    """)

    all_text = cursor.fetchall()

    # Separate symbols (x~490-510) and descriptions (x~520-650)
    symbols = []
    descriptions = []

    for row in all_text:
        text = row['text'].strip()
        x = row['x']
        y = row['y']

        # Skip headers
        if text in ['SYMBOLS', 'DESCRIPTIONS', 'scale', '1:100']:
            continue

        # Skip numbers that are dimensions/counts
        if text.isdigit():
            continue

        # Symbols column (x around 497-500)
        if 495 <= x <= 505:
            symbols.append({'text': text, 'x': x, 'y': y})

        # Descriptions column (x around 530-650)
        elif 525 <= x <= 655:
            descriptions.append({'text': text, 'x': x, 'y': y})

    print(f"\nFound {len(symbols)} symbols")
    print(f"Found {len(descriptions)} descriptions")

    # Pair symbols with descriptions by Y proximity
    legend_entries = []

    for symbol in symbols:
        # Find description within 5 points of Y
        matching_desc = None
        for desc in descriptions:
            if abs(symbol['y'] - desc['y']) < 15:  # Within 15 points
                matching_desc = desc['text']
                break

        if matching_desc:
            legend_entries.append({
                'symbol_id': symbol['text'],
                'description': matching_desc,
                'y': symbol['y']
            })

    # Categorize symbols
    for entry in legend_entries:
        symbol = entry['symbol_id']
        desc = entry['description'].lower()

        # Determine category
        if any(word in desc for word in ['water', 'closet', 'basin', 'sink', 'shower', 'tap', 'trap', 'tank']):
            entry['category'] = 'plumbing'
        elif any(word in desc for word in ['switch', 'light', 'power', 'outlet', 'fan', 'point']):
            entry['category'] = 'electrical'
        elif any(word in desc for word in ['door', 'window']):
            entry['category'] = 'openings'
        else:
            entry['category'] = 'general'

    # Load standards reference
    standards = load_standards()

    # Merge with standards for missing symbols
    pdf_symbols = set(entry['symbol_id'] for entry in legend_entries)

    # Add from standards if not in PDF legend
    standards_added = []
    if standards:
        for category_name, category_data in standards.items():
            if category_name.startswith('_') or category_name in ['extraction_priority', 'usage_notes']:
                continue

            for subcategory, symbols in category_data.items():
                if not isinstance(symbols, dict):
                    continue

                for symbol_id, symbol_data in symbols.items():
                    if symbol_id not in pdf_symbols and isinstance(symbol_data, dict):
                        # Determine category
                        if 'plumbing' in category_name:
                            cat = 'plumbing'
                        elif 'electrical' in category_name:
                            cat = 'electrical'
                        elif 'door' in category_name:
                            cat = 'openings'
                        elif 'window' in category_name:
                            cat = 'openings'
                        elif 'appliance' in category_name:
                            cat = 'appliance'
                        else:
                            cat = 'general'

                        legend_entries.append({
                            'symbol_id': symbol_id,
                            'description': symbol_data.get('description', symbol_data.get('full_name', '')),
                            'category': cat,
                            'source': 'standards'
                        })
                        standards_added.append(symbol_id)

    # Clear existing legend and insert merged
    cursor.execute("DELETE FROM context_legend")

    for entry in legend_entries:
        source = entry.get('source', 'pdf_legend')
        cursor.execute("""
            INSERT INTO context_legend
            (symbol_id, symbol_text, description, category, page)
            VALUES (?, ?, ?, ?, ?)
        """, (
            entry['symbol_id'],
            entry['symbol_id'],  # symbol_text same as symbol_id
            entry['description'],
            entry['category'],
            1 if source == 'pdf_legend' else 0  # Page 1 for PDF, 0 for standards
        ))

    conn.commit()

    if standards_added:
        print(f"\n✅ Added {len(standards_added)} symbols from standards: {', '.join(standards_added)}")

    # Display results
    print("\n" + "=" * 70)
    print("EXTRACTED LEGEND ENTRIES:")
    print("=" * 70)

    cursor.execute("""
        SELECT symbol_id, description, category
        FROM context_legend
        ORDER BY symbol_id
    """)

    for row in cursor.fetchall():
        print(f"  {row['symbol_id']:8s} → {row['description']:40s} [{row['category']}]")

    cursor.execute("SELECT COUNT(*) as count FROM context_legend")
    count = cursor.fetchone()['count']

    print("=" * 70)
    print(f"✅ Total legend entries: {count}")
    print("=" * 70)

    conn.close()
    return count


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python3 extract_complete_legend.py <database_path>")
        print("\nExample:")
        print("  python3 extract_complete_legend.py 'output_artifacts/TB-LKTN HOUSE_ANNOTATION_FROM_2D.db'")
        sys.exit(1)

    db_path = sys.argv[1]

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    extract_legend_from_page1(db_path)


if __name__ == "__main__":
    main()
