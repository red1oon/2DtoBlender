#!/usr/bin/env python3
"""
Enhanced OCR with better preprocessing for room labels.
Try higher DPI, contrast enhancement, sharpening.
"""

import pytesseract
import pdf2image
import numpy as np
import cv2
import json
from pathlib import Path


def extract_with_enhanced_ocr(pdf_path: str, page: int = 1) -> dict:
    """Extract OCR with enhanced preprocessing."""
    print(f"Converting page {page} at 600 DPI...")
    pages = pdf2image.convert_from_path(pdf_path, dpi=600, first_page=page, last_page=page)
    img = np.array(pages[0])

    print(f"Image size: {img.shape[1]}x{img.shape[0]}px")

    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img

    # Enhance contrast (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)

    # Sharpen
    kernel = np.array([[-1,-1,-1],
                       [-1, 9,-1],
                       [-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(sharpened, h=10)

    print("Running OCR on enhanced image...")
    ocr_data = pytesseract.image_to_data(denoised, output_type=pytesseract.Output.DICT)

    # Compile results
    results = []
    for i in range(len(ocr_data['text'])):
        text = ocr_data['text'][i].strip()
        if not text:
            continue

        conf = ocr_data['conf'][i]
        if conf < 0:
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

    print("=" * 80)
    print("ENHANCED OCR WITH PREPROCESSING")
    print("=" * 80)

    # Try page 1
    print("\n--- PAGE 1 ---")
    ocr_p1 = extract_with_enhanced_ocr(pdf_path, page=1)

    # Save results
    with open("output_artifacts/ocr_enhanced_p1.json", 'w') as f:
        json.dump(ocr_p1, f, indent=2)

    # Check for room keywords
    room_keywords = ['BILIK', 'RUANG', 'DAPUR', 'TAMU', 'UTAMA', 'MANDI', 'TANDAS', 'BASUH']
    matches = []

    for item in ocr_p1['items']:
        text_upper = item['text'].upper()
        for keyword in room_keywords:
            if keyword in text_upper:
                matches.append(item)
                print(f"  Found '{item['text']}' at ({item['center_x']:.0f}, {item['center_y']:.0f})px, conf={item['confidence']:.0f}")

    print(f"\nPage 1 results:")
    print(f"  Total items: {ocr_p1['total_items']}")
    print(f"  Room keyword matches: {len(matches)}")

    # Try page 2 (ELEC - user said it's cleaner)
    print("\n--- PAGE 2 (ELEC) ---")
    ocr_p2 = extract_with_enhanced_ocr(pdf_path, page=2)

    with open("output_artifacts/ocr_enhanced_p2.json", 'w') as f:
        json.dump(ocr_p2, f, indent=2)

    matches_p2 = []
    for item in ocr_p2['items']:
        text_upper = item['text'].upper()
        for keyword in room_keywords:
            if keyword in text_upper:
                matches_p2.append(item)
                print(f"  Found '{item['text']}' at ({item['center_x']:.0f}, {item['center_y']:.0f})px, conf={item['confidence']:.0f}")

    print(f"\nPage 2 results:")
    print(f"  Total items: {ocr_p2['total_items']}")
    print(f"  Room keyword matches: {len(matches_p2)}")

    print("\n" + "=" * 80)
    if matches or matches_p2:
        print("✓ Found room labels - can proceed with Voronoi assignment")
    else:
        print("✗ No room labels found - may need to stick with existing ROOM_BOUNDS")
    print("=" * 80)


if __name__ == "__main__":
    main()
