"""Écrit les sprites des assembleurs 1 à 3 dans pixel/mod/graphics/overrides/base/ puis régénère le manifeste.

Usage : python pixel/pillow/export_mod.py
Pour chaque niveau : planche 8 x 4 images (x4, 224 x 272 par image), image d'ombre, icône (64 px + mips 32/16/8).
Le cadrage (taille, échelle, décalage) est appliqué côté Lua, dans pixel/mod/data-final-fixes.lua.
"""
import os, subprocess, sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from assembler import draw_assembler, shadow_of, N_FRAMES, W, H, SCALE

OVR = ROOT / "pixel" / "mod" / "graphics" / "overrides" / "base"


def up(img):
    return img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)


def icon_of(frame):
    box = frame.getbbox()
    spr = frame.crop(box)
    base = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    base.alpha_composite(spr, ((64 - spr.width) // 2, (64 - spr.height) // 2))
    out = Image.new("RGBA", (120, 64), (0, 0, 0, 0))
    x = 0
    for size in (64, 32, 16, 8):
        out.alpha_composite(base if size == 64 else base.resize((size, size), Image.BOX), (x, 0))
        x += size
    return out


for tier in (1, 2, 3):
    name = f"assembling-machine-{tier}"
    frames = [draw_assembler(i / N_FRAMES, tier) for i in range(N_FRAMES)]
    sheet = Image.new("RGBA", (W * 8, H * 4), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        sheet.alpha_composite(fr, (W * (i % 8), H * (i // 8)))
    ent = OVR / "entity" / name
    ent.mkdir(parents=True, exist_ok=True)
    up(sheet).save(ent / f"{name}.png")
    up(shadow_of(frames[0])).save(ent / f"{name}-shadow.png")
    (OVR / "icons").mkdir(parents=True, exist_ok=True)
    icon_of(frames[0]).save(OVR / "icons" / f"{name}.png")
    print(name, "ok")

subprocess.run([sys.executable, str(ROOT / "tools" / "build_manifest.py"), "pixel"], check=True)
