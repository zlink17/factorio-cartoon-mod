"""Propulseur (thruster, Space Age) : ESSAI de la méthode « image cible ComfyUI, production Blender ».

Usage : python cartoon/blender/thruster.py <dossier_sortie>

Cible : la variante m70-42 générée par ComfyUI (cartoon/concept/cibles/propulseur-m70-42.png), choisie par
Bastien le 11 octobre 2026. On en garde les grandes masses et les couleurs, pas la tuyauterie fine.
Écrit pour l'instant une seule image fixe au cadre de l'original (thruster-essai.png, 264 x 542) ; la planche
animée (64 images : toute la machine vibre), le support au sol, les raccords et l'icône viendront si la méthode
est retenue.

Le propulseur (4 x 5 cases, plus la tuyère au-dessus du vide, vers le sud) : châssis gris-bleu, bloc moteur crème
coiffé de deux chapeaux cuivre, baie de machinerie sombre parcourue de tubes cuivre et de durites bleues, collier,
tuyère en cloche crème à nervures gris-bleu, fentes orange (feu) entre les pétales, bouche sombre cerclée.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, crop_centered, cyl, load, mat, render_scene, reset, rod
from pipe import tube_path

PX_PER_TILE = 64
CANVAS = 800                                   # le cadre (542 px, décalé de 114 vers le bas) doit y tenir
OUTLINE = 0.022
SPRITE = ((264, 542), (3.0, 114.0))            # cadre de l'original (taille, décalage en px = shift x 64)

# couleurs relevées sur la cible (m70-42), propres à l'essai : à reporter dans style.py si la méthode est retenue
HEX = dict(cream="#dccdaa", steel="#6f8899", steel_dark="#46525c", copper="#b8743a", hose="#3f86c4",
           bay="#3a3532", bronze="#8a5a30",
           dark="#3a3126", inner="#4a2e1c", stripe="#8a5a35", glow="#ffa030")
C = {k: S._lin(v) for k, v in HEX.items()}

D = dict(
    zc=0.9,                   # hauteur de l'axe de la tuyère (sous le niveau de la plateforme : elle est au-dessus du vide)
    y_collar=-4.27,           # collier (début de la tuyère) ; tuyère courte, bouche large face à nous, comme la cible
    y_mouth=-5.84,            # bouche
    r_throat=1.22, r_mouth=1.42,
    wall=0.14,                # épaisseur de la cloche
)
# contour du châssis (moitié droite, x >= 0, du nord au sud), relevé sur la silhouette de la cible : étroit au fond,
# élargi au milieu, encoche à la hauteur des raccords, bras le long de la tuyère
FOOT = [(1.0, 2.45), (1.2, 1.6), (1.6, 1.05), (1.78, 0.8), (1.78, -0.2), (1.48, -0.4), (1.48, -0.85), (1.92, -1.2),
        (1.92, -3.0), (1.78, -3.3), (1.78, -4.0), (1.5, -4.2)]


def flat(name, rgb):
    """Aplat sans ombrage (lumières : feu, voyants)."""
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def metal(name, rgb, shine=(1.0, 0.86, 0.55)):
    """Métal des tuyaux, ESSAI hors guide (qui ne prévoit que trois tons) : bandes selon la normale pour qu'un tube
    se lise rond et se détache de ses voisins, comme dans la cible : bords sombres (x0,5), flanc moyen (x1,0),
    dessus clair (x1,2), reflet (45 % vers `shine` : doré pour le cuivre) ; les faces tournées vers l'avant gardent au moins le ton avant (x0,85)."""
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    n = nt.nodes
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Normal"], sep.inputs[0])

    def step(sock, thr):
        x = n.new("ShaderNodeMath"); x.operation = "GREATER_THAN"; x.inputs[1].default_value = thr
        nt.links.new(sock, x.inputs[0]); return x.outputs[0]

    def madd(a, k, c):
        x = n.new("ShaderNodeMath"); x.operation = "MULTIPLY_ADD"
        nt.links.new(a, x.inputs[0]); x.inputs[1].default_value = k
        if isinstance(c, float):
            x.inputs[2].default_value = c
        else:
            nt.links.new(c, x.inputs[2])
        return x.outputs[0]
    negy = n.new("ShaderNodeMath"); negy.operation = "MULTIPLY"; negy.inputs[1].default_value = -1.0
    nt.links.new(sep.outputs["Y"], negy.inputs[0])
    shade = madd(step(sep.outputs["Z"], 0.35), 0.5, 0.5)
    shade = madd(step(sep.outputs["Z"], 0.7), 0.2, shade)
    front = madd(step(negy.outputs[0], 0.5), 0.85, 0.0)
    mx = n.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    nt.links.new(shade, mx.inputs[0]); nt.links.new(front, mx.inputs[1])
    comb = n.new("ShaderNodeCombineXYZ")
    for i in range(3):
        nt.links.new(mx.outputs[0], comb.inputs[i])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[6].default_value = (*rgb, 1)
    nt.links.new(comb.outputs[0], mix.inputs[7])
    hi = n.new("ShaderNodeMix"); hi.data_type = "RGBA"; hi.blend_type = "MIX"       # reflet : vers le blanc
    nt.links.new(madd(step(sep.outputs["Z"], 0.9), 0.45, 0.0), hi.inputs[0])
    nt.links.new(mix.outputs[2], hi.inputs[6]); hi.inputs[7].default_value = (*shine, 1)
    em = n.new("ShaderNodeEmission"); nt.links.new(hi.outputs[2], em.inputs["Color"])
    out = n.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs[0])
    return m


