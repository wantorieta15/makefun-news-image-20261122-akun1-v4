#!/usr/bin/env python3
"""Sunday 22 November 2026 in one page: 33 stories, 7 regions.

A one-page newspaper drawn entirely in code with the Python 3 standard
library only. Writes entry.png (1024x1024) to $MAKEFUN_OUTPUT_DIR.
Deterministic: same input, same bytes, every run. No system fonts, no
network, no files read, no randomness.

Text is rendered with a 5x7 bitmap face defined below (all caps, the
classic newspaper caps look), scaled 1x for body copy, 2x for card
headlines and 6x for the masthead title. Every picture and the dotted
world map are drawn in code from flat shapes: no speckle, no noise, no
paper grain, so the page stays clean at any size.

What the page carries, in the order a reader meets it:
  * masthead + the date in a big title, and a two-line deck naming the
    three biggest stories of the day;
  * a region bar (7 regions, counts add up to 33) and a UTC timeline
    strip with the press time;
  * three large top stories with flat illustrated scenes and a status
    badge on every card (CONFIRMED / CLAIM / REPORTED / PENDING);
  * a THE DAY IN NUMBERS panel with six big verified figures;
  * ten more illustrated stories, each with its own flat icon scene
    and status badge;
  * ALSO ON SUNDAY, 20 more numbered stories, each naming its outlet;
  * a dotted world map with numbered pins matching the 13 illustrated
    stories, a legend explaining the status tags, and a DATE CHECK box
    naming the stories left out because they belong to other days.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER   = (247, 241, 222)
INK     = (28, 28, 28)
INKSOFT = (74, 70, 60)
RED     = (178, 38, 30)
DARKRED = (138, 24, 18)
CREAM   = (252, 248, 235)
WHITE   = (255, 255, 255)
BLACK   = (12, 12, 12)
GOLD    = (198, 152, 48)
BLUE    = (31, 78, 156)
NAVY    = (18, 32, 64)
GREEN   = (30, 122, 70)
AMBER   = (199, 122, 26)
BROWN   = (138, 109, 59)
PURPLE  = (106, 74, 158)
GREY    = (120, 116, 104)
TAN     = (176, 158, 104)
SKY     = (146, 196, 224)

# ---------------------------------------------------------------- canvas
# One flat bytearray, row-major RGB. No supersampling: the bitmap face
# and the flat shapes are crisp at 1x by construction.
canvas = bytearray(bytes(PAPER) * W * H)


def fill_rect(x, y, w, h, c):
    # floor/ceil (never round): a 1px rect at a .5 offset must still
    # paint at least one pixel; round() can collapse it to zero width.
    x0 = int(math.floor(x))
    y0 = int(math.floor(y))
    x1 = int(math.ceil(x + w))
    y1 = int(math.ceil(y + h))
    if x0 < 0:
        x0 = 0
    if y0 < 0:
        y0 = 0
    if x1 > W:
        x1 = W
    if y1 > H:
        y1 = H
    if x1 <= x0 or y1 <= y0:
        return
    span = bytes(c) * (x1 - x0)
    for yy in range(y0, y1):
        o = (yy * W + x0) * 3
        canvas[o:o + len(span)] = span


def rect_outline(x, y, w, h, c, t=1):
    fill_rect(x, y, w, t, c)
    fill_rect(x, y + h - t, w, t, c)
    fill_rect(x, y, t, h, c)
    fill_rect(x + w - t, y, t, h, c)


def fill_circle(cx, cy, r, c):
    cx, cy, r = float(cx), float(cy), float(r)
    y0 = max(0, int(math.floor(cy - r)))
    y1 = min(H - 1, int(math.ceil(cy + r)))
    for yy in range(y0, y1 + 1):
        dy = yy + 0.5 - cy
        dx = math.sqrt(max(0.0, r * r - dy * dy))
        x0 = int(math.ceil(cx - dx))
        x1 = int(math.floor(cx + dx)) + 1
        if x0 < 0:
            x0 = 0
        if x1 > W:
            x1 = W
        if x1 > x0:
            span = bytes(c) * (x1 - x0)
            o = (yy * W + x0) * 3
            canvas[o:o + len(span)] = span


def fill_ellipse(cx, cy, rx, ry, c):
    cx, cy, rx, ry = float(cx), float(cy), float(rx), float(ry)
    y0 = max(0, int(math.floor(cy - ry)))
    y1 = min(H - 1, int(math.ceil(cy + ry)))
    for yy in range(y0, y1 + 1):
        dy = (yy + 0.5 - cy) / ry if ry else 0.0
        dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
        x0 = int(math.ceil(cx - dx))
        x1 = int(math.floor(cx + dx)) + 1
        if x0 < 0:
            x0 = 0
        if x1 > W:
            x1 = W
        if x1 > x0:
            span = bytes(c) * (x1 - x0)
            o = (yy * W + x0) * 3
            canvas[o:o + len(span)] = span


def fill_polygon(pts, c):
    """Even-odd scanline fill of a polygon given in page coordinates."""
    if len(pts) < 3:
        return
    ymin = max(0, int(math.floor(min(p[1] for p in pts))))
    ymax = min(H - 1, int(math.ceil(max(p[1] for p in pts))))
    n = len(pts)
    for yy in range(ymin, ymax + 1):
        yc = yy + 0.5
        xs = []
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if (y1 <= yc < y2) or (y2 <= yc < y1):
                t = (yc - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            x0 = int(math.ceil(xs[k]))
            x1 = int(math.floor(xs[k + 1])) + 1
            if x0 < 0:
                x0 = 0
            if x1 > W:
                x1 = W
            if x1 > x0:
                span = bytes(c) * (x1 - x0)
                o = (yy * W + x0) * 3
                canvas[o:o + len(span)] = span


def thick_line(x1, y1, x2, y2, w, c):
    """A thick straight segment, drawn as a polygon with round ends."""
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy)
    if ln < 0.001:
        fill_circle(x1, y1, w / 2.0, c)
        return
    nx, ny = -dy / ln * w / 2.0, dx / ln * w / 2.0
    fill_polygon([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                  (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], c)
    fill_circle(x1, y1, w / 2.0, c)
    fill_circle(x2, y2, w / 2.0, c)


def thin_line(x1, y1, x2, y2, c):
    """A 1-pixel line (Bresenham)."""
    x1, y1 = int(round(x1)), int(round(y1))
    x2, y2 = int(round(x2)), int(round(y2))
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    x, y = x1, y1
    while True:
        if 0 <= x < W and 0 <= y < H:
            o = (y * W + x) * 3
            canvas[o:o + 3] = bytes(c)
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def vgrad(x, y, w, h, c1, c2):
    """Flat vertical gradient, one solid row per step (no dither)."""
    y0 = int(round(y))
    y1 = int(round(y + h))
    for yy in range(y0, y1):
        t = (yy - y) / h if h else 0.0
        fill_rect(x, yy, w, 1, (int(c1[0] + (c2[0] - c1[0]) * t),
                                int(c1[1] + (c2[1] - c1[1]) * t),
                                int(c1[2] + (c2[2] - c1[2]) * t)))


def mix(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def write_png(path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += canvas[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- 5x7 face
# A plain 5x7 bitmap face, 7 rows of 5 bits each. All text on the page is
# set in capitals (the classic broadsheet caps look); lower-case input is
# folded to capitals when drawn, so only one case is needed.
F5 = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "~": ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
}
# Middle dot and degree sign are drawn with the same small patterns.
F5["\u00b7"] = ("00000", "00000", "00000", "01100", "01100", "00000", "00000")
F5["\u2022"] = ("00000", "00000", "01100", "01110", "01110", "01100", "00000")
F5["\u00b0"] = ("01100", "10010", "10010", "01100", "00000", "00000", "00000")

# Fold typographic punctuation to the plain glyphs above.
FOLD = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u00b0": "\u00b0"}


def _norm(text):
    out = []
    for ch in text:
        ch = FOLD.get(ch, ch)
        out.append(ch.upper())
    return "".join(out)


def text_width(text, scale=1):
    return len(_norm(text)) * 6 * scale - scale if text else 0


def text(x, y, s, c, scale=1):
    """Draw text; (x, y) is the top-left of the 7px cell, scaled.

    The origin is rounded to an integer first: a .5 offset makes
    Python's banker's rounding collapse 1px glyph columns to zero
    width, which eats the vertical stems of every letter.
    """
    x = int(round(x))
    y = int(round(y))
    s = _norm(s)
    cx = x
    for ch in s:
        g = F5.get(ch, F5["?"])
        for r in range(7):
            row = g[r]
            for col in range(5):
                if row[col] == "1":
                    fill_rect(cx + col * scale, y + r * scale,
                              scale, scale, c)
        cx += 6 * scale


def text_c(cx, y, s, c, scale=1):
    text(cx - text_width(s, scale) / 2.0, y, s, c, scale)


def wrap(text, maxw, scale=1):
    """Greedy word wrap; returns a list of lines."""
    words = _norm(text).split(" ")
    lines = []
    cur = ""
    for wd in words:
        trial = wd if not cur else cur + " " + wd
        if text_width(trial, scale) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def para(x, y, s, maxw, c, scale=1, lh=None):
    if lh is None:
        lh = 7 * scale + 2
    lines = wrap(s, maxw, scale)
    for ln in lines:
        text(x, y, ln, c, scale)
        y += lh
    return len(lines)


def chip(x, y, s, bg, fg):
    """Small label chip (1x text); returns its width."""
    w = text_width(s, 1) + 8
    fill_rect(x, y, w, 13, bg)
    text(x + 4, y + 3, s, fg, 1)
    return w


BADGE = {"CONFIRMED": GREEN, "CLAIM": AMBER,
         "REPORTED": BLUE, "PENDING": PURPLE}

# ---------------------------------------------------------------- pictures
def flame(x, y, s):
    """Layered flame; base centre (x, y), height about 15*s."""
    fill_polygon([(x - 6 * s, y), (x - 7.5 * s, y - 6 * s),
                  (x - 2 * s, y - 12 * s), (x + 1 * s, y - 15 * s),
                  (x + 4 * s, y - 10 * s), (x + 7 * s, y - 5 * s),
                  (x + 6 * s, y)], (206, 52, 28))
    fill_polygon([(x - 4 * s, y), (x - 5 * s, y - 4 * s),
                  (x - 1 * s, y - 9 * s), (x + 1 * s, y - 11 * s),
                  (x + 3.5 * s, y - 7 * s), (x + 4.5 * s, y - 3 * s),
                  (x + 4 * s, y)], (240, 128, 32))
    fill_polygon([(x - 2.2 * s, y), (x - 2.8 * s, y - 2.5 * s),
                  (x - 0.5 * s, y - 6.5 * s), (x + 1 * s, y - 7.5 * s),
                  (x + 2.2 * s, y - 4 * s), (x + 2.4 * s, y - 1 * s),
                  (x + 2 * s, y)], (248, 205, 80))


def smoke(x, y, n, r, drift, c0, c1):
    for i in range(n):
        cx = x + drift * i
        cy = y - i * 7
        rr = r * (1 + 0.13 * i)
        fill_circle(cx, cy, rr, mix(c0, c1, i / max(1, n - 1)))


def building(x, y, w, h, c, lit, win=(245, 197, 66)):
    """Dark block, top-left (x, y); lit windows in a fixed pattern."""
    fill_rect(x, y, w, h, c)
    fill_rect(x, y, w, 2, mix(c, WHITE, 0.18))
    cols = max(1, int(w // 7))
    rows = max(1, int(h // 9))
    for r in range(rows):
        for cc in range(cols):
            if ((r * 7 + cc * 3 + int(x)) % 10) < int(lit * 10):
                fill_rect(x + 3 + cc * 7, y + 4 + r * 9, 3, 4, win)


def person(x, y, s, skin, hair, suit):
    """Seated delegate: head centre (x, y), shoulders below."""
    fill_circle(x, y - 1.5 * s, 6.4 * s, hair)
    fill_circle(x, y + 0.8 * s, 5.6 * s, skin)
    fill_polygon([(x - 11 * s, y + 19 * s), (x - 8 * s, y + 8 * s),
                  (x + 8 * s, y + 8 * s), (x + 11 * s, y + 19 * s)], suit)
    fill_polygon([(x - 2.5 * s, y + 8 * s), (x + 2.5 * s, y + 8 * s),
                  (x, y + 14 * s)], WHITE)
    fill_polygon([(x - 1 * s, y + 9 * s), (x + 1 * s, y + 9 * s),
                  (x + 0.8 * s, y + 15 * s), (x - 0.8 * s, y + 15 * s)],
                 (40, 40, 40))


def flag(x, y, w, h, stripes):
    """Tiny flag on a pole; stripes = list of colours top to bottom."""
    thin_line(x, y, x, y + h + 7, (60, 60, 60))
    n = len(stripes)
    for i, c in enumerate(stripes):
        fill_rect(x, y + i * h / n, w, h / n + 0.6, c)


def scene_cop31(x0, y0, w, h):
    vgrad(x0, y0, w, h, (216, 224, 230), (238, 228, 198))
    for lx in (x0 + 50, x0 + 125, x0 + 200):
        thin_line(lx, y0, lx, y0 + 12, (90, 80, 60))
        fill_polygon([(lx - 6, y0 + 12), (lx + 6, y0 + 12), (lx + 2, y0 + 18),
                      (lx - 2, y0 + 18)], (70, 60, 40))
        fill_circle(lx, y0 + 20, 3, (250, 220, 130))
    # big screen with a globe
    fill_rect(x0 + 10, y0 + 26, 84, 46, (24, 42, 68))
    fill_rect(x0 + 13, y0 + 29, 78, 40, SKY)
    fill_circle(x0 + 52, y0 + 49, 14, (52, 110, 168))
    fill_ellipse(x0 + 47, y0 + 43, 6, 3.5, (84, 160, 90))
    fill_ellipse(x0 + 57, y0 + 52, 5, 3.5, (84, 160, 90))
    fill_ellipse(x0 + 50, y0 + 57, 3.5, 2, (84, 160, 90))
    thin_line(x0 + 38, y0 + 49, x0 + 66, y0 + 49, (220, 235, 245))
    thin_line(x0 + 52, y0 + 35, x0 + 52, y0 + 63, (220, 235, 245))
    # flags row
    flag(x0 + 104, y0 + 30, 13, 9, [(178, 38, 30), (178, 38, 30)])
    flag(x0 + 120, y0 + 30, 13, 9, [(31, 78, 156), (31, 78, 156)])
    flag(x0 + 136, y0 + 30, 13, 9, [(120, 180, 220), (120, 180, 220)])
    flag(x0 + 152, y0 + 30, 13, 9, [(30, 140, 70), (240, 210, 60),
                                    (30, 140, 70)])
    flag(x0 + 168, y0 + 30, 13, 9, [(240, 130, 40), (255, 255, 255),
                                    (30, 140, 70)])
    # clock: 03:00
    fill_circle(x0 + 222, y0 + 34, 14, (250, 248, 240))
    rect_outline(x0 + 208, y0 + 20, 28, 28, (40, 40, 40), 2)
    for a in range(12):
        ang = a * math.pi / 6
        thin_line(x0 + 222 + 10 * math.sin(ang), y0 + 34 - 10 * math.cos(ang),
                  x0 + 222 + 12 * math.sin(ang), y0 + 34 - 12 * math.cos(ang),
                  (40, 40, 40))
    thick_line(x0 + 222, y0 + 34, x0 + 222 + 7, y0 + 34, 2, (30, 30, 30))
    thick_line(x0 + 222, y0 + 34, x0 + 222, y0 + 34 - 10, 2, (30, 30, 30))
    fill_circle(x0 + 222, y0 + 34, 1.5, RED)
    # delegates behind the table
    skins = [(232, 190, 150), (198, 150, 110), (238, 200, 165),
             (210, 165, 125), (228, 185, 145), (190, 140, 100),
             (236, 196, 158)]
    hairs = [(40, 32, 24), (90, 90, 90), (20, 20, 20), (120, 100, 70),
             (60, 45, 30), (30, 30, 30), (150, 150, 150)]
    suits = [(31, 58, 110), (90, 40, 40), (40, 90, 70), (70, 70, 80),
             (120, 60, 90), (50, 70, 50), (140, 90, 30)]
    for i in range(7):
        px = x0 + 24 + i * 30
        person(px, y0 + 74, 1.0, skins[i], hairs[i], suits[i])
        thin_line(px + 8, y0 + 96, px + 12, y0 + 82, (40, 40, 40))
        fill_circle(px + 12, y0 + 81, 1.6, (40, 40, 40))
    # long table
    fill_rect(x0 + 8, y0 + 96, w - 16, 8, (122, 82, 48))
    fill_rect(x0 + 8, y0 + 104, w - 16, 28, (96, 62, 34))
    fill_rect(x0 + 8, y0 + 104, w - 16, 3, (150, 108, 66))
    for i in range(7):
        px = x0 + 24 + i * 30
        fill_rect(px - 9, y0 + 106, 18, 7, WHITE)
        fill_rect(px - 9, y0 + 106, 18, 2, (200, 200, 200))
        fill_rect(px + 12, y0 + 100, 7, 4, WHITE)
        fill_rect(px + 13, y0 + 101, 5, 2, (210, 225, 235))
    # floor
    fill_rect(x0, y0 + 132, w, 20, (88, 62, 36))
    fill_rect(x0, y0 + 132, w, 2, (140, 100, 60))


def scene_kyiv(x0, y0, w, h):
    vgrad(x0, y0, w, h, (13, 21, 46), (28, 40, 72))
    # fixed stars (part of the night scene, not texture)
    for (sx, sy) in [(20, 12), (48, 26), (80, 10), (116, 20), (150, 8),
                     (182, 24), (210, 12), (236, 30), (32, 44), (100, 40),
                     (168, 44), (66, 58), (136, 56), (198, 58)]:
        fill_rect(x0 + sx, y0 + sy, 2, 2, (230, 235, 250))
    # moon
    fill_circle(x0 + 222, y0 + 24, 13, (214, 206, 178))
    fill_circle(x0 + 222, y0 + 24, 9, (238, 232, 208))
    fill_circle(x0 + 218, y0 + 20, 2, (214, 206, 178))
    fill_circle(x0 + 226, y0 + 28, 1.8, (214, 206, 178))
    # searchlight beams (narrow, pale)
    fill_polygon([(x0 + 44, y0 + 152), (x0 + 54, y0 + 152),
                  (x0 + 98, y0 + 20), (x0 + 90, y0 + 20)], (140, 132, 86))
    fill_polygon([(x0 + 196, y0 + 152), (x0 + 206, y0 + 152),
                  (x0 + 180, y0 + 28), (x0 + 172, y0 + 28)], (140, 132, 86))
    # drones with dotted trails
    for (dx, dy) in [(50, 28), (100, 16), (150, 32), (190, 20),
                     (70, 48), (210, 44), (130, 12)]:
        for k in range(5):
            fill_circle(x0 + dx - k * 5, y0 + dy + k * 3, 1, (200, 200, 210))
        fill_polygon([(x0 + dx - 5, y0 + dy), (x0 + dx, y0 + dy - 3),
                      (x0 + dx + 5, y0 + dy), (x0 + dx, y0 + dy + 3)],
                     (16, 16, 20))
        fill_circle(x0 + dx, y0 + dy, 1.5, (230, 60, 40))
    # skyline
    base = y0 + 152
    specs = [(0, 22, 50), (24, 28, 66), (54, 20, 42), (76, 26, 76),
             (104, 18, 46), (124, 30, 62), (156, 22, 70), (180, 26, 52),
             (208, 20, 60), (230, 18, 44)]
    for (bx, bw, bh) in specs:
        building(x0 + bx, base - bh, bw, bh, (16, 22, 40), 0.5)
    # tower with antenna
    fill_rect(x0 + 128, base - 108, 6, 30, (16, 22, 40))
    thin_line(x0 + 131, base - 108, x0 + 131, base - 122, (16, 22, 40))
    fill_circle(x0 + 131, base - 123, 2, (230, 60, 40))
    # church dome
    fill_circle(x0 + 170, base - 92, 9, (30, 36, 58))
    fill_rect(x0 + 161, base - 92, 18, 14, (30, 36, 58))
    thin_line(x0 + 170, base - 104, x0 + 170, base - 112, (220, 190, 90))
    thin_line(x0 + 166, base - 109, x0 + 174, base - 109, (220, 190, 90))
    # fires at building bases
    for (fx, fs) in ((x0 + 60, 1.4), (x0 + 135, 1.8), (x0 + 205, 1.3)):
        fill_ellipse(fx, base - 2, 26 * fs, 8 * fs, (120, 50, 20))
        fill_ellipse(fx, base - 3, 18 * fs, 6 * fs, (190, 90, 30))
        flame(fx - 8, base - 2, fs * 0.9)
        flame(fx + 6, base - 2, fs * 1.1)
        flame(fx + 16, base - 2, fs * 0.7)
        smoke(fx + 10, base - 26, 5, 5, 2.5, (70, 70, 78), (110, 110, 118))
    # tracer fire
    for (tx, ty, tdx) in ((x0 + 36, base, 22), (x0 + 230, base, -24),
                          (x0 + 110, base, 18)):
        thin_line(tx, ty, tx + tdx, ty - 34, (240, 150, 50))
        fill_circle(tx + tdx, ty - 34, 1.6, (250, 200, 90))


def scene_bahrain(x0, y0, w, h):
    vgrad(x0, y0, w, 74, (235, 160, 95), (200, 95, 60))
    fill_rect(x0, y0 + 74, w, 22, (178, 82, 62))
    # low sun
    fill_circle(x0 + 210, y0 + 80, 15, (240, 170, 110))
    fill_circle(x0 + 210, y0 + 80, 11, (252, 222, 166))
    # birds
    for (bx, by) in ((x0 + 30, y0 + 22), (x0 + 48, y0 + 30), (x0 + 80, y0 + 18)):
        thin_line(bx - 4, by, bx, by + 3, (60, 40, 40))
        thin_line(bx, by + 3, bx + 4, by, (60, 40, 40))
    # sea
    vgrad(x0, y0 + 96, w, 56, (34, 62, 96), (18, 36, 64))
    for (wx, wy, wl) in [(10, 104, 18), (40, 118, 12), (76, 108, 20),
                         (110, 128, 16), (150, 112, 18), (196, 124, 14),
                         (220, 108, 18), (16, 136, 16), (120, 140, 20),
                         (196, 142, 16)]:
        thin_line(x0 + wx, y0 + wy, x0 + wx + wl, y0 + wy, (70, 110, 150))
    # industrial shore, left
    fill_rect(x0 + 6, y0 + 96, 78, 34, (70, 60, 58))
    for tx in (x0 + 12, x0 + 34, x0 + 56):
        fill_rect(tx, y0 + 100, 18, 26, (222, 222, 214))
        fill_ellipse(tx + 9, y0 + 100, 9, 3.5, (240, 240, 234))
        fill_rect(tx, y0 + 100, 18, 3, (180, 180, 172))
    thin_line(x0 + 78, y0 + 126, x0 + 78, y0 + 88, (50, 48, 48))
    flame(x0 + 78, y0 + 88, 0.8)
    # tanker
    fill_polygon([(x0 + 84, y0 + 112), (x0 + 244, y0 + 112),
                  (x0 + 238, y0 + 140), (x0 + 90, y0 + 140)], (38, 38, 46))
    fill_rect(x0 + 88, y0 + 132, 154, 8, (150, 40, 30))
    fill_rect(x0 + 88, y0 + 112, 154, 3, (90, 90, 100))
    for (cx, cc) in [(x0 + 96, (200, 60, 40)), (x0 + 116, (40, 90, 160)),
                     (x0 + 136, (40, 140, 80)), (x0 + 96, (220, 160, 40)),
                     (x0 + 116, (160, 60, 120))]:
        fill_rect(cx, y0 + 100, 18, 12, cc)
    # superstructure
    fill_rect(x0 + 176, y0 + 88, 38, 24, (232, 232, 226))
    fill_rect(x0 + 176, y0 + 88, 38, 4, (180, 40, 30))
    for wy in (y0 + 96, y0 + 103):
        for wx in range(180, 210, 7):
            fill_rect(wx, wy, 4, 3, (40, 70, 100))
    # funnel with smoke
    fill_rect(x0 + 158, y0 + 94, 10, 18, (60, 60, 66))
    fill_rect(x0 + 158, y0 + 94, 10, 4, (230, 200, 60))
    smoke(x0 + 163, y0 + 90, 4, 4, -2, (52, 52, 58), (84, 84, 90))
    # big fire amidships + black smoke
    fill_ellipse(x0 + 130, y0 + 110, 26, 8, (120, 50, 20))
    fill_ellipse(x0 + 130, y0 + 109, 18, 6, (190, 90, 30))
    flame(x0 + 116, y0 + 110, 1.5)
    flame(x0 + 130, y0 + 110, 1.8)
    flame(x0 + 144, y0 + 110, 1.3)
    smoke(x0 + 124, y0 + 80, 6, 5, -3, (44, 44, 50), (88, 88, 96))
    smoke(x0 + 188, y0 + 84, 5, 4.5, 2, (44, 44, 50), (80, 80, 88))
    flame(x0 + 196, y0 + 88, 1.1)
    # bow wave
    thin_line(x0 + 240, y0 + 140, x0 + 248, y0 + 136, (200, 220, 240))
    thin_line(x0 + 240, y0 + 144, x0 + 248, y0 + 142, (200, 220, 240))

# ---------------------------------------------------------------- mini scenes
# Each mini scene is a flat icon picture, 192x54, drawn from a handful of
# solid shapes on a flat background. No texture, no noise.

def mini_ballot(x0, y0, w, h):
    fill_rect(x0, y0, w, h, (226, 232, 238))
    fill_rect(x0, y0 + 40, w, 14, (31, 78, 156))
    # ballot box
    fill_rect(x0 + 70, y0 + 20, 52, 26, (178, 38, 30))
    fill_rect(x0 + 70, y0 + 20, 52, 4, (138, 24, 18))
    fill_rect(x0 + 84, y0 + 16, 24, 4, (28, 28, 28))
    # ballot paper going in, with a red check
    fill_polygon([(x0 + 88, y0 + 2), (x0 + 108, y0 + 2), (x0 + 104, y0 + 16),
                  (x0 + 92, y0 + 16)], WHITE)
    thick_line(x0 + 92, y0 + 9, x0 + 96, y0 + 13, 2, RED)
    thick_line(x0 + 96, y0 + 13, x0 + 104, y0 + 4, 2, RED)
    text(x0 + 8, y0 + 6, "VOTE", (28, 28, 28), 2)


def mini_cricket(x0, y0, w, h):
    fill_rect(x0, y0, w, h, (120, 190, 120))
    fill_rect(x0, y0 + 34, w, 20, (80, 150, 80))
    # pitch strip
    fill_rect(x0 + 60, y0 + 8, 72, 40, (220, 200, 150))
    # stumps
    for sx in (x0 + 66, x0 + 71, x0 + 76):
        fill_rect(sx, y0 + 14, 2, 14, (240, 210, 90))
    fill_rect(x0 + 66, y0 + 12, 12, 2, (240, 210, 90))
    # bat
    fill_polygon([(x0 + 118, y0 + 10), (x0 + 124, y0 + 12),
                  (x0 + 112, y0 + 34), (x0 + 106, y0 + 32)], (150, 105, 60))
    # ball
    fill_circle(x0 + 150, y0 + 20, 6, RED)
    fill_circle(x0 + 150, y0 + 20, 3, (240, 120, 100))


def mini_f1(x0, y0, w, h):
    fill_rect(x0, y0, w, h, (24, 28, 52))
    fill_rect(x0, y0 + 38, w, 16, (60, 60, 66))
    # track dashes
    for dx in range(6, w - 8, 22):
        fill_rect(x0 + dx, y0 + 45, 12, 2, (230, 230, 230))
    # race car
    fill_polygon([(x0 + 52, y0 + 30), (x0 + 62, y0 + 20), (x0 + 96, y0 + 18),
                  (x0 + 118, y0 + 24), (x0 + 128, y0 + 30)], (200, 40, 30))
    fill_rect(x0 + 58, y0 + 28, 66, 6, (220, 60, 40))
    fill_rect(x0 + 126, y0 + 14, 6, 18, (220, 60, 40))
    fill_circle(x0 + 68, y0 + 34, 7, (12, 12, 12))
    fill_circle(x0 + 68, y0 + 34, 3, (180, 180, 180))
    fill_circle(x0 + 112, y0 + 34, 7, (12, 12, 12))
    fill_circle(x0 + 112, y0 + 34, 3, (180, 180, 180))
    # chequered flag, below the badge chip
    for r in range(2):
        for cc in range(4):
            if (r + cc) % 2 == 0:
                fill_rect(x0 + 150 + cc * 6, y0 + 28 + r * 6, 6, 6, WHITE)
            else:
                fill_rect(x0 + 150 + cc * 6, y0 + 28 + r * 6, 6, 6, BLACK)
    thin_line(x0 + 150, y0 + 28, x0 + 150, y0 + 50, (220, 220, 220))


def mini_basket(x0, y0, w, h):
    fill_rect(x0, y0, w, h, (240, 220, 180))
    fill_rect(x0, y0 + 40, w, 14, (120, 90, 50))
    # hoop
    fill_ellipse(x0 + 150, y0 + 16, 18, 5, (200, 80, 30))
    thin_line(x0 + 134, y0 + 18, x0 + 140, y0 + 34, WHITE)
    thin_line(x0 + 166, y0 + 18, x0 + 160, y0 + 34, WHITE)
    thin_line(x0 + 140, y0 + 34, x0 + 160, y0 + 34, WHITE)
    fill_rect(x0 + 168, y0 + 8, 4, 26, (220, 220, 220))
    # ball
    fill_circle(x0 + 60, y0 + 26, 20, (230, 120, 40))
    fill_circle(x0 + 60, y0 + 26, 20, (230, 120, 40))
    thin_line(x0 + 40, y0 + 26, x0 + 80, y0 + 26, (120, 60, 20))
    thin_line(x0 + 60, y0 + 6, x0 + 60, y0 + 46, (120, 60, 20))
    fill_ellipse(x0 + 60, y0 + 26, 20, 8, (230, 120, 40))
    thin_line(x0 + 42, y0 + 18, x0 + 78, y0 + 18, (120, 60, 20))
    thin_line(x0 + 42, y0 + 34, x0 + 78, y0 + 34, (120, 60, 20))


def mini_pope(x0, y0, w, h):
    fill_rect(x0, y0, w, h, (238, 232, 214))
    fill_rect(x0, y0 + 44, w, 10, (120, 140, 90))
    # basilica: dome + drum + columns
    fill_circle(x0 + 96, y0 + 26, 16, (200, 170, 110))
    fill_rect(x0 + 80, y0 + 26, 32, 18, (222, 212, 182))
    thin_line(x0 + 96, y0 + 4, x0 + 96, y0 + 10, GOLD)
    thin_line(x0 + 92, y0 + 7, x0 + 100, y0 + 7, GOLD)
    for cx in range(58, 140, 13):
        fill_rect(cx, y0 + 28, 5, 16, (245, 238, 218))
    fill_rect(x0 + 52, y0 + 26, 88, 3, (190, 180, 150))
    fill_rect(x0 + 52, y0 + 44, 88, 3, (190, 180, 150))
    # dove
    fill_ellipse(x0 + 162, y0 + 16, 8, 4, WHITE)
    fill_circle(x0 + 169, y0 + 13, 3, WHITE)
    fill_polygon([(x0 + 154, y0 + 16), (x0 + 146, y0 + 12),
                  (x0 + 146, y0 + 20)], WHITE)


def mini_pylon(x0, y0, w, h):
    vgrad(x0, y0, w, h, (24, 28, 52), (48, 52, 84))
    fill_circle(x0 + 168, y0 + 12, 8, (240, 235, 210))
    fill_circle(x0 + 164, y0 + 10, 7, (24, 28, 52))
    # dark blocks with a few lit windows
    building(x0 + 8, y0 + 26, 26, 28, (16, 18, 34), 0.28)
    building(x0 + 38, y0 + 18, 30, 36, (18, 20, 38), 0.22)
    building(x0 + 72, y0 + 30, 24, 24, (16, 18, 34), 0.15)
    # pylon
    px = x0 + 138
    thick_line(px - 12, y0 + 54, px, y0 + 12, 2, (10, 10, 14))
    thick_line(px + 12, y0 + 54, px, y0 + 12, 2, (10, 10, 14))
    thick_line(px - 12, y0 + 54, px + 12, y0 + 54, 2, (10, 10, 14))
    thick_line(px - 14, y0 + 20, px + 14, y0 + 20, 2, (10, 10, 14))
    thick_line(px - 8, y0 + 32, px + 8, y0 + 32, 2, (10, 10, 14))
    # lightning bolt
    fill_polygon([(px - 34, y0 + 8), (px - 24, y0 + 8), (px - 30, y0 + 20),
                  (px - 22, y0 + 20), (px - 36, y0 + 40), (px - 30, y0 + 22),
                  (px - 38, y0 + 22)], (250, 220, 60))


def mini_factory(x0, y0, w, h):
    fill_rect(x0, y0, w, h, (226, 232, 238))
    fill_rect(x0, y0 + 44, w, 10, (150, 140, 120))
    # factory with sawtooth roof
    fill_rect(x0 + 20, y0 + 22, 90, 22, (120, 110, 96))
    fill_polygon([(x0 + 20, y0 + 22), (x0 + 42, y0 + 10), (x0 + 65, y0 + 22),
                  (x0 + 87, y0 + 10), (x0 + 110, y0 + 22)], (96, 88, 78))
    fill_rect(x0 + 120, y0 + 8, 10, 36, (90, 84, 74))
    fill_rect(x0 + 118, y0 + 6, 14, 4, (70, 64, 56))
    for wx in range(28, 104, 14):
        fill_rect(wx, y0 + 28, 6, 8, (250, 220, 130))
    flame(x0 + 60, y0 + 22, 1.2)
    flame(x0 + 88, y0 + 22, 1.5)
    smoke(x0 + 74, y0 + 8, 4, 4, 2, (90, 88, 84), (130, 128, 124))


def mini_khartoum(x0, y0, w, h):
    vgrad(x0, y0, w, h, (226, 214, 190), (240, 230, 210))
    building(x0 + 10, y0 + 14, 34, 40, (120, 110, 96), 0.35,
             win=(200, 190, 150))
    building(x0 + 50, y0 + 6, 40, 48, (96, 88, 78), 0.3,
             win=(200, 190, 150))
    building(x0 + 96, y0 + 18, 36, 36, (130, 120, 106), 0.35,
             win=(200, 190, 150))
    # blast between the blocks
    fill_polygon([(x0 + 96, y0 + 20), (x0 + 104, y0 + 10),
                  (x0 + 110, y0 + 20), (x0 + 120, y0 + 14),
                  (x0 + 118, y0 + 26), (x0 + 128, y0 + 28),
                  (x0 + 116, y0 + 34), (x0 + 118, y0 + 44),
                  (x0 + 106, y0 + 38), (x0 + 98, y0 + 46),
                  (x0 + 96, y0 + 34), (x0 + 86, y0 + 32),
                  (x0 + 94, y0 + 26)], (240, 150, 40))
    fill_polygon([(x0 + 102, y0 + 24), (x0 + 108, y0 + 18),
                  (x0 + 113, y0 + 25), (x0 + 118, y0 + 30),
                  (x0 + 110, y0 + 34), (x0 + 104, y0 + 32)], (250, 210, 90))
    smoke(x0 + 108, y0 + 10, 4, 4.5, 2, (90, 88, 84), (130, 128, 124))
    # drone above
    fill_polygon([(x0 + 158, y0 + 14), (x0 + 163, y0 + 11),
                  (x0 + 168, y0 + 14), (x0 + 163, y0 + 17)], (16, 16, 20))
    fill_circle(x0 + 163, y0 + 14, 1.5, (230, 60, 40))
    fill_rect(x0, y0 + 48, w, 6, (90, 84, 72))


def mini_hospital(x0, y0, w, h):
    fill_rect(x0, y0, w, h, (232, 238, 240))
    fill_rect(x0, y0 + 40, w, 14, (180, 190, 196))
    # monitor with ECG
    fill_rect(x0 + 128, y0 + 8, 48, 30, (30, 34, 40))
    fill_rect(x0 + 131, y0 + 11, 42, 24, (12, 40, 26))
    pts = [(132, 27), (138, 27), (141, 20), (144, 31), (147, 16),
           (150, 27), (158, 27), (161, 22), (164, 27), (170, 27)]
    for i in range(len(pts) - 1):
        thin_line(x0 + pts[i][0], y0 + pts[i][1], x0 + pts[i + 1][0],
                  y0 + pts[i + 1][1], (80, 230, 120))
    text(x0 + 134, y0 + 13, "72", (120, 230, 140), 1)
    # IV pole + bag
    thin_line(x0 + 108, y0 + 8, x0 + 108, y0 + 46, (90, 90, 90))
    fill_rect(x0 + 102, y0 + 10, 12, 16, (210, 225, 235))
    fill_rect(x0 + 102, y0 + 20, 12, 6, (150, 200, 220))
    thin_line(x0 + 108, y0 + 26, x0 + 96, y0 + 36, (120, 120, 120))
    # bed + patient
    fill_rect(x0 + 14, y0 + 34, 84, 5, (120, 130, 140))
    fill_rect(x0 + 14, y0 + 39, 84, 9, (90, 100, 110))
    fill_rect(x0 + 18, y0 + 30, 16, 5, WHITE)
    fill_circle(x0 + 26, y0 + 28, 5, (232, 190, 150))
    fill_circle(x0 + 26, y0 + 26, 5.2, (120, 120, 120))
    fill_polygon([(x0 + 34, y0 + 32), (x0 + 92, y0 + 32),
                  (x0 + 92, y0 + 39), (x0 + 34, y0 + 39)], (120, 160, 200))


def mini_fbi(x0, y0, w, h):
    fill_rect(x0, y0, w, h, (226, 232, 238))
    # server rack
    fill_rect(x0 + 20, y0 + 8, 44, 40, (30, 34, 40))
    for r in range(4):
        fill_rect(x0 + 24, y0 + 12 + r * 9, 36, 5, (60, 64, 72))
        fill_circle(x0 + 28, y0 + 14 + r * 9, 1.5, (80, 230, 120))
        fill_rect(x0 + 34, y0 + 13 + r * 9, 20, 2, (120, 130, 140))
    # magnifier
    fill_circle(x0 + 120, y0 + 24, 14, WHITE)
    rect_outline(x0 + 106, y0 + 10, 28, 28, (40, 40, 40), 2)
    fill_circle(x0 + 120, y0 + 24, 10, (180, 210, 230))
    text(x0 + 115, y0 + 21, "?", (28, 28, 28), 1)
    thick_line(x0 + 130, y0 + 34, x0 + 142, y0 + 46, 3, (40, 40, 40))
    # warning triangle
    fill_polygon([(x0 + 168, y0 + 10), (x0 + 180, y0 + 30),
                  (x0 + 156, y0 + 30)], (240, 180, 40))
    text(x0 + 165, y0 + 20, "!", (28, 28, 28), 1)

# ---------------------------------------------------------------- world map
# Dotted map from coarse land blobs (ellipses in lon/lat space). Each
# blob is a rough continent outline, deliberately simple: at 244 px wide
# the reader only needs the shape of the world, and the numbered pins
# carry the precision.
BLOBS = [
    (-102, 48, 38, 17), (-95, 30, 18, 8), (-85, 12, 8, 5),   # N America
    (-42, 72, 10, 5),                                          # Greenland
    (-60, -15, 15, 22), (-68, -35, 8, 12),                    # S America
    (20, 5, 18, 22), (25, -20, 10, 10),                       # Africa
    (15, 52, 18, 8), (28, 62, 12, 6), (30, 45, 12, 5),        # Europe
    (90, 55, 45, 15), (105, 35, 20, 10), (78, 22, 10, 8),     # Asia
    (100, 15, 10, 8), (115, -3, 15, 5),                       # SE Asia
    (134, -25, 13, 8),                                         # Australia
    (172, -41, 3, 4),                                          # New Zealand
    (138, 37, 3, 5),                                           # Japan
    (-2, 54, 2, 3),                                            # Britain
]
# (lon, lat) of the 13 illustrated stories, in story order.
PINS = [(30.7, 36.9), (30.5, 50.4), (50.6, 26.2), (114.2, 22.3),
        (174.8, -41.3), (-115.1, 36.2), (-98.5, 29.4), (12.45, 41.9),
        (51.4, 35.7), (106.1, -6.1), (32.5, 15.6), (-47.9, -15.8),
        (-77.0, 38.9)]


def _on_land(lon, lat):
    for (cx, cy, rx, ry) in BLOBS:
        if ((lon - cx) / rx) ** 2 + ((lat - cy) / ry) ** 2 <= 1.0:
            return True
    return False


def draw_map(mx, my, mw, mh):
    step = 5
    y = my
    while y <= my + mh:
        x = mx
        while x <= mx + mw:
            lon = (x - mx) / mw * 360.0 - 170.0
            lat = 75.0 - (y - my) / mh * 130.0
            if _on_land(lon, lat):
                fill_circle(x, y, 1.6, TAN)
            x += step
        y += step
    for i, (lon, lat) in enumerate(PINS, 1):
        px = mx + (lon + 170.0) / 360.0 * mw
        py = my + (75.0 - lat) / 130.0 * mh
        fill_circle(px, py, 6, RED)
        s = str(i)
        text(px - text_width(s, 1) / 2.0, py - 3.5, s, WHITE, 1)

# ---------------------------------------------------------------- content
TITLE = "SUNDAY 22 NOVEMBER 2026"
DECK1 = "186 DRONES OVER UKRAINE - COP31 DEAL NAMES NO FOSSIL FUELS"
DECK2 = "IRAN'S RADAR CLAIM MEETS BAHRAIN'S DENIAL"
COUNT_LINE = "33 STORIES \u00b7 7 REGIONS \u00b7 EVERY ONE DATED SUNDAY 22 NOVEMBER 2026"
TIMELINE = ("THE DAY IN UTC   01:00 HK POLLS OPEN  \u00b7  03:00 COP31 "
            "OBJECTIONS CLOSE  \u00b7  05:30 VERSTAPPEN WINS VEGAS  \u00b7  "
            "06:00 COP31 APPROVAL DUE  \u00b7  09:45 PRESS TIME")

REGIONS = [("EUROPE 6", BLUE), ("MIDDLE EAST 6", RED),
           ("AMERICAS 5", GREEN), ("ASIA-PACIFIC 7", AMBER),
           ("AFRICA 4", BROWN), ("OCEANIA 4", PURPLE), ("WORLD 1", GREY)]

NUMBERS = [
    ("186", "DRONES FIRED AT UKRAINE OVERNIGHT"),
    ("161", "DOWNED OR JAMMED BY AIR DEFENCE"),
    ("98.37%", "HONG KONG TURNOUT BY 5 PM"),
    ("720/9", "INDIA'S RECORD TEST TOTAL IN NZ"),
    ("50", "WEMBANYAMA POINTS VS PELICANS"),
    ("856", "CANDIDATES FOR HK ELECTION COMMITTEE"),
]

TOP = [
    ("COP31: DEAL CLOSE", "PENDING", "1 ANTALYA, TURKIYE \u00b7 CLIMATE",
     "COP31 DEAL LANDS WITHOUT MENTIONING FOSSIL FUELS",
     "DROPS THE $120BN TARGET, KEEPS 35% BY 2035. ADMITS 1.5C OVERSHOOT. "
     "(REUTERS)",
     scene_cop31),
    ("186 DRONES OVERNIGHT", "CONFIRMED", "2 KYIV REGION, UKRAINE \u00b7 WAR",
     "RUSSIA FIRES 186 DRONES; 161 ARE SHOT DOWN",
     "161 OF 186 DOWNED OR JAMMED; HITS AT 18 SITES. "
     "(UKRAINIAN AIR FORCE)",
     scene_kyiv),
    ("CLAIM VS DENIAL", "CLAIM", "3 MANAMA, BAHRAIN \u00b7 IRAN",
     "IRAN CLAIMS TWO US RADARS HIT; BAHRAIN DENIES IT",
     "IRGC: TWO PATRIOT RADARS DESTROYED. BAHRAIN: CIVILIAN SITE HIT. "
     "(AL JAZEERA)",
     scene_bahrain),
]

CARDS = [
    ("HK VOTES", "CONFIRMED", "4 HONG KONG \u00b7 ELECTION",
     "HONG KONG ELECTS ITS ELECTION COMMITTEE",
     "856 CANDIDATES, 723 SEATS; TURNOUT 98.37% BY 5 PM. (SCMP)",
     mini_ballot),
    ("720/9 DECLARED", "CONFIRMED", "5 WELLINGTON \u00b7 CRICKET",
     "INDIA DECLARE 720/9, RECORD IN NZ",
     "RAHUL 136, GILL 128; HOSTS 119/2. (ESPNCRICINFO)", mini_cricket),
    ("VERSTAPPEN WINS", "CONFIRMED", "6 LAS VEGAS \u00b7 FORMULA 1",
     "VERSTAPPEN TAKES THE LAS VEGAS GRAND PRIX",
     "FROM POLE IN 1:37:59.24; NORRIS +0.639. (FIA)",
     mini_f1),
    ("50 POINTS", "CONFIRMED", "7 SAN ANTONIO \u00b7 NBA",
     "WEMBANYAMA SCORES 50 AS THE SPURS ROLL ON",
     "50 PTS, 19 REBOUNDS, 5 BLOCKS; 114-91. (REUTERS)",
     mini_basket),
    ("POPE HOSTS 1,300", "CONFIRMED", "8 VATICAN CITY \u00b7 FAITH",
     "POPE LEO XIV HOSTS 1,300 POOR GUESTS",
     "LUNCH FOR THE 10TH WORLD DAY OF THE POOR. (VATICAN NEWS)",
     mini_pope),
    ("POWER CUTS", "CONFIRMED", "9 TEHRAN, IRAN \u00b7 ENERGY",
     "IRAN BEGINS RATIONING ELECTRICITY",
     "ROLLING CUTS UP TO TWO HOURS A DAY. (WIRES)",
     mini_pylon),
    ("3 DEAD, 36 MISSING", "CONFIRMED", "10 CIKANDE, INDONESIA \u00b7 FIRE",
     "CANDY-FACTORY FIRE IN CIKANDE: 3 DEAD",
     "BLAZE TORE THROUGH THE BANTEN PLANT. (DETIKNEWS)",
     mini_factory),
    ("DRONES OVER KHARTOUM", "REPORTED", "11 KHARTOUM \u00b7 WAR",
     "DRONES STRIKE HOMES NEAR KHARTOUM",
     "ARMY AIR DEFENCES ENGAGED. (AFP)", mini_khartoum),
    ("IN INTENSIVE CARE", "CONFIRMED", "12 BRASILIA, BRAZIL \u00b7 HEALTH",
     "BOLSONARO IN INTENSIVE CARE",
     "ACUTE BOWEL OBSTRUCTION, STABLE. (REUTERS)",
     mini_hospital),
    ("FBI PROBE", "REPORTED", "13 WASHINGTON \u00b7 CYBER",
     "FBI PROBES HACK OF ITS CRIME DATABASE",
     "WASHINGTON STATE PAUSES GUN-DEALER CHECKS. (AP)",
     mini_fbi),
]

ALSO_LEFT = [
    "GAZA: ISRAELI FIRE KILLS FOUR - 3 KILLED IN A FOOD VEHICLE. "
    "(AL JAZEERA)",
    "ISRAEL: EISENKOT INVITES LIKUD TO COALITION TALKS. (REUTERS)",
    "SAUDI ARABIA: AIR DEFENCES DOWN A MISSILE AIMED AT RIYADH. (ANADOLU)",
    "LEBANON: AOUN DEMANDS ISRAELI WITHDRAWAL. (AL JAZEERA)",
    "DYMER: DRONE COLLAPSES PART OF APARTMENT BLOCK, 14 MAY BE TRAPPED. "
    "(REUTERS)",
    "DENMARK: EXPELS RUSSIAN ATTACHE OVER ALLEGED PLOT AGAINST UKRAINIAN. "
    "(GUARDIAN)",
    "ESTONIA: TO SHUT FIVE RUSSIA BORDER CROSSINGS 1 DEC, AFTER A "
    "SABOTAGE BID. (REUTERS)",
    "NEPAL: PM SHAH LANDS IN DELHI ON FIRST VISIT; MEETS MODI MONDAY. "
    "(IANS)",
    "ASIA: CHINESE BOMBER TURNS BACK 170 KM FROM MANILA. (AP)",
    "PHILIPPINES: M 5.9 QUAKE, 898 KM DEEP, OFF PALAWAN. (EMSC)",
]
ALSO_RIGHT = [
    "SUDAN: RSF ACCUSED OF KILLING CIVILIANS, INCL. 3 CHILDREN, IN "
    "W. KORDOFAN. (CLAIMS)",
    "SOMALIA: EXPELS UAE AMBASSADOR, RECALLS ITS ENVOY. (WIRES)",
    "KENYA: DISCHARGES ITS LAST EBOLA PATIENT. (WIRES)",
    "MELBOURNE: 70 YEARS SINCE THE 1956 OLYMPICS OPENED. (ABC)",
    "AUSTRALIA: CUMMINS KEEPS TEST CAPTAINCY. (WIRES)",
    "CANBERRA: MARLES REJECTS US REPORT ON AUKUS SUBS. (REUTERS)",
    "US: TRUMP SEEKS 'PERMANENT' IRAN DEAL; DOHA TALKS TO MEDIATORS. "
    "(AL JAZEERA)",
    "JAPAN: SNOW STRANDS ABOUT 1,500 IN VILLAGE, FUKUSHIMA. (DPA)",
    "SEOUL: EDUCATION MINISTER'S RESIGNATION ACCEPTED. (REUTERS)",
    "TURIN: ZVEREV V ALCARAZ IN TODAY'S ATP FINALS FINAL. (ATP)",
]

DATE_CHECK = ("EVERY STORY ON THIS PAGE HAPPENED OR WAS FIRST REPORTED ON "
              "SUNDAY 22 NOVEMBER 2026 (UTC), TO PRESS TIME 09:45 UTC. "
              "LEFT OUT BECAUSE THEY HAPPENED ON AN EARLIER DAY: PERU "
              "EARTHQUAKE FRI 20 NOV \u00b7 'EL CHAPO ISIDRO' ARREST SAT 21 "
              "NOV \u00b7 KRYVYI RIH STRIKE SAT 21 NOV \u00b7 SPARTA II SHIP "
              "HIT SAT 21 NOV \u00b7 MYANMAR GENOCIDE RULING THU 19 NOV "
              "\u00b7 NVIDIA SEC PROBE FRI 20 NOV \u00b7 SAUDI STRIKES ON "
              "HODEIDAH 20-21 NOV \u00b7 FRED NILE DEATH SAT 21 NOV \u00b7 "
              "THE 400-DRONE BARRAGE THU 19-FRI 20 NOV. TONIGHT'S REAL "
              "COUNT: 186 DRONES, NOT 400.")

LEGEND = ("HOW TO READ THE TAGS: CONFIRMED = 2+ OUTLETS \u00b7 CLAIM = ONE "
          "SIDE'S CLAIM, CONTESTED \u00b7 REPORTED = WITNESSES / ONE SOURCE "
          "\u00b7 PENDING = NOT SETTLED YET")

SOURCES = ("SOURCES: REUTERS, BBC, AL JAZEERA, THE GUARDIAN, AP, AFP, SCMP, "
           "ESPNCRICINFO, FIA, DETIKNEWS, DPA, IANS, EMSC, ANADOLU, VATICAN "
           "NEWS, ABC. EVERY STORY NAMES ITS OUTLET. SCENES ARE DRAWN "
           "ILLUSTRATIONS, NOT PHOTOGRAPHS.")


def draw_also(x, y, items, first_no, maxw):
    for k, item in enumerate(items):
        no = str(first_no + k)
        lines = wrap(item, maxw - text_width(no + " ", 1), 1)
        text(x, y, no, RED, 1)
        for j, ln in enumerate(lines):
            text(x + text_width(no + " ", 1), y + j * 9, ln, INK, 1)
        y += len(lines) * 9 + 3
    return y


def draw_page():
    # ---- masthead
    text(16, 8, "THE WORLD IN ONE DAY", RED, 2)
    text(1008 - text_width(COUNT_LINE, 1), 11, COUNT_LINE, INK, 1)
    fill_rect(16, 26, 992, 2, INK)
    # ---- title + deck
    text_c(512, 32, TITLE, INK, 6)
    text_c(512, 80, DECK1, RED, 2)
    text_c(512, 96, DECK2, RED, 2)
    # ---- region bar
    cw = 992 / 7.0
    for i, (lab, c) in enumerate(REGIONS):
        x = 16 + cw * i
        fill_rect(x, 116, cw + 0.5, 18, c)
        text_c(x + cw / 2.0, 121, lab, WHITE, 1)
    # ---- timeline strip
    fill_rect(16, 138, 992, 16, NAVY)
    text_c(512, 142, TIMELINE, WHITE, 1)
    # ---- top stories + numbers panel
    for k, (tag, badge, kicker, head, body, fn) in enumerate(TOP):
        x = 16 + k * 258
        fn(x, 160, 250, 152)
        rect_outline(x, 160, 250, 152, INK, 1)
        chip(x + 4, 164, tag, RED, WHITE)
        chip(x + 250 - 4 - (text_width(badge, 1) + 8), 164,
             badge, BADGE[badge], WHITE)
        text(x, 316, kicker, RED, 1)
        lines = wrap(head, 250, 2)
        for j, ln in enumerate(lines[:3]):
            text(x, 326 + j * 16, ln, INK, 2)
        blines = wrap(body, 250, 1)
        for j, ln in enumerate(blines[:2]):
            text(x, 378 + j * 9, ln, INKSOFT, 1)
    # numbers panel
    nx, nw = 790, 218
    fill_rect(nx, 160, nw, 198, NAVY)
    text(nx + 10, 168, "THE DAY IN NUMBERS", GOLD, 1)
    fill_rect(nx + 10, 182, nw - 20, 1, GOLD)
    yy = 188
    for num, lab in NUMBERS:
        text(nx + 10, yy, num, GOLD, 2)
        lines = wrap(lab, nw - 20 - text_width(num + " ", 2), 1)
        for j, ln in enumerate(lines):
            text(nx + 10 + text_width(num + " ", 2), yy + 2 + j * 9,
                 ln, WHITE, 1)
        yy += 28
    # ---- tier-2 cards, two rows of five
    xs = [16, 216, 416, 616, 816]
    for idx, (tag, badge, kicker, head, body, fn) in enumerate(CARDS):
        row, col = divmod(idx, 5)
        x = xs[col]
        y = 398 + row * 140
        fn(x, y, 192, 54)
        rect_outline(x, y, 192, 54, INK, 1)
        chip(x + 3, y + 3, tag, RED, WHITE)
        chip(x + 192 - 3 - (text_width(badge, 1) + 8), y + 3,
             badge, BADGE[badge], WHITE)
        text(x, y + 58, kicker, RED, 1)
        lines = wrap(head, 192, 2)
        for j, ln in enumerate(lines[:3]):
            text(x, y + 68 + j * 16, ln, INK, 2)
        blines = wrap(body, 192, 1)
        by = y + 68 + min(len(lines), 3) * 16 + 2
        for j, ln in enumerate(blines[:2]):
            text(x, by + j * 9, ln, INKSOFT, 1)
    # ---- bottom: also list + map + legend
    text(16, 684, "ALSO ON SUNDAY 22 NOVEMBER - 20 MORE STORIES", INK, 2)
    text(780, 684, "WHERE IT HAPPENED", INK, 2)
    text(780, 700, "PINS MATCH STORY NUMBERS", INKSOFT, 1)
    draw_also(16, 702, ALSO_LEFT, 14, 372)
    draw_also(396, 702, ALSO_RIGHT, 24, 372)
    draw_map(780, 706, 228, 150)
    # legend under the map
    fill_rect(780, 862, 228, 52, CREAM)
    rect_outline(780, 862, 228, 52, INK, 1)
    para(786, 867, LEGEND, 216, INK, 1, lh=9)
    # ---- date check
    rect_outline(16, 920, 992, 58, RED, 2)
    text(24, 927, "DATE CHECK", RED, 1)
    para(24, 939, DATE_CHECK, 976, INK, 1, lh=9)
    # ---- footer
    para(16, 982, SOURCES, 992, INKSOFT, 1, lh=9)
    fill_rect(16, 1004, 992, 1, INK)
    text(16, 1008, "THE WORLD IN ONE DAY", INK, 1)
    text(1008 - text_width("SUNDAY 22 NOVEMBER 2026 \u00b7 ONE PAGE", 1),
         1008, "SUNDAY 22 NOVEMBER 2026 \u00b7 ONE PAGE", INK, 1)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    draw_page()
    path = os.path.join(outdir, "entry.png")
    size = write_png(path)
    print("wrote %s (%d bytes, 1024x1024)" % (path, size))


if __name__ == "__main__":
    main()
