"""
Generate a simple application icon (icon.ico) for the Windows build.

Uses Pillow if available; otherwise creates a minimal valid .ico file
from a raw bitmap so the build never fails for want of an icon.

Usage:
    python packaging/windows/generate_icon.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "icon.ico"


def _generate_with_pillow() -> bool:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False

    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    for size in sizes:
        img = Image.new("RGBA", (size, size), (13, 17, 23, 255))
        draw = ImageDraw.Draw(img)
        # Simple "robot eye" mark — two rounded rectangles + centre dot
        pad = size // 6
        cx, cy = size // 2, size // 2
        r = size // 4
        # Outer ring (accent blue)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(76, 194, 255, 255))
        # Inner dark circle
        ir = int(r * 0.55)
        draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=(13, 17, 23, 255))
        # Centre dot
        dr = max(2, int(r * 0.22))
        draw.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=(76, 194, 255, 255))
        images.append(img)

    images[0].save(str(OUTPUT), format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Icon generated with Pillow: {OUTPUT}")
    return True


def _generate_minimal() -> bool:
    """Create a minimal but valid 32x32 32-bit ICO file."""
    width = height = 32
    # RGBA pixels — dark blue background, accent-blue centre circle
    pixels = bytearray()
    cx = cy = 16
    for y in range(height):
        for x in range(width):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy <= 64:          # centre dot
                pixels += bytes([76, 194, 255, 255])  # BGRA for ICO
            elif dx * dx + dy * dy <= 144:        # ring
                pixels += bytes([76, 194, 255, 255])
            else:
                pixels += bytes([13, 17, 23, 255])

    # BMP DIB header for the icon image (BITMAPINFOHEADER)
    dib_header = struct.pack(
        "<IIIHHIIIIII",
        40,            # biSize
        width,          # biWidth
        height * 2,     # biHeight (doubled: XOR + AND masks)
        1,              # biPlanes
        32,             # biBitCount
        0, 0, 0, 0, 0, 0,  # biCompression, biSizeImage, biXPels, biYPels, biClrUsed, biClrImportant
    )
    # AND mask (1 bit/pixel, all zeros = fully opaque)
    and_mask = b"\x00" * (((width + 31) // 32) * 4 * height)
    image_data = dib_header + bytes(pixels) + and_mask

    # ICONDIR header
    icondir = struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY
    offset = 6 + 16
    entry = struct.pack(
        "<BBBBHHII",
        width if width < 256 else 0,
        height if height < 256 else 0,
        0, 0,           # colours, reserved
        1, 32,           # planes, bpp
        len(image_data), offset,
    )
    OUTPUT.write_bytes(icondir + entry + image_data)
    print(f"Icon generated (minimal fallback): {OUTPUT}")
    return True


def main():
    if _generate_with_pillow():
        return 0
    if _generate_minimal():
        return 0
    print("ERROR: could not generate icon", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
