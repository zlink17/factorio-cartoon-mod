"""Fonctions partagées des outils d'images cibles (planche.py, compare.py)."""
import json, os
from PIL import Image, ImageDraw

DATA = os.environ.get("FACTORIO_DIR", "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio") + "/data/"
PX = 64                      # pixels par case dans les fichiers du jeu (sprites à scale 0,5)
SOLS = {                     # (fond, case, joint) : sols neutres pour juger un sprite « en jeu »
    "gris": ((70, 72, 76), (70, 72, 76), (70, 72, 76)),
    "herbe": ((92, 104, 58), (92, 104, 58), (84, 96, 52)),
    "plateforme": ((8, 10, 22), (96, 98, 104), (78, 80, 86)),
}


def sol(name, tw, th):
    """Sol de `tw` x `th` cases ; « plateforme » : cases grises sur la moitié haute, vide spatial dessous."""
    bg, tile, joint = SOLS[name]
    c = Image.new("RGBA", (tw * PX, th * PX), bg + (255,))
    d = ImageDraw.Draw(c)
    rows = th // 2 if name == "plateforme" else th
    for tx in range(tw):
        for ty in range(rows):
            d.rectangle((tx * PX, ty * PX, tx * PX + PX - 1, ty * PX + PX - 1), fill=tile, outline=joint)
    return c


def background_mask(rgb, tol=18):
    """Masque (L, 255 = objet) d'une génération à fond uni : tout ce qui touche le bord et ressemble à la couleur
    des coins (à `tol` près) est du fond. Pour les variantes libres, qui débordent de la silhouette de l'original."""
    import cv2, numpy as np
    im = np.ascontiguousarray(np.asarray(rgb.convert("RGB"))[:, :, ::-1])
    h, w = im.shape[:2]
    ff = np.zeros((h + 2, w + 2), np.uint8)
    flags = 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8)
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if not ff[y + 1, x + 1]:
            cv2.floodFill(im, ff, (x, y), 0, (tol,) * 3, (tol,) * 3, flags)
    obj = (ff[1:-1, 1:-1] == 0).astype(np.uint8)
    obj = cv2.morphologyEx(obj, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return Image.fromarray(obj * 255)


def to_frame(path, guides, info=None, detour="original"):
    """Remet une génération (taille de la toile) au cadre du sprite original, détourée par sa silhouette
    (`detour="original"`) ou par son propre fond uni (`detour="fond"`, variantes qui changent la silhouette).

    guide-cadre.txt : position et taille, dans la toile, de la partie visible du sprite agrandie ;
    guide-sprite.json : taille du cadre (`frame`) et boîte de la partie visible dans ce cadre (`bbox`)."""
    info = info or json.load(open(os.path.join(guides, "guide-sprite.json")))
    W, H = info["frame"]
    x0, y0, x1, y1 = info["bbox"]
    ox, oy, bw, bh = map(int, open(os.path.join(guides, "guide-cadre.txt")).read().split())
    mask = Image.open(os.path.join(guides, "guide-masque.png")).convert("L")
    g = Image.open(path).convert("RGB").resize(mask.size, Image.LANCZOS)
    g.putalpha(background_mask(g) if detour == "fond" else mask)
    part = g.crop((ox, oy, ox + bw, oy + bh)).resize((x1 - x0, y1 - y0), Image.LANCZOS)
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frame.alpha_composite(part, (x0, y0))
    return frame


def pixelise(frame, shift=(0, 0), k=4, colors=24):
    """Aperçu « pixel art » d'un sprite au cadre de l'original : réduit à 1 px d'art pour k px de fichier (grille
    alignée sur le monde, comme pixel/pixlib/cadre.py), transparence nette, `colors` couleurs (palette adaptée à
    l'image : la palette du mod se fixe justement d'après les cibles), puis agrandi au plus proche voisin."""
    W, H = frame.size
    ox = (round(W / 2 - shift[0] * PX) % k)
    oy = (round(H / 2 - shift[1] * PX) % k)
    px, py = (k - ox) % k, (k - oy) % k                  # marge pour que la grille commence au bord
    cw, ch = -(-(W + px) // k) * k, -(-(H + py) // k) * k
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    canvas.alpha_composite(frame, (px, py))
    small = canvas.resize((cw // k, ch // k), Image.BOX)
    alpha = small.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    rgb = small.convert("RGB").quantize(colors, method=Image.Quantize.MEDIANCUT).convert("RGB")
    rgb.putalpha(alpha)
    big = rgb.resize((cw, ch), Image.NEAREST)
    return big.crop((px, py, px + W, py + H))
