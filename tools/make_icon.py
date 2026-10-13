"""
Draw assets/app.ico: the header avatar (blurple circle with a play arrow).

Needs Pillow (build-time only): pip install pillow
"""
import os

from PIL import Image, ImageDraw

BLURPLE = (88, 101, 242, 255)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def draw(size):
    scale = 4  # supersample, then downsize for smooth edges
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, s - 1, s - 1), fill=BLURPLE)
    # Play triangle, nudged right so it looks optically centred
    d.polygon([(s * 0.38, s * 0.28), (s * 0.38, s * 0.72), (s * 0.74, s * 0.50)], fill="white")
    return img.resize((size, size), Image.LANCZOS)


def main():
    out = os.path.join(ROOT, "assets", "app.ico")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    draw(256).save(out, sizes=[(n, n) for n in sizes], append_images=[draw(n) for n in sizes[:-1]])
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
