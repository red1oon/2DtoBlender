#!/usr/bin/env python3
"""
Extract room label positions from PDF using deterministic OCR
NO AI - pure geometric text extraction
"""

import pdfplumber
import json

PDF_PATH = "TB-LKTN HOUSE.pdf"

def extract_room_positions():
    """Extract room label positions from page 1"""

    room_labels = [
        "BILIK UTAMA",
        "BILIK 2",
        "BILIK 3",
        "BILIK MANDI",
        "RUANG TAMU",
        "RUANG MAKAN",
        "DAPUR",
        "FOOD STORAGE",
        "RUANG BASUH",
        "TANDAS"
    ]

    positions = {}

    with pdfplumber.open(PDF_PATH) as pdf:
        page = pdf.pages[0]  # Page 1 - floor plan

        # Extract all words with bounding boxes
        words = page.extract_words()

        print(f"Total words on page 1: {len(words)}")

        # Find room labels
        for word in words:
            text = word['text'].strip()

            # Check if this word is part of a room label
            for room_label in room_labels:
                if text in room_label or room_label.startswith(text):
                    # Get position (center of bbox)
                    x0, y0, x1, y1 = word['x0'], word['top'], word['x1'], word['bottom']
                    cx = (x0 + x1) / 2.0
                    cy = (y0 + y1) / 2.0

                    # For multi-word labels, we need to group them
                    # For now, just capture the first word position
                    if room_label not in positions:
                        positions[room_label] = {
                            'x': cx,
                            'y': cy,
                            'text': text,
                            'bbox': [x0, y0, x1, y1]
                        }
                        print(f"Found: {room_label} at ({cx:.2f}, {cy:.2f})")

    return positions

def group_multi_word_labels(page):
    """
    Group multi-word room labels by proximity
    e.g., 'BILIK' + 'UTAMA' → 'BILIK UTAMA'
    """
    words = page.extract_words()

    room_keywords = ['BILIK', 'RUANG', 'DAPUR', 'TANDAS', 'FOOD', 'STORAGE']

    grouped = []
    i = 0
    while i < len(words):
        word = words[i]
        text = word['text'].strip()

        if text in room_keywords:
            # Check if next word is close (part of same label)
            if i + 1 < len(words):
                next_word = words[i + 1]

                # If next word is within 50pt horizontally and 10pt vertically
                dx = next_word['x0'] - word['x1']
                dy = abs(next_word['top'] - word['top'])

                if dx < 50 and dy < 10:
                    # Combine words
                    combined_text = f"{text} {next_word['text'].strip()}"
                    combined_bbox = [
                        word['x0'],
                        word['top'],
                        next_word['x1'],
                        next_word['bottom']
                    ]
                    cx = (combined_bbox[0] + combined_bbox[2]) / 2.0
                    cy = (combined_bbox[1] + combined_bbox[3]) / 2.0

                    grouped.append({
                        'text': combined_text,
                        'x': cx,
                        'y': cy,
                        'bbox': combined_bbox
                    })
                    i += 2  # Skip next word
                    continue

        # Single word or not a room label
        cx = (word['x0'] + word['x1']) / 2.0
        cy = (word['top'] + word['bottom']) / 2.0
        grouped.append({
            'text': text,
            'x': cx,
            'y': cy,
            'bbox': [word['x0'], word['top'], word['x1'], word['bottom']]
        })
        i += 1

    return grouped

if __name__ == "__main__":
    print("Extracting room label positions from PDF...")

    with pdfplumber.open(PDF_PATH) as pdf:
        page = pdf.pages[0]
        grouped_words = group_multi_word_labels(page)

        # Debug: print all grouped words that might be room labels
        print(f"\nDEBUG: Total grouped words: {len(grouped_words)}")
        print("\nDEBUG: First 30 words on page:")
        for i, word in enumerate(grouped_words[:30]):
            print(f"  {i}: '{word['text']}'")

        print("\nDEBUG: Searching for room keywords...")

        for word in grouped_words:
            text = word['text']
            if any(keyword in text for keyword in ['BILIK', 'RUANG', 'DAPUR', 'TANDAS', 'FOOD', 'STORAGE', 'BASUH', 'MANDI', 'TOILET']):
                print(f"  Found: '{text}' at ({word['x']:.2f}, {word['y']:.2f})")

        # Filter for room labels only
        room_labels = [
            "BILIK UTAMA",
            "BILIK 2",
            "BILIK 3",
            "BILIK MANDI",
            "RUANG TAMU",
            "RUANG MAKAN",
            "DAPUR",
            "FOOD STORAGE",
            "RUANG BASUH",
            "TANDAS"
        ]

        room_positions = {}
        for word in grouped_words:
            if word['text'] in room_labels:
                room_positions[word['text']] = {
                    'x': word['x'],
                    'y': word['y'],
                    'bbox': word['bbox']
                }

        print(f"\n{'='*60}")
        print("ROOM LABEL POSITIONS (PDF coordinates)")
        print(f"{'='*60}")

        for label, pos in sorted(room_positions.items()):
            print(f"{label:20s}: ({pos['x']:8.2f}, {pos['y']:8.2f})")

        # Save to JSON
        output = {
            'pdf_coordinates': room_positions,
            'note': 'These are PDF coordinate space - need to apply calibration scale to convert to meters'
        }

        with open('output_artifacts/room_positions.json', 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n✅ Saved to output_artifacts/room_positions.json")
        print(f"   Found {len(room_positions)} room labels")
