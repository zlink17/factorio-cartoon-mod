#!/usr/bin/env python3
"""Prépare une image générée par IA pour l'utiliser comme sprite Factorio.

Usage :
    python tools/complex/postprocess.py --input gemini_out.png \\
        --reference "<data>/base/graphics/entity/assembling-machine-1/assembling-machine-1.png" \\
        --mod base --path entity/assembling-machine-1/assembling-machine-1.png

- détoure le fond (couleur du coin supérieur gauche, avec tolérance),
- redimensionne à la taille exacte du sprite original,
- écrit le résultat dans graphics/overrides/<mod>/<path> puis régénère manifest.lua.
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from build_manifest import build_manifest  # noqa: E402


def remove_background(img_bgr, tolerance):
    corner = img_bgr[0, 0].astype(np.int32)
    diff = np.abs(img_bgr.astype(np.int32) - corner).sum(axis=2)
    alpha = np.where(diff <= tolerance, 0, 255).astype(np.uint8)
    # adoucit légèrement le bord du détourage
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    return np.dstack([img_bgr, alpha])


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="Image générée")
    parser.add_argument("--reference", required=True, type=Path,
                        help="Sprite original (pour récupérer la taille)")
    parser.add_argument("--mod", default="base")
    parser.add_argument("--path", required=True,
                        help="Chemin du sprite sous <mod>/graphics/, ex. entity/foo/foo.png")
    parser.add_argument("--tolerance", type=int, default=60,
                        help="Tolérance du détourage (somme des écarts BGR)")
    args = parser.parse_args()

    gen = cv2.imread(str(args.input), cv2.IMREAD_COLOR)
    ref = cv2.imread(str(args.reference), cv2.IMREAD_UNCHANGED)
    if gen is None or ref is None:
        sys.exit("Impossible de lire l'image générée ou le sprite de référence.")

    h, w = ref.shape[:2]
    out = remove_background(gen, args.tolerance)
    out = cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA)

    dst = ROOT / "graphics" / "overrides" / args.mod / args.path
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), out)
    build_manifest()
    print(f"OK {dst.relative_to(ROOT)} ({w}x{h})")


if __name__ == "__main__":
    main()
