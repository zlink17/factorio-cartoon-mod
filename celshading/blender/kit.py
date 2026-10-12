"""Boîte de pièces du mod cel-shading : formes communes aux machines, aux proportions « Metal Slug » de la charte
(voir ../STYLE.md). Tirée de l'assembleur 1 (validé le 12 octobre) ; une machine est un assemblage de ces pièces.

Toutes les pièces prennent des matières de lib (couleur, mat) et des positions en unités du monde (1 case = 1).
Les pièces animées prennent `phase` (0 -> 1 = une boucle d'animation complète, sans à-coup au raccord).
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from lib import box, cyl, gear


def lisse(o):
    """Normales lissées : la frontière d'ombre suit la courbe (cylindres, cônes)."""
    for poly in o.data.polygons:
        poly.use_smooth = True
    return o


def arrondi(o, largeur, segments=3):
    """Gros biseau arrondi sur toutes les arêtes."""
    mod = o.modifiers.new("Bevel", "BEVEL")
    mod.width = largeur
    mod.segments = segments
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


def engrenage_debout(center, r, dents, angle, m, moyeu):
    """Engrenage dressé face à la caméra (plan x-z), qui tourne dans son plan."""
    o = gear((0, 0, 0), r, 0.12, dents, 0.0, m)
    o.location = center
    o.rotation_mode = "ZYX"
    o.rotation_euler = (math.radians(90), 0, math.radians(angle))
    cyl((center[0], center[1] - 0.08, center[2]), r * 0.35, 0.06, moyeu, verts=24, rot=(90, 0, 0))
    return o


def va_et_vient(phase, decalage=0.0):
    """0 -> 1 -> 0 en douceur sur une boucle (cosinus), décalé de `decalage` boucle."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * (phase + decalage))


def piston(x, y, z0, course, tige, tete, presse=None, longueur=0.2, r_tete=0.17, r_tige=0.065):
    """Piston vertical qui sort d'un support dont le haut est à `z0` : presse-étoupe (si `presse`), tige sortie de
    `longueur` + `course`, tête ronde. `course` = sortie actuelle (calculée par l'appelant, ex. va_et_vient)."""
    if presse:
        lisse(cyl((x, y, z0 + 0.035), r_tige * 1.85, 0.06, presse, verts=32))   # au-dessus du support : pas de faces confondues
    lisse(cyl((x, y, z0 + (longueur + course) / 2), r_tige, longueur + course, tige, verts=24))
    lisse(cyl((x, y, z0 + longueur + 0.04 + course), r_tete, 0.09, tete, verts=40))


def poutre(p0, p1, largeur, epaisseur, m, biseau=0.05):
    """Poutre arrondie entre deux points du plan x-z (même y) : section `largeur` (profondeur, y) x `epaisseur`."""
    (x0, y, z0), (x1, _, z1) = p0, p1
    longueur = math.hypot(x1 - x0, z1 - z0)
    angle = math.degrees(math.atan2(z1 - z0, x1 - x0))
    o = box(((x0 + x1) / 2, y, (z0 + z1) / 2), (longueur, largeur, epaisseur), m, rot_y=-angle)
    return arrondi(o, biseau, 2)


def articulation(p, r, m, largeur=0.3):
    """Gros axe d'articulation (cylindre couché selon y, face à la caméra)."""
    return lisse(cyl(p, r, largeur, m, verts=32, rot=(90, 0, 0)))


def bras_articule(epaule, l1, l2, a1, a2, bras, axe, largeur=0.2, epaisseur=0.16):
    """Bras à deux segments dans le plan x-z (perpendiculaire à la vue : le mouvement se lit le mieux) ; `a1`, `a2` :
    directions absolues (degrés, 0 = vers +x, 90 = vers le haut) du bras et de l'avant-bras. Renvoie le poignet."""
    x, y, z = epaule
    coude = (x + l1 * math.cos(math.radians(a1)), y, z + l1 * math.sin(math.radians(a1)))
    poignet = (coude[0] + l2 * math.cos(math.radians(a2)), y, coude[2] + l2 * math.sin(math.radians(a2)))
    poutre(epaule, coude, largeur, epaisseur, bras)
    poutre(coude, poignet, largeur * 0.85, epaisseur * 0.85, bras)
    articulation(epaule, epaisseur * 0.75, axe, largeur * 1.4)
    articulation(coude, epaisseur * 0.65, axe, largeur * 1.3)
    return poignet


def incliner(objets, pivot, angle, point=None):
    """Fait pivoter des objets déjà créés autour de l'axe x passant par `pivot`, de `angle` degrés vers l'arrière
    (le haut part vers +y). La caméra des bâtiments regarde presque d'en haut : un mouvement vertical n'y paraît
    qu'à moitié, un mouvement dans un plan penché de 60° vers l'arrière (face à la caméra) paraît en entier.
    Renvoie `point` pivoté (ex. le poignet d'un bras), pour y accrocher la suite."""
    from mathutils import Matrix, Vector
    p = Vector(pivot)
    rot = Matrix.Translation(p) @ Matrix.Rotation(math.radians(-angle), 4, "X") @ Matrix.Translation(-p)
    bpy.context.view_layer.update()
    for o in objets:
        o.matrix_world = rot @ o.matrix_world
    return tuple(rot @ Vector(point)) if point is not None else None
