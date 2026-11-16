#!/usr/bin/env python3
"""ai-excited-01 entry — "IT WAS IN THE SEED ALL ALONG."

A tiny seed cracks open at the bottom of the frame and a whole sun
rises out of it. The smallest thing holds the biggest light: that
scale twist is the hook. The image is drawn entirely in code with
the Python standard library only — no image files are read, no
network, no timestamps. One fixed seed drives every random choice,
so two runs write byte-identical PNGs.

Layout (1024x1024):
  * dawn sky, deep indigo at the top melting to gold at the horizon
  * a large sun rising out of the crack, with long thin rays and a
    soft radial glow
  * dark soil along the bottom, and the split seed in the centre,
    its two halves pushed apart by the light spilling from the crack
  * sparks and tiny birds rising from the seed into the sky
  * one quiet line of text at the bottom, in a small 5x7 font

Run:  python3 main.py
  Writes entry.png next to this script, or to $MAKEFUN_OUTPUT_DIR
  when that is set. Deterministic: run it twice, the bytes match.
"""

import math
import os
import random
import struct
import zlib

WIDTH = 1024
HEIGHT = 1024
SEED = 20261117

# ------------------------------------------------------------------
# Canvas: a plain RGB framebuffer with alpha blending.
# ------------------------------------------------------------------


