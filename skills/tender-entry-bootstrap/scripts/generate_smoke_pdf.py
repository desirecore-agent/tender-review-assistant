#!/usr/bin/env python3
"""Generate the non-sensitive visual smoke PDF for tender-entry-bootstrap.

Standard library only (zlib/os/sys/tempfile/math). No network, no input execution.

fix-round-1 changes:
  E05: the unique mark is carried ONLY by a genuinely embedded raster bitmap
       (Image XObject, FlateDecode raw RGB) rendered from a 5x7 pixel font.
       No text operator carries the mark, and the text layer never spells it,
       so ordinary text extraction cannot recover it. Visual acceptance
       requires a real rendered read (Read pdf_mode=render, pages="1").
  E04: output is written through a random exclusive temp file created with
       tempfile.mkstemp (O_EXCL; never follows a pre-placed '.tmp' symlink),
       fsynced, then os.replace'd. Only temp files this call owns are removed.
       A pre-existing symlink at the explicit output path is refused.

The fixture has two layers:
  1. Extractable text layer (Helvetica): an English paragraph well over 50
     characters, deliberately NOT containing the mark string.
  2. Embedded bitmap badge inside a stroked hexagon, carrying the mark.

Usage: generate_smoke_pdf.py [output.pdf]
Default output: ../assets/smoke-tender-entry.pdf (relative to this script).
Exit codes: 0 ok, 3 usage/IO error, 4 refused (symlink/unsafe output).
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import zlib

MARK_TEXT = "TEB-01"

# 5x7 pixel font (1 = mark pixel)
FONT = {
    "T": [
        "XXXXX",
        "..X..",
        "..X..",
        "..X..",
        "..X..",
        "..X..",
        "..X..",
    ],
    "E": [
        "XXXXX",
        "X....",
        "X....",
        "XXXX.",
        "X....",
        "X....",
        "XXXXX",
    ],
    "B": [
        "XXXX.",
        "X...X",
        "X...X",
        "XXXX.",
        "X...X",
        "X...X",
        "XXXX.",
    ],
    "-": [
        ".....",
        ".....",
        ".....",
        "XXXXX",
        ".....",
        ".....",
        ".....",
    ],
    "0": [
        ".XXX.",
        "X...X",
        "X..XX",
        "X.X.X",
        "XX..X",
        "X...X",
        ".XXX.",
    ],
    "1": [
        "..X..",
        ".XX..",
        "..X..",
        "..X..",
        "..X..",
        "..X..",
        ".XXX.",
    ],
}

# Text layer must stay > 50 chars and must NOT contain the mark.
BODY_LINES = [
    "Tender Entry Bootstrap smoke document (non-sensitive fixture).",
    "This page exists only to verify visual PDF rendering on this client.",
    "The text layer must stay extractable and be longer than fifty characters;",
    "if you can read these sentences, text extraction works on this instance.",
    "Below, a hexagon encloses an embedded raster bitmap badge whose contents",
    "are carried purely by pixel data, never by any text operator on this page.",
    "Visual acceptance requires actually seeing that bitmap badge after a real",
    "rendered read; ordinary text extraction must NOT recover the badge string.",
    "No tender content, no personal data, no prices: this fixture is synthetic.",
]

INK = (26, 51, 115)       # mark pixel color
BG = (255, 255, 255)      # badge background
SCALE = 6
GLYPH_W, GLYPH_H = 5, 7
CHAR_GAP = 1


def render_badge():
    """Render MARK_TEXT into raw RGB scanlines (top row first) using the pixel font."""
    chars = [FONT[c] for c in MARK_TEXT]
    small_w = (GLYPH_W + CHAR_GAP) * len(chars) - CHAR_GAP
    small_h = GLYPH_H
    grid = [[BG] * small_w for _ in range(small_h)]
    x0 = 0
    for glyph in chars:
        for row in range(GLYPH_H):
            for col in range(GLYPH_W):
                if glyph[row][col] == "X":
                    grid[row][x0 + col] = INK
        x0 += GLYPH_W + CHAR_GAP
    # upscale with nearest-neighbor + 2px quiet border
    border = 2
    w = small_w * SCALE + 2 * border
    h = small_h * SCALE + 2 * border
    raw = bytearray()
    for y in range(h):
        for x in range(w):
            px = BG
            gx, gy = (x - border) // SCALE, (y - border) // SCALE
            if 0 <= gx < small_w and 0 <= gy < small_h:
                px = grid[gy][gx]
            raw += bytes(px)
    return w, h, bytes(raw)


def pdf_str(s: str) -> bytes:
    return b"(" + s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)").encode("latin-1") + b")"


def stream_obj(body: bytes, compress: bool = True):
    if compress:
        data = zlib.compress(body, 9)
        return b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream"
    return b"<< /Length %d >>\nstream\n" % len(body) + body + b"\nendstream"


def build() -> bytes:
    bw, bh, raw_rgb = render_badge()

    # page geometry: hexagon centered at (306, 330), radius 150; bitmap centered inside
    cx, cy, r = 306.0, 330.0, 150.0
    bx = cx - bw / 2.0
    by = cy - bh / 2.0

    ops = []
    ops.append("BT /F1 13 Tf 16 TL 60 730 Td")
    for i, line in enumerate(BODY_LINES):
        if i:
            ops.append("T*")
        ops.append("%s Tj" % pdf_str(line).decode("latin-1"))
    ops.append("ET")
    pts = [(cx + r * math.cos(math.radians(60 * k + 30)), cy + r * math.sin(math.radians(60 * k + 30))) for k in range(6)]
    ops.append("4 w 0.1 0.2 0.45 RG")
    ops.append("%.2f %.2f m" % pts[0])
    for x, y in pts[1:]:
        ops.append("%.2f %.2f l" % (x, y))
    ops.append("h S")
    ops.append("q %d 0 0 %d %.2f %.2f cm /Im1 Do Q" % (bw, bh, bx, by))
    ops.append("0 0 0 RG 0 0 0 rg")
    content = "\n".join(ops).encode("latin-1")

    objs = {}
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    objs[3] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> /XObject << /Im1 6 0 R >> >> /Contents 4 0 R >>"
    objs[4] = stream_obj(content)
    objs[5] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    img_data = zlib.compress(raw_rgb, 9)
    objs[6] = (
        b"<< /Type /XObject /Subtype /Image /Width %d /Height %d "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length %d >>\nstream\n"
        % (bw, bh, len(img_data)) + img_data + b"\nendstream"
    )

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += b"%d 0 obj\n" % oid + objs[oid] + b"\nendobj\n"
    xref_pos = len(out)
    n = max(objs) + 1
    out += b"xref\n0 %d\n" % n
    out += b"0000000000 65535 f \n"
    for i in range(1, n):
        out += b"%010d 00000 n \n" % offsets[i]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (n, xref_pos)
    return bytes(out)


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = argv[1] if len(argv) > 1 else os.path.join(here, "..", "assets", "smoke-tender-entry.pdf")
    out_path = os.path.abspath(out_path)
    if os.path.islink(out_path):
        print("ERROR: refusing to write through a symlink at the explicit output path: %s" % out_path, file=sys.stderr)
        return 4
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    data = build()
    d = os.path.dirname(out_path)
    # Random exclusive temp (O_EXCL, mode 0600): never follows any pre-placed link.
    fd, tmp = tempfile.mkstemp(prefix=".smoke-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, out_path)
    except BaseException:
        try:
            os.unlink(tmp)  # only ever removes the temp file this call owns
        except OSError:
            pass
        raise
    print("WROTE %s (%d bytes)" % (out_path, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
