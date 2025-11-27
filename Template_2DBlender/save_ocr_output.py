#!/usr/bin/env python3
"""
Save complete OCR output to file for debugging.
Shows all detected text with positions and confidence.
"""

import pytesseract
import pdf2image
import numpy as np
import json
from pathlib import Path


def extract_all_ocr_data(pdf_path: str, page: int = 1) -> dict:
    """Extract all OCR data from PDF page."""
    print(f"Converting page {page}...")
    pages = pdf2image.convert_from_path(pdf_path, dpi=300, first_page=page, last_page=page)
    img = np.array(pages[0])

    print("Running OCR...")
    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    # Compile results
    results = []
    for i in range(len(ocr_data['text'])):
        text = ocr_data['text'][i].strip()
        if not text:  # Skip empty
            continue

        conf = ocr_data['conf'][i]
        if conf < 0:  # Skip invalid
            continue

        results.append({
            'text': text,
            'confidence': conf,
            'left': ocr_data['left'][i],
            'top': ocr_data['top'][i],
            'width': ocr_data['width'][i],
            'height': ocr_data['height'][i],
            'center_x': ocr_data['left'][i] + ocr_data['width'][i] / 2,
            'center_y': ocr_data['top'][i] + ocr_data['height'][i] / 2
        })

    return {
        'page': page,
        'total_items': len(results),
        'items': results,
        'image_size': {
            'width': img.shape[1],
            'height': img.shape[0]
        }
    }


def main():
    pdf_path = "TB-LKTN HOUSE.pdf"
    page = 1

    print("=" * 80)
    print("EXTRACTING ALL OCR DATA")
    print("=" * 80)

    ocr_output = extract_all_ocr_data(pdf_path, page)

    # Save JSON
    json_path = "output_artifacts/ocr_complete_output.json"
    with open(json_path, 'w') as f:
        json.dump(ocr_output, f, indent=2)

    print(f"\n✓ Saved JSON: {json_path}")

    # Save human-readable text
    txt_path = "output_artifacts/ocr_complete_output.txt"
    with open(txt_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write(f"OCR OUTPUT - Page {page}\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total items: {ocr_output['total_items']}\n")
        f.write(f"Image size: {ocr_output['image_size']['width']}x{ocr_output['image_size']['height']}px\n")
        f.write("=" * 80 + "\n\n")

        # Sort by confidence (high to low)
        sorted_items = sorted(ocr_output['items'], key=lambda x: x['confidence'], reverse=True)

        f.write("ALL DETECTED TEXT (sorted by confidence):\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Text':<30} {'Conf':<6} {'Position (x,y)':<20} {'Size (w×h)':<15}\n")
        f.write("-" * 80 + "\n")

        for item in sorted_items:
            text = item['text'][:28]  # Truncate long text
            conf = item['confidence']
            pos = f"({item['left']}, {item['top']})"
            size = f"{item['width']}×{item['height']}"
            f.write(f"{text:<30} {conf:<6.0f} {pos:<20} {size:<15}\n")

        # Room-related keywords
        f.write("\n" + "=" * 80 + "\n")
        f.write("ROOM-RELATED TEXT (keyword search):\n")
        f.write("=" * 80 + "\n")

        room_keywords = ['RUANG', 'TAMU', 'DAPUR', 'BILIK', 'UTAMA', 'MANDI', 'TANDAS', 'BASUH']

        for keyword in room_keywords:
            f.write(f"\nKeyword: '{keyword}'\n")
            f.write("-" * 40 + "\n")

            matches = [item for item in sorted_items if keyword.upper() in item['text'].upper()]

            if matches:
                for match in matches:
                    f.write(f"  '{match['text']}' at ({match['center_x']:.0f}, {match['center_y']:.0f})px, conf={match['confidence']:.0f}\n")
            else:
                f.write("  (No matches)\n")

    print(f"✓ Saved TXT: {txt_path}")

    # Summary
    print(f"\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total OCR items: {ocr_output['total_items']}")

    high_conf = len([x for x in ocr_output['items'] if x['confidence'] > 80])
    med_conf = len([x for x in ocr_output['items'] if 50 <= x['confidence'] <= 80])
    low_conf = len([x for x in ocr_output['items'] if x['confidence'] < 50])

    print(f"  High confidence (>80): {high_conf}")
    print(f"  Medium confidence (50-80): {med_conf}")
    print(f"  Low confidence (<50): {low_conf}")

    # Check for room keywords
    print(f"\nRoom keyword occurrences:")
    room_keywords = ['RUANG', 'TAMU', 'DAPUR', 'BILIK', 'UTAMA', 'MANDI', 'TANDAS', 'BASUH']
    for keyword in room_keywords:
        count = len([x for x in ocr_output['items'] if keyword.upper() in x['text'].upper()])
        print(f"  {keyword}: {count} occurrences")

    print(f"\n✓ Files saved - review to debug room label detection")
    print("=" * 80)


if __name__ == "__main__":
    main()
