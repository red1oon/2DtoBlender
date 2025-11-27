#!/usr/bin/env python3
"""
Extract door/window schedules from Page 8.
This is the ground truth for door specifications and room assignments.
"""

import pytesseract
import pdf2image
import numpy as np
import cv2
import json


def extract_schedule_page(pdf_path: str, page: int = 8, dpi: int = 300):
    """Extract text from schedule page."""
    print(f"Converting page {page} at {dpi} DPI...")
    pages = pdf2image.convert_from_path(pdf_path, dpi=dpi, first_page=page, last_page=page)
    img = np.array(pages[0])

    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img

    # Enhance for better OCR
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    print("Running OCR...")
    ocr_data = pytesseract.image_to_data(enhanced, output_type=pytesseract.Output.DICT)

    # Collect all text items
    items = []
    for i in range(len(ocr_data['text'])):
        text = ocr_data['text'][i].strip()
        if not text:
            continue
        if ocr_data['conf'][i] < 0:
            continue

        items.append({
            'text': text,
            'conf': ocr_data['conf'][i],
            'x': ocr_data['left'][i],
            'y': ocr_data['top'][i],
            'w': ocr_data['width'][i],
            'h': ocr_data['height'][i]
        })

    return items, img


def parse_door_schedule(items):
    """Parse door schedule from OCR items."""
    print("\nParsing door schedule...")

    # Look for door codes (D1, D2, D3, etc.)
    door_entries = {}

    for i, item in enumerate(items):
        text = item['text'].upper()

        # Match door codes
        if text in ['D1', 'D2', 'D3', 'D4', 'D5']:
            # Collect nearby text (next 20 items in reading order)
            nearby = []
            for j in range(i+1, min(i+20, len(items))):
                if abs(items[j]['y'] - item['y']) < 30:  # Same line
                    nearby.append(items[j]['text'])

            context = ' '.join(nearby)
            door_entries[text] = {
                'code': text,
                'context': context,
                'position': (item['x'], item['y'])
            }

            print(f"  {text}: {context[:100]}")

    return door_entries


def parse_window_schedule(items):
    """Parse window schedule from OCR items."""
    print("\nParsing window schedule...")

    window_entries = {}

    for i, item in enumerate(items):
        text = item['text'].upper()

        # Match window codes
        if text in ['W1', 'W2', 'W3', 'W4', 'W5']:
            nearby = []
            for j in range(i+1, min(i+20, len(items))):
                if abs(items[j]['y'] - item['y']) < 30:
                    nearby.append(items[j]['text'])

            context = ' '.join(nearby)
            window_entries[text] = {
                'code': text,
                'context': context,
                'position': (item['x'], item['y'])
            }

            print(f"  {text}: {context[:100]}")

    return window_entries


def main():
    pdf_path = "TB-LKTN HOUSE.pdf"

    print("=" * 80)
    print("EXTRACT DOOR/WINDOW SCHEDULES FROM PAGE 8")
    print("=" * 80)

    # Extract page 8
    items, img = extract_schedule_page(pdf_path, page=8)
    print(f"\nExtracted {len(items)} text items from page 8")

    # Parse schedules
    doors = parse_door_schedule(items)
    windows = parse_window_schedule(items)

    # Save raw OCR output
    output = {
        'doors': doors,
        'windows': windows,
        'all_text_items': items
    }

    with open('output_artifacts/page8_schedules.json', 'w') as f:
        json.dump(output, f, indent=2)

    # Also save human-readable
    with open('output_artifacts/page8_schedules.txt', 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("DOOR/WINDOW SCHEDULES (Page 8)\n")
        f.write("=" * 80 + "\n\n")

        f.write("DOOR SCHEDULE:\n")
        f.write("-" * 80 + "\n")
        for code, entry in sorted(doors.items()):
            f.write(f"{code}: {entry['context']}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("WINDOW SCHEDULE:\n")
        f.write("-" * 80 + "\n")
        for code, entry in sorted(windows.items()):
            f.write(f"{code}: {entry['context']}\n")

    print(f"\n✓ Saved: output_artifacts/page8_schedules.json")
    print(f"✓ Saved: output_artifacts/page8_schedules.txt")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Doors found: {len(doors)}")
    print(f"Windows found: {len(windows)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
