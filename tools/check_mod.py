#!/usr/bin/env python3
"""Contrôle d'un mod avant installation.

Usage : python tools/check_mod.py [cartoon] [--jeu]

Contrôles sur les fichiers (rapides) :
  - chaque image a la taille de l'original : sinon Factorio refuse de démarrer quand le prototype en découpe une
    partie (« sprite rectangle is outside the actual sprite size ») ; les icônes gardent ainsi leurs mipmaps ;
  - chaque image a un canal alpha si l'original en a un ;
  - aucune ombre (fichier « shadow ») n'est entièrement transparente : elle ne produirait aucune ombre en jeu ;
  - manifest.lua liste exactement les images présentes ;
  - avertissement pour les images qu'aucun prototype du jeu n'utilise (voir tools/inventory.py).

--jeu : test de chargement dans une instance isolée de Factorio (tools/factorio.py) avec le mod activé : le mod
doit se charger, et aucun prototype ne doit encore pointer vers un original que le mod remplace.

Ne convient pas au mod pixel, dont les sprites sont agrandis et recadrés côté Lua.
"""
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factorio  # noqa: E402

ROOT = factorio.ROOT


def png_header(path):
    """(largeur, hauteur, type de couleur) lus dans l'en-tête PNG."""
    with open(path, "rb") as f:
        head = f.read(26)
    width, height = struct.unpack(">II", head[16:24])
    return width, height, head[25]


def has_alpha(color_type):
    return color_type in (4, 6)                       # niveaux de gris + alpha, RGBA


def empty(png):
    """Vrai si l'image est entièrement transparente (sans OpenCV : jamais)."""
    try:
        import cv2
    except ImportError:
        return False
    im = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
    return im is not None and im.ndim == 3 and im.shape[2] == 4 and im[:, :, 3].max() == 0


def check_files(mod):
    overrides = ROOT / mod / "mod" / "graphics" / "overrides"
    errors = []
    files = sorted(overrides.rglob("*.png"))
    for png in files:
        rel = png.relative_to(overrides).as_posix()          # base/entity/.../x.png
        game, _, rest = rel.partition("/")
        orig = factorio.DATA / game / "graphics" / rest
        if not orig.exists():
            errors.append(f"ABSENT de l'original : {rel}")
            continue
        w, h, ct = png_header(png)
        ow, oh, oct_ = png_header(orig)
        if (w, h) != (ow, oh):
            errors.append(f"TAILLE {w}x{h} au lieu de {ow}x{oh} : {rel}")
        if has_alpha(oct_) and not has_alpha(ct):
            errors.append(f"SANS ALPHA : {rel}")
        if "shadow" in png.name and empty(png):
            errors.append(f"OMBRE VIDE : {rel}")

    manifest = ROOT / mod / "mod" / "manifest.lua"
    listed = set(re.findall(r'\["__(.+?)__/graphics/(.+?)"\]', manifest.read_text(encoding="utf-8")))
    present = {tuple(p.relative_to(overrides).as_posix().split("/", 1)) for p in files}
    for game, rest in sorted(present - listed):
        errors.append(f"HORS MANIFESTE (lancer tools/build_manifest.py) : {game}/{rest}")
    for game, rest in sorted(listed - present):
        errors.append(f"MANIFESTE sans fichier : {game}/{rest}")
    return files, errors


def unused(mod):
    """Images du mod qu'aucun prototype du jeu d'origine n'utilise."""
    import inventory
    images, done = inventory.load(mod)
    return sorted(done - {i.rel for i in images.values()})


def check_game(mod):
    """Charge le jeu avec le mod ; renvoie la liste des problèmes."""
    name = factorio.install(mod)
    try:
        dump = json.loads(factorio.dump(mods=[name]).read_text(encoding="utf-8"))
    except RuntimeError as e:
        return [f"LE MOD NE SE CHARGE PAS :\n{e}"]
    strings = set()

    def walk(node):
        if isinstance(node, dict):
            node = node.values()
        for v in node:
            if isinstance(v, str):
                if v.endswith(".png"):
                    strings.add(v)
            elif isinstance(v, (dict, list)):
                walk(v)

    walk(dump)
    overrides = ROOT / mod / "mod" / "graphics" / "overrides"
    replaced = {f"__{p.relative_to(overrides).as_posix().split('/', 1)[0]}__/graphics/"
                f"{p.relative_to(overrides).as_posix().split('/', 1)[1]}" for p in overrides.rglob("*.png")}
    errors = [f"NON REMPLACÉ en jeu : {s}" for s in sorted(strings & replaced)]
    prefix = f"__{name}__/graphics/overrides/"
    used = {s[len(prefix):] for s in strings if s.startswith(prefix)}
    errors += [f"RÉFÉRENCE sans fichier : {u}" for u in sorted(u for u in used if not (overrides / u).exists())]
    print(f"Chargement : {len(used)} images du mod utilisées par les prototypes.")
    return errors


def main(argv):
    mod = next((a for a in argv if not a.startswith("-")), "cartoon")
    files, errors = check_files(mod)
    for path in unused(mod):
        print(f"(avertissement) aucun prototype n'utilise : {path}")
    if "--jeu" in argv:
        errors += check_game(mod)
    print("\n".join(errors))
    print(f"{len(files)} images contrôlées, {len(errors)} problèmes.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
