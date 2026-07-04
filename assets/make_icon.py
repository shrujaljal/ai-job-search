"""Generate a 'J' app icon (multi-resolution .ico) in the app's blue theme."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "job_app_agent.ico"
BG = (47, 84, 150)        # #2F5496 — the resume/app accent blue
FG = (255, 255, 255)      # white J
BASE = 256


def _font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "seguisb.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


img = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Rounded-square background.
d.rounded_rectangle([8, 8, BASE - 8, BASE - 8], radius=48, fill=BG)

# Centered bold "J".
font = _font(180)
box = d.textbbox((0, 0), "J", font=font)
w, h = box[2] - box[0], box[3] - box[1]
x = (BASE - w) / 2 - box[0]
y = (BASE - h) / 2 - box[1]
d.text((x, y), "J", font=font, fill=FG)

img.save(OUT, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote", OUT)
