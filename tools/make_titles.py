"""Draws the loading-screen title as pictures (static/title-<lang>.png) with headless Chrome.

Pictures instead of live SVG text: the Telegram web view (WebKit) cut off the ends of the stretched, filtered text.
Run from the project folder:  python3 tools/make_titles.py
Layout units: 550 = the width of the widest line on screen (69% of a phone), measured on a 362x585 screen.
"""
import base64, math, pathlib, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAD_W, PAD_H, SCALE = 670, 330, 1.6         # picture size in units (room for shadow and swashes), pixels per unit
SKEW = 9                                   # degrees that straighten the slanted face
# lang: three lines as (text, baseline, font size, forced width or 0), and the vertical middle of the lettering
TITLES = {
    "ru": ([("Целуй", 80, 112, 350), ("и", 123, 54, 0), ("Знакомься", 193, 114, 546)], 97),
    "uz": ([("O'p", 78, 112, 0), ("va", 130, 52, 0), ("Tanishing", 228, 114, 546)], 119),
    "en": ([("Kiss", 80, 112, 0), ("&amp;", 128, 54, 0), ("Meet", 202, 124, 0)], 101),
}


def faces():
    out = ""
    for sub in ("cyrillic", "latin", "latin-ext"):
        data = base64.b64encode((ROOT / "static" / "fonts" / f"lobster-{sub}.woff2").read_bytes()).decode()
        rng = {"cyrillic": "U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116", "latin": "U+0000-00FF,U+2000-206F",
               "latin-ext": "U+0100-02BA,U+1E00-1E9F"}[sub]
        out += f"@font-face{{font-family:L;src:url(data:font/woff2;base64,{data}) format('woff2');unicode-range:{rng}}}"
    return out


def words(lines):
    tan = math.tan(math.radians(SKEW))
    out = ""
    for text, y, size, width in lines:
        x = 275 - (y - size * .35) * tan
        fit = f' textLength="{width}" lengthAdjust="spacingAndGlyphs"' if width else ""
        out += f'<text x="{x:.1f}" y="{y}" font-size="{size}"{fit}>{text}</text>'
    return out


def layer(lines, paint, stroke_w, dx=0, dy=0, extra=""):
    return (f'<g transform="translate({dx} {dy}) skewX({SKEW})" fill="{paint}" stroke="{paint}" stroke-width="{stroke_w}" '
            f'stroke-linejoin="round" text-anchor="middle" style="font-family:L" {extra}>{words(lines)}</g>')


def svg(lines, mid):
    big, small = [lines[0], lines[2]], [lines[1]]
    top = mid - PAD_H / 2

    def stack(ls):      # soft shadow, darker lower edge, light upper edge, then the face
        return (layer(ls, "#3c4a14", 5, 3, 7.5, 'opacity=".52" filter="url(#blur)"') + layer(ls, "#d6761f", 3, .7, 2.8)
                + layer(ls, "#ffedaa", 3, -.4, -1.8) + layer(ls, "url(#face)", 2.4))

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(PAD_W * SCALE)}" height="{int(PAD_H * SCALE)}" viewBox="-60 {top} {PAD_W} {PAD_H}">'
            f'<style>{faces()}</style><defs>'
            f'<radialGradient id="face" gradientUnits="userSpaceOnUse" cx="275" cy="{mid + 8}" r="300">'
            '<stop offset="0" stop-color="#fdd456"/><stop offset=".45" stop-color="#f9bd49"/><stop offset="1" stop-color="#ee923c"/></radialGradient>'
            '<filter id="blur" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="4.5"/></filter></defs>'
            + stack(big) + stack(small) + "</svg>")


with tempfile.TemporaryDirectory() as tmp:
    for lang, (lines, mid) in TITLES.items():
        src = pathlib.Path(tmp) / f"{lang}.svg"
        src.write_text(svg(lines, mid), encoding="utf-8")
        out = ROOT / "static" / f"title-{lang}.webp"
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp}/chrome",
                        "--default-background-color=00000000", "--virtual-time-budget=4000",
                        f"--window-size={int(PAD_W * SCALE)},{int(PAD_H * SCALE)}", f"--screenshot={out}", src.as_uri()],
                       check=True, capture_output=True, timeout=60)
        print(out.name, out.stat().st_size, "bytes")
