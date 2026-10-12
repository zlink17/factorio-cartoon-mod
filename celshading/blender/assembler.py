"""Assembleurs 1 à 3, modèles propres au mod cel-shading. L'assembleur 1 suit les images cibles e-11 et e-15
(celshading/concept/cibles/assembleur-1.png et assembleur-1-b.png) ; les 2 et 3 en dérivent
(concept/descriptions/assembleurs.md).

Usage : python celshading/blender/assembler.py <dossier_sortie> tout [niveau]
          planche animée (32 images, 8 x 4, comme l'original), ombre et icône, dans l'arborescence de graphics/overrides ;
          les trois niveaux, ou le seul `niveau` (1 à 3)
        python celshading/blender/assembler.py <dossier_sortie> [phase 0..1] [facteur de taille] [niveau]
          une image <sortie>/assembleur.png calée sur le cadre de l'original, `facteur` fois plus grande

Famille commune : corps trapu sur un socle sombre, grand tablier avant incliné en quatre panneaux, plateau entouré
d'un rebord ; à gauche, moteur à « œil » jaune, tambour cuivré d'où sort un piston, cheminée de laiton ; engrenages
debout à l'arrière. Pièces mobiles de plus en plus nombreuses d'un niveau à l'autre, comme dans le jeu :
1 : piston, engrenages ; à droite, entonnoir, long arbre et paire d'engrenages couchés (corps rouille pâle) ;
2 : à droite, un grand bras articulé qui travaille une pièce sur le plateau (corps bleu) ;
3 : le bras, et trois grands pistons verticaux qui dépassent au-dessus de la machine (corps vert sauge).
`build(phase, niveau)` est paramétré pour l'animation, boucle complète sur phase 0 -> 1.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from lib import (S, reset, couleur, box, cyl, gear, rod, render_scene, render_shadow, crop_centered, entity_path,
                 save_icon, sheet)
from kit import (lisse, arrondi, prisme, coins_coupes, engrenage_debout, va_et_vient, piston, bras_articule,
                 articulation, incliner)

N_FRAMES = 32
COLUMNS = 8
SUN_SHEAR = (0.5, 0.03)          # ombre au sol : décalage par unité de hauteur (droite, vers le bas) ;
                                 # calé pour que l'ombre de l'assembleur 1 aille aussi loin à droite que l'originale
CANVAS = 400
PISTON_COURSE = 0.30             # course du piston du tambour (unités : 1 case = 1)
GRANDS_PISTONS = 0.4             # course des grands pistons de l'assembleur 3 (vue d'en haut : paraît moitié moins)
BRAS_INCLINAISON = 60           # plan du bras articulé penché vers l'arrière (degrés) : face à la caméra

# Par niveau : cadre de l'original (px), pixels opaques de son image 0 (largeur et bas servent au calage), cadre de
# l'ombre et position de son centre par rapport au centre du sprite (px : écart des `shift` du prototype x 64),
# couleurs du corps et du plateau (ton « éclairé ») ; corps (Bastien, 12 octobre) : 1 rouille pâle (la rouille de
# l'original, en pastel), 2 bleu clair, 3 vert sauge (l'ancien vert du 1).
NIVEAUX = {
    1: dict(frame=(214, 226), bbox=(25, 2, 188, 199), ombre=((190, 165), (17, 6)), corps="#d29c80", plateau="#4b7a8e"),
    2: dict(frame=(214, 218), bbox=(26, 1, 187, 190), ombre=((196, 163), (24, 1.5)), corps="#86a6c6",
            plateau="#6b4f3a"),
    3: dict(frame=(214, 237), bbox=(26, 1, 187, 209), ombre=((260, 162), (56, 9.5)), corps="#9ab590",
            plateau="#4b7a8e"),
}

# couleurs mesurées sur les images cibles de l'assembleur 1 (ton « éclairé »)
LAITON, CUIVRE, SOMBRE = "#e5aa44", "#8a5d31", "#3b3f3a"
ROUGE, BLANC = "#b5503a", "#e4e2d4"
ACIER = "#8a949b"                # bras articulé et tiges des grands pistons (niveaux 2 et 3)


def name(niveau):
    return f"assembling-machine-{niveau}"


def build(phase=0.0, niveau=1):
    reset()
    corps, plateau = couleur("corps", NIVEAUX[niveau]["corps"]), couleur("plateau", NIVEAUX[niveau]["plateau"])
    laiton, cuivre, sombre = couleur("laiton", LAITON), couleur("cuivre", CUIVRE), couleur("sombre", SOMBRE)
    rouge, blanc = couleur("rouge", ROUGE), couleur("blanc", BLANC)

    # --- socle et corps ----------------------------------------------------------------------------------------
    box((0, 0, 0.05), (2.8, 2.75, 0.1), sombre, 0.04)
    zt = 1.0
    arrondi(prisme(coins_coupes(-1.36, -1.36, 1.36, 1.3, 0.1, 0.4), coins_coupes(-1.2, -0.85, 1.2, 1.15, zt, 0.3),
                   corps), 0.09)

    # pieds sombres sous le bord avant (e-11)
    for x in (-1.08, -0.54, 0.0, 0.54, 1.08):
        arrondi(box((x, -1.38, 0.05), (0.3, 0.1, 0.1), sombre), 0.03, 2)

    # tablier avant : quatre panneaux posés sur la pente
    pente = math.degrees(math.atan((1.36 - 0.85) / (zt - 0.1)))
    for x in (-0.87, -0.29, 0.29, 0.87):
        arrondi(box((x, -1.12, 0.52), (0.52, 0.04, 0.78), corps, rot_x=-pente), 0.03, 2)

    # --- dessus : dalle aux coins coupés (rebord), plateau posé dessus -------------------------------------------
    arrondi(prisme(coins_coupes(-1.2, -0.85, 1.2, 1.15, zt - 0.01, 0.3), coins_coupes(-1.2, -0.85, 1.2, 1.15, zt + 0.12, 0.3),
                   corps), 0.05)
    prisme(coins_coupes(-1.02, -0.68, 1.02, 0.98, zt + 0.12, 0.2), coins_coupes(-1.02, -0.68, 1.02, 0.98, zt + 0.15, 0.2),
           plateau)

    # --- côté gauche, commun aux trois niveaux -----------------------------------------------------------------
    # moteur arrondi, haut, « œil » jaune dessus
    arrondi(box((-0.55, 0.3, zt + 0.45), (0.78, 0.85, 0.85), corps), 0.14)
    lisse(cyl((-0.55, 0.3, zt + 0.89), 0.22, 0.05, laiton, verts=40))
    cyl((-0.55, 0.3, zt + 0.92), 0.09, 0.03, sombre, verts=24)
    # tambour cuivré devant le moteur, bague de laiton ; assez bas pour que le piston qui en sort ne cache pas l'œil
    lisse(cyl((-0.55, -0.38, zt + 0.27), 0.29, 0.48, cuivre, verts=48))
    lisse(cyl((-0.55, -0.38, zt + 0.12), 0.305, 0.16, laiton, verts=48))
    lisse(cyl((-0.55, -0.38, zt + 0.47), 0.305, 0.08, laiton, verts=48))
    # deux engrenages debout qui dépassent du bord arrière ; ils s'engrènent (tournent en sens inverse) ;
    # 3 dents par boucle : assez vite pour se voir, boucle sans à-coup. Niveaux 2 et 3 : plus bas (cadre de
    # l'assembleur 2 moins haut ; au 3, les grands pistons dépassent à leur place)
    a = phase * 3 * 360 / 10
    dz = 0.0 if niveau == 1 else -0.2
    engrenage_debout((0.15, 1.0, zt + 0.5 + dz), 0.38, 10, a, laiton, cuivre)
    engrenage_debout((-0.62, 1.02, zt + 0.42 + dz), 0.27, 7, -a * 10 / 7 + 12, cuivre, laiton)
    if niveau == 1:
        mecanisme_1(phase, zt, a, laiton, cuivre, corps)
    else:
        mecanisme_bras(phase, zt, niveau, laiton, cuivre, sombre, blanc)
    # piston qui sort du tambour : une course aller-retour par boucle
    piston(-0.55, -0.38, zt + 0.51, PISTON_COURSE * va_et_vient(phase), sombre, laiton, presse=sombre)
    # cheminée de laiton à gauche, un peu penchée
    lisse(cyl((-1.0, 0.8, zt + 0.45), 0.11, 0.8, laiton, verts=32, rot=(0, -12, 0)))
    # tuyau qui descend le long de la paroi gauche, vanne blanche
    for p0, p1 in [((-0.9, 0.05, zt + 0.55), (-1.22, 0.05, zt + 0.55)), ((-1.22, 0.05, zt + 0.55), (-1.4, 0.05, 0.25))]:
        lisse(rod(p0, p1, 0.07, corps, verts=24))
    bpy.ops.mesh.primitive_torus_add(location=(-1.27, 0.05, zt + 0.4), rotation=(0, math.radians(90 - 11), 0),
                                     major_radius=0.12, minor_radius=0.04, major_segments=32, minor_segments=12)
    lisse(bpy.context.object).data.materials.append(blanc)
    # bande rouge au coin arrière gauche
    arrondi(box((-1.12, 0.62, zt + 0.08), (0.06, 0.5, 0.22), rouge), 0.02, 2)


def mecanisme_1(phase, zt, a, laiton, cuivre, corps):
    """Assembleur 1, côté droit : entonnoir, long arbre, paire d'engrenages couchés, troisième engrenage debout."""
    # long arbre de laiton vers la droite
    lisse(cyl((0.4, -0.45, zt + 0.3), 0.12, 1.25, laiton, verts=32, rot=(0, 90, 0)))
    # entonnoir de laiton couché, pointé vers la droite, et son embout
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.44, radius2=0.2, depth=0.6,
                                    location=(0.3, 0.45, zt + 0.55), rotation=(0, math.radians(90), 0))
    o = bpy.context.object
    o.data.materials.append(laiton)
    lisse(o)
    lisse(cyl((0.8, 0.45, zt + 0.55), 0.2, 0.42, laiton, verts=40, rot=(0, 90, 0)))
    arrondi(box((-0.07, 0.45, zt + 0.55), (0.3, 0.38, 0.38), corps), 0.08)     # raccord moteur-entonnoir
    # paire d'engrenages couchés sur le plateau, à droite (2 dents par boucle)
    b = phase * 2 * 360 / 8
    gear((0.5, -0.08, zt + 0.15), 0.21, 0.1, 8, b, laiton, cuivre)
    gear((0.83, -0.1, zt + 0.15), 0.15, 0.1, 6, -b * 8 / 6 + 15, cuivre, laiton)
    # troisième engrenage, en cuivre, à moitié caché derrière l'entonnoir (e-15)
    engrenage_debout((0.62, 0.95, zt + 0.42), 0.24, 7, -a * 10 / 7 + 30, cuivre, laiton)
    # raccord entre le tambour et l'arbre, avec un tuyau qui monte vers le moteur
    arrondi(box((-0.12, -0.45, zt + 0.3), (0.26, 0.34, 0.34), corps), 0.06)
    lisse(rod((-0.12, -0.38, zt + 0.45), (-0.12, -0.05, zt + 0.62), 0.065, corps, verts=24))


