#!/usr/bin/env python3
"""
Prepare a portrait photo for clean ASCII conversion:
  1. remove the background (rembg with u2net model) so the subject is isolated
  2. boost LOCAL contrast (CLAHE) so a flatly-lit face gains highlights and
     shadows -- this is what turns a dark blob into a recognizable face
  3. composite the subject onto pure white so the background reads as blank
     (white -> spaces in the ascii ramp)

Output: source-prepped.png (grayscale), consumed by make_ascii_svg.py.
Run once whenever the source photo changes; the ascii SVG itself is static.

    python scripts/prep_photo.py [input.png/jpg] [output.png]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))

def get_default_input():
    for name in ["source-photo.png", "source-photo.jpg", "source-photo.jpeg"]:
        p = os.path.join(HERE, "..", name)
        if os.path.exists(p):
            return p
    return os.path.join(HERE, "..", "source-photo.png")

INP = sys.argv[1] if len(sys.argv) > 1 else get_default_input()
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")

def main():
    if not os.path.exists(INP):
        print(f"Error: input photo not found: {INP}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {INP} -> {OUT}...")
    img = Image.open(INP).convert("RGBA")

    try:
        from rembg import new_session, remove
        session = new_session("u2net")
        cut = remove(img, session=session)
    except Exception as e:
        print(f"rembg removal fallback: {e}")
        from rembg import remove
        cut = remove(img)

    rgb = np.array(cut.convert("RGB"))
    alpha = np.array(cut.split()[-1])  # 0 = background

    # 2. local-contrast the luminance (CLAHE)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # a touch of global lift so the face sits in the sparse end of the ramp
    gray = cv2.convertScaleAbs(gray, alpha=1.05, beta=18)

    # 3. paste onto white using the alpha mask (feathered a hair to avoid a halo)
    mask = alpha.astype(np.float32) / 255.0
    mask = cv2.GaussianBlur(mask, (0, 0), 1.0)
    out = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out, mode="L").save(OUT)
    print("wrote", OUT, out.shape)

if __name__ == "__main__":
    main()
