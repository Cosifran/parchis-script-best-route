"""
Calibration helper for Parchís Pathfinding - CLI version.

Captures screenshot and helps you find HSV values for color detection.
"""

import cv2
import numpy as np
import sys

def capture_and_analyze():
    """Capture screenshot and analyze clicked colors."""
    
    # This is a simplified version - the full GUI calibration has issues on Windows
    # Instead, we'll create a simple HSV picker using OpenCV
    
    print("=== Parchís HSV Calibration Tool ===")
    print()
    print("This tool will help you find the correct HSV ranges for your emulators screen.")
    print()
    print("To use:")
    print("1. Take a screenshot: python main.py capture")
    print("2. Open screenshot.png in any image editor")
    print("3. Use any HSV color picker to find the HSV values for each player color")
    print()
    print("Example HSV ranges (you may need to adjust):")
    print()
    print("BLUE:")
    print("  lower: [100, 100, 50]")
    print("  upper: [140, 255, 255]")
    print()
    print("YELLOW:")
    print("  lower: [20, 100, 100]")
    print("  upper: [40, 255, 255]")
    print()
    print("GREEN:")
    print("  lower: [40, 50, 50]")
    print("  upper: [80, 255, 255]")
    print()
    print("RED (may need two ranges - low and high hue):")
    print("  lower: [0, 100, 50]")
    print("  upper: [10, 255, 255]")
    print()
    print("After finding your values, edit config/calibration.yaml")
    print()
    
    # Try to show how to use OpenCV to find HSV
    print("Quick HSV finder - run this Python code:")
    print("-" * 40)
    print("""
import cv2
import numpy as np

def get_hsv(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        hsv = hsv_frame[y, x]
        print(f"Clicked pixel HSV: {hsv}")

img = cv2.imread('screenshot.png')
hsv_frame = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

cv2.namedWindow('image')
cv2.setMouseCallback('image', get_hsv)
cv2.imshow('image', img)
cv2.waitKey(0)
""")
    print("-" * 40)


if __name__ == "__main__":
    capture_and_analyze()