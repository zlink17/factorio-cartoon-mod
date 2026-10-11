"""Machine à vapeur (steam-engine) : planches animées horizontale et verticale, ombres, icône.

Usage : python cartoon/blender/steam_engine.py <dossier_sortie> [H|V|toutes] [--apercu]
        --apercu : une seule image par planche (réglages)

Écrit, aux chemins de l'original (base/entity/steam-engine/ et base/icons/) :
  steam-engine-H.png          32 images (8 par ligne), machine posée est-ouest
  steam-engine-H-shadow.png   32 ombres, noires unies
  steam-engine-V.png          32 images, machine posée nord-sud
  steam-engine-V-shadow.png   32 ombres
  steam-engine.png (icône)    64 px + mipmaps
Les restes sont laissés d'origine (lot 3.9).

La machine (5 x 3 cases) : châssis sombre sur pieds en A rouille, trois cylindres à vapeur verticaux en rangée
(tôle claire, couvercle à soupape), longue conduite claire devant les cylindres, volant et engrenages sur la face
avant à droite, entraînés par une bielle depuis une crosse qui coulisse. Aux deux bouts, les raccords sont le tube
et la bride du tuyau (pipe.py), au bord de la case comme ceux de la chaudière : entre deux machines en file, les
deux brides forment le joint, dégagé par un châssis plus court que la machine (comme l'original).
Modèle construit à l'horizontale (axe x) puis tourné pour la planche verticale : les engrenages passent alors sur
le côté gauche, comme dans l'original. La planche verticale est allongée nord-sud de KY (le sol est raccourci
de cos 30° à l'écran) pour couvrir ses 5 cases, sinon un vide sépare deux machines en file. L'animation (32 images, en boucle) fait un tour de volant.
"""
import math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
import pipe as PIPE
from lib import box, crop_centered, cyl, entity_path, gear, load, mat, render_scene, render_shadow, reset, rod, save_icon, sheet

P = S.PALETTE
NAME = "steam-engine"
PX_PER_TILE = 64
CANVAS = 768                                    # l'ombre horizontale (508 px, décalée de 96) doit tenir dedans
N_FRAMES, COLUMNS = 32, 8
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.022
KY = 1 / math.cos(math.radians(S.PITCH_BUILDING_DEG))   # le sol nord-sud est raccourci de cos 30° à l'écran
YAW = {"H": 0, "V": -90}                       # verticale : l'avant (engrenages) passe à gauche
# cadres de l'original (taille, décalage en px = shift x 64) : sprite, puis ombre
FRAMES = {
    "H": (((352, 257), (2.0, -9.5)), ((508, 160), (96.0, 48.0))),
    "V": (((225, 391), (9.5, -12.5)), ((330, 307), (81.0, 18.5))),
}

# dimensions (cases), ajustées sur la silhouette de l'original (deux planches, image 0)
DIMS = dict(
    L=4.4, D=2.6,                  # châssis : longueur (x), profondeur (y) ; raccourci pour dégager les raccords
    zc=0.5,                        # dessus du châssis
    rk=0.7, hk=1.6, yk=0.4,        # cylindres : rayon, hauteur au-dessus du châssis, position y
    down=0.24,                     # décalage de tout le dessin vers le bas de l'écran (comme les originaux)
)
TANK_X = (-1.55, 0.0, 1.55)        # trois cylindres presque jointifs
# bornes de l'ajustement : laissés libres, cylindres et châssis grandissent et cachent le mécanisme (la moitié
# basse de l'original)
BOUNDS = dict(rk=(0.45, 0.7), L=(4.0, 4.9), D=(1.6, 2.6), zc=(0.4, 0.7), yk=(0.3, 0.6))


def within(d):
    return all(lo <= d[k] <= hi for k, (lo, hi) in BOUNDS.items())


def face_camera(view, tilt):
    """Orientation (matrice 3 x 3, repère du modèle) d'une pièce plate qui, une fois le modèle tourné pour `view`,
    est inclinée de `tilt` degrés vers l'avant du monde, donc face à la caméra."""
    from mathutils import Matrix
    return (Matrix.Rotation(math.radians(-YAW[view]), 3, "Z") @ Matrix.Rotation(math.radians(tilt), 3, "X"))


