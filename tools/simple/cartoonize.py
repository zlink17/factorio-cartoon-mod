#!/usr/bin/env python3
"""Convertit les textures de Factorio en style cartoon.

Usage :
    python tools/cartoonize.py --data "<dossier Factorio>/data" [--mods base] [--limit 20]

Pour chaque PNG de <data>/<mod>/graphics, écrit la version cartoon dans
graphics/generated/<mod>/... (à la racine du mod) puis régénère manifest.lua.
Le canal alpha est conservé tel quel.
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from build_manifest import build_manifest  # noqa: E402


def cartoonize(img_bgra, colors=12, edge_strength=1):
    bgr = img_bgra[:, :, :3]
    alpha = img_bgra[:, :, 3]

    # 1. Lissage des aplats en conservant les contours
    smooth = bgr
    for _ in range(2):
        smooth = cv2.bilateralFilter(smooth, d=7, sigmaColor=40, sigmaSpace=7)

    # 2. Réduction du nombre de couleurs (k-means sur les pixels opaques)
    mask = alpha > 0
    pixels = smooth[mask].astype(np.float32)
    if len(pixels) > colors:
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels, colors, None, criteria, 2, cv2.KMEANS_PP_CENTERS
        )
        quant = smooth.copy()
        quant[mask] = centers.astype(np.uint8)[labels.flatten()]
    else:
        quant = smooth

    # 3. Saturation augmentée
    hsv = cv2.cvtColor(quant, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.25, 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.05, 0, 255)
    quant = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 4. Contours noirs
    gray = cv2.cvtColor(smooth, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(
        cv2.medianBlur(gray, 3), 255,
        cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 7, 6,
    )
    if edge_strength > 1:
        edges = cv2.erode(edges, np.ones((edge_strength, edge_strength), np.uint8))
    quant = cv2.bitwise_and(quant, quant, mask=edges)

    out = np.dstack([quant, alpha])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path,
                        help="Dossier data/ de l'installation Factorio")
    parser.add_argument("--mods", nargs="+", default=["base"],
                        help="Sous-dossiers de data/ à traiter (base, core, space-age...)")
    parser.add_argument("--colors", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0,
                        help="Ne traiter que N fichiers (pour tester)")
    args = parser.parse_args()

    converted = []
    for mod in args.mods:
        gfx_dir = args.data / mod / "graphics"
        for src in sorted(gfx_dir.rglob("*.png")):
            if args.limit and len(converted) >= args.limit:
                break
            rel = src.relative_to(gfx_dir).as_posix()
            img = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
            if img is None:
                continue
            if img.ndim == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            if img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            dst = ROOT / "graphics" / "generated" / mod / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(dst), cartoonize(img, colors=args.colors))
            converted.append(f"__{mod}__/graphics/{rel}")
            print("OK", converted[-1])

    build_manifest()
    print(f"{len(converted)} fichiers convertis.")


if __name__ == "__main__":
    main()
