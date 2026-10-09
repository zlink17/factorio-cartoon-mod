"""Test : rendu toon d'une machine simple (Blender/bpy), fond transparent."""
import math, sys
import bpy

OUT = sys.argv[1] if len(sys.argv) > 1 else "out.png"
SIZE = 256

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def flat_mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1)
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def add(obj, mat):
    obj.data.materials.append(mat)
    return obj


body_m = flat_mat("body", (0.95, 0.55, 0.15))
panel_m = flat_mat("panel", (1.0, 0.8, 0.35))
base_m = flat_mat("base", (0.35, 0.45, 0.8))
gear_m = flat_mat("gear", (0.95, 0.95, 0.95))

# socle
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.15))
o = bpy.context.object; o.scale = (3, 3, 0.3)
add(o, base_m)
# corps
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.9))
o = bpy.context.object; o.scale = (2.6, 2.6, 1.2)
bpy.ops.object.modifier_add(type="BEVEL"); o.modifiers["Bevel"].width = 0.15; o.modifiers["Bevel"].segments = 3
add(o, body_m)
# panneau dessus
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.52))
o = bpy.context.object; o.scale = (2.0, 2.0, 0.08)
add(o, panel_m)
# engrenage
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.7, depth=0.15, location=(0, 0, 1.65))
add(bpy.context.object, gear_m)
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.25, depth=0.2, location=(0, 0, 1.66))
add(bpy.context.object, panel_m)

# caméra orthographique (vue 3/4 type Factorio)
bpy.ops.object.camera_add(location=(6, -6, 6.2))
cam = bpy.context.object
cam.data.type = "ORTHO"; cam.data.ortho_scale = 5.2
cam.rotation_euler = (math.radians(58), 0, math.radians(45))
scene.camera = cam

# rendu
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 4
scene.cycles.use_denoising = False
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = SIZE
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.render.filepath = OUT

# contours noirs (Freestyle)
scene.render.use_freestyle = True
scene.render.line_thickness_mode = "ABSOLUTE"
scene.render.line_thickness = 2.2
vl = scene.view_layers[0]
vl.use_freestyle = True
ls = vl.freestyle_settings.linesets.new("outline")
ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
ls.linestyle.color = (0.05, 0.03, 0.03)

bpy.ops.render.render(write_still=True)
print("rendered", OUT)
