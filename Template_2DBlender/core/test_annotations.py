#!/usr/bin/env python3
"""
Extract text from PDF annotations (AutoCAD SHX Text)
"""

import pdfplumber
import sys

def extract_annotations(pdf_path):
    """Extract all annotation text"""

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in [1, 2]:
            page = pdf.pages[page_num - 1]

            print(f"\n{'='*70}")
            print(f"PAGE {page_num} - ANNOTATIONS")
            print(f"{'='*70}\n")

            if hasattr(page, 'annots') and page.annots:
                print(f"Total annotations: {len(page.annots)}\n")

                discharge_annots = []
                for idx, annot in enumerate(page.annots):
                    contents = annot.get('contents', '')
                    if contents and 'DISCHARGE' in contents.upper():
                        discharge_annots.append(annot)
                        print(f"✅ FOUND 'DISCHARGE' in annotation #{idx}")
                        print(f"   Contents: {contents}")
                        print(f"   Position: x0={annot['x0']:.1f}, y0={annot['y0']:.1f}")
                        print(f"   Title: {annot.get('title', 'N/A')}")
                        print()

                if not discharge_annots:
                    print("❌ No 'DISCHARGE' found in annotations")
                    print("\nShowing all annotation contents:")
                    for idx, annot in enumerate(page.annots[:20]):  # First 20
                        contents = annot.get('contents', '')
                        if contents:
                            print(f"   [{idx}] {contents}")
            else:
                print("No annotations on this page")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_annotations.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    extract_annotations(pdf_path)
