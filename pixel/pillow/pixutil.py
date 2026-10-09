"""Utilitaires de dessin pixel art : ombrage automatique d'une forme (contour, lumière haut-gauche, ombre bas-droite)."""
from PIL import Image


def autoshade(mask, ramp):
    """`mask` : image L (255 = dans la forme) ; `ramp` : (contour, ombre, moyen, lumière) en RGBA.

    Contour = pixels de la forme qui touchent un pixel vide ; juste à l'intérieur, lumière du côté haut/gauche,
    ombre du côté bas/droite, ton moyen ailleurs.
    """
    out_c, dark, mid, light = ramp
    w, h = mask.size
    px = mask.load()
    inside = lambda x, y: 0 <= x < w and 0 <= y < h and px[x, y] > 0
    edge = {(x, y) for y in range(h) for x in range(w) if inside(x, y)
            and not (inside(x - 1, y) and inside(x + 1, y) and inside(x, y - 1) and inside(x, y + 1))}
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            if not inside(x, y):
                continue
            if (x, y) in edge:
                c = out_c
            elif (x - 1, y) in edge or (x, y - 1) in edge:
                c = light
            elif (x + 1, y) in edge or (x, y + 1) in edge:
                c = dark
            else:
                c = mid
            img.putpixel((x, y), c)
    return img


def silhouette(img, color=(0, 0, 0, 255)):
    """Forme pleine d'une image (pour les ombres)."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(color, (0, 0), img.getchannel("A").point(lambda v: 255 if v else 0))
    return out


def upscale(img, k):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)
