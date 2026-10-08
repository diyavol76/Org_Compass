#!/usr/bin/env python3
"""Cut a large or dense diagram image into overlapping, upscaled tiles so small text,
arrowheads and gateway markers survive the vision model's downscaling.

Usage: tile_image.py <image> --out DIR [--cols 2] [--rows 2] [--overlap 0.15] [--scale 2.0]
Requires Pillow (pip install pillow). Writes DIR/tile_r{row}_c{col}.png and DIR/overview.png.
Vision models lose small markers (dashed message flows, event-gateway pentagons, '+' in diamonds)
when a big image is downscaled: always read tiles for dense diagrams, then the overview for topology.
"""
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow missing: pip install pillow")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--rows", type=int, default=2)
    ap.add_argument("--overlap", type=float, default=0.15)
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--max-side", type=int, default=2000, help="cap tile longest side after scaling")
    a = ap.parse_args()
    im = Image.open(a.image).convert("RGB")
    W, H = im.size
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tw, th = W / a.cols, H / a.rows
    ox, oy = tw * a.overlap, th * a.overlap
    for r in range(a.rows):
        for c in range(a.cols):
            box = (max(0, int(c * tw - ox)), max(0, int(r * th - oy)),
                   min(W, int((c + 1) * tw + ox)), min(H, int((r + 1) * th + oy)))
            t = im.crop(box)
            s = min(a.scale, a.max_side / max(t.size))
            t = t.resize((int(t.width * s), int(t.height * s)), Image.LANCZOS)
            p = out / f"tile_r{r + 1}_c{c + 1}.png"
            t.save(p)
            print(f"{p}  region(px)={box}  size={t.size}")
    ov = im.copy()
    ov.thumbnail((a.max_side, a.max_side))
    ov.save(out / "overview.png")
    print(f"{out / 'overview.png'}  size={ov.size}  (original {W}x{H})")


if __name__ == "__main__":
    main()
