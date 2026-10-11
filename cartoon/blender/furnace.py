"""Four en pierre (stone-furnace) : sprite, ombre, icône et flammes.

Usage : python cartoon/blender/furnace.py <dossier_sortie>

Écrit, aux chemins de l'original (base/entity/stone-furnace/ et base/icons/) :
  stone-furnace.png          le four (151 x 146), rendu à 64 px par case et découpé au cadre du prototype
  stone-furnace-shadow.png   son ombre portée, noire unie (le jeu la rend semi-transparente)
  stone-furnace-fire.png     48 images de flammes (41 x 100, 8 par ligne), dessinées en aplats (procédural 2D)
  stone-furnace.png (icône)  64 px + mipmaps
Les halos lumineux (stone-furnace-light, -ground-light) et les restes sont laissés d'origine.

Le four : pyramide tronquée plus étroite à l'arrière (dimensions ajustées sur la silhouette de l'original,
recouvrement 92 %), briques ocre peintes par une texture procédurale (pas de relief, donc pas un contour par
brique), bandeau et cheminée en pierre grise, bouche encadrée de pierre à l'intérieur sombre. Les flammes sont
dessinées dans l'ouverture repérée sur notre rendu (elles s'affichent par-dessus quand le four chauffe).
"""
import math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, crop_centered, entity_path, load, mat, render_scene, render_shadow, reset, save_icon

P = S.PALETTE
NAME = "stone-furnace"
PX_PER_TILE = 64
CANVAS = 512
SPRITE = ((151, 146), (-0.5, 12.0))        # taille et décalage (px) du cadre de l'original (shift x 64)
SHADOW_CELL = ((164, 74), (29.0, 26.0))
SUN_SHEAR = (0.45, 0.02)                   # ombre : décalage au sol par unité de hauteur (droite, bas)
OUTLINE = 0.02                             # contour un peu plus fin : beaucoup de briques

# dimensions (unités du monde = cases), ajustées automatiquement sur la silhouette de l'original :
# corps en pyramide tronquée plus étroite à l'arrière qu'à l'avant (vu de face, comme l'original)
DIMS = dict(
    wf0=1.67, wb0=1.29, yf0=-0.81, yb0=0.38,   # au sol : largeur avant, largeur arrière, y avant, y arrière
    wf1=0.8, wb1=0.63, yf1=-0.27, yb1=0.27,    # en haut : idem
    h=1.24,                                    # hauteur du corps (recouvrement de silhouette : 92 %)
)
BAND = 0.2                                 # bandeau de pierre en haut des parois (hauteur)
CHIMNEY_H = 0.15                           # cheminée : hauteur au-dessus du corps
BRICK_ROWS = 5                             # rangées de briques sur la hauteur des parois


