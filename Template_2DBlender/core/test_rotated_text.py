#!/usr/bin/env python3
"""
Test extraction of rotated/vertical DISCHARGE text

Uses pdfplumber layout-aware extraction
"""

import pdfplumber
import sys

def test_rotated_text(pdf_path, page_num=2):
    """Test extraction including rotated text"""

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]

        print(f"\n{'='*70}")
        print(f"PAGE {page_num} - ROTATED TEXT EXTRACTION")
        print(f"{'='*70}\n")

        # Method 1: extract_text with layout=True
        print("📍 METHOD 1: extract_text(layout=True)")
        text_layout = page.extract_text(layout=True)
        if text_layout:
            lines = text_layout.split('\n')
            discharge_lines = [line for line in lines if 'DISCHARGE' in line.upper()]
            print(f"   Found {len(discharge_lines)} lines:")
            for line in discharge_lines:
                print(f"   - {line}")
        else:
            print("   No text extracted")

        # Method 2: Extract chars and check for rotated text
        print(f"\n📍 METHOD 2: chars with rotation detection")
        chars = page.chars

        # Check char orientations
        rotations = {}
        for char in chars:
            matrix = char.get('matrix', None)
            if matrix:
                # matrix[0] and matrix[3] indicate rotation
                rotation = f"{matrix[0]},{matrix[3]}"
                rotations[rotation] = rotations.get(rotation, 0) + 1

        print(f"   Text orientations found: {len(rotations)}")
        for rot, count in rotations.items():
            print(f"   - Matrix {rot}: {count} chars")

        # Method 3: Search for DISCHARGE in all chars regardless of rotation
        print(f"\n📍 METHOD 3: Full char scan (all rotations)")
        all_char_text = ''.join([c['text'] for c in chars])

        # Search for DISCHARGE
        if 'DISCHARGE' in all_char_text.upper():
            idx = all_char_text.upper().find('DISCHARGE')
            discharge_chars = chars[idx:idx+9]

            print(f"   ✅ Found 'DISCHARGE' at char index {idx}")
            print(f"   Position: ({discharge_chars[0]['x0']:.1f}, {discharge_chars[0]['top']:.1f})")
            print(f"   Text: {''.join([c['text'] for c in discharge_chars])}")
            print(f"   Matrix: {discharge_chars[0].get('matrix', 'N/A')}")
        else:
            print(f"   ❌ No DISCHARGE found")

        # Method 4: Extract text from annotations/objects
        print(f"\n📍 METHOD 4: Annotations check")
        if hasattr(page, 'annots') and page.annots:
            print(f"   Found {len(page.annots)} annotations")
            for ann in page.annots[:5]:
                print(f"   - {ann}")
        else:
            print(f"   No annotations")

        # Method 5: Check all unique words extracted
        print(f"\n📍 METHOD 5: All unique words (first 50)")
        words = page.extract_words()
        unique_words = list(set([w['text'] for w in words]))[:50]
        print(f"   Total words: {len(words)}, Unique: {len(set([w['text'] for w in words]))}")

        # Check if any word contains partial DISCHARGE
        discharge_partials = [w for w in unique_words if any(sub in w.upper() for sub in ['DIS', 'CHAR', 'ARGE', 'DISC', 'HARGE'])]
        if discharge_partials:
            print(f"   Partial matches: {discharge_partials}")

        # Show sample of words near top of page (where DISCHARGE should be)
        top_words = [w for w in words if w['top'] < 100]  # Top 100 points
        print(f"\n   Words in top 100pt of page: {len(top_words)}")
        for w in top_words[:10]:
            print(f"   - '{w['text']}' at ({w['x0']:.1f}, {w['top']:.1f})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_rotated_text.py <pdf_path> [page_num]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    page_num = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    test_rotated_text(pdf_path, page_num)
