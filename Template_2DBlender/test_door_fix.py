"""
Test door detection with fixed parameters
Using blur7_standard_very_sensitive configuration
"""

import cv2
import numpy as np
import pdf2image
import json

def detect_doors_fixed(image):
    """
    Detect doors using the optimized configuration from debug
    """
    # Preprocessing - Using optimal configuration from debug
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)  # blur7 configuration
    edges = cv2.Canny(blurred, 50, 150)

    # Detect circles (door arcs) - Using blur7_standard_very_sensitive configuration
    circles = cv2.HoughCircles(
        edges,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,  # Minimum distance between centers
        param1=50,   # Canny high threshold
        param2=15,   # Very sensitive threshold
        minRadius=20,  # Typical door arc radius in pixels
        maxRadius=120  # Increased from 100
    )

    doors = []
    if circles is not None:
        circles = np.uint16(np.around(circles))

        for i, circle in enumerate(circles[0, :]):
            cx, cy, radius = circle

            # Check if this is likely a door arc (quarter circle)
            # Door arcs are typically 90-120 pixels radius at 300 DPI
            if 90 <= radius <= 130:
                doors.append({
                    'id': f'DOOR_{i+1:03d}',
                    'center': (int(cx), int(cy)),
                    'radius': int(radius),
                    'type': 'arc'
                })

    return doors, circles


def main():
    print("=" * 70)
    print("DOOR DETECTION TEST WITH FIXED PARAMETERS")
    print("=" * 70)

    # Convert PDF to image
    pdf_path = "/home/red1/Documents/bonsai/2DtoBlender/Template_2DBlender/TB-LKTN HOUSE.pdf"
    print(f"Converting page 1...")
    images = pdf2image.convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
    image = np.array(images[0])

    # Detect doors
    print("Detecting doors with fixed parameters...")
    doors, all_circles = detect_doors_fixed(image)

    print(f"\nFound {len(doors)} door arcs")
    print(f"Total circles detected: {len(all_circles[0]) if all_circles is not None else 0}")

    # Visualize
    vis = image.copy()

    # Draw all circles in blue
    if all_circles is not None:
        for circle in all_circles[0, :]:
            cx, cy, radius = circle
            cv2.circle(vis, (cx, cy), radius, (255, 0, 0), 2)
            cv2.circle(vis, (cx, cy), 2, (255, 0, 0), 3)

    # Draw doors in red
    for door in doors:
        cx, cy = door['center']
        radius = door['radius']
        cv2.circle(vis, (cx, cy), radius, (0, 0, 255), 3)
        cv2.circle(vis, (cx, cy), 3, (0, 0, 255), 5)
        cv2.putText(vis, door['id'], (cx + 10, cy - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # Save visualization
    output_path = "door_detection_fixed.jpg"
    cv2.imwrite(output_path, vis)
    print(f"\n✓ Saved visualization: {output_path}")

    # Save results
    results = {
        'doors': doors,
        'total_circles': len(all_circles[0]) if all_circles is not None else 0,
        'parameters': {
            'preprocessing': 'blur7',
            'canny': '(50, 150)',
            'param2': 15,
            'radius': '20-120'
        }
    }

    with open("output_artifacts/door_detection_fixed.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"✓ Saved results: output_artifacts/door_detection_fixed.json")

    # Print door details
    if doors:
        print("\nDoor details:")
        for door in doors:
            print(f"  {door['id']}: center={door['center']}, radius={door['radius']}px")
    else:
        print("\n⚠️ No doors found with radius 90-130px")
        print("  You may need to adjust the radius threshold")

        # Show some circles that were detected
        if all_circles is not None and len(all_circles[0]) > 0:
            print("\n  Some circles detected (first 10):")
            for i, circle in enumerate(all_circles[0, :10]):
                cx, cy, radius = circle
                print(f"    Circle {i+1}: radius={radius}px at ({cx}, {cy})")


if __name__ == "__main__":
    main()