def tgear(center, r, teeth, angle, m, hub_m, orient):
    """Engrenage tourné face à la caméra (`orient`, voir face_camera) : debout face à l'avant, une roue est
    écrasée de moitié par la vue à 30° et se perd dans le plateau ; l'original les montre presque rondes."""
    from mathutils import Matrix, Vector
    o = gear((0, 0, 0), r, 0.08, teeth, angle, m)
    o.matrix_world = Matrix.Translation(center) @ orient.to_4x4()
    hub = cyl((0, 0, 0), r * 0.34, 0.06, hub_m, verts=12)
    hub.matrix_world = Matrix.Translation(Vector(center) + orient @ Vector((0, 0, 0.06))) @ orient.to_4x4()
    return o


def build(view="H", phase=0.0, d=None):
    import bpy
    from mathutils import Matrix
    reset()
    d = d or DIMS
    dark = mat("dark", P["dark"])
    rust = mat("rust", P["engine_rust"])
    tank = mat("tank", P["engine_tank"])
    pipe = mat("pipe", P["engine_pipe"])
    copper = mat("copper", P["brown"])
    brass = mat("brass", P["yellow"])
    iron = mat("iron", P["iron"])
    L, D, zc = d["L"], d["D"], d["zc"]
    # châssis et pieds en A (devant et derrière)
    box((0, 0, zc - 0.12), (L, D * 0.8, 0.24), dark)
    for x in (-1.7, -0.55, 0.6, 1.75):
        for s in (-1, 1):
            rod((x - 0.28, s * D * 0.55, 0.02), (x, s * D * 0.38, zc - 0.2), 0.07, rust, verts=8)
            rod((x + 0.28, s * D * 0.55, 0.02), (x, s * D * 0.38, zc - 0.2), 0.07, rust, verts=8)
    # raccords de fluide aux deux bouts : posés après la rotation (connectors)
    # trois cylindres à vapeur au fond du plateau, couvercle et soupape laiton
    rk, hk, yk = d["rk"], d["hk"], d["yk"]
    for x in TANK_X:
        cyl((x, yk, zc + hk / 2), rk, hk, tank, verts=32)
        cyl((x, yk, zc + hk + 0.04), rk * 0.75, 0.08, pipe, verts=32)
        for z in (zc + 0.25, zc + hk - 0.12):
            cyl((x, yk, z), rk + 0.025, 0.08, copper, verts=32)                     # cerclages
        cyl((x, yk, zc + hk + 0.18), 0.09, 0.22, pipe, verts=12)
        cyl((x, yk, zc + hk + 0.3), 0.14, 0.05, brass, verts=12)
        rod((x + 0.25, yk - rk * 0.75, zc + hk - 0.1), (x + 0.25, yk - rk - 0.32, zc + 0.75), 0.07, copper, verts=12)
    # conduite claire devant les cylindres, de bout en bout, qui descend vers le raccord gauche
    yp = yk - rk - 0.08
    rod((-2.1, yp, zc + 0.75), (2.1, yp, zc + 0.75), 0.1, pipe, verts=16)
    rod((-2.1, yp, zc + 0.75), (-2.1, 0.1, 0.45), 0.1, pipe, verts=16)
    # devant, sur le plateau : radiateur à gauche (lamelles peintes en bandes), glissière et crosse au centre,
    # volant et engrenages debout à droite, face à l'avant ; une bielle relie la crosse au volant
    yf = yk - rk - 0.6
    box((-1.5, yf, zc + 0.3), (0.9, 0.45, 0.6), rust)
    for k in range(4):
        box((-1.85 + k * 0.23, yf - 0.24, zc + 0.3), (0.1, 0.04, 0.5), pipe)
    a = phase * 360
    fx, fz, fr = 1.25, zc + 0.75, 0.5
    from mathutils import Vector
    orient = face_camera(view, S.PITCH_BUILDING_DEG)
    tgear((fx, yf, fz), fr, 18, a, iron, brass, orient)
    tgear((fx + 0.72, yf - 0.1, fz - 0.12), 0.25, 9, -a * 18 / 9 + 10, brass, iron, orient)
    tgear((fx - 0.66, yf + 0.1, fz + 0.12), 0.2, 8, -a * 18 / 8 + 5, brass, iron, orient)
    rr = fr * 0.65
    pin = tuple(Vector((fx, yf, fz)) + orient @ Vector((rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a)),
                                                        0.1)))
    cross_x = fx - 1.25 + rr * math.cos(math.radians(a))
    box((-0.15, yf, zc + 0.15), (1.3, 0.4, 0.3), iron)                             # glissière
    box((cross_x, yf - 0.05, zc + 0.42), (0.32, 0.24, 0.26), brass)                # crosse
    rod((cross_x, yf - 0.1, zc + 0.48), pin, 0.075, pipe, verts=10)                # bielle
    rod((cross_x - 0.75, yf - 0.05, zc + 0.42), (cross_x, yf - 0.05, zc + 0.42), 0.065, pipe, verts=10)   # tige
    # évent de vapeur à l'arrière gauche (le jeu fait sortir la fumée là)
    rod((-2.15, D * 0.3, zc), (-2.15, D * 0.3, zc + 1.7), 0.07, pipe, verts=10)
    bpy.context.view_layer.update()          # matrices à jour (sinon le dernier objet perd son échelle)
    rot = Matrix.Rotation(math.radians(YAW[view]), 4, "Z")
    if view == "V":                          # nord-sud : allongée de KY pour couvrir ses 5 cases à l'écran
        rot = Matrix.Diagonal((1, KY, 1, 1)) @ rot
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.matrix_world = rot @ o.matrix_world
    connectors(view, d)


