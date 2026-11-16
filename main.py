#!/usr/bin/env python3
"""IT WAS IN THE SEED ALL ALONG — ai-excited-01 entry (take 12).

A tiny seed in dark soil splits open and a whole sun hatches out of
it. Dawn sky, long thin rays, sparks and small birds rising from the
crack, one quiet line of text at the bottom. Drawn entirely in code
with the Python standard library only. One fixed seed drives every
random choice, so two runs write byte-identical PNGs.

Usage:  python3 main.py
Output: entry.png (1024x1024) next to this script, or in
$MAKEFUN_OUTPUT_DIR when that variable is set.
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
SEED = 20261117
rng = random.Random(SEED)

# ---------------------------------------------------------------- framebuffer

fb = bytearray(W * H * 3)


def blend(x, y, r, g, b, a):
    """Paint one pixel, alpha-blending over what is already there."""
    if x < 0 or x >= W or y < 0 or y >= H:
        return
    if a <= 0.0:
        return
    i = (y * W + x) * 3
    if a >= 1.0:
        fb[i] = r
        fb[i + 1] = g
        fb[i + 2] = b
        return
    fb[i] = int(fb[i] * (1.0 - a) + r * a + 0.5)
    fb[i + 1] = int(fb[i + 1] * (1.0 - a) + g * a + 0.5)
    fb[i + 2] = int(fb[i + 2] * (1.0 - a) + b * a + 0.5)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t) + 0.5),
            int(lerp(c1[1], c2[1], t) + 0.5),
            int(lerp(c1[2], c2[2], t) + 0.5))


def fill_rect(x0, y0, x1, y1, color, a=1.0):
    for y in range(max(0, y0), min(H, y1)):
        for x in range(max(0, x0), min(W, x1)):
            blend(x, y, color[0], color[1], color[2], a)


def fill_ellipse(cx, cy, rx, ry, color, a=1.0):
    """Filled axis-aligned ellipse, tested per pixel in its bbox."""
    x0 = max(0, int(cx - rx))
    x1 = min(W - 1, int(cx + rx) + 1)
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1):
        dy = (y - cy) / ry
        for x in range(x0, x1):
            dx = (x - cx) / rx
            if dx * dx + dy * dy <= 1.0:
                blend(x, y, color[0], color[1], color[2], a)


def disc(cx, cy, r, color, a=1.0):
    fill_ellipse(cx, cy, r, r, color, a)


def fill_poly(points, color, a=1.0):
    """Scanline polygon fill (even-odd rule)."""
    ys = [p[1] for p in points]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)) + 1)
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, y1p = points[i]
            x2, y2p = points[(i + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / (y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(max(0, int(xs[k]) + 1), min(W, int(xs[k + 1]) + 1)):
                blend(x, y, color[0], color[1], color[2], a)


def draw_line(x0, y0, x1, y1, width, color, a=1.0):
    """Thick line drawn as a chain of small discs."""
    length = math.hypot(x1 - x0, y1 - y0)
    steps = max(1, int(length))
    for s in range(steps + 1):
        t = s / steps
        disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, width / 2.0, color, a)


def arc_points(cx, cy, rx, ry, rot_deg, a0_deg, a1_deg, n=48):
    """Points along a rotated ellipse arc (angles in degrees)."""
    rot = math.radians(rot_deg)
    cr, sr = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(n + 1):
        ang = math.radians(a0_deg + (a1_deg - a0_deg) * i / n)
        ex, ey = rx * math.cos(ang), ry * math.sin(ang)
        pts.append((cx + ex * cr - ey * sr, cy + ex * sr + ey * cr))
    return pts


# ---------------------------------------------------------------- PNG encoder

def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += fb[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
           _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
           _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- sky and sun

# Gradient stops from the top of the frame down to the horizon.
SKY_STOPS = [
    (0.00, (24, 16, 64)),     # deep indigo
    (0.30, (62, 42, 110)),    # violet
    (0.55, (150, 74, 110)),   # mauve dusk
    (0.75, (228, 128, 58)),   # burning orange
    (1.00, (252, 198, 96)),   # gold at the horizon
]
HORIZON_Y = 800
SUN_CX, SUN_CY, SUN_R = 512, 520, 205


def draw_sky():
    for y in range(HORIZON_Y):
        t = y / HORIZON_Y
        for i in range(len(SKY_STOPS) - 1):
            t0, c0 = SKY_STOPS[i]
            t1, c1 = SKY_STOPS[i + 1]
            if t0 <= t <= t1:
                color = mix(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0.0)
                break
        else:
            color = SKY_STOPS[-1][1]
        for x in range(W):
            blend(x, y, color[0], color[1], color[2], 1.0)


def draw_stars():
    # Only in the dark upper third, so the dawn stays clean below.
    for _ in range(150):
        x = rng.uniform(0, W)
        y = rng.uniform(0, 300)
        r = rng.uniform(0.6, 1.8)
        bright = rng.uniform(0.35, 0.95)
        disc(x, y, r, (255, 244, 214), bright)


def draw_sun_glow():
    # One per-pixel pass: a soft radial halo that fades with distance.
    glow_r = 470
    x0 = max(0, int(SUN_CX - glow_r))
    x1 = min(W - 1, int(SUN_CX + glow_r) + 1)
    y0 = max(0, int(SUN_CY - glow_r))
    y1 = min(H - 1, int(SUN_CY + glow_r) + 1)
    for y in range(y0, y1):
        for x in range(x0, x1):
            d = math.hypot(x - SUN_CX, y - SUN_CY) / glow_r
            if d >= 1.0:
                continue
            a = 0.34 * (1.0 - d) * (1.0 - d)
            blend(x, y, 255, 196, 110, a)


def draw_rays():
    # Long thin triangles bursting out of the sun, alternating length.
    for i in range(34):
        ang = (i / 34.0) * 2.0 * math.pi + 0.06
        long_ray = (i % 2 == 0)
        r_out = SUN_R + (300 if long_ray else 165) + rng.uniform(-12, 12)
        r_in = SUN_R - 30
        half_w = 0.016 if long_ray else 0.011
        tip = (SUN_CX + r_out * math.cos(ang), SUN_CY + r_out * math.sin(ang))
        left = (SUN_CX + r_in * math.cos(ang - half_w),
                SUN_CY + r_in * math.sin(ang - half_w))
        right = (SUN_CX + r_in * math.cos(ang + half_w),
                 SUN_CY + r_in * math.sin(ang + half_w))
        fill_poly([tip, left, right], (255, 214, 130), 0.55)


def draw_sun():
    # Radial gradient, largest ring first: amber rim deepening inward
    # to a pale gold core, so the sun reads as a glowing disc.
    for ring in range(24):
        t = ring / 23.0
        r = SUN_R * (1.0 - t * 0.94)
        color = mix((250, 176, 72), (255, 248, 214), t)
        fill_ellipse(SUN_CX, SUN_CY, r, r, color, 1.0)


# ---------------------------------------------------------------- soil and seed

SOIL_TOP = 800
SEED_CX, SEED_CY = 512, 838


def draw_soil():
    # Dark earth with a gently mounded top edge.
    fill_rect(0, SOIL_TOP + 18, W, H, (38, 24, 16), 1.0)
    fill_ellipse(512, SOIL_TOP + 18, 720, 46, (38, 24, 16), 1.0)
    # Warm rim-light where the dawn catches the mound.
    fill_ellipse(512, SOIL_TOP + 16, 720, 40, (96, 58, 30), 0.35)
    # Speckles: lighter crumbs and darker clods, all seeded.
    for _ in range(900):
        x = rng.uniform(0, W)
        y = rng.uniform(SOIL_TOP + 8, H)
        if rng.random() < 0.5:
            disc(x, y, rng.uniform(0.7, 2.2), (112, 78, 44),
                 rng.uniform(0.25, 0.6))
        else:
            disc(x, y, rng.uniform(0.7, 2.0), (16, 10, 6),
                 rng.uniform(0.3, 0.65))
    # A few small pebbles catching the light.
    for _ in range(26):
        x = rng.uniform(40, W - 40)
        y = rng.uniform(SOIL_TOP + 30, H - 30)
        disc(x, y, rng.uniform(2.0, 4.5), (88, 62, 38), 0.9)
        disc(x - 1, y - 1, rng.uniform(0.8, 1.6), (170, 128, 80), 0.8)


def draw_seed():
    # Light spilling up out of the crack toward the sun.
    spill = [(SEED_CX - 26, SEED_CY - 10), (SEED_CX + 26, SEED_CY - 10),
             (SEED_CX + 70, SUN_CY + SUN_R - 40),
             (SEED_CX - 70, SUN_CY + SUN_R - 40)]
    fill_poly(spill, (255, 200, 100), 0.30)
    # Glow pooled inside the crack.
    fill_ellipse(SEED_CX, SEED_CY - 6, 60, 34, (255, 190, 90), 0.55)
    fill_ellipse(SEED_CX, SEED_CY - 6, 34, 20, (255, 232, 170), 0.85)

    # Two shell halves, pushed apart and tilted outward by the light.
    left = arc_points(SEED_CX - 44, SEED_CY + 4, 92, 52, -24, 55, 305)
    right = arc_points(SEED_CX + 44, SEED_CY + 4, 92, 52, 24, -125, 125)
    fill_poly(left + [(SEED_CX - 44, SEED_CY + 4)], (74, 44, 24), 1.0)
    fill_poly(right + [(SEED_CX + 44, SEED_CY + 4)], (74, 44, 24), 1.0)
    # Shell rim light on the inner edges, facing the crack.
    draw_line(SEED_CX - 8, SEED_CY - 34, SEED_CX - 16, SEED_CY + 34,
              5, (214, 150, 84), 0.9)
    draw_line(SEED_CX + 8, SEED_CY - 34, SEED_CX + 16, SEED_CY + 34,
              5, (214, 150, 84), 0.9)
    # Shell speckle and a hairline crack at the base.
    for _ in range(60):
        x = rng.uniform(SEED_CX - 130, SEED_CX + 130)
        y = rng.uniform(SEED_CY - 30, SEED_CY + 44)
        disc(x, y, rng.uniform(0.6, 1.6), (52, 30, 16),
             rng.uniform(0.3, 0.7))
    draw_line(SEED_CX - 4, SEED_CY + 40, SEED_CX + 6, SEED_CY + 52,
              2, (20, 12, 7), 0.9)


def draw_sparks():
    # Embers spiralling up from the crack into the sky.
    for i in range(70):
        t = i / 70.0
        spread = 26 + 300 * t
        x = SEED_CX + rng.uniform(-spread, spread)
        y = SEED_CY - 30 - t * 560 + rng.uniform(-26, 26)
        size = rng.uniform(1.0, 3.4) * (1.0 - t * 0.55)
        warm = rng.random() < 0.7
        color = (255, 214, 130) if warm else (255, 244, 214)
        disc(x, y, size, color, rng.uniform(0.5, 1.0))
        if rng.random() < 0.35:  # a few four-point star sparks
            draw_line(x - size * 2.4, y, x + size * 2.4, y, 1.2, color, 0.8)
            draw_line(x, y - size * 2.4, x, y + size * 2.4, 1.2, color, 0.8)


def draw_birds():
    # Tiny distant birds riding the updraft, small "v" strokes.
    for _ in range(14):
        x = rng.uniform(90, W - 90)
        y = rng.uniform(120, 470)
        s = rng.uniform(5, 11)
        lift = rng.uniform(0.3, 0.55)
        draw_line(x - s, y - s * lift, x, y, 2, (36, 22, 52), 0.85)
        draw_line(x, y, x + s, y - s * lift, 2, (36, 22, 52), 0.85)


# ---------------------------------------------------------------- text (5x7 font)

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}

TEXT = "IT WAS IN THE SEED ALL ALONG."


def draw_text(text, cx, y, scale, color, a=1.0):
    char_w = 6 * scale
    total = len(text) * char_w - scale
    x = cx - total // 2
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == "1":
                    fill_rect(x + col * scale, y + row * scale,
                              x + (col + 1) * scale, y + (row + 1) * scale,
                              color, a)
        x += char_w


# ---------------------------------------------------------------- scene

def main():
    draw_sky()
    draw_stars()
    draw_sun_glow()
    draw_rays()
    draw_sun()
    draw_soil()
    draw_seed()
    draw_sparks()
    draw_birds()
    draw_text(TEXT, W // 2, 946, 3, (255, 232, 180), 0.95)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    path = os.path.join(out_dir, "entry.png") if out_dir else "entry.png"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    write_png(path)
    print(f"wrote {path} ({W}x{H})")


if __name__ == "__main__":
    main()
