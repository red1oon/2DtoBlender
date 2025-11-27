#!/usr/bin/env python3
"""
Test updated primitive extractor with annotation text support
"""

from primitive_extractor import PrimitiveExtractor

def test_discharge_extraction():
    """Test that DISCHARGE is now captured"""

    pdf_path = "../TB-LKTN HOUSE.pdf"

    print("Testing updated primitive extractor...")
    print("=" * 70)

    extractor = PrimitiveExtractor()
    primitives = extractor.extract_all_primitives(pdf_path)

    # Check pages 1 and 2 for DISCHARGE
    for page_num in [1, 2]:
        page_key = f'page_{page_num}'
        page_data = primitives.get(page_key, {})
        text_prims = page_data.get('primitives', {}).get('text', [])

        print(f"\nPAGE {page_num}:")
        print(f"  Total text primitives: {len(text_prims)}")

        # Find DISCHARGE
        discharge_items = [t for t in text_prims if 'DISCHARGE' in t['text'].upper()]
        print(f"  DISCHARGE occurrences: {len(discharge_items)}")

        if discharge_items:
            print(f"\n  ✅ DISCHARGE found at positions:")
            for item in discharge_items[:5]:  # First 5
                source = item.get('source', 'regular')
                print(f"     - '{item['text']}' at ({item['x']:.1f}, {item['y']:.1f}) [{source}]")

        # Check filter stats
        stats = page_data.get('filter_stats', {})
        annot_count = stats.get('annotation_text', 0)
        if annot_count > 0:
            print(f"\n  📝 Annotation text extracted: {annot_count} items")

if __name__ == "__main__":
    test_discharge_extraction()
