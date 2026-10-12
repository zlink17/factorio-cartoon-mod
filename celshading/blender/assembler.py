"""Assembleur 1, modèle propre au mod cel-shading, d'après les images cibles e-11 et e-15
(celshading/concept/cibles/assembleur-1.png et assembleur-1-b.png).

Usage : python celshading/blender/assembler.py <dossier_sortie> tout
          planche animée (32 images, 8 x 4, comme l'original), ombre et icône, dans l'arborescence de graphics/overrides
        python celshading/blender/assembler.py <dossier_sortie> [phase 0..1] [facteur de taille]
          une image <sortie>/assembleur.png calée sur le cadre de l'original (214 x 226), `facteur` fois plus grande

Peu de grosses formes, arrondies : corps trapu vert sauge sur un socle sombre, grand tablier avant incliné en quatre
panneaux, plateau bleu entouré d'un rebord ; mécanisme : moteur vert à « œil » jaune, tambour cuivré, long arbre de
laiton, entonnoir de laiton, deux engrenages debout qui dépassent du bord arrière, cheminée de laiton à gauche.
`build(phase)` est paramétré pour l'animation (engrenages), boucle complète sur phase 0 -> 1.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from lib import (S, reset, couleur, box, cyl, gear, rod, render_scene, render_shadow, crop_centered, entity_path,
                 save_icon, sheet)

NAME = "assembling-machine-1"
FRAME = (214, 226)
BBOX = (25, 2, 188, 199)       # pixels opaques de l'image 0 de l'original : largeur et bas servent au calage
N_FRAMES = 32
COLUMNS = 8
SHADOW_CELL, SHADOW_OFFSET = (190, 165), (17, 6)   # cadre de l'ombre originale et position de son centre (px)
SUN_SHEAR = (0.5, 0.03)          # ombre au sol : décalage par unité de hauteur (droite, vers le bas) ;
                                 # calé pour que l'ombre aille aussi loin à droite que l'originale
CANVAS = 400
PISTON_COURSE = 0.30             # course du piston du tambour (unités : 1 case = 1)

# couleurs mesurées sur les images cibles (ton « éclairé »)
VERT, BLEU = "#9ab590", "#4b7a8e"
LAITON, CUIVRE, SOMBRE = "#e5aa44", "#8a5d31", "#3b3f3a"
ROUGE, BLANC = "#b5503a", "#e4e2d4"


def lisse(o):
    """Normales lissées : la frontière d'ombre suit la courbe (cylindres, cônes)."""
    for poly in o.data.polygons:
        poly.use_smooth = True
    return o


def arrondi(o, largeur, segments=3):
    mod = o.modifiers.new("Bevel", "BEVEL")
    mod.width = largeur
    mod.segments = segments
    return o


def engrenage_debout(center, r, dents, angle, m, moyeu):
    """Engrenage dressé face à la caméra (plan x-z), qui tourne dans son plan."""
    o = gear((0, 0, 0), r, 0.12, dents, 0.0, m)
    o.location = center
    o.rotation_mode = "ZYX"
    o.rotation_euler = (math.radians(90), 0, math.radians(angle))
    cyl((center[0], center[1] - 0.08, center[2]), r * 0.35, 0.06, moyeu, verts=24, rot=(90, 0, 0))
    return o


