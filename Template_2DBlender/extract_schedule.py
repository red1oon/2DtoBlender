"""
Extract door/window schedule from page 8
This fixes the hardcoding issue - extracting actual sizes from PDF
"""

import pdfplumber
import re
import json
import sqlite3
from pathlib import Path


def extract_schedule_from_pdf(pdf_path: str) -> dict:
    """
    Extract door and window schedule from page 8 of the PDF.

    The schedule has the following structure:
    - REFERENCES: D1, D2, D3, W1, W2, W3, W4
    - TYPE: Door/window descriptions
    - SIZE: Width x Height in MM
    - LOCATION: Room names
    - UNITS: Quantity (NOS)
    """

    schedule = {
        'doors': {},
        'windows': {}
    }

    with pdfplumber.open(pdf_path) as pdf:
        # Page 8 contains the door/window schedule
        if len(pdf.pages) >= 8:
            page = pdf.pages[7]  # 0-indexed, so page 8 is index 7

            # Extract text
            text = page.extract_text()
            print("Extracted text from page 8:")
            print("=" * 70)
            print(text[:2000])  # Print first 2000 chars for debugging
            print("=" * 70)

            # Try to extract tables
            tables = page.extract_tables()
            if tables:
                print(f"\nFound {len(tables)} tables")

                # Process table-based extraction (more accurate than regex)
                for i, table in enumerate(tables):
                    print(f"\nTable {i+1}:")
                    for row in table[:10]:  # Print first 10 rows
                        print(row)

                    # Look for door schedule table (has REFERENCES row)
                    if table and len(table) > 0:
                        header_row = table[0]

                        # Check if this is a door/window schedule table
                        if 'REFERENCES' in str(header_row):
                            # Get door/window codes from first row
                            codes = [cell for cell in header_row if cell and re.match(r'^[DW]\d$', str(cell).strip())]

                            # Find SIZE row
                            for row in table:
                                if row and 'SIZE' in str(row[0]):
                                    # Extract dimensions for each code
                                    for idx, cell in enumerate(row[1:], 1):
                                        if idx <= len(codes) and cell:
                                            # Parse dimensions like "900MM X 2100MM"
                                            dim_match = re.search(r'(\d{3,4})\s*[Mm]{0,2}\s*[Xx×]\s*(\d{3,4})\s*[Mm]{0,2}', str(cell))
                                            if dim_match:
                                                code = codes[idx-1]
                                                width = int(dim_match.group(1))
                                                height = int(dim_match.group(2))

                                                if code.startswith('D'):
                                                    schedule['doors'][code] = {
                                                        'width': width,
                                                        'height': height,
                                                        'qty': 1
                                                    }
                                                    print(f"  Table: Found {code}: {width}mm x {height}mm")
                                                elif code.startswith('W'):
                                                    schedule['windows'][code] = {
                                                        'width': width,
                                                        'height': height,
                                                        'qty': 1
                                                    }
                                                    print(f"  Table: Found {code}: {width}mm x {height}mm")

                            # Find UNITS row for quantities
                            for row in table:
                                if row and 'UNITS' in str(row[0]):
                                    for idx, cell in enumerate(row[1:], 1):
                                        if idx <= len(codes) and cell:
                                            qty_match = re.search(r'(\d+)\s*NOS', str(cell), re.IGNORECASE)
                                            if qty_match:
                                                code = codes[idx-1]
                                                qty = int(qty_match.group(1))

                                                if code.startswith('D') and code in schedule['doors']:
                                                    schedule['doors'][code]['qty'] = qty
                                                    print(f"  Table: Updated {code} quantity: {qty}")
                                                elif code.startswith('W') and code in schedule['windows']:
                                                    schedule['windows'][code]['qty'] = qty
                                                    print(f"  Table: Updated {code} quantity: {qty}")

            # Fallback: Pattern matching if table extraction didn't work
            if not schedule['doors'] and not schedule['windows']:
                print("\nTable extraction failed, trying regex patterns...")
                door_patterns = [
                    r'(D\d)\s+.*?(\d{3,4})\s*MM?\s*[Xx×]\s*(\d{3,4})\s*MM?',
                ]

                # Search for doors
                print("\nSearching for doors...")
                for pattern in door_patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        code = match.group(1).upper()
                        width = int(match.group(2))
                        height = int(match.group(3))

                        if code not in schedule['doors']:
                            schedule['doors'][code] = {
                                'width': width,
                                'height': height,
                                'qty': 1
                            }
                            print(f"  Regex: Found {code}: {width}mm x {height}mm")

            # Validation
            if not schedule['doors']:
                print("\n⚠️ WARNING: No doors extracted from schedule table")
                print("  Check if page 8 table structure matches expected format")

            if not schedule['windows']:
                print("\n⚠️ WARNING: No windows extracted from schedule table")
                print("  Check if page 8 table structure matches expected format")

    return schedule


