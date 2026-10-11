"""Guides pour ComfyUI à partir d'un sprite du jeu : contours, profondeur, masque et cadrage.

Lancé avec l'environnement de ComfyUI (transformers, pour Depth Anything V2) :
  ~/workspace/comfyui/.venv/bin/python -I celshading/concept/prepare.py <sortie> <sprite> [l h] [--toile L H]
<sprite> : chemin sous data/ de Factorio (ex. base/graphics/entity/assembling-machine-1/assembling-machine-1.png) ;
l h : taille d'une image de la planche (découpe en haut à gauche ; sinon le fichier entier) ;
--toile : taille de génération (défaut 1024 x 1024 ; SDXL travaille vers 1 Mpx, côtés multiples de 64).

Écrit dans <sortie> : guide-original.png (sprite agrandi sur fond gris), guide-contours.png (Canny lissé +
silhouette), guide-profondeur.png, guide-masque.png, guide-cadre.txt (x y l h du sprite dans la toile).
D'après les scripts de l'essai du propulseur (mod cartoon, 11 octobre).
"""
import argparse, os
import cv2
import numpy as np
from PIL import Image

DATA = os.environ.get("FACTORIO_DIR", "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio") + "/data/"
BG = (150, 150, 150)

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("sprite")
ap.add_argument("cell", nargs="*", type=int)
ap.add_argument("--toile", nargs=2, type=int, default=(1024, 1024))
a = ap.parse_args()
CW, CH = a.toile
os.makedirs(a.out, exist_ok=True)

fr = Image.open(DATA + a.sprite).convert("RGBA")
if a.cell:
    fr = fr.crop((0, 0, a.cell[0], a.cell[1]))
fr = fr.crop(fr.getbbox())
k = min(CW / fr.width, CH / fr.height) * 0.9
big = fr.resize((round(fr.width * k), round(fr.height * k)), Image.LANCZOS)
ox, oy = (CW - big.width) // 2, (CH - big.height) // 2
on_bg = Image.new("RGBA", (CW, CH), BG + (255,))
on_bg.alpha_composite(big, (ox, oy))
on_bg = on_bg.convert("RGB")
on_bg.save(f"{a.out}/guide-original.png")
alpha = np.zeros((CH, CW), np.uint8)
alpha[oy:oy + big.height, ox:ox + big.width] = np.asarray(big)[:, :, 3]
mask = (alpha > 128).astype(np.uint8)
Image.fromarray(mask * 255).save(f"{a.out}/guide-masque.png")
open(f"{a.out}/guide-cadre.txt", "w").write(f"{ox} {oy} {big.width} {big.height}\n")

# contours : Canny sur l'original lissé (grandes formes, pas le bruit de texture) + silhouette
g = cv2.cvtColor(np.asarray(on_bg), cv2.COLOR_RGB2GRAY)
g = cv2.bilateralFilter(g, 9, 60, 9)
edges = cv2.Canny(g, 60, 140)
edges[mask == 0] = 0
sil = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) * 255
Image.fromarray(np.maximum(edges, sil)).save(f"{a.out}/guide-contours.png")

# profondeur : Depth Anything V2 (petit modèle), fond repoussé au loin
from transformers import pipeline
depth = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=0)
dm = np.asarray(depth(on_bg)["depth"].resize((CW, CH)), np.float32)
lo, hi = np.percentile(dm[mask > 0], 2), np.percentile(dm[mask > 0], 99.5)
dm = np.clip((dm - lo) / (hi - lo), 0, 1) * 200 + 40
dm[mask == 0] = 0
Image.fromarray(dm.astype(np.uint8)).save(f"{a.out}/guide-profondeur.png")
print("guides dans", a.out)
