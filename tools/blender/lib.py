"""Fonctions communes de rendu toon (voir ../../STYLE.md et style.py)."""
import math, os, sys
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgb):
    """Aplat de couleur à trois tons : dessus clair, face avant moyenne, côtés sombres."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    n = nt.nodes
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    top = n.new("ShaderNodeMath"); top.operation = "GREATER_THAN"; top.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs["Z"], top.inputs[0])
    negy = n.new("ShaderNodeMath"); negy.operation = "MULTIPLY"; negy.inputs[1].default_value = -1.0
    nt.links.new(sep.outputs["Y"], negy.inputs[0])
    front = n.new("ShaderNodeMath"); front.operation = "GREATER_THAN"; front.inputs[1].default_value = 0.5
    nt.links.new(negy.outputs[0], front.inputs[0])
    a = n.new("ShaderNodeMath"); a.operation = "MULTIPLY_ADD"
    a.inputs[1].default_value = S.SHADE_TOP - S.SHADE_SIDE; a.inputs[2].default_value = S.SHADE_SIDE
    nt.links.new(top.outputs[0], a.inputs[0])
    b = n.new("ShaderNodeMath"); b.operation = "MULTIPLY_ADD"
    b.inputs[1].default_value = S.SHADE_FRONT - S.SHADE_SIDE
    nt.links.new(front.outputs[0], b.inputs[0]); nt.links.new(a.outputs[0], b.inputs[2])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[6].default_value = (*rgb, 1)
    comb = n.new("ShaderNodeCombineXYZ")
    for i in range(3):
        nt.links.new(b.outputs[0], comb.inputs[i])
    nt.links.new(comb.outputs[0], mix.inputs[7])
    em = n.new("ShaderNodeEmission")
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    out = n.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def box(loc, scale, m, bevel=0.0, rot_z=0.0, rot_x=0.0, rot_y=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    o.rotation_euler = (math.radians(rot_x), math.radians(rot_y), math.radians(rot_z))
    if bevel:
        bpy.ops.object.modifier_add(type="BEVEL")
        o.modifiers["Bevel"].width = bevel
        o.modifiers["Bevel"].segments = 2
    o.data.materials.append(m)
    return o


def cyl(loc, r, d, m, verts=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc,
                                        rotation=tuple(math.radians(a) for a in rot))
    o = bpy.context.object
    o.data.materials.append(m)
    return o


def blob(loc, r, m):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=loc)
    o = bpy.context.object
    o.data.materials.append(m)
    return o


def frustum(z0, h, w0, d0, w1, d1, m, cy=0.0, bevel=0.0):
    """Tronc de pyramide (parois inclinées, comme les machines de Factorio) centré en x=0."""
    import bmesh
    bm = bmesh.new()
    b = [bm.verts.new(v) for v in ((-w0/2, cy-d0/2, z0), (w0/2, cy-d0/2, z0), (w0/2, cy+d0/2, z0), (-w0/2, cy+d0/2, z0))]
    t = [bm.verts.new(v) for v in ((-w1/2, cy-d1/2, z0+h), (w1/2, cy-d1/2, z0+h), (w1/2, cy+d1/2, z0+h), (-w1/2, cy+d1/2, z0+h))]
    bm.faces.new(b[::-1]); bm.faces.new(t)
    for k in range(4):
        bm.faces.new((b[k], b[(k+1) % 4], t[(k+1) % 4], t[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new("frustum")
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new("frustum", mesh)
    bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(m)
    if bevel:
        bpy.context.view_layer.objects.active = o
        mod = o.modifiers.new("Bevel", "BEVEL"); mod.width = bevel; mod.segments = 2
    return o


def tri_plate(center, w, h, depth, tilt_deg, m):
    """Triangle en relief (sommet vers le haut) posé sur une paroi avant inclinée de `tilt_deg`."""
    import bmesh
    t = math.radians(tilt_deg)
    up = (0.0, math.sin(t), math.cos(t))        # le long de la paroi, vers le haut
    nrm = (0.0, -math.cos(t), math.sin(t))      # normale sortante
    cx, cy, cz = center

    def pt(a, b, c):
        return (cx + a, cy + b * up[1] + c * nrm[1], cz + b * up[2] + c * nrm[2])

    base = [(0, h / 2), (-w / 2, -h / 2), (w / 2, -h / 2)]
    bm = bmesh.new()
    back = [bm.verts.new(pt(a, b, 0)) for a, b in base]
    front = [bm.verts.new(pt(a, b, depth)) for a, b in base]
    bm.faces.new(back[::-1]); bm.faces.new(front)
    for k in range(3):
        bm.faces.new((back[k], back[(k + 1) % 3], front[(k + 1) % 3], front[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new("tri")
    bm.to_mesh(mesh); bm.free()
    o = bpy.data.objects.new("tri", mesh)
    bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(m)
    return o


def gear(center, r, depth, teeth, angle_deg, m, hub_m=None):
    """Engrenage horizontal d'un seul maillage (contours propres). `angle_deg` sert à l'animation."""
    import bmesh
    cx, cy, cz = center
    tip = r * 1.22
    pts = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a0 = math.radians(angle_deg) + i * step
        for frac, rad in ((0.0, r), (0.09, tip), (0.41, tip), (0.5, r)):
            a = a0 + frac * step
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    bm = bmesh.new()
    low = [bm.verts.new((x, y, cz - depth / 2)) for x, y in pts]
    high = [bm.verts.new((x, y, cz + depth / 2)) for x, y in pts]
    bm.faces.new(low[::-1])
    bm.faces.new(high)
    n = len(pts)
    for k in range(n):
        bm.faces.new((low[k], low[(k + 1) % n], high[(k + 1) % n], high[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new("gear")
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new("gear", mesh)
    bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(m)
    if hub_m:
        cyl((cx, cy, cz + depth * 0.5), r * 0.32, depth * 0.4, hub_m, verts=16)
    return o


def render_scene(path, size=256, scale=4.4, pitch_deg=S.PITCH_BUILDING_DEG, cy=0.0, supersample=None, shift_y=0.0):
    """Rend la scène courante avec la projection du guide de style.

    Le rendu est fait à `supersample` fois la taille puis réduit (alpha prémultiplié)."""
    ss = supersample or getattr(S, "SUPERSAMPLE", 1)
    final_path = path
    size_final = size if isinstance(size, tuple) else (size, size)   # (largeur, hauteur)
    size = (size_final[0] * ss, size_final[1] * ss)
    if ss > 1:
        path = path + ".big.png"
    p = math.radians(pitch_deg)
    # étire le sol en Y pour que, une fois raccourci par la caméra, il reste carré
    root = bpy.data.objects.new("root", None)
    bpy.context.scene.collection.objects.link(root)
    root.scale = (1, 1 / math.cos(p), 1) if S.GROUND_STRETCH else (1, 1, 1)
    for o in list(bpy.context.scene.objects):
        if o.type == "MESH":
            o.parent = root
    d = 20
    bpy.ops.object.camera_add(location=(0, -d * math.sin(p), d * math.cos(p) + cy))
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale   # couvre la plus grande dimension du rendu
    cam.data.shift_y = shift_y
    cam.data.clip_end = 100
    cam.rotation_euler = (p, 0, 0)
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = S.RENDER_SAMPLES
    sc.cycles.use_denoising = False
    sc.render.film_transparent = S.FILM_TRANSPARENT
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = S.VIEW_TRANSFORM
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = S.OUTLINE_UNITS * max(size) / scale
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    vl.freestyle_settings.crease_angle = math.radians(S.OUTLINE_CREASE_DEG)
    ls = vl.freestyle_settings.linesets.new("outline")
    ls.select_silhouette = ls.select_border = ls.select_crease = True
    ls.linestyle.color = S.OUTLINE_COLOR
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    if ss > 1:
        import cv2, numpy as np
        im = cv2.imread(path, cv2.IMREAD_UNCHANGED).astype(np.float32)
        a = im[:, :, 3:4] / 255.0
        pre = np.dstack([im[:, :, :3] * a, im[:, :, 3:4]])
        small = cv2.resize(pre, size_final, interpolation=cv2.INTER_AREA)
        al = np.clip(small[:, :, 3:4] / 255.0, 1e-6, 1)
        out = np.dstack([np.clip(small[:, :, :3] / al, 0, 255), small[:, :, 3:4]])
        cv2.imwrite(final_path, np.clip(out, 0, 255).astype(np.uint8))
        os.remove(path)
    return final_path