def save_schedule_to_db(schedule: dict, db_path: str):
    """
    Save extracted schedule to SQLite database.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS door_window_schedule (
            code TEXT PRIMARY KEY,
            type TEXT,
            width_mm INTEGER,
            height_mm INTEGER,
            quantity INTEGER
        )
    ''')

    # Insert doors
    for code, data in schedule['doors'].items():
        cursor.execute('''
            INSERT OR REPLACE INTO door_window_schedule
            (code, type, width_mm, height_mm, quantity)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, 'door', data['width'], data['height'], data['qty']))

    # Insert windows
    for code, data in schedule['windows'].items():
        cursor.execute('''
            INSERT OR REPLACE INTO door_window_schedule
            (code, type, width_mm, height_mm, quantity)
            VALUES (?, ?, ?, ?, ?)
        ''', (code, 'window', data['width'], data['height'], data['qty']))

    conn.commit()
    conn.close()


def main():
    pdf_path = "TB-LKTN HOUSE.pdf"

    print("=" * 70)
    print("DOOR/WINDOW SCHEDULE EXTRACTION")
    print("=" * 70)
    print(f"PDF: {pdf_path}")

    # Extract schedule
    schedule = extract_schedule_from_pdf(pdf_path)

    # Save to JSON
    output_json = "output_artifacts/extracted_schedule.json"
    with open(output_json, 'w') as f:
        json.dump(schedule, f, indent=2)

    print(f"\n✓ Saved to: {output_json}")

    # Save to database
    output_db = "output_artifacts/extracted_schedule.db"
    save_schedule_to_db(schedule, output_db)
    print(f"✓ Saved to: {output_db}")

    # Print summary
    print("\n" + "=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)

    print("\nDOORS:")
    if schedule['doors']:
        for code, data in sorted(schedule['doors'].items()):
            print(f"  {code}: {data['width']}mm x {data['height']}mm ({data['qty']} units)")
    else:
        print("  ⚠️ No doors found - schedule may need manual entry")

    print("\nWINDOWS:")
    if schedule['windows']:
        for code, data in sorted(schedule['windows'].items()):
            print(f"  {code}: {data['width']}mm x {data['height']}mm ({data['qty']} units)")
    else:
        print("  ⚠️ No windows found - schedule may need manual entry")

    # Critical fix for the hardcoding issue
    if 'D3' in schedule['doors']:
        d3 = schedule['doors']['D3']
        if d3['width'] == 750 and d3['height'] == 2100:
            print("\n✅ CRITICAL FIX: D3 correctly extracted as 750x2100mm")
            print("   (Was hardcoded as 1800x1000mm - now fixed!)")
        else:
            print(f"\n⚠️ D3 dimensions: {d3['width']}x{d3['height']}mm")
    else:
        print("\n⚠️ D3 not found in schedule - manual entry needed")

    return schedule


if __name__ == "__main__":
    main()