def mecanisme_bras(phase, zt, niveau, laiton, cuivre, sombre, blanc):
    """Niveaux 2 et 3, côté droit : grand bras articulé sur un pied, qui descend vers une pièce posée sur le
    plateau et remonte (une fois par boucle) ; niveau 3 : trois grands pistons verticaux à l'arrière."""
    acier = couleur("acier", ACIER)
    y = -0.15
    # pied du bras, à droite, et pièce de cuivre sur le plateau, sous la pince en bas de course
    arrondi(box((0.8, y, zt + 0.4), (0.34, 0.38, 0.5), sombre), 0.08)
    arrondi(box((0.14, -0.4, zt + 0.25), (0.36, 0.32, 0.2), cuivre), 0.05)
    t = va_et_vient(phase)
    a1 = 105 + 30 * t                     # bras : dressé, puis penché vers la gauche
    a2 = 230 + 25 * t                     # avant-bras : vers la gauche, puis vers le bas, jusqu'à la pièce
    epaule = (0.8, y, zt + 0.65)
    avant = set(bpy.data.objects)
    poignet = bras_articule(epaule, 0.7, 0.65, a1, a2, acier, laiton, largeur=0.26, epaisseur=0.2)
    articulation(poignet, 0.1, laiton, 0.3)
    poignet = incliner([o for o in bpy.data.objects if o not in avant], epaule, BRAS_INCLINAISON, poignet)
    # pince : deux mâchoires droites sous le poignet, qui se serrent en bas de course, sur la pièce
    px, py, pz = poignet
    for s in (-1, 1):
        ecart = 0.15 - 0.06 * t
        arrondi(box((px + s * ecart, py, pz - 0.12), (0.08, 0.24, 0.22), sombre), 0.03, 2)
    if niveau == 3:
        # trois grands pistons verticaux à l'arrière, décalés d'un tiers de boucle : chemise de cuivre, tige d'acier,
        # tête blanche
        for k, (x, yy) in enumerate(((0.05, 0.7), (0.47, 0.85), (0.95, 0.72))):
            h = 0.62 if k != 1 else 0.75
            lisse(cyl((x, yy, zt + 0.15 + h / 2), 0.15, h, cuivre, verts=40))
            lisse(cyl((x, yy, zt + 0.15 + h - 0.04), 0.17, 0.08, laiton, verts=40))
            piston(x, yy, zt + 0.15 + h, GRANDS_PISTONS * va_et_vient(phase, k / 3), acier, blanc,
                   longueur=0.12, r_tete=0.15, r_tige=0.07)


