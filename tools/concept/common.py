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


def to_frame(path, guides, info=None):
    """Remet une génération (taille de la toile) au cadre du sprite original, détourée par sa silhouette.

    guide-cadre.txt : position et taille, dans la toile, de la partie visible du sprite agrandie ;
    guide-sprite.json : taille du cadre (`frame`) et boîte de la partie visible dans ce cadre (`bbox`)."""
    info = info or json.load(open(os.path.join(guides, "guide-sprite.json")))
    W, H = info["frame"]
    x0, y0, x1, y1 = info["bbox"]
    ox, oy, bw, bh = map(int, open(os.path.join(guides, "guide-cadre.txt")).read().split())
    mask = Image.open(os.path.join(guides, "guide-masque.png")).convert("L")
    g = Image.open(path).convert("RGB").resize(mask.size, Image.LANCZOS)
    g.putalpha(mask)
    part = g.crop((ox, oy, ox + bw, oy + bh)).resize((x1 - x0, y1 - y0), Image.LANCZOS)
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frame.alpha_composite(part, (x0, y0))
    return frame
