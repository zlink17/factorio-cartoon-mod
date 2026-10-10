"""Objets intermédiaires (plaques, engrenage, circuits, packs de science...) : icônes, aussi posées sur les convoyeurs.

Usage : python cartoon/blender/items.py <dossier_sortie> [objet[,objet...]|tous]

Écrit base/icons/<objet>.png : 64 px + mipmaps (120 x 64), par lib.save_icon. Les objets ne sont pas des bâtiments :
vus plus inclinés (45°, `PITCH_ITEM_DEG`) pour montrer leur volume, et tournés librement (`turn`) comme les icônes
d'origine ; les plaques de fer et de cuivre sont tournées en sens inverse pour les distinguer d'un coup d'œil.
"""
import math, os, sys
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import blob, box, cyl, gear, mat, reset, save_icon
from ore import Rng

P = S.PALETTE


# --- briques ----------------------------------------------------------------------------------------------------

def turn(yaw):
    """Tourne toute la scène de `yaw` degrés autour de l'axe vertical."""
    a = math.radians(yaw)
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            x, y, z = o.location
            o.location = (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z)
            o.rotation_euler[2] += a


def lathe(profile, m, verts=32):
    """Solide de révolution autour de l'axe vertical : `profile` = [(rayon, hauteur), ...] de bas en haut."""
    import bmesh
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / verts), r * math.sin(2 * math.pi * k / verts), z))
                          for k in range(verts)])
    for lo, hi in zip(rings, rings[1:]):
        if len(lo) == 1:
            for k in range(verts):
                bm.faces.new((lo[0], hi[(k + 1) % verts], hi[k]))
        elif len(hi) == 1:
            for k in range(verts):
                bm.faces.new((lo[k], lo[(k + 1) % verts], hi[0]))
        else:
            for k in range(verts):
                bm.faces.new((lo[k], lo[(k + 1) % verts], hi[(k + 1) % verts], hi[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new("lathe")
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new("lathe", mesh)
    bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(m)
    return o


def tube(points, r, m):
    """Tube de rayon `r` le long d'une polyligne 3D (fil, câble, mèche)."""
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, (x, y, z) in zip(sp.points, points):
        p.co = (x, y, z, 1)
    cu.materials.append(m)
    o = bpy.data.objects.new("tube", cu)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.object


def hole(o, loc, r, depth):
    """Perce `o` d'un trou cylindrique vertical (modificateur booléen)."""
    cutter = cyl(loc, r, depth, o.data.materials[0], verts=32)
    mod = o.modifiers.new("hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="hole")
    bpy.data.objects.remove(cutter)
    return o


def lying_cyl(loc, r, length, m, yaw=0.0, verts=24):
    """Cylindre couché, d'axe horizontal tourné de `yaw` degrés depuis l'axe x."""
    return cyl(loc, r, length, m, verts, rot=(0, 90, yaw))


# --- modèles ----------------------------------------------------------------------------------------------------

def plate(color, yaw):
    """Plaque carrée biseautée ; fer et cuivre sont tournés en sens inverse (comme l'original, pour les distinguer)."""
    def build():
        reset()
        box((0, 0, 0.07), (1.0, 1.0, 0.14), mat("plate", P[color]), bevel=0.035)
        turn(yaw)
    return build


def steel_plate():
    """Poutre en I couchée."""
    reset()
    m = mat("steel", P["steel"])
    box((0, 0, 0.03), (1.0, 0.34, 0.06), m)
    box((0, 0, 0.21), (1.0, 0.08, 0.32), m)
    box((0, 0, 0.39), (1.0, 0.34, 0.06), m)
    turn(-60)


def gear_wheel():
    reset()
    g = gear((0, 0, 0.11), 0.4, 0.22, 9, 0, mat("gear", P["iron"]))
    hole(g, (0, 0, 0.11), 0.2, 0.4)
    turn(10)


def copper_cable():
    """Bobine de fil de cuivre en spirale, posée à plat."""
    reset()
    pts = []
    turns, r0, r1 = 3.2, 0.1, 0.44
    for k in range(int(turns * 48) + 1):
        t = k / 48
        a = t * math.tau
        r = r0 + (r1 - r0) * t / turns
        pts.append((r * math.cos(a), r * math.sin(a), 0.045))
    pts.append((pts[-1][0] + 0.1, pts[-1][1] - 0.12, 0.045))      # bout libre
    tube(pts, 0.045, mat("copper", P["ore_copper"]))


def iron_stick():
    reset()
    lying_cyl((0, 0, 0.08), 0.08, 1.1, mat("stick", P["steel_light"]), yaw=55, verts=16)


def circuit(color):
    """Carte à trois pistes de laiton coudées, terminées par des pastilles."""
    def build():
        reset()
        box((0, 0, 0.04), (1.0, 0.82, 0.08), mat("board", P[color]))
        brass = mat("trace", P["brass"])
        for y in (-0.25, 0.0, 0.25):
            box((-0.28, y - 0.03, 0.095), (0.3, 0.12, 0.03), brass)               # piste
            box((-0.1, y + 0.02, 0.095), (0.12, 0.22, 0.03), brass)               # coude
            box((0.08, y + 0.07, 0.095), (0.3, 0.12, 0.03), brass)
            cyl((0.29, y + 0.07, 0.1), 0.1, 0.04, brass, verts=20)                # pastille
        turn(-10)
    return build


def stone_brick():
    reset()
    box((0, 0, 0.19), (0.95, 0.6, 0.38), mat("brick", P["brick"]), bevel=0.04)
    turn(-25)


def wood():
    """Trois rondins empilés, bois clair aux bouts."""
    reset()
    bark, cut = mat("bark", P["bark"]), mat("cut", P["wood_cut"])
    for x, y, z in ((0, -0.2, 0.17), (0, 0.2, 0.17), (0.05, 0.0, 0.47)):
        lying_cyl((x, y, z), 0.17, 0.9, bark, verts=12)
        for side in (-1, 1):
            lying_cyl((x + side * 0.46, y, z), 0.14, 0.03, cut, verts=12)
    turn(62)


def plastic_bar():
    reset()
    box((0, 0, 0.13), (0.95, 0.42, 0.26), mat("plastic", P["plastic"]), bevel=0.1)
    turn(-25)


def sulfur():
    """Amas de cristaux jaunes pointus, inclinés vers l'extérieur."""
    reset()
    m = mat("sulfur", P["sulfur"])
    rng = Rng(3)
    for k in range(8):
        a = k * 2.4
        d = 0.0 if k == 0 else 0.2 + 0.04 * (k % 3)
        r, h = rng.u(0.07, 0.1), rng.u(0.4, 0.65) * (1.3 if k == 0 else 1.0)
        o = lathe([(0, 0), (r, 0), (r, h * 0.7), (0, h)], m, verts=6)
        o.location = (d * math.cos(a), d * math.sin(a), 0)
        o.rotation_euler = (-d * 1.8 * math.sin(a), d * 1.8 * math.cos(a), rng.u(0, 6))


def battery():
    """Pile couchée, deux bornes rouge et bleue sur le dessus."""
    reset()
    box((0, 0, 0.22), (0.62, 0.95, 0.44), mat("case", P["dark_grey"]), bevel=0.14)
    for x, c in ((-0.15, "sci_red"), (0.15, "sci_blue")):
        cyl((x, -0.25, 0.47), 0.09, 0.08, mat(c, P[c]), verts=20)
    turn(-25)


def engine_unit():
    """Bloc moteur : carter, cylindre à ailettes, tubulure et volant."""
    reset()
    grey, dark, brass = mat("block", P["iron"]), mat("dark", P["dark_grey"]), mat("brass", P["brass"])
    box((0, 0, 0.17), (0.8, 0.55, 0.34), grey, bevel=0.04)
    cyl((-0.08, 0, 0.5), 0.17, 0.34, dark, verts=24)
    for k in range(4):
        cyl((-0.08, 0, 0.39 + 0.085 * k), 0.27, 0.035, grey, verts=24)
    box((0, 0, 0.345), (0.82, 0.57, 0.05), brass)
    lying_cyl((0.3, -0.05, 0.42), 0.08, 0.35, dark, verts=12)
    lying_cyl((-0.48, 0.0, 0.17), 0.13, 0.1, dark, verts=20)
    turn(-25)


def electric_engine_unit():
    """Moteur électrique : cylindre couché à flasques rouges, arbre et socle."""
    reset()
    grey, red, dark = mat("body", P["iron"]), mat("red", P["sci_red"]), mat("dark", P["dark_grey"])
    lying_cyl((0, 0, 0.3), 0.26, 0.7, grey, verts=24)
    for x in (-0.36, 0.36):
        lying_cyl((x, 0, 0.3), 0.28, 0.06, red, verts=24)
    lying_cyl((0.46, 0, 0.3), 0.06, 0.16, dark, verts=12)
    box((0, 0, 0.04), (0.6, 0.5, 0.08), dark)
    turn(-30)


def flying_robot_frame():
    """Cerclage à hélice sur trois pieds."""
    reset()
    steel, dark, blade = mat("ring", P["steel"]), mat("dark", P["dark_grey"]), mat("blade", P["dark_grey"])
    for z in (0.06, 0.5):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.4, minor_radius=0.07, major_segments=32, minor_segments=8,
                                         location=(0, 0, z))
        bpy.context.object.data.materials.append(steel)
    for k in range(4):
        a = k * math.tau / 4 + 0.4
        cyl((0.4 * math.cos(a), 0.4 * math.sin(a), 0.28), 0.04, 0.44, dark, verts=10)
        box((0.17 * math.cos(a), 0.17 * math.sin(a), 0.5), (0.3, 0.14, 0.03), blade, rot_z=math.degrees(a), rot_x=20)
    blob((0, 0, 0.53), 0.1, dark)


def low_density_structure():
    """Quatre alvéoles hexagonales de cuivre, soudées."""
    reset()
    m = mat("ldsr", P["ore_copper"])
    for x, y in ((0, 0), (0.32, 0.18), (-0.32, 0.18), (0, -0.37)):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.075, major_segments=6, minor_segments=4,
                                         location=(x, y, 0.075))
        bpy.context.object.data.materials.append(m)
    turn(15)


def rocket_fuel():
    """Cartouche couchée : embouts gris, fenêtre jaune au milieu."""
    reset()
    grey, dark, fuel = mat("shell", P["iron"]), mat("dark", P["dark_grey"]), mat("fuel", P["fuel"])
    lying_cyl((0, 0, 0.2), 0.2, 0.36, fuel, verts=20)
    for x in (-0.32, 0.32):
        lying_cyl((x, 0, 0.2), 0.21, 0.28, grey, verts=20)
    lying_cyl((-0.5, 0, 0.2), 0.1, 0.1, dark, verts=12)
    turn(-35)


def solid_fuel():
    reset()
    box((0, 0, 0.27), (0.6, 0.6, 0.54), mat("fuel", P["dark_grey"]), bevel=0.05)
    turn(-25)


def explosives():
    """Fagot de bâtons de dynamite rouges liés par deux bandes grises, avec une mèche."""
    reset()
    red, band, fuse = mat("stick", P["sci_red"]), mat("band", P["iron"]), mat("fuse", P["dark"])
    r = 0.11
    for dy, dz in ((0, 0), (2 * r, 0), (-2 * r, 0), (r, 1.7 * r), (-r, 1.7 * r), (0, 3.4 * r)):
        lying_cyl((0, dy, r + dz), r, 0.85, red, verts=16)
    for x in (-0.22, 0.22):
        box((x, 0, 0.27), (0.07, 0.7, 0.56), band, bevel=0.05)
    tube([(-0.43, 0, 0.3), (-0.55, -0.05, 0.25), (-0.6, -0.15, 0.1), (-0.68, -0.25, 0.04)], 0.025, fuse)
    turn(-35)


def uranium(color):
    """Gros galet à facettes, accompagné d'un plus petit."""
    def build():
        reset()
        m = mat("u", P[color])
        rng = Rng(11)
        for loc, r, sc in (((0, 0.05, 0.3), 0.42, (1.0, 0.85, 0.75)), ((0.3, -0.18, 0.15), 0.22, (1.0, 0.9, 0.7))):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=loc)
            o = bpy.context.object
            o.scale = sc
            for v in o.data.vertices:                                 # sommets irréguliers : un caillou
                v.co *= rng.u(0.88, 1.12)
            o.rotation_euler = (0.2, 0.1, 0.4)
            o.data.materials.append(m)
    return build


# flacon d'Erlenmeyer : corps conique presque plein de liquide, col de verre, bague et ouverture sombre
FLASK_LIQUID = [(0, 0), (0.28, 0), (0.35, 0.03), (0.38, 0.09), (0.37, 0.15), (0.2, 0.46), (0, 0.46)]
FLASK_GLASS = [(0.2, 0.46), (0.12, 0.57), (0.11, 0.6), (0.11, 0.86), (0.15, 0.87), (0.15, 0.95), (0.1, 0.95),
               (0.1, 0.93), (0, 0.93)]


def science(color):
    def build():
        reset()
        lathe(FLASK_LIQUID, mat("liquid", P[color]))
        lathe(FLASK_GLASS, mat("glass", P["glass"]))
        cyl((0, 0, 0.945), 0.1, 0.01, mat("opening", P["dark"]), verts=32)
    return build


ITEMS = {
    "iron-plate": plate("steel_light", -35),
    "copper-plate": plate("ore_copper", 35),
    "steel-plate": steel_plate,
    "iron-gear-wheel": gear_wheel,
    "copper-cable": copper_cable,
    "iron-stick": iron_stick,
    "electronic-circuit": circuit("pcb_green"),
    "advanced-circuit": circuit("pcb_red"),
    "processing-unit": circuit("pcb_blue"),
    "stone-brick": stone_brick,
    "wood": wood,
    "plastic-bar": plastic_bar,
    "sulfur": sulfur,
    "battery": battery,
    "engine-unit": engine_unit,
    "electric-engine-unit": electric_engine_unit,
    "flying-robot-frame": flying_robot_frame,
    "low-density-structure": low_density_structure,
    "rocket-fuel": rocket_fuel,
    "solid-fuel": solid_fuel,
    "explosives": explosives,
    "uranium-235": uranium("u235"),
    "uranium-238": uranium("u238"),
    "automation-science-pack": science("sci_red"),
    "logistic-science-pack": science("sci_green"),
    "military-science-pack": science("sci_grey"),
    "chemical-science-pack": science("sci_blue"),
    "production-science-pack": science("sci_purple"),
    "utility-science-pack": science("sci_yellow"),
    "space-science-pack": science("sci_white"),
}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "items_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    os.makedirs(out, exist_ok=True)
    for name in (ITEMS if which == "tous" else which.split(",")):
        save_icon(out, name, ITEMS[name], fill=58, outline_px=0.45, pitch_deg=S.PITCH_ITEM_DEG)
        print("OK", name, flush=True)
