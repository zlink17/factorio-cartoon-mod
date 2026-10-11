"""Références de style pour l'IP-Adapter : nos propres rendus cel-shading, recadrés et centrés sur fond gris (512 px).

Usage : python tools/concept/styles.py <dossier_guides> <image>...
Chaque <image> est un PNG RGBA (chemin du repo), suivi éventuellement de :l:h pour découper la première image d'une
planche (ex. celshading/mod/graphics/overrides/base/entity/assembling-machine-1/assembling-machine-1.png:214:226).
Écrit <dossier_guides>/style-0.png, style-1.png...
"""
import sys
import cv2
import numpy as np


def square(im, size=512, fill=440, grey=150):
    ys, xs = np.where(im[:, :, 3] > 0)
    im = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    s = fill / max(im.shape[:2])
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    out = np.full((size, size, 3), grey, np.float32)
    h, w = im.shape[:2]
    y, x = (size - h) // 2, (size - w) // 2
    a = im[:, :, 3:4] / 255.0
    out[y:y + h, x:x + w] = im[:, :, :3] * a + out[y:y + h, x:x + w] * (1 - a)
    return out.astype(np.uint8)


if __name__ == "__main__":
    out, *images = sys.argv[1:]
    for i, spec in enumerate(images):
        path, *cell = spec.split(":")
        im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if cell:
            im = im[:int(cell[1]), :int(cell[0])]
        cv2.imwrite(f"{out}/style-{i}.png", square(im))
        print(f"{out}/style-{i}.png", "<-", spec)