def prisme(bas, haut, m):
    """Volume entre deux polygones horizontaux de même nombre de sommets (même ordre)."""
    import bmesh
    bm = bmesh.new()
    b = [bm.verts.new(v) for v in bas]
    h = [bm.verts.new(v) for v in haut]
    n = len(b)
    bm.faces.new(b[::-1])
    bm.faces.new(h)
    for k in range(n):
        bm.faces.new((b[k], b[(k + 1) % n], h[(k + 1) % n], h[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("prisme")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("prisme", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(m)
    return o


def coins_coupes(x0, y0, x1, y1, z, c):
    """Rectangle aux deux coins arrière coupés (de `c`), dans l'ordre : avant gauche, avant droit, puis l'arrière."""
    return [(x0, y0, z), (x1, y0, z), (x1, y1 - c, z), (x1 - c, y1, z), (x0 + c, y1, z), (x0, y1 - c, z)]


def build(phase=0.0):
    reset()
    vert, bleu = couleur("vert", VERT), couleur("bleu", BLEU)
    laiton, cuivre, sombre = couleur("laiton", LAITON), couleur("cuivre", CUIVRE), couleur("sombre", SOMBRE)
    rouge, blanc = couleur("rouge", ROUGE), couleur("blanc", BLANC)

    # --- socle et corps ----------------------------------------------------------------------------------------
    box((0, 0, 0.05), (2.8, 2.75, 0.1), sombre, 0.04)
    zt = 1.0
    arrondi(prisme(coins_coupes(-1.36, -1.36, 1.36, 1.3, 0.1, 0.4), coins_coupes(-1.2, -0.85, 1.2, 1.15, zt, 0.3),
                   vert), 0.09)

    # pieds sombres sous le bord avant (e-11)
    for x in (-1.08, -0.54, 0.0, 0.54, 1.08):
        arrondi(box((x, -1.38, 0.05), (0.3, 0.1, 0.1), sombre), 0.03, 2)

    # tablier avant : quatre panneaux posés sur la pente
    pente = math.degrees(math.atan((1.36 - 0.85) / (zt - 0.1)))
    for x in (-0.87, -0.29, 0.29, 0.87):
        arrondi(box((x, -1.12, 0.52), (0.52, 0.04, 0.78), vert, rot_x=-pente), 0.03, 2)

    # --- dessus : dalle aux coins coupés (rebord), plateau bleu posé dessus --------------------------------------
    arrondi(prisme(coins_coupes(-1.2, -0.85, 1.2, 1.15, zt - 0.01, 0.3), coins_coupes(-1.2, -0.85, 1.2, 1.15, zt + 0.12, 0.3),
                   vert), 0.05)
    prisme(coins_coupes(-1.02, -0.68, 1.02, 0.98, zt + 0.12, 0.2), coins_coupes(-1.02, -0.68, 1.02, 0.98, zt + 0.15, 0.2),
           bleu)

    # --- mécanisme : peu de grosses pièces, qui couvrent l'essentiel du plateau ---------------------------------
    # moteur vert arrondi, haut, « œil » jaune dessus
    arrondi(box((-0.55, 0.3, zt + 0.45), (0.78, 0.85, 0.85), vert), 0.14)
    lisse(cyl((-0.55, 0.3, zt + 0.89), 0.22, 0.05, laiton, verts=40))
    cyl((-0.55, 0.3, zt + 0.92), 0.09, 0.03, sombre, verts=24)
    # tambour cuivré devant le moteur, bague de laiton ; assez bas pour que le piston qui en sort ne cache pas l'œil
    lisse(cyl((-0.55, -0.38, zt + 0.27), 0.29, 0.48, cuivre, verts=48))
    lisse(cyl((-0.55, -0.38, zt + 0.12), 0.305, 0.16, laiton, verts=48))
    lisse(cyl((-0.55, -0.38, zt + 0.47), 0.305, 0.08, laiton, verts=48))
    # long arbre de laiton vers la droite
    lisse(cyl((0.4, -0.45, zt + 0.3), 0.12, 1.25, laiton, verts=32, rot=(0, 90, 0)))
    # entonnoir de laiton couché, pointé vers la droite, et son embout
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.44, radius2=0.2, depth=0.6,
                                    location=(0.3, 0.45, zt + 0.55), rotation=(0, math.radians(90), 0))
    o = bpy.context.object
    o.data.materials.append(laiton)
    lisse(o)
    lisse(cyl((0.8, 0.45, zt + 0.55), 0.2, 0.42, laiton, verts=40, rot=(0, 90, 0)))
    arrondi(box((-0.07, 0.45, zt + 0.55), (0.3, 0.38, 0.38), vert), 0.08)     # raccord moteur-entonnoir
    # deux engrenages debout qui dépassent du bord arrière ; ils s'engrènent (tournent en sens inverse) ;
    # 3 dents par boucle : assez vite pour se voir, boucle sans à-coup
    a = phase * 3 * 360 / 10
    engrenage_debout((0.15, 1.0, zt + 0.5), 0.38, 10, a, laiton, cuivre)
    engrenage_debout((-0.62, 1.02, zt + 0.42), 0.27, 7, -a * 10 / 7 + 12, cuivre, laiton)
    # paire d'engrenages couchés sur le plateau, à droite (2 dents par boucle)
    b = phase * 2 * 360 / 8
    gear((0.5, -0.08, zt + 0.15), 0.21, 0.1, 8, b, laiton, cuivre)
    gear((0.83, -0.1, zt + 0.15), 0.15, 0.1, 6, -b * 8 / 6 + 15, cuivre, laiton)
    # piston qui sort du tambour : une course aller-retour par boucle (assembleurs 2 et 3 : davantage de pièces
    # mobiles, l'assembleur 1 reste le plus simple)
    course = PISTON_COURSE * (0.5 - 0.5 * math.cos(2 * math.pi * phase))
    z0 = zt + 0.51                                                   # haut du tambour
    lisse(cyl((-0.55, -0.38, z0 + 0.03), 0.12, 0.06, sombre, verts=32))   # presse-étoupe
    lisse(cyl((-0.55, -0.38, z0 + 0.1 + course / 2), 0.065, 0.2 + course, sombre, verts=24))   # tige
    lisse(cyl((-0.55, -0.38, z0 + 0.24 + course), 0.17, 0.09, laiton, verts=40))              # tête
    # cheminée de laiton à gauche, un peu penchée
    lisse(cyl((-1.0, 0.8, zt + 0.45), 0.11, 0.8, laiton, verts=32, rot=(0, -12, 0)))

    # --- détails (e-15) ---------------------------------------------------------------------------------------------
    # troisième engrenage, en cuivre, à moitié caché derrière l'entonnoir
    engrenage_debout((0.62, 0.95, zt + 0.42), 0.24, 7, -a * 10 / 7 + 30, cuivre, laiton)
    # raccord entre le tambour et l'arbre, avec un tuyau vert qui monte vers le moteur
    arrondi(box((-0.12, -0.45, zt + 0.3), (0.26, 0.34, 0.34), vert), 0.06)
    lisse(rod((-0.12, -0.38, zt + 0.45), (-0.12, -0.05, zt + 0.62), 0.065, vert, verts=24))
    # tuyau vert qui descend le long de la paroi gauche, vanne blanche
    for p0, p1 in [((-0.9, 0.05, zt + 0.55), (-1.22, 0.05, zt + 0.55)), ((-1.22, 0.05, zt + 0.55), (-1.4, 0.05, 0.25))]:
        lisse(rod(p0, p1, 0.07, vert, verts=24))
    bpy.ops.mesh.primitive_torus_add(location=(-1.27, 0.05, zt + 0.4), rotation=(0, math.radians(90 - 11), 0),
                                     major_radius=0.12, minor_radius=0.04, major_segments=32, minor_segments=12)
    lisse(bpy.context.object).data.materials.append(blanc)
    # bande rouge au coin arrière gauche
    arrondi(box((-1.12, 0.62, zt + 0.08), (0.06, 0.5, 0.22), rouge), 0.02, 2)

def measure(path):
    import cv2, numpy as np
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    ys, xs = np.where(im[:, :, 3] > 200)
    return xs.min(), ys.min(), xs.max(), ys.max()


def fit_camera(out, phase=0.0):
    """Échelle et décalage de caméra qui donnent la même largeur et le même bas que l'original."""
    tw = BBOX[2] - BBOX[0] + 1
    scale, shift = 3.9, 0.0
    path = os.path.join(out, "_fit.png")
    for _ in range(4):
        build(phase)
        render_scene(path, size=FRAME, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift)
        x0, y0, x1, y1 = measure(path)
        scale *= (x1 - x0 + 1) / tw
        shift -= (y1 - BBOX[3]) / max(FRAME)
    os.remove(path)
    return scale, shift


def render_phase(path, phase, scale, shift, factor=1):
    build(phase)
    return render_scene(path, size=(FRAME[0] * factor, FRAME[1] * factor), scale=scale,
                        pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift)


def produire(out):
    """Planche animée, ombre (une image, recopiée : seuls les engrenages bougent) et icône, au format du jeu."""
    import cv2
    scale, shift = fit_camera(out, 0.0)
    tmp = os.path.join(out, "_image.png")
    frames = []
    for i in range(N_FRAMES):
        render_phase(tmp, i / N_FRAMES, scale, shift)
        frames.append(cv2.imread(tmp, cv2.IMREAD_UNCHANGED))
    os.remove(tmp)
    cv2.imwrite(entity_path(out, NAME), sheet(frames, COLUMNS))
    fh = max(FRAME)
    big = render_shadow(lambda: build(0.0), os.path.join(out, "_ombre.png"), (CANVAS, CANVAS), scale * CANVAS / fh,
                        SUN_SHEAR, shift_y=shift * fh / CANVAS)
    cell = crop_centered(big, SHADOW_CELL, SHADOW_OFFSET)
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-shadow.png"), sheet([cell] * N_FRAMES, COLUMNS))
    print("icône :", save_icon(out, NAME, lambda: build(0.0), 60, 0.5))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sortie"
    if len(sys.argv) > 2 and sys.argv[2] == "tout":
        os.makedirs(out, exist_ok=True)
        produire(out)
        sys.exit()
    phase = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    factor = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    os.makedirs(out, exist_ok=True)
    scale, shift = fit_camera(out, phase)
    path = render_phase(os.path.join(out, "assembleur.png"), phase, scale, shift, factor)
    print("OK", path, "échelle", round(scale, 3), "décalage", round(shift, 4))
