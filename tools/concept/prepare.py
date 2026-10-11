"""Guides pour ComfyUI à partir d'un sprite du jeu : contours, profondeur, masque et cadrage.

Lancé avec l'environnement de ComfyUI (transformers, pour Depth Anything V2) :
  ~/workspace/comfyui/.venv/bin/python -I tools/concept/prepare.py <sortie> <sprite> [l h] [--toile L H]
                                                                    [--shift X Y]
<sprite> : chemin sous data/ de Factorio (ex. base/graphics/entity/assembling-machine-1/assembling-machine-1.png),
           ou chemin absolu (image composée à part : calques d'un personnage, masque teinté) ;
l h : taille d'une image de la planche (découpe en haut à gauche ; sinon le fichier entier) ;
--toile : taille de génération ; par défaut, ~1 Mpx aux proportions du sprite (côtés multiples de 64, ce que
          SDXL attend) : un sprite haut (propulseur) n'est pas écrasé dans un carré ;
--shift : décalage du sprite en cases (`shift` du prototype) : place le sprite dans les vues « en jeu ».

Écrit dans <sortie> : guide-original.png (sprite agrandi sur fond gris, à la taille de la toile : concept.py en
reprend la taille), guide-contours.png (Canny lissé + silhouette), guide-profondeur.png, guide-masque.png,
guide-cadre.txt (x y l h de la partie visible du sprite dans la toile), guide-sprite.json (sprite, taille du cadre,
boîte de la partie visible dans le cadre, shift : pour remettre une génération au format du jeu, voir common.py).
"""
import argparse, json, math, os
import cv2
import numpy as np
from PIL import Image

DATA = os.environ.get("FACTORIO_DIR", "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio") + "/data/"
BG = (150, 150, 150)

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("sprite")
ap.add_argument("cell", nargs="*", type=int)
ap.add_argument("--toile", nargs=2, type=int)
ap.add_argument("--shift", nargs=2, type=float, default=(0.0, 0.0))
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

fr = Image.open(a.sprite if os.path.isabs(a.sprite) else DATA + a.sprite).convert("RGBA")
if a.cell:
    fr = fr.crop((0, 0, a.cell[0], a.cell[1]))
frame = fr.size
bbox = fr.getbbox()
fr = fr.crop(bbox)
if a.toile:
    CW, CH = a.toile
else:                                              # ~1 Mpx aux proportions de la partie visible
    r = fr.width / fr.height
    CW = max(512, round(math.sqrt(1024 * 1024 * r) / 64) * 64)
    CH = max(512, round(math.sqrt(1024 * 1024 / r) / 64) * 64)
json.dump({"sprite": a.sprite, "frame": list(frame), "bbox": list(bbox), "shift": list(a.shift)},
          open(f"{a.out}/guide-sprite.json", "w"), indent=1)
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