class Canvas:
    """An RGB image held as one flat bytearray, row-major."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 3)

    def _index(self, x, y):
        return (y * self.width + x) * 3

    def put(self, x, y, color):
        """Set one pixel, silently ignoring out-of-frame points."""
        if 0 <= x < self.width and 0 <= y < self.height:
            i = self._index(x, y)
            self.pixels[i] = color[0]
            self.pixels[i + 1] = color[1]
            self.pixels[i + 2] = color[2]

    def blend(self, x, y, color, alpha):
        """Blend a colour over the pixel at (x, y); alpha in 0..1."""
        if alpha <= 0.0:
            return
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        i = self._index(x, y)
        if alpha >= 1.0:
            self.pixels[i] = color[0]
            self.pixels[i + 1] = color[1]
            self.pixels[i + 2] = color[2]
            return
        inv = 1.0 - alpha
        self.pixels[i] = int(self.pixels[i] * inv + color[0] * alpha + 0.5)
        self.pixels[i + 1] = int(self.pixels[i + 1] * inv + color[1] * alpha + 0.5)
        self.pixels[i + 2] = int(self.pixels[i + 2] * inv + color[2] * alpha + 0.5)

    def add(self, x, y, color, amount):
        """Add a colour scaled by amount (0..1) — a light falloff."""
        if amount <= 0.0:
            return
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        i = self._index(x, y)
        self.pixels[i] = min(255, self.pixels[i] + int(color[0] * amount))
        self.pixels[i + 1] = min(255, self.pixels[i + 1] + int(color[1] * amount))
        self.pixels[i + 2] = min(255, self.pixels[i + 2] + int(color[2] * amount))

    def fill_row(self, y, color):
        """Paint one whole scanline a single colour."""
        if 0 <= y < self.height:
            i = y * self.width * 3
            self.pixels[i:i + self.width * 3] = bytes(color) * self.width

    def fill_rect(self, x0, y0, x1, y1, color):
        """Paint an axis-aligned rectangle, clipped to the frame."""
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.width, x1)
        y1 = min(self.height, y1)
        row = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            i = y * self.width * 3 + x0 * 3
            self.pixels[i:i + (x1 - x0) * 3] = row


def lerp_color(a, b, t):
    """Linear blend between two RGB colours; t in 0..1."""
    return (
        int(a[0] + (b[0] - a[0]) * t + 0.5),
        int(a[1] + (b[1] - a[1]) * t + 0.5),
        int(a[2] + (b[2] - a[2]) * t + 0.5),
    )


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


# ------------------------------------------------------------------
# PNG encoder: 8-bit RGB, no interlace, filter 0 on every row.
# ------------------------------------------------------------------


def _chunk(kind, payload):
    out = struct.pack(">I", len(payload)) + kind + payload
    out += struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    return out


def encode_png(canvas):
    """Serialise the canvas as a PNG byte string."""
    header = struct.pack(
        ">IIBBBBB",
        canvas.width, canvas.height, 8, 2, 0, 0, 0,
    )
    raw = bytearray()
    stride = canvas.width * 3
    for y in range(canvas.height):
        raw.append(0)
        start = y * stride
        raw += canvas.pixels[start:start + stride]
    data = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", header)
    png += _chunk(b"IDAT", data)
    png += _chunk(b"IEND", b"")
    return png


# ------------------------------------------------------------------
# Drawing primitives. All of them are written for this picture:
# smooth filled ellipses, scanline polygons, soft radial light,
# thin rays, a seeded starfield and a small 5x7 bitmap font.
# ------------------------------------------------------------------


def draw_ellipse(canvas, cx, cy, rx, ry, color, alpha=1.0):
    """Filled ellipse with a one-pixel soft edge.

    A pixel is fully inside when its normalised distance from the
    centre is below 1, and fades out across one pixel of distance,
    which keeps large round shapes free of stair steps.
    """
    x0 = max(0, int(cx - rx - 2))
    x1 = min(canvas.width, int(cx + rx + 3))
    y0 = max(0, int(cy - ry - 2))
    y1 = min(canvas.height, int(cy + ry + 3))
    for y in range(y0, y1):
        ny = (y + 0.5 - cy) / ry
        for x in range(x0, x1):
            nx = (x + 0.5 - cx) / rx
            d = math.sqrt(nx * nx + ny * ny)
            if d >= 1.0 + 1.0 / max(rx, ry):
                continue
            edge = clamp01((1.0 + 1.0 / max(rx, ry) - d) * max(rx, ry))
            canvas.blend(x, y, color, alpha * edge)


def draw_half_ellipse(canvas, cx, cy, rx, ry, color, side, alpha=1.0):
    """One half of a filled ellipse: side -1 keeps x < cx, +1 keeps x > cx."""
    x0 = max(0, int(cx - rx - 2))
    x1 = min(canvas.width, int(cx + rx + 3))
    y0 = max(0, int(cy - ry - 2))
    y1 = min(canvas.height, int(cy + ry + 3))
    for y in range(y0, y1):
        ny = (y + 0.5 - cy) / ry
        for x in range(x0, x1):
            if side < 0 and x + 0.5 >= cx:
                continue
            if side > 0 and x + 0.5 < cx:
                continue
            nx = (x + 0.5 - cx) / rx
            d = math.sqrt(nx * nx + ny * ny)
            if d >= 1.0 + 1.0 / max(rx, ry):
                continue
            edge = clamp01((1.0 + 1.0 / max(rx, ry) - d) * max(rx, ry))
            canvas.blend(x, y, color, alpha * edge)


def draw_polygon(canvas, points, color, alpha=1.0):
    """Filled polygon by scanline, one row at a time."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    y0 = max(0, int(min(ys)))
    y1 = min(canvas.height, int(max(ys)) + 1)
    n = len(points)
    for y in range(y0, y1):
        xs = []
        for i in range(n):
            ax, ay = points[i]
            bx, by = points[(i + 1) % n]
            if (ay <= y + 0.5 < by) or (by <= y + 0.5 < ay):
                t = (y + 0.5 - ay) / (by - ay)
                xs.append(ax + t * (bx - ax))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            xa = max(0, int(math.ceil(xs[i])))
            xb = min(canvas.width, int(math.floor(xs[i + 1])))
            for x in range(xa, xb):
                canvas.blend(x, y, color, alpha)


def draw_glow(canvas, cx, cy, radius, color, strength):
    """Soft radial light: brightest at the centre, fading to nothing.

    Additive, so it can only lift the pixels underneath — it never
    darkens the sky it shines through.
    """
    x0 = max(0, int(cx - radius))
    x1 = min(canvas.width, int(cx + radius) + 1)
    y0 = max(0, int(cy - radius))
    y1 = min(canvas.height, int(cy + radius) + 1)
    for y in range(y0, y1):
        dy = (y + 0.5 - cy) / radius
        for x in range(x0, x1):
            dx = (x + 0.5 - cx) / radius
            d = math.sqrt(dx * dx + dy * dy)
            if d >= 1.0:
                continue
            fall = (1.0 - d) * (1.0 - d)
            canvas.add(x, y, color, strength * fall)


