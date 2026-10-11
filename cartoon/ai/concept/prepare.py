"""Guides pour ComfyUI : contours et profondeur du propulseur original, références de style (nos sprites validés).

Lancé avec l'environnement de ComfyUI (transformers pour Depth Anything V2).
Usage : python prepare.py <dossier_sortie> <repo>
"""
import sys
import cv2
import numpy as np
from PIL import Image

OUT, REPO = sys.argv[1], sys.argv[2]
D = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio/data/"
OV = f"{REPO}/cartoon/mod/graphics/overrides/base/entity/"
CW, CH = 512, 1024          # toile de génération (SDXL : ~0,5 Mpx, rapport du sprite 264 x 542)
BG = (150, 150, 150)

fr = Image.open(D + "space-age/graphics/entity/thruster/thruster-1.png").convert("RGBA").crop((0, 0, 264, 542))
k = min(CW / fr.width, CH / fr.height) * 0.96
big = fr.resize((round(fr.width * k), round(fr.height * k)), Image.LANCZOS)
ox, oy = (CW - big.width) // 2, (CH - big.height) // 2
on_bg = Image.new("RGBA", (CW, CH), BG + (255,))
on_bg.alpha_composite(big, (ox, oy))
on_bg = on_bg.convert("RGB")
on_bg.save(f"{OUT}/guide-original.png")
alpha = np.zeros((CH, CW), np.uint8)
alpha[oy:oy + big.height, ox:ox + big.width] = np.asarray(big)[:, :, 3]
mask = (alpha > 128).astype(np.uint8)
Image.fromarray(mask * 255).save(f"{OUT}/guide-masque.png")
# cadrage, pour remettre la génération au format du sprite
open(f"{OUT}/guide-cadre.txt", "w").write(f"{ox} {oy} {big.width} {big.height}\n")

# contours : Canny sur l'original lissé (on garde les grandes formes, pas le bruit de texture) + silhouette
g = cv2.cvtColor(np.asarray(on_bg), cv2.COLOR_RGB2GRAY)
g = cv2.bilateralFilter(g, 9, 60, 9)
edges = cv2.Canny(g, 60, 140)
edges[mask == 0] = 0
sil = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) * 255
Image.fromarray(np.maximum(edges, sil)).save(f"{OUT}/guide-contours.png")

# profondeur : Depth Anything V2 (petit modèle), fond repoussé au loin
from transformers import pipeline
depth = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=0)
dm = np.asarray(depth(on_bg)["depth"].resize((CW, CH)), np.float32)
lo, hi = np.percentile(dm[mask > 0], 2), np.percentile(dm[mask > 0], 99.5)
dm = np.clip((dm - lo) / (hi - lo), 0, 1) * 200 + 40
dm[mask == 0] = 0
Image.fromarray(dm.astype(np.uint8)).save(f"{OUT}/guide-profondeur.png")

# références de style : quelques sprites du mod, chacun sur fond gris, carrés
refs = [("assembling-machine-1/assembling-machine-1.png", (214, 226)),
        ("boiler/boiler-N-idle.png", None),
        ("steam-engine/steam-engine-H.png", (352, 257)),
        ("radar/radar.png", (196, 254)),
        ("lab/lab.png", (194, 174))]
for i, (rel, cell) in enumerate(refs):
    im = Image.open(OV + rel).convert("RGBA")
    if cell:
        im = im.crop((0, 0) + cell)
    im = im.crop(im.getbbox())
    s = 448 / max(im.size)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    sq = Image.new("RGBA", (512, 512), BG + (255,))
    sq.alpha_composite(im, ((512 - im.width) // 2, (512 - im.height) // 2))
    sq.convert("RGB").save(f"{OUT}/style-{i}.png")
print("ok", ox, oy, big.size)
