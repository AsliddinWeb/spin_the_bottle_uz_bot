"""Generates static/banner.png (the /start welcome picture). Run once: .venv/bin/python tools_banner.py"""
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1000, 560
random.seed(7)
img = Image.new("RGB", (W, H))
px = img.load()
for y in range(H):
    for x in range(W):
        t = y / H
        base = (int(222 - 28 * t), int(158 - 36 * t), int(88 - 30 * t))
        px[x, y] = base
# wood grain
d = ImageDraw.Draw(img, "RGBA")
for _ in range(900):
    x = random.randint(0, W); y = random.randint(0, H); l = random.randint(40, 220)
    a = random.randint(6, 22)
    d.line([(x, y), (x + random.randint(-2, 2), y + l)], fill=(110, 55, 10, a) if random.random() < .6 else (255, 225, 170, a), width=random.randint(1, 3))
# vignette
vig = Image.new("L", (W, H), 0)
vd = ImageDraw.Draw(vig); vd.ellipse([-W * .15, -H * .25, W * 1.15, H * 1.25], fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(120))
dark = Image.new("RGB", (W, H), (120, 60, 12))
img = Image.composite(img, dark, vig)

emoji_font = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 160)
def emoji(ch, size):
    layer = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((20, 10), ch, font=emoji_font, embedded_color=True)
    bbox = layer.getbbox() or (0, 0, 200, 200)
    return layer.crop(bbox).resize((size, int(size * (bbox[3] - bbox[1]) / (bbox[2] - bbox[0]))), Image.LANCZOS)

def card(face, tilt, grad):
    cw, ch = 300, 360
    c = Image.new("RGBA", (cw + 40, ch + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([24, 28, cw + 16, ch + 24], 22, fill=(60, 25, 0, 120))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    inner = Image.new("RGBA", (cw, ch))
    idr = ImageDraw.Draw(inner)
    for y in range(ch):
        k = y / ch
        idr.line([(0, y), (cw, y)], fill=(int(grad[0][0] * (1 - k) + grad[1][0] * k), int(grad[0][1] * (1 - k) + grad[1][1] * k), int(grad[0][2] * (1 - k) + grad[1][2] * k), 255))
    f = emoji(face, 250); inner.alpha_composite(f, ((cw - f.width) // 2, 60))
    mask = Image.new("L", (cw, ch), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw - 1, ch - 1], 22, fill=255)
    framed = Image.new("RGBA", (cw + 16, ch + 16), (0, 0, 0, 0))
    ImageDraw.Draw(framed).rounded_rectangle([0, 0, cw + 15, ch + 15], 26, fill=(255, 255, 255, 255))
    framed.paste(inner, (8, 8), mask)
    c.alpha_composite(framed, (12, 12))
    return c.rotate(tilt, resample=Image.BICUBIC, expand=True)

base = img.convert("RGBA")
left = card("👩", 9, ((255, 214, 170), (240, 170, 120)))
right = card("👨", -8, ((235, 215, 190), (200, 160, 120)))
base.alpha_composite(left, (80, 20)); base.alpha_composite(right, (610, 36))
for ch, size, pos in [("👑", 130, (60, 5)), ("👑", 120, (800, 0)), ("❤️", 110, (30, 250)), ("❤️", 130, (840, 120)), ("❤️", 90, (860, 380)), ("❤️", 80, (150, 380)), ("❤️", 70, (710, 410))]:
    base.alpha_composite(emoji(ch, size), pos)
lips = emoji("💋", 250); base.alpha_composite(lips, ((W - lips.width) // 2, 130))

title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Black.ttf", 150)
sub = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Black.ttf", 92)
def stroked(img, xy, txt, font, fill):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    ld.text((xy[0] + 5, xy[1] + 9), txt, font=font, fill=(90, 25, 5, 255), stroke_width=12, stroke_fill=(90, 25, 5, 255))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(2)))
    ld2 = ImageDraw.Draw(img)
    ld2.text(xy, txt, font=font, fill=fill, stroke_width=11, stroke_fill=(255, 255, 255, 255))
stroked(base, (330, 285), "Spin", title, (226, 70, 36, 255))
stroked(base, (285, 415), "the Bottle", sub, (226, 70, 36, 255))
base.convert("RGB").save("static/banner.png", optimize=True)
print("ok")