# raccords du prototype (cases, y vers le sud comme dans le jeu) : position du bord, direction vers l'extérieur
CONNECTIONS = {"H": [((-2.5, 0), (-1, 0)), ((2.5, 0), (1, 0))], "V": [((0, -2.5), (0, -1)), ((0, 2.5), (0, 1))]}
STUB = 0.6                                   # longueur de l'embout, du bord de la case vers l'intérieur


def connectors(view, d=None):
    """Embouts des raccords : le tube et la bride du tuyau (pipe.py) au bord de la case, posés dans le repère du
    monde comme ceux de la chaudière : à l'écran, ils tombent exactement sur ceux d'un tuyau ou d'une autre machine
    voisine, dont la bride complète le raccord (un bord à `gy` cases du centre, y vers le sud, est en
    y = (-gy + down) KY + yc dans le monde)."""
    d = d or DIMS
    pd, m = PIPE.DIMS, PIPE.mats()
    for (gx, gy), (vx, vy) in CONNECTIONS[view]:
        edge = np.array((gx, (-gy + d["down"]) * KY + pd["yc"], pd["r"]))
        out = np.array((vx, -vy, 0.0))       # repère de Blender : y vers le nord
        PIPE.tube_path([tuple(edge), tuple(edge - out * STUB)], pd["r"], m["tube"])
        PIPE.flange(tuple(edge), (-vx, vy), pd, m)


def camera_shift(d=None):
    """Décalage de caméra (fraction du canevas) qui descend le dessin de `down` cases à l'écran."""
    return (d or DIMS)["down"] * PX_PER_TILE / CANVAS


def frame(view, phase, out):
    """Une image : sprite et ombre, découpés aux cadres de l'original."""
    path = os.path.join(out, "_engine.png")
    build(view, phase)
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE, shift_y=camera_shift())
    sprite = crop_centered(load(path), *FRAMES[view][0])
    shadow = render_shadow(lambda: build(view, phase), path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR,
                           shift_y=camera_shift())
    return sprite, crop_centered(shadow, *FRAMES[view][1])


def render_view(view, out, preview=False):
    n = 1 if preview else N_FRAMES
    sprites, shadows = zip(*[frame(view, i / N_FRAMES, out) for i in range(n)])
    if preview:
        sprites, shadows = sprites * N_FRAMES, shadows * N_FRAMES
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-{view}.png"), sheet(list(sprites), COLUMNS))
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-{view}-shadow.png"), sheet(list(shadows), COLUMNS))


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--apercu" in args
    args = [a for a in args if a != "--apercu"]
    out = args[0] if args else "steam_engine_out"
    which = args[1] if len(args) > 1 else "toutes"
    os.makedirs(out, exist_ok=True)
    for v in (FRAMES if which == "toutes" else which.split(",")):
        render_view(v, out, preview)
        print("OK", v, flush=True)
    if which == "toutes":
        save_icon(out, NAME, lambda: build("H", 0.0))