def lathe(profile, m, zc, verts=40, inward=False, arc=None):
    """Surface de révolution autour d'un axe parallèle à y (x = 0, z = zc) ; `profile` = [(y, r), ...] ;
    `arc` = (début, fin) en degrés pour n'en faire qu'une portion (pétale)."""
    import bpy, bmesh
    bm = bmesh.new()
    a0, a1 = (0.0, 360.0) if arc is None else arc
    closed = arc is None
    cnt = verts if closed else max(2, round(verts * (a1 - a0) / 360) + 1)
    ang = [math.radians(a0 + (a1 - a0) * k / (verts if closed else cnt - 1)) for k in range(cnt)]
    rings = []
    for y, r in profile:
        rings.append([bm.verts.new((r * math.cos(t), y, zc + r * math.sin(t))) for t in ang])
    for a, b in zip(rings, rings[1:]):
        for k in range(cnt if closed else cnt - 1):
            f = (a[k], a[(k + 1) % cnt], b[(k + 1) % cnt], b[k])
            bm.faces.new(f[::-1] if inward else f)
    bm.normal_update()
    # normales : vers l'extérieur de l'axe (ou vers l'axe pour l'intérieur de la cloche)
    for f in bm.faces:
        c = f.calc_center_median()
        radial = (c.x, 0.0, c.z - zc)
        dot = f.normal.x * radial[0] + f.normal.z * radial[2]
        if (dot < 0) != inward:
            f.normal_flip()
    me = bpy.data.meshes.new("lathe")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("lathe", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(m)
    return o


def prism(half, z0, z1, m):
    """Prisme vertical sur un contour symétrique (`half` = moitié droite, du nord au sud)."""
    import bpy, bmesh
    pts = list(half) + [(-x, y) for x, y in reversed(half)]
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(bot[::-1]); bm.faces.new(top)
    n = len(pts)
    for k in range(n):
        bm.faces.new((bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("prism"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("prism", me); bpy.context.scene.collection.objects.link(o); me.materials.append(m)
    return o


def inset(half, t):
    """Contour rentré de `t` (approché : x réduit, bouts nord et sud rapprochés)."""
    y0, y1 = half[0][1], half[-1][1]
    return [(max(0.05, x - t), min(y0 - t, max(y1 + t, y))) for x, y in half]


def smooth(points, per=8):
    """Ligne brisée lissée (Catmull-Rom passant par les points) : coudes arrondis au lieu d'angles."""
    if len(points) < 3:
        return points
    p = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                                    + (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(points[-1])
    return out


def tube(points, r, m, rings=(), ring_m=None):
    """Tube d'un seul maillage aux coudes arrondis, avec des bagues (fractions de la longueur, 0..1) en `ring_m`."""
    from mathutils import Vector
    points = smooth(points)
    o = tube_path(points, r, m)
    if rings:
        pts = [Vector(p) for p in points]
        seg = [(p, q, (q - p).length) for p, q in zip(pts, pts[1:])]
        total = sum(l for _, _, l in seg)
        for t in rings:
            u = t * total
            for p, q, l in seg:
                if u <= l:
                    c, dirv = p + (q - p) * (u / l), (q - p).normalized()
                    break
                u -= l
            ring = cyl(tuple(c), r * 1.35, r * 0.9, ring_m, verts=16)
            ring.rotation_euler = dirv.to_track_quat("Z", "Y").to_euler()
    return o


def fitting(loc, r, m_ring, m_hole, axis="z"):
    """Raccord rond : bague épaisse et trou sombre (« œil »), tourné vers le haut (z) ou vers le sud (y)."""
    rot = (0, 0, 0) if axis == "z" else (90, 0, 0)
    off = (0, 0, r * 0.3) if axis == "z" else (0, -r * 0.3, 0)
    cyl(loc, r, r * 0.6, m_ring, verts=20, rot=rot)
    cyl(tuple(a + b for a, b in zip(loc, off)), r * 0.5, r * 0.05 + 0.02, m_hole, verts=16, rot=rot)


def build(d=None):
    import bpy, bmesh
    reset()
    d = d or D
    cream, steel, sdark = mat("cream", C["cream"]), mat("steel", C["steel"]), mat("steel_dark", C["steel_dark"])
    copper, hose, dark = metal("copper", C["copper"]), metal("hose", C["hose"], shine=(0.8, 0.92, 1.0)), mat("dark", C["dark"])
    inner, stripe, glow = mat("inner", C["inner"]), mat("stripe", C["stripe"]), flat("glow", C["glow"])
    bronze = metal("bronze", C["bronze"])
    zc, yc, ym, rt, rm = d["zc"], d["y_collar"], d["y_mouth"], d["r_throat"], d["r_mouth"]

    # --- châssis : cadre gris-bleu épais qui suit la silhouette, intérieur sombre plus haut (le cadre fait bordure)
    prism(FOOT, 0.0, 0.7, steel)
    prism(inset(FOOT, 0.3), 0.0, 0.82, mat("bay", C["bay"]))
    for sx in (-1, 1):                                  # bras le long de la tuyère : deux segments et une articulation
        y0, y1 = yc + 0.3, ym - 0.3
        box((sx * 1.75, (y0 + yc - 0.9) / 2, zc - 0.15), (0.42, y0 - yc + 0.9, 1.3), steel, bevel=0.06)
        box((sx * 1.75, (yc - 1.1 + y1) / 2, zc - 0.25), (0.42, yc - 1.1 - y1, 1.5), steel, bevel=0.06)
        cyl((sx * 1.75, yc - 1.0, zc + 0.2), 0.2, 0.5, sdark, verts=16, rot=(0, 90, 0))
        box((sx * 0.62, ym - 0.45, zc - 1.6), (0.5, 0.4, 0.24), sdark, bevel=0.03)      # nacelles des voyants
        box((sx * 0.62, ym - 0.47, zc - 1.47), (0.36, 0.26, 0.04), glow)
        box((sx * 0.62, ym - 0.15, zc - 1.62), (0.2, 0.3, 0.16), sdark)                  # attache à l'anneau

    # --- colonne crème au fond : cylindre debout, tambour en travers, second cylindre ; chapeaux cuivre
    cyl((0, 1.3, 1.35), 0.44, 1.1, cream, verts=24)
    cyl((0, 1.3, 1.93), 0.3, 0.08, copper, verts=24)
    cyl((0, 1.3, 1.98), 0.16, 0.03, dark, verts=16)
    cyl((0, 0.2, 1.5), 0.36, 1.15, cream, verts=24, rot=(0, 90, 0))
    for sx in (-1, 1):
        cyl((sx * 0.6, 0.2, 1.5), 0.4, 0.08, sdark, verts=24, rot=(0, 90, 0))           # flasques du tambour
    cyl((0.05, -0.35, 1.3), 0.32, 0.9, cream, verts=24)
    for sx in (-1, 1):
        cyl((sx * 0.62, 1.6, 1.05), 0.26, 0.9, copper, verts=16)
        cyl((sx * 0.62, 1.6, 1.25), 0.3, 0.1, sdark, verts=16)                           # bague
        cyl((sx * 0.62, 1.6, 1.51), 0.15, 0.03, dark, verts=16)
        box((sx * 1.2, 1.4, 1.0), (0.45, 0.8, 0.4), steel, bevel=0.05)                   # caissons du fond

    # --- baie de machinerie : durites bleues, tubes cuivre bagués, raccords ronds, coude vers le raccord est
    tube([(0.05, -0.2, 1.7), (0.05, -1.4, 1.75), (0.25, -2.4, 1.55), (0.1, yc + 0.15, 1.5)], 0.13, hose,
         rings=(0.35, 0.8), ring_m=steel)
    tube([(-0.35, 0.6, 1.3), (-0.8, -0.3, 1.35), (-0.85, -1.8, 1.35), (-0.6, yc + 0.15, 1.3)], 0.11, hose,
         rings=(0.5,), ring_m=steel)
    tube([(0.45, 0.6, 1.2), (0.75, -1.0, 1.3), (0.7, -2.2, 1.45)], 0.1, hose)
    tube([(-0.25, -0.6, 1.45), (-0.3, -1.6, 1.5), (-0.15, -2.3, 1.5), (-0.25, yc + 0.15, 1.4)], 0.14, copper,
         rings=(0.25, 0.6, 0.9), ring_m=dark)
    tube([(0.4, -0.5, 1.5), (0.45, -1.2, 1.6), (1.25, -1.2, 1.6), (1.55, -1.3, 1.3), (1.6, -2.4, 1.0)], 0.16, copper,
         rings=(0.2, 0.55, 0.85), ring_m=dark)                                            # gros coude vers l'est
    tube([(-0.5, 0.9, 1.1), (-1.2, 0.9, 1.1), (-1.35, 0.4, 1.0), (-1.35, -2.0, 1.0)], 0.13, bronze,
         rings=(0.3, 0.7), ring_m=dark)
    tube([(-1.75, -2.9, 1.05), (1.75, -2.9, 1.05)], 0.15, copper, rings=(0.08, 0.92), ring_m=dark)  # collecteur
    for sx in (-1, 1):                                                                    # tubes fins le long du cadre
        tube([(sx * 1.35, 1.6, 0.95), (sx * 1.5, 0.6, 0.95), (sx * 1.5, -0.4, 0.95)], 0.05, copper)
        tube([(sx * 1.2, 1.7, 0.95), (sx * 1.35, -0.3, 1.0), (sx * 1.2, -1.0, 1.05)], 0.05, copper)
        box((sx * 1.45, -2.0, 1.0), (0.3, 0.45, 0.35), sdark, bevel=0.04)               # vannes
        cyl((sx * 1.45, -2.0, 1.25), 0.1, 0.18, copper, verts=12)
    tube([(0.95, 0.9, 1.05), (1.35, 0.9, 1.05), (1.35, 0.1, 1.05)], 0.12, copper, rings=(0.5,), ring_m=dark)
    # tuyauterie dense : chevauchements à plusieurs hauteurs (cible : on ne voit presque plus le fond)
    tube([(-0.55, 0.95, 1.25), (-1.0, 0.6, 1.4), (-1.1, -0.4, 1.5), (-0.7, -1.2, 1.6), (-0.75, -2.0, 1.55)], 0.15,
         copper, rings=(0.3, 0.65), ring_m=dark)                                          # grand S à gauche
    tube([(-1.62, -1.45, 1.1), (-0.35, -1.45, 1.3)], 0.12, bronze, rings=(0.2, 0.8), ring_m=dark)
    tube([(-0.2, 0.05, 1.65), (-0.65, -0.6, 1.8), (-0.45, -1.5, 1.85), (-0.95, -2.6, 1.45)], 0.1, hose,
         rings=(0.5,), ring_m=steel)                                                      # durite en boucle
    for dx in (0.0, 0.2):                                                                 # faisceaux de tubes fins
        tube([(-1.05 - dx, 1.05, 1.0), (-1.15 - dx, -0.2, 1.1), (-1.3 - dx, -1.2, 1.15), (-1.3 - dx, -2.7, 1.05)],
             0.05, bronze)
        tube([(1.0 + dx, 1.05, 1.0), (1.15 + dx, 0.2, 1.1), (1.15 + dx, -1.0, 1.15), (1.3 + dx, -2.7, 1.05)],
             0.05, bronze)
    tube([(0.45, 1.0, 1.2), (1.0, 0.75, 1.35), (1.1, -0.15, 1.5), (0.85, -0.6, 1.6)], 0.15, copper,
         rings=(0.35, 0.75), ring_m=dark)                                                 # grand S à droite
    tube([(0.95, -1.5, 1.3), (0.95, -2.75, 1.25)], 0.14, bronze, rings=(0.3, 0.7), ring_m=dark)
    tube([(0.3, -0.35, 1.75), (0.7, -1.6, 1.85), (0.45, -2.6, 1.65)], 0.1, hose, rings=(0.45,), ring_m=steel)
    tube([(0.15, -2.0, 1.75), (1.5, -2.0, 1.35)], 0.12, copper, rings=(0.5,), ring_m=dark)
    tube([(-0.65, 0.78, 1.55), (0.0, 0.72, 1.85), (0.65, 0.78, 1.55)], 0.1, hose)        # durite devant la colonne
    tube([(-0.5, -1.0, 1.9), (0.0, -1.1, 2.0), (0.55, -0.95, 1.85)], 0.11, copper, rings=(0.5,), ring_m=dark)
    for loc, r in (((-1.0, -0.4, 1.55), 0.2), ((0.55, -1.75, 1.95), 0.2), ((-0.45, -1.95, 1.75), 0.18),
                   ((1.15, -2.0, 1.45), 0.18)):                                           # raccords aux croisements
        fitting(loc, r, copper, dark)
    for loc in ((-0.75, -2.3, 1.55), (0.95, -2.35, 1.45), (-1.25, -0.9, 1.3)):           # petites vannes sombres
        box(loc, (0.26, 0.22, 0.18), sdark, bevel=0.03)
    fitting((-0.15, -2.5, 1.55), 0.3, copper, dark)                                       # « œil » central
    fitting((-1.05, -2.2, 1.3), 0.24, copper, dark)
    fitting((1.0, -0.5, 1.35), 0.22, copper, dark)
    for sx, x in ((-1, -0.95), (1, 1.05)):                                                # pompes gris-bleu
        cyl((x, -3.15, 1.25), 0.4, 0.5, steel, verts=24, rot=(90, 0, 0))
        fitting((x, -3.42, 1.25), 0.24, copper, dark, axis="y")
    for sx in (-1, 1):                                    # raccord latéral, à la connexion de fluide (x = ±1,5 ; y = 0)
        cyl((sx * 1.62, 0.0, 0.9), 0.22, 0.36, copper, verts=16, rot=(0, 90, 0))
        cyl((sx * 1.48, 0.0, 0.9), 0.27, 0.08, dark, verts=16, rot=(0, 90, 0))

    # --- collier gris-bleu boulonné, pétales crème en relief sur le feu, bouche cerclée
    cyl((0, yc, zc), rt + 0.22, 0.42, steel, verts=40, rot=(90, 0, 0))
    for k in range(10):                                                                   # boulons du collier
        t = math.radians(10 + 16 * k)
        cyl(((rt + 0.23) * math.cos(t), yc - 0.05, zc + (rt + 0.23) * math.sin(t)), 0.06, 0.12, sdark, verts=8,
            rot=(90, 0, 0))
    prof = [(yc - 0.2, rt), (yc - 0.75, rt + 0.1), (ym, rm)]
    lathe([(y, r - 0.02) for y, r in prof], glow, zc)                                     # feu sous les pétales
    for c in (30, 90, 150, 210, 270, 330):                                                # pétales (gaps de 14°)
        lathe([(y, r + 0.06) for y, r in prof], cream, zc, arc=(c - 23, c + 23))
        t = math.radians(c)                                                               # fente sombre au milieu
        r = rt + 0.12
        box((r * math.cos(t), yc - 0.55, zc + r * math.sin(t)), (0.08, 0.3, 0.05), dark, rot_y=-(c - 90))
    lathe([(y, r - d["wall"]) for y, r in prof], inner, zc, inward=True)
    ro, ri, yf = rm + 0.12, rm - 0.06, ym - 0.06
    lathe([(ym + 0.3, ro), (yf, ro)], steel, zc)                                          # anneau de la bouche
    lathe([(yf, ri), (ym + 0.22, ri)], steel, zc, inward=True)
    bm = bmesh.new()                                                                      # face avant de l'anneau
    n = 48
    outer = [bm.verts.new((ro * math.cos(2 * math.pi * k / n), yf, zc + ro * math.sin(2 * math.pi * k / n)))
             for k in range(n)]
    inn = [bm.verts.new((ri * math.cos(2 * math.pi * k / n), yf, zc + ri * math.sin(2 * math.pi * k / n)))
           for k in range(n)]
    for k in range(n):
        bm.faces.new((outer[k], inn[k], inn[(k + 1) % n], outer[(k + 1) % n]))
    me = bpy.data.meshes.new("rim"); bm.to_mesh(me); bm.free()
    rim = bpy.data.objects.new("rim", me); bpy.context.scene.collection.objects.link(rim); me.materials.append(steel)
    for k in range(4):                                                                    # pattes du cerclage
        t = math.radians(-60 + 40 * k) if k < 2 else math.radians(200 + 40 * (k - 2))
        box(((ro + 0.05) * math.cos(t), ym + 0.15, zc + (ro + 0.05) * math.sin(t)), (0.22, 0.34, 0.16), sdark,
            rot_y=-math.degrees(t))
    # fond : disque sombre, couronne de dents gris-bleu, stries rayonnantes claires sur l'intérieur
    cyl((0, yc - 0.3, zc), rt - 0.1, 0.05, dark, verts=40, rot=(90, 0, 0))
    for k in range(9):                                                                   # dents du bas de la bouche
        t = math.radians(200 + 140 * k / 8)
        r = ri - 0.02
        bm = bmesh.new()
        u, v = (math.cos(t), math.sin(t)), (-math.sin(t), math.cos(t))      # radial et tangent (plan x, z)
        pts = [(r * u[0] + 0.1 * v[0], r * u[1] + 0.1 * v[1]), (r * u[0] - 0.1 * v[0], r * u[1] - 0.1 * v[1]),
               ((r - 0.2) * u[0], (r - 0.2) * u[1])]
        f0 = [bm.verts.new((x, ym + 0.1, zc + z)) for x, z in pts]
        f1 = [bm.verts.new((x, ym + 0.4, zc + z)) for x, z in pts]
        bm.faces.new(f0); bm.faces.new(f1[::-1])
        for i in range(3):
            bm.faces.new((f0[i], f1[i], f1[(i + 1) % 3], f0[(i + 1) % 3]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("dent"); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new("dent", me); bpy.context.scene.collection.objects.link(o); me.materials.append(steel)
    for k in range(20):
        t = 2 * math.pi * (k + 0.5) / 20
        rod(((rt - 0.15) * math.cos(t), yc - 0.5, zc + (rt - 0.15) * math.sin(t)),
            ((rm - d["wall"] - 0.1) * math.cos(t), ym + 0.3, zc + (rm - d["wall"] - 0.1) * math.sin(t)),
            0.05, stripe, verts=4)
    bpy.context.view_layer.update()


def write(out):
    import cv2
    path = os.path.join(out, "_thruster.png")
    build()
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE)
    sprite = crop_centered(load(path), *SPRITE)
    cv2.imwrite(os.path.join(out, "thruster-essai.png"), sprite)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "thruster_out"
    os.makedirs(out, exist_ok=True)
    write(out)
    print("OK thruster (essai)", flush=True)
