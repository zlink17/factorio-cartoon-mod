"""Génère la planche d'animation de l'assembleur (32 images, 8 colonnes x 4 lignes).

Usage : python tools/blender/animate.py <dossier_sortie>

Sortie :
  <sortie>/frames/frame_00.png ... frame_31.png   images séparées (214 x 226, transparentes)
  <sortie>/assembling-machine-1.png                planche 1712 x 904, même agencement que l'original
  <sortie>/apercu.gif                              aperçu animé sur fond gris (non utilisé par le mod)
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2
import numpy as np
from assembler import FRAME, N_FRAMES, fit_camera, render_phase

COLUMNS = 8


def main(out):
    frames_dir = os.path.join(out, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    scale, shift = fit_camera(out, 0.0)          # une seule caméra pour toutes les images
    print("caméra", round(scale, 4), round(shift, 4))
    paths = []
    for i in range(N_FRAMES):
        p = os.path.join(frames_dir, f"frame_{i:02d}.png")
        render_phase(p, i / N_FRAMES, scale, shift)
        paths.append(p)
    w, h = FRAME
    rows = (N_FRAMES + COLUMNS - 1) // COLUMNS
    sheet = np.zeros((rows * h, COLUMNS * w, 4), np.uint8)
    for i, p in enumerate(paths):
        r, c = divmod(i, COLUMNS)
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    cv2.imwrite(os.path.join(out, "assembling-machine-1.png"), sheet)
    # aperçu animé
    from PIL import Image
    imgs = []
    for p in paths:
        im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        a = im[:, :, 3:4] / 255.0
        bg = np.full(im.shape[:2] + (3,), 90, np.float32)
        flat = (im[:, :, :3] * a + bg * (1 - a)).astype(np.uint8)
        flat = cv2.resize(flat, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        imgs.append(Image.fromarray(cv2.cvtColor(flat, cv2.COLOR_BGR2RGB)))
    imgs[0].save(os.path.join(out, "apercu.gif"), save_all=True, append_images=imgs[1:], duration=60, loop=0)
    print("OK", sheet.shape, os.path.join(out, "assembling-machine-1.png"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "animation_out")
