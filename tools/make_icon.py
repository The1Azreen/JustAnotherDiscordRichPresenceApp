"""
Draw assets/app.ico: a pixel-art retro window in the1azreen.neocities.org colours
(neon yellow border, teal title bar, deep purple body) holding a play arrow.

Each size is drawn on a pixel grid and scaled up with nearest-neighbour, so the
icon stays crisp like the site's pixelated art. 16px gets its own simpler grid.

Needs Pillow (build-time only): pip install pillow
Usage: python tools/make_icon.py [output dir]   (default: assets/)
"""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BORDER = (247, 201, 72, 255)    # neon yellow
TITLE = (109, 224, 246, 255)    # teal
WINDOW = (43, 27, 79, 255)      # deep purple
CONTENT = (27, 27, 47, 255)     # dark blue
ARROW = (255, 111, 242, 255)    # magenta
SHADOW = (18, 11, 38, 255)      # drop shadow, like the site's box-shadow
WHITE = (255, 255, 255, 255)


def rect(d, x1, y1, x2, y2, color):
    """Filled rectangle using inclusive pixel coordinates."""
    d.rectangle((x1, y1, x2, y2), fill=color)


def play_arrow(d, left, top, height, color):
    """Pixel play triangle pointing right, widest in the middle row."""
    half = height // 2
    for row in range(height):
        width = half + 1 - abs(row - half)
        rect(d, left, top + row, left + width - 1, top + row, color)


def grid32():
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rect(d, 3, 4, 31, 31, SHADOW)            # offset shadow
    rect(d, 0, 1, 28, 28, BORDER)            # window border
    rect(d, 2, 3, 26, 26, WINDOW)
    rect(d, 3, 4, 25, 9, BORDER)             # title bar with its own border
    rect(d, 4, 5, 24, 8, TITLE)
    for x in (16, 19, 22):                   # _ [] x buttons
        rect(d, x, 6, x + 1, 7, WHITE)
    rect(d, 3, 11, 25, 25, BORDER)           # content area with border
    rect(d, 4, 12, 24, 24, CONTENT)
    play_arrow(d, 11, 13, 11, ARROW)
    return img


def grid16():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rect(d, 2, 2, 15, 15, SHADOW)
    rect(d, 0, 0, 13, 13, BORDER)
    rect(d, 1, 1, 12, 3, TITLE)
    rect(d, 1, 4, 12, 12, CONTENT)
    play_arrow(d, 5, 5, 7, ARROW)
    return img


def draw(size):
    base = grid16() if size <= 24 else grid32()
    if size % base.width == 0:
        return base.resize((size, size), Image.NEAREST)
    # Sizes that aren't a whole multiple (24, 48): blow up first, then shrink
    big = base.resize((base.width * 8, base.height * 8), Image.NEAREST)
    return big.resize((size, size), Image.LANCZOS)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "app.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    draw(256).save(out, sizes=[(n, n) for n in sizes], append_images=[draw(n) for n in sizes[:-1]])
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
