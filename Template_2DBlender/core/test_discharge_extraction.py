#!/usr/bin/env python3
"""
Test DISCHARGE text extraction using multiple methods

Tests different pdfplumber extraction approaches to find "DISCHARGE" text
"""

import pdfplumber
import sys

def test_extraction_methods(pdf_path):
    """Test different extraction methods to find DISCHARGE"""

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in [1, 2]:  # Pages 1 and 2
            page = pdf.pages[page_num - 1]
            print(f"\n{'='*70}")
            print(f"PAGE {page_num}")
            print(f"{'='*70}")

            # Method 1: extract_words() - Current method
            print(f"\n📍 METHOD 1: extract_words()")
            words = page.extract_words()
            discharge_words = [w for w in words if 'DISCHARGE' in w['text'].upper() or 'discharge' in w['text']]
            print(f"   Found {len(discharge_words)} matches")
            for w in discharge_words:
                print(f"   - '{w['text']}' at ({w['x0']:.1f}, {w['top']:.1f})")

            # Method 2: extract_text() - Full text extraction
            print(f"\n📍 METHOD 2: extract_text()")
            text = page.extract_text()
            if text and ('DISCHARGE' in text.upper() or 'discharge' in text):
                lines_with_discharge = [line for line in text.split('\n') if 'DISCHARGE' in line.upper() or 'discharge' in line]
                print(f"   Found {len(lines_with_discharge)} lines with DISCHARGE:")
                for line in lines_with_discharge[:5]:  # First 5
                    print(f"   - {line}")
            else:
                print(f"   No DISCHARGE found")

            # Method 3: chars - Character-level extraction
            print(f"\n📍 METHOD 3: chars (character-level)")
            chars = page.chars
            discharge_chars = []
            char_text = ''.join([c['text'] for c in chars])

            # Search for DISCHARGE in concatenated chars
            if 'DISCHARGE' in char_text.upper():
                # Find position
                idx = char_text.upper().find('DISCHARGE')
                if idx != -1:
                    discharge_chars = chars[idx:idx+9]  # 9 chars = "DISCHARGE"
                    print(f"   Found 'DISCHARGE' at char index {idx}")
                    if discharge_chars:
                        print(f"   Position: ({discharge_chars[0]['x0']:.1f}, {discharge_chars[0]['top']:.1f})")
                        print(f"   Text: {''.join([c['text'] for c in discharge_chars])}")
            else:
                print(f"   No DISCHARGE found")

            # Method 4: Search all text including variations
            print(f"\n📍 METHOD 4: Variations search")
            all_words_text = [w['text'] for w in words]
            variations = ['DISCHARGE', 'discharge', 'Discharge', 'DIS CHARGE', 'DISCH ARGE']
            for var in variations:
                matches = [w for w in all_words_text if var in w]
                if matches:
                    print(f"   Found '{var}': {matches}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_discharge_extraction.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    test_extraction_methods(pdf_path)