def draw_ray(canvas, cx, cy, angle_deg, length, width, color, alpha):
    """One thin triangular ray from (cx, cy) out at angle_deg."""
    ang = math.radians(angle_deg)
    dx = math.cos(ang)
    dy = math.sin(ang)
    # A triangle: a wide base at the centre tapering to a point.
    tip = (cx + dx * length, cy + dy * length)
    px = -dy * width
    py = dx * width
    base1 = (cx + px, cy + py)
    base2 = (cx - px, cy - py)
    draw_polygon(canvas, [base1, base2, tip], color, alpha)


def draw_starfield(canvas, rng, count, y_max, bright):
    """Seeded stars in the upper sky: dots, a few with a cross glint."""
    for _ in range(count):
        x = rng.randint(0, canvas.width - 1)
        y = rng.randint(0, y_max)
        size = rng.choice([1, 1, 1, 2, 2, 3])
        col = rng.choice([(255, 255, 255), (255, 240, 200), (200, 220, 255)])
        a = rng.uniform(0.35, 1.0)
        if size == 1:
            canvas.blend(x, y, col, a * bright)
        else:
            for ox in range(-size // 2, size // 2 + 1):
                for oy in range(-size // 2, size // 2 + 1):
                    canvas.blend(x + ox, y + oy, col, a * bright * 0.7)
        if rng.random() < 0.12:
            # A four-point glint on the brightest few.
            for ox, oy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                canvas.blend(x + ox, y + oy, col, a * bright * 0.5)


# A 5x7 bitmap font, one row per string, '#' lit. Only the letters
# this picture needs, plus space and the full stop.
FONT_5X7 = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00000", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def draw_text(canvas, text, x, y, scale, color, alpha=1.0):
    """Draw one line of caps text with the 5x7 font, left-aligned at x."""
    cursor = x
    for ch in text:
        glyph = FONT_5X7.get(ch)
        if glyph is None:
            cursor += 6 * scale
            continue
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    canvas.fill_rect(
                        cursor + col * scale, y + row * scale,
                        cursor + (col + 1) * scale, y + (row + 1) * scale,
                        color,
                    )
        cursor += 6 * scale
    return cursor


def text_width(text, scale):
    return len(text) * 6 * scale - scale


# ------------------------------------------------------------------
# The scene.
# ------------------------------------------------------------------


def paint_vertical_gradient(canvas, stops, y0, y1):
    """Fill rows y0..y1 with colours interpolated between stops.

    stops is a list of (y, rgb) in increasing y; rows between two
    stops blend linearly, rows outside the range take the nearest.
    """
    for y in range(y0, y1):
        if y <= stops[0][0]:
            color = stops[0][1]
        elif y >= stops[-1][0]:
            color = stops[-1][1]
        else:
            color = stops[-1][1]
            for i in range(len(stops) - 1):
                ya, ca = stops[i]
                yb, cb = stops[i + 1]
                if ya <= y <= yb:
                    t = 0.0 if yb == ya else (y - ya) / (yb - ya)
                    color = lerp_color(ca, cb, t)
                    break
        canvas.fill_row(y, color)


def draw_bird(canvas, cx, cy, size, color, alpha):
    """A tiny bird: two short strokes meeting in a shallow V."""
    draw_polygon(
        canvas,
        [
            (cx - size, cy - size * 0.45),
            (cx, cy + size * 0.2),
            (cx - size * 0.55, cy - size * 0.15),
        ],
        color, alpha,
    )
    draw_polygon(
        canvas,
        [
            (cx + size, cy - size * 0.45),
            (cx, cy + size * 0.2),
            (cx + size * 0.55, cy - size * 0.15),
        ],
        color, alpha,
    )


def build_scene():
    """Draw the seed, the sun and the sky. Returns the canvas."""
    rng = random.Random(SEED)
    canvas = Canvas(WIDTH, HEIGHT)

    # Dawn sky, deep indigo up top melting to gold at the horizon.
    sky_stops = [
        (0, (24, 10, 44)),
        (260, (56, 26, 88)),
        (480, (116, 44, 92)),
        (660, (190, 84, 62)),
        (800, (240, 150, 70)),
        (820, (250, 175, 85)),
    ]
    paint_vertical_gradient(canvas, sky_stops, 0, 821)

    # Stars, only where the sky is still dark.
    draw_starfield(canvas, rng, 210, 470, 0.9)

    # The sun: a wide glow, long thin rays, then a hot disc.
    # It sits almost on top of the seed, hatching out of the crack.
    sun_x, sun_y = 512, 590
    draw_glow(canvas, sun_x, sun_y, 430, (255, 170, 60), 0.5)
    draw_glow(canvas, sun_x, sun_y, 230, (255, 212, 95), 0.65)
    for k in range(12):
        angle = k * 30.0 + 7.0
        length = 385 if k % 2 == 0 else 265
        width = 7.0 if k % 2 == 0 else 4.0
        alpha = 0.30 if k % 2 == 0 else 0.18
        draw_ray(canvas, sun_x, sun_y, angle, length, width,
                 (255, 200, 80), alpha)
    draw_ellipse(canvas, sun_x, sun_y, 142, 142, (255, 140, 30))
    draw_ellipse(canvas, sun_x, sun_y, 128, 128, (255, 205, 70))
    draw_ellipse(canvas, sun_x, sun_y, 100, 100, (255, 246, 214))

    # A column of light where the sun meets the crack, so the two
    # halves of the picture belong to each other.
    draw_glow(canvas, 512, 745, 110, (255, 190, 90), 0.8)

    # Dark soil along the bottom, with a warm horizon glow.
    soil_stops = [(820, (52, 28, 48)), (1024, (20, 11, 24))]
    paint_vertical_gradient(canvas, soil_stops, 821, 1024)
    draw_glow(canvas, 512, 822, 60, (255, 180, 80), 0.35)
    for _ in range(260):
        x = rng.randint(0, WIDTH - 1)
        y = rng.randint(830, HEIGHT - 1)
        shade = rng.choice([(30, 18, 34), (70, 40, 60), (90, 55, 70)])
        canvas.blend(x, y, shade, rng.uniform(0.25, 0.6))

    # The seed, split in two by the light. First the glow of the
    # crack itself, then the two dark halves pushed apart.
    seed_y = 860
    draw_glow(canvas, 512, seed_y, 110, (255, 200, 80), 0.9)
    crack = [
        (492, seed_y - 88), (512, seed_y - 46), (494, seed_y - 10),
        (514, seed_y + 24), (496, seed_y + 58), (512, seed_y + 92),
        (530, seed_y + 56), (514, seed_y + 20), (531, seed_y - 14),
        (513, seed_y - 50), (528, seed_y - 90),
    ]
    draw_polygon(canvas, crack, (255, 224, 130), 0.95)
    draw_half_ellipse(canvas, 512 - 30, seed_y, 180, 105, (40, 21, 10), -1)
    draw_half_ellipse(canvas, 512 + 30, seed_y, 180, 105, (40, 21, 10), 1)
    # A warm rim on the inner edge of each half, lit by the crack.
    for yy in range(seed_y - 78, seed_y + 80, 4):
        t = 1.0 - abs(yy - seed_y) / 80.0
        canvas.blend(512 - 34, yy, (255, 160, 70), 0.55 * t)
        canvas.blend(512 + 34, yy, (255, 160, 70), 0.55 * t)

    # Sparks and tiny birds rising from the seed into the sky.
    for _ in range(46):
        t = rng.random()
        x = int(512 + (rng.random() - 0.5) * (120 + 420 * t))
        y = int(seed_y - 40 - t * 560)
        size = rng.choice([1, 1, 2, 2, 3])
        col = rng.choice([(255, 233, 168), (255, 255, 255), (255, 190, 90)])
        a = rng.uniform(0.4, 1.0)
        if size == 1:
            canvas.blend(x, y, col, a)
        else:
            draw_ellipse(canvas, x, y, size, size, col, a * 0.8)
    bird_spots = [(330, 300, 16), (700, 250, 13), (620, 340, 18),
                  (400, 210, 12), (760, 400, 15)]
    for bx, by, bs in bird_spots:
        draw_bird(canvas, bx, by, bs, (45, 22, 55), 0.85)

    # One quiet line at the bottom, in warm gold.
    line = "IT WAS IN THE SEED ALL ALONG."
    scale = 3
    width = text_width(line, scale)
    draw_text(canvas, line, (WIDTH - width) // 2, 986, scale,
              (255, 210, 120))
    return canvas


def main():
    canvas = build_scene()
    data = encode_png(canvas)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "entry.png")
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "entry.png")
    with open(path, "wb") as handle:
        handle.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