def hull(bottom, top, m):
    """Volume à 6 faces entre deux quadrilatères horizontaux (listes de 4 points (x, y, z), même ordre)."""
    import bpy, bmesh
    bm = bmesh.new()
    b = [bm.verts.new(v) for v in bottom]
    t = [bm.verts.new(v) for v in top]
    bm.faces.new(b[::-1]); bm.faces.new(t)
    for k in range(4):
        bm.faces.new((b[k], b[(k + 1) % 4], t[(k + 1) % 4], t[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("hull")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("hull", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(m)
    return o


def quad(d, f, z):
    """Quadrilatère de la section à la fraction `f` de la hauteur (0 sol, 1 haut), à l'altitude z."""
    lerp = lambda k: d[k + "0"] + (d[k + "1"] - d[k + "0"]) * f
    wf, wb, yf, yb = lerp("wf"), lerp("wb"), lerp("yf"), lerp("yb")
    return [(-wf / 2, yf, z), (wf / 2, yf, z), (wb / 2, yb, z), (-wb / 2, yb, z)]


def mat_bricks(name, c1, c2, mortar, rows):
    """Comme lib.mat (trois tons selon l'orientation de la face), mais la couleur vient d'une texture de briques
    procédurale (rangées décalées, deux teintes de brique, joints sombres), plaquée sur chaque paroi : u le long
    de la paroi (x ou y selon son orientation), v la hauteur. Pas de relief : pas de contour sur chaque brique."""
    import bpy
    m = mat(name, (1, 1, 1))
    nt = m.node_tree
    n = nt.nodes
    mix = next(x for x in n if x.bl_idname == "ShaderNodeMix")
    geo = n.new("ShaderNodeNewGeometry")
    tc = n.new("ShaderNodeTexCoord")
    sep_p = n.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep_p.inputs[0])
    sep_n = n.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Normal"], sep_n.inputs[0])
    ax = n.new("ShaderNodeMath"); ax.operation = "ABSOLUTE"; nt.links.new(sep_n.outputs["X"], ax.inputs[0])
    ay = n.new("ShaderNodeMath"); ay.operation = "ABSOLUTE"; nt.links.new(sep_n.outputs["Y"], ay.inputs[0])
    side = n.new("ShaderNodeMath"); side.operation = "GREATER_THAN"
    nt.links.new(ax.outputs[0], side.inputs[0]); nt.links.new(ay.outputs[0], side.inputs[1])
    u = n.new("ShaderNodeMix"); u.data_type = "FLOAT"
    nt.links.new(side.outputs[0], u.inputs[0])
    nt.links.new(sep_p.outputs["X"], u.inputs[2]); nt.links.new(sep_p.outputs["Y"], u.inputs[3])
    vec = n.new("ShaderNodeCombineXYZ")
    nt.links.new(u.outputs[0], vec.inputs[0]); nt.links.new(sep_p.outputs["Z"], vec.inputs[1])
    tex = n.new("ShaderNodeTexBrick")
    row_h = (DIMS["h"] - BAND) / rows
    tex.inputs["Scale"].default_value = 1.0
    tex.inputs["Row Height"].default_value = row_h
    tex.inputs["Brick Width"].default_value = row_h * 1.9
    tex.inputs["Mortar Size"].default_value = 0.022
    tex.inputs["Mortar Smooth"].default_value = 0.0
    tex.inputs["Bias"].default_value = 0.0
    tex.offset = 0.5
    tex.inputs["Color1"].default_value = (*c1, 1)
    tex.inputs["Color2"].default_value = (*c2, 1)
    tex.inputs["Mortar"].default_value = (*mortar, 1)
    nt.links.new(vec.outputs[0], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], mix.inputs[6])
    return m


def build(d=None):
    reset()
    d = d or DIMS
    bricks = mat_bricks("bricks", P["furnace_brick"], P["furnace_brick_dark"], P["furnace_mortar"], BRICK_ROWS)
    stone, soot = mat("stone", P["furnace_stone"]), mat("soot", P["furnace_soot"])
    h = d["h"]
    fb = 1 - BAND / h
    hull(quad(d, 0, 0), quad(d, fb, h - BAND), bricks)
    hull(quad(d, fb, h - BAND), quad(d, 1, h), stone)                       # bandeau de pierre
    top = quad(d, 1, h)
    hull(top, [(x, y, h + CHIMNEY_H) for x, y, _ in top], stone)            # cheminée
    cx, cy = 0.0, (d["yf1"] + d["yb1"]) / 2
    box((cx, cy, h + CHIMNEY_H), (d["wb1"] * 0.6, (d["yb1"] - d["yf1"]) * 0.6, 0.03), soot)
    # bouche : encadrement de pierre encastré dans la paroi avant (montants et linteau), ouverture sombre
    yf = d["yf0"]
    for x in (-0.27, 0.27):
        box((x, yf + 0.02, 0.36), (0.12, 0.24, 0.72), stone, 0.015)         # montants
    box((0, yf + 0.06, 0.8), (0.66, 0.16, 0.16), stone, 0.015)              # linteau
    box((0, yf + 0.06, 0.36), (0.44, 0.12, 0.72), soot)                     # fond de la bouche
    box((0, yf - 0.04, 0.025), (0.7, 0.14, 0.05), stone, 0.01)              # seuil


# --- flammes (procédural 2D) -------------------------------------------------------------------------------
FIRE = ((41, 100), (-1.5, 11.0))          # cadre d'une image de flammes et son décalage (px), comme l'original
FIRE_FRAMES, FIRE_COLUMNS = 48, 8
FIRE_TONES = ("#c8402a", "#f08a2c", "#ffd44a")   # extérieur, milieu, cœur
SS = 4


def mouth_box(sprite):
    """Ouverture de la bouche dans notre sprite (pixels de suie, moitié basse), en px du cadre des flammes."""
    soot = np.array([int(S.PALETTE_HEX["furnace_soot"][k:k + 2], 16) for k in (5, 3, 1)], np.float32)
    h, w = sprite.shape[:2]
    near = (np.abs(sprite[:, :, :3].astype(np.float32) - soot).max(2) < 10) & (sprite[:, :, 3] > 200)
    near[: h // 2] = False
    ys, xs = np.nonzero(near)
    (fw, fh), (fx, fy) = FIRE
    (sw, sh), (sx, sy) = SPRITE
    dx, dy = sx - sw / 2 - (fx - fw / 2), sy - sh / 2 - (fy - fh / 2)
    return xs.min() + dx, ys.min() + dy, xs.max() + 1 + dx, ys.max() + 1 + dy


def fire_frame(i, box_):
    """Une image : braises au fond, trois langues de flamme qui ondulent (boucle de FIRE_FRAMES images)."""
    (fw, fh), _ = FIRE
    x0, y0, x1, y1 = (v * SS for v in box_)
    W, H = fw * SS, fh * SS
    t = 2 * math.pi * i / FIRE_FRAMES
    img = np.zeros((H, W, 4), np.float32)
    cols = [tuple(int(c[k:k + 2], 16) for k in (5, 3, 1)) for c in FIRE_TONES]
    wid, hei = x1 - x0, y1 - y0
    for tone, (scale_w, scale_h) in enumerate(((1.0, 1.0), (0.72, 0.72), (0.42, 0.45))):
        m = np.zeros((H, W), np.uint8)
        for k, (cx, f, ph) in enumerate(((0.25, 2, 0.0), (0.52, 3, 1.7), (0.78, 2, 3.1))):
            top = hei * scale_h * (0.62 + 0.22 * math.sin(f * t + ph) + 0.08 * math.sin(5 * t + k))
            half = wid * 0.2 * scale_w
            bx = x0 + wid * cx + wid * 0.03 * math.sin(3 * t + ph)
            sway = wid * 0.06 * math.sin(2 * t + ph + 1)
            n = 16                                                  # langue : goutte arrondie en bas, pointe en haut
            left, right = [], []
            for j in range(n + 1):
                f = j / n
                r = half * math.sin(math.pi * (0.5 + 0.5 * f)) ** 0.7 * (1 - 0.15 * f) if f < 1 else 0.0
                y = y1 - top * f
                left.append((bx + sway * f * f - r, y))
                right.append((bx + sway * f * f + r, y))
            cv2.fillPoly(m, [np.round(np.array(left + right[::-1])).astype(np.int32)], 1)
        cv2.rectangle(m, (int(x0), int(y1 - hei * 0.18 * scale_h)), (int(x1), int(y1)), 1, -1)   # braises
        img[m > 0, :3] = cols[tone]
        img[m > 0, 3] = 255
    clip = np.zeros((H, W), np.float32)
    clip[int(y0):int(y1), int(x0):int(x1)] = 1
    img *= clip[..., None]
    small = cv2.resize(img, (fw, fh), interpolation=cv2.INTER_AREA)
    a = np.clip(small[..., 3:4] / 255.0, 1e-6, 1)
    return np.dstack([np.clip(small[..., :3] / a, 0, 255), small[..., 3:4]]).astype(np.uint8)


def render(out):
    path = os.path.join(out, "_furnace.png")
    build()
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE)
    big = load(path)
    sprite = crop_centered(big, *SPRITE)
    cv2.imwrite(entity_path(out, NAME), sprite)
    mb = mouth_box(sprite)
    frames = [fire_frame(i, mb) for i in range(FIRE_FRAMES)]
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-fire.png"), np.vstack(
        [np.hstack(frames[r:r + FIRE_COLUMNS]) for r in range(0, FIRE_FRAMES, FIRE_COLUMNS)]))
    shadow = render_shadow(build, path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR)
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-shadow.png"), crop_centered(shadow, *SHADOW_CELL))
    save_icon(out, NAME, build)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "furnace_out"
    os.makedirs(out, exist_ok=True)
    render(out)
    print("OK", NAME)
