"""Draws the table's wood grain (own art): long soft wavy lines and a few knots on a transparent layer -> static/wood.svg."""
import math, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parent.parent
random.seed(11)
W, H = 800, 700
KNOTS = [(610, 120, 70, 16), (330, 610, 130, 30), (120, 330, 50, 12), (700, 470, 60, 13)]   # x, y, half width, half height


def bend(x, y):          # grain flows around the knots
    for kx, ky, rx, ry in KNOTS:
        d = ((x - kx) / (rx * 1.7)) ** 2 + ((y - ky) / (ry * 3.2)) ** 2
        y += math.copysign(ry * 1.5 * math.exp(-d), y - ky or 1)
    return y


paths = []
y = -10.0
while y < H + 10:
    phase, amp = random.uniform(0, 6.3), random.uniform(2, 9)
    pts = [(x, bend(x, y + amp * math.sin(x / random.uniform(150, 165) + phase))) for x in range(-20, W + 41, 40)]
    d = f"M{pts[0][0]} {pts[0][1]:.1f}" + "".join(f"Q{pts[i][0]} {pts[i][1]:.1f} {(pts[i][0] + pts[i + 1][0]) / 2:.0f} {(pts[i][1] + pts[i + 1][1]) / 2:.1f}" for i in range(1, len(pts) - 1))
    light = random.random() < .45
    paths.append(f'<path d="{d}" stroke="{"#ffd596" if light else "#8a4c18"}" stroke-width="{random.uniform(1, 5.5):.1f}" stroke-opacity="{random.uniform(.1, .26):.2f}"/>')
    y += random.uniform(7, 20)
for kx, ky, rx, ry in KNOTS:
    for i in range(4):
        k = 1 - i * .23
        paths.append(f'<ellipse cx="{kx + i * 3}" cy="{ky}" rx="{rx * k:.0f}" ry="{ry * k:.1f}" stroke="{"#8a4c18" if i % 2 == 0 else "#ffd596"}" stroke-width="2.2" stroke-opacity="{.2 + i * .02:.2f}"/>')
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" preserveAspectRatio="none" fill="none" stroke-linecap="round">{"".join(paths)}</svg>\n'
(ROOT / "static" / "wood.svg").write_text(svg)
print(len(svg), "bytes")
