"""
Draw assets/badges/*.png: pixel-style console badges for Discord's small image.

Each badge is a brand-coloured circle (PlayStation blue, Xbox green, Nintendo red)
with a light ring and the console's short name in the bundled pixel font, so it
stays readable at the ~20px Discord shows small images at, on a dark profile.

The game database links to them on GitHub (see BADGE_URL in main.py), so commit
and push new badges before Discord can show them.

Needs Pillow: pip install pillow
Usage: python tools/make_badges.py [output dir]   (default: assets/badges/)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "fonts", "PressStart2P-Regular.ttf")
SIZE = 256

SONY, XBOX, NINTENDO = "#0070D1", "#107C10", "#E60012"
BADGES = {  # database sheet name -> (file name, label, colour)
    "PS1": ("ps1", "PS1", SONY), "PS2": ("ps2", "PS2", SONY), "PS3": ("ps3", "PS3", SONY),
    "PS4": ("ps4", "PS4", SONY), "PS5": ("ps5", "PS5", SONY), "PSP": ("psp", "PSP", SONY),
    "PS Vita": ("ps-vita", "VITA", SONY),
    "OG Xbox": ("xbox", "XBOX", XBOX), "Xbox 360": ("xbox-360", "360", XBOX),
    "Xbox One": ("xbox-one", "ONE", XBOX), "Xbox Series X": ("xbox-series", "X|S", XBOX),
    "NES": ("nes", "NES", NINTENDO), "SNES": ("snes", "SNES", NINTENDO),
    "Nintendo 64": ("n64", "N64", NINTENDO), "GameCube": ("gamecube", "GC", NINTENDO),
    "Wii": ("wii", "Wii", NINTENDO), "Wii U": ("wii-u", "WiiU", NINTENDO),
    "Nintendo Switch": ("switch", "NSW", NINTENDO), "Nintendo Switch 2": ("switch-2", "NS2", NINTENDO),
    "Game Boy": ("game-boy", "GB", NINTENDO), "Game Boy Color": ("game-boy-color", "GBC", NINTENDO),
    "Game Boy Advance": ("game-boy-advance", "GBA", NINTENDO),
    "Nintendo DS": ("ds", "DS", NINTENDO), "Nintendo 3DS": ("3ds", "3DS", NINTENDO),
}


def badge(label, colour):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, SIZE - 1, SIZE - 1), fill="#FFFFFF")          # light ring
    d.ellipse((14, 14, SIZE - 15, SIZE - 15), fill=colour)
    # Biggest pixel-font size (multiples of 8 stay crisp) that fits inside the circle
    for size in range(96, 7, -8):
        font = ImageFont.truetype(FONT, size)
        left, top, right, bottom = d.textbbox((0, 0), label, font=font)
        if right - left <= SIZE * 0.66:
            break
    x = (SIZE - (right - left)) / 2 - left
    y = (SIZE - (bottom - top)) / 2 - top
    shadow = max(4, size // 12)
    d.text((x + shadow, y + shadow), label, font=font, fill=(0, 0, 0, 110))
    d.text((x, y), label, font=font, fill="#FFFFFF")
    return img


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "badges")
    os.makedirs(out, exist_ok=True)
    for slug, label, colour in BADGES.values():
        badge(label, colour).save(os.path.join(out, f"{slug}.png"), optimize=True)
    print(f"Wrote {len(BADGES)} badges to {out}")


if __name__ == "__main__":
    main()
