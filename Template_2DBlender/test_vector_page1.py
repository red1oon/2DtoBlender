#!/usr/bin/env python3
"""
Test vector extraction on Page 1 (architectural plan)
Door arcs should be more prominent on architectural drawing.
"""

from core.vector_extractor import VectorSemanticExtractor
import json

def test_page1():
    """Extract from page 1 where doors are clearer"""

    pdf_path = "TB-LKTN HOUSE.pdf"
    db_path = "output_artifacts/vector_page1.db"

    print("=" * 70)
    print("TESTING PAGE 1 EXTRACTION (Architectural Plan)")
    print("=" * 70)

    extractor = VectorSemanticExtractor(db_path)

    # Extract from page 1 (architectural plan)
    results = extractor.extract_all_vectors(pdf_path, page_num=1)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    # Analyze door detection
    if results['doors']:
        print(f"\n✓ Found {len(results['doors'])} doors:")
        for i, door in enumerate(results['doors'][:3], 1):
            print(f"  Door {i}:")
            print(f"    Position: ({door['world_x']:.2f}, {door['world_y']:.2f}) m")
            print(f"    Width: {door['width_mm']:.0f} mm")
            print(f"    Swing: {door['swing_direction']}")
            print(f"    Confidence: {door['confidence']:.2%}")
    else:
        print("\n⚠️ No doors found - need to adjust parameters")

    # Check wall thicknesses
    if results['walls']:
        thicknesses = [w['thickness_mm'] for w in results['walls'] if w['thickness_mm'] > 0]
        if thicknesses:
            avg_thickness = sum(thicknesses) / len(thicknesses)
            print(f"\n✓ Found {len(results['walls'])} wall segments")
            print(f"  Average thickness: {avg_thickness:.0f} mm")

            # Count by type
            types = {}
            for w in results['walls']:
                types[w['wall_type']] = types.get(w['wall_type'], 0) + 1
            print(f"  Types: {types}")

    # Windows
    if results['windows']:
        print(f"\n✓ Found {len(results['windows'])} windows:")
        for i, window in enumerate(results['windows'][:3], 1):
            print(f"  Window {i}: {window['width_mm']:.0f} x {window['height_mm']:.0f} mm")

    # Grids
    if results['grids']:
        print(f"\n✓ Found {len(results['grids'])} grid circles")

    # Save results
    with open("output_artifacts/page1_extraction.json", 'w') as f:
        json_results = {
            'summary': {
                'doors': len(results['doors']),
                'walls': len(results['walls']),
                'windows': len(results['windows']),
                'grids': len(results['grids'])
            },
            'doors': results['doors'][:5] if results['doors'] else [],
            'metadata': {
                'page': 1,
                'dpi': results['dpi'],
                'scale_factor': results['scale_factor'],
                'pixels_per_meter': results['pixels_per_meter']
            }
        }
        json.dump(json_results, f, indent=2)

    extractor.close()
    print(f"\n✓ Saved to output_artifacts/page1_extraction.json")
    return results

if __name__ == "__main__":
    test_page1()