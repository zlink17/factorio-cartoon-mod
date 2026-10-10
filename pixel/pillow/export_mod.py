"""Écrit les sprites des assembleurs 1 à 3 dans pixel/mod/graphics/overrides/base/ puis régénère le manifeste.

Usage : python pixel/pillow/export_mod.py
Assembleurs, pour chaque niveau : planche 8 x 4 images (x4, 224 x 272 par image), image d'ombre, icône (64 px + mips 32/16/8).
Le cadrage (taille, échelle, décalage) est appliqué côté Lua, dans pixel/mod/data-final-fixes.lua.
"""
import os, subprocess, sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import belt, belt_structures as bs, inserter, ore
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
    shadows = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        shadows.alpha_composite(shadow_of(fr), (W * (i % 8), H * (i // 8)))
    up(shadows).save(ent / f"{name}-shadow.png")
    (OVR / "icons").mkdir(parents=True, exist_ok=True)
    icon_of(frames[0]).save(OVR / "icons" / f"{name}.png")
    print(name, "ok")

# convoyeurs : jaune (basique, 16 images), rouge (rapide) et bleu (express), 32 images
GAME = OVR / "entity"
for tier, name, frames in (("yellow", "transport-belt", 16), ("red", "fast-transport-belt", 32), ("blue", "express-transport-belt", 32)):
    d = GAME / name
    d.mkdir(parents=True, exist_ok=True)
    up(belt.sheet(tier, frames)).save(d / f"{name}.png")
    print(name, "ok")

# inserters : tige, mains, plateforme par type ; ombres communes (celles du burner, réutilisées par les autres)
for kind in inserter.RAMPS:
    d = GAME / kind
    d.mkdir(parents=True, exist_ok=True)
    sp = inserter.sprites(kind)
    for part in ("hand-base", "hand-open", "hand-closed", "platform"):
        sp[part].save(d / f"{kind}-{part}.png")
    if kind in ("burner-inserter", "bulk-inserter"):      # le burner fournit les ombres communes ; le vrac a les siennes (mains plus larges)
        for part, img in sp["shadow"].items():
            if kind == "bulk-inserter" and part == "hand-base":
                continue
            alpha = img.getchannel("A").point(lambda v: 90 if v else 0)
            img.putalpha(alpha)
            img.save(d / f"{kind}-{part}-shadow.png")
    print(kind, "ok")

# souterrains (planche 768 x 768 comme l'original) et répartiteurs (32 images par orientation)
for tier, ug, sp in (("yellow", "underground-belt", "splitter"), ("red", "fast-underground-belt", "fast-splitter"),
                     ("blue", "express-underground-belt", "express-splitter")):
    d = GAME / ug
    d.mkdir(parents=True, exist_ok=True)
    up(bs.underground_sheet(tier)).save(d / f"{ug}-structure.png")
    d = GAME / sp
    d.mkdir(parents=True, exist_ok=True)
    for direction in ("north", "east", "south", "west"):
        up(bs.splitter_sheet(direction[0].upper(), tier)).save(d / f"{sp}-{direction}.png")
    print(ug, sp, "ok")

# minerais : planche 8 x 8 (étapes x variantes), 128 px par cellule
for kind in ore.RAMPS:
    d = GAME / kind
    d.mkdir(parents=True, exist_ok=True)
    up(ore.sheet(kind)).save(d / f"{kind}.png")
    print(kind, "ok")

subprocess.run([sys.executable, str(ROOT / "tools" / "build_manifest.py"), "pixel"], check=True)
