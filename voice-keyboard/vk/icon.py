"""The microphone icon, drawn in code so there are no image files to ship."""
from PIL import Image, ImageDraw

GREY = (150, 150, 150, 255)
RED = (230, 40, 40, 255)
BLUE = (37, 99, 235, 255)


def make_icon(color, size=64):
    s = size / 64  # drawn on a 64x64 grid, scaled to the requested size

    def box(*xy):
        return tuple(round(v * s) for v in xy)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(1, round(4 * s))
    d.rounded_rectangle(box(22, 6, 42, 40), radius=round(10 * s), fill=color)  # mic head
    d.arc(box(14, 18, 50, 50), start=0, end=180, fill=color, width=w)          # holder
    d.line(box(32, 50, 32, 58), fill=color, width=w)                           # stand
    d.line(box(22, 58, 42, 58), fill=color, width=w)
    return img


def save_ico(path):
    make_icon(BLUE, 256).save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])


if __name__ == "__main__":
    import sys
    save_ico(sys.argv[1] if len(sys.argv) > 1 else "icon.ico")