def measure(path):
    import cv2, numpy as np
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    ys, xs = np.where(im[:, :, 3] > 200)
    return xs.min(), ys.min(), xs.max(), ys.max()


def fit_camera(out, niveau, phase=0.0):
    """Échelle et décalage de caméra qui donnent la même largeur et le même bas que l'original."""
    frame, bbox = NIVEAUX[niveau]["frame"], NIVEAUX[niveau]["bbox"]
    tw = bbox[2] - bbox[0] + 1
    scale, shift = 3.9, 0.0
    path = os.path.join(out, "_fit.png")
    for _ in range(4):
        build(phase, niveau)
        render_scene(path, size=frame, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift)
        x0, y0, x1, y1 = measure(path)
        scale *= (x1 - x0 + 1) / tw
        shift -= (y1 - bbox[3]) / max(frame)
    os.remove(path)
    return scale, shift


def render_phase(path, phase, scale, shift, niveau, factor=1):
    frame = NIVEAUX[niveau]["frame"]
    build(phase, niveau)
    return render_scene(path, size=(frame[0] * factor, frame[1] * factor), scale=scale,
                        pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift)


def produire(out, niveau):
    """Planche animée, ombre (une image, recopiée : l'ombre des pièces mobiles ne se voit pas) et icône."""
    import cv2
    frame, (shadow_cell, shadow_offset) = NIVEAUX[niveau]["frame"], NIVEAUX[niveau]["ombre"]
    nom = name(niveau)
    scale, shift = fit_camera(out, niveau, 0.0)
    tmp = os.path.join(out, "_image.png")
    frames = []
    for i in range(N_FRAMES):
        render_phase(tmp, i / N_FRAMES, scale, shift, niveau)
        frames.append(cv2.imread(tmp, cv2.IMREAD_UNCHANGED))
    os.remove(tmp)
    cv2.imwrite(entity_path(out, nom), sheet(frames, COLUMNS))
    fh = max(frame)
    big = render_shadow(lambda: build(0.0, niveau), os.path.join(out, "_ombre.png"), (CANVAS, CANVAS),
                        scale * CANVAS / fh, SUN_SHEAR, shift_y=shift * fh / CANVAS)
    cell = crop_centered(big, shadow_cell, shadow_offset)
    cv2.imwrite(entity_path(out, nom, f"{nom}-shadow.png"), sheet([cell] * N_FRAMES, COLUMNS))
    print("icône :", save_icon(out, nom, lambda: build(0.0, niveau), 60, 0.5))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sortie"
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 2 and sys.argv[2] == "tout":
        for niveau in ([int(sys.argv[3])] if len(sys.argv) > 3 else sorted(NIVEAUX)):
            produire(out, niveau)
        sys.exit()
    phase = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    factor = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    niveau = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    scale, shift = fit_camera(out, niveau, phase)
    path = render_phase(os.path.join(out, "assembleur.png"), phase, scale, shift, niveau, factor)
    print("OK", path, "échelle", round(scale, 3), "décalage", round(shift, 4))
