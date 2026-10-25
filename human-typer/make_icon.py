"""Draws the app icon (a little keyboard). Used only when building the .exe."""
import sys

from PIL import Image, ImageDraw


def draw(size=256):
    s = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4 * s, 14 * s, 60 * s, 50 * s], radius=6 * s, fill=(37, 99, 235, 255))
    key = (255, 255, 255, 255)
    for row, y in enumerate((19, 27)):
        for i in range(6 - row):
            x = 9 + row * 4 + i * 8
            d.rounded_rectangle([x * s, y * s, (x + 6) * s, (y + 5) * s], radius=1.5 * s, fill=key)
    d.rounded_rectangle([17 * s, 37 * s, 47 * s, 43 * s], radius=1.5 * s, fill=key)  # space bar
    return img


if __name__ == "__main__":
    draw().save(sys.argv[1] if len(sys.argv) > 1 else "icon.ico",
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
