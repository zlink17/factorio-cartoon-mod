#!/usr/bin/env python3
"""Inventaire des images du jeu et couverture d'un mod.

Lit data-raw-dump.json (produit par `factorio --dump-data`, voir tools/factorio.py) : chaque image PNG référencée
par un prototype, avec son rôle (sprite, ombre, masque...), les prototypes qui l'utilisent et le découpage déclaré.

Usage :
  python tools/inventory.py [cartoon]                 écrit docs/<mod>/couverture.md et affiche le résumé
  python tools/inventory.py [cartoon] liste MOTIF     fichiers dont le chemin contient MOTIF (ex. entity/stone-furnace)
  python tools/inventory.py [cartoon] orphelins       images du mod qu'aucun prototype n'utilise
  python tools/inventory.py [cartoon] --rafraichir    relance l'extraction (sinon cache .cache/, refait à chaque version du jeu)

Rôles :
  sprite     image vue telle quelle (entité, sol, décoration...)
  icone      icône (objet, recette, technologie, interface)
  ombre      calque dessiné comme ombre (draw_as_shadow)
  lumiere    calque de lumière (draw_as_light) : halo qui éclaire la nuit, non dessiné en couleur
  masque     zone teintée par le jeu (couleur du joueur, du train...) : suit la silhouette du sprite
  technique  table de couleurs, bruit, carte d'effet, reflet : pas d'aspect visible propre, on ne le refait pas
"""
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factorio  # noqa: E402

ROOT = factorio.ROOT
ICON_KEYS = {"icon", "small_icon", "starmap_icon", "dark_background_icon", "icon_tintable"}
TECHNICAL_KEYS = {"lut", "frozen_color_lookup", "icon_tintable_mask", "icon_color_indicator_mask"}
TECHNICAL_PATH = re.compile(r"(effect[-_]map|noise|shader|-spec\.|reflection|/lut/|color_luts|[-_]lut\b|_normal|gradient)", re.I)
FRAMING_KEYS = ("width", "height", "size", "frame_count", "line_length", "direction_count", "variation_count",
                "scale", "shift", "x", "y")
ORDER = ["sprite", "icone", "ombre", "lumiere", "masque", "technique"]


class Image:
    def __init__(self, path):
        self.path = path                       # __base__/graphics/entity/x/y.png
        game, _, rest = path.partition("/graphics/")
        self.game = game.strip("_")
        parts = rest.split("/")
        self.category = parts[0] if len(parts) > 1 else "(racine)"
        if self.category in ("icons", "technology") or len(parts) <= 2:
            stem = re.sub(r"(-\d+)?\.png$", "", parts[-1])
            self.family = stem if self.category == "icons" else self.category
        else:
            self.family = parts[1]
        self.rel = f"{self.game}/{rest}"       # chemin sous graphics/overrides/
        self.roles = set()
        self.users = set()                     # (type, nom)
        self.framing = None                    # premier découpage rencontré

    @property
    def role(self):
        """Rôle principal : le plus « visible » des rôles rencontrés."""
        return next(r for r in ORDER if r in self.roles)

    @property
    def counted(self):
        return self.role != "technique"


def role_of(key, context, path):
    name = path.rsplit("/", 1)[-1]
    if key in TECHNICAL_KEYS or TECHNICAL_PATH.search(path):
        return "technique"
    if key in ICON_KEYS or "/icons/" in path or "/technology/" in path:
        return "icone"
    if context.get("draw_as_shadow") or "shadow" in name:
        return "ombre"
    if context.get("draw_as_light") or re.search(r"[-_]light", name):   # draw_as_glow : dessiné aussi en couleur
        return "lumiere"
    if context.get("apply_runtime_tint") or "mask" in key or "mask" in name:
        return "masque"
    return "sprite"


def collect(dump):
    images = {}

    def note(path, key, context, owner):
        image = images.get(path) or images.setdefault(path, Image(path))
        image.roles.add(role_of(key, context, path))
        image.users.add(owner)
        if image.framing is None:
            image.framing = {k: context[k] for k in FRAMING_KEYS if k in context}

    def walk(node, key, owner, context):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, str):
                    if v.endswith(".png"):
                        note(v, k, node, owner)
                else:
                    walk(v, k, owner, node)
        elif isinstance(node, list):
            for v in node:
                if isinstance(v, str):
                    if v.endswith(".png"):            # listes « filenames » (variantes)
                        note(v, key, context, owner)
                else:
                    walk(v, key, owner, context)

    for ptype, protos in dump.items():
        for name, proto in protos.items():
            walk(proto, None, (ptype, name), {})
    return images


def png_size(path):
    try:
        with open(path, "rb") as f:
            return struct.unpack(">II", f.read(24)[16:24])
    except OSError:
        return None


def load(mod, refresh=False):
    dump = json.loads(factorio.dump_data(refresh).read_text(encoding="utf-8"))
    images = collect(dump)
    overrides = ROOT / mod / "mod" / "graphics" / "overrides"
    done = {p.relative_to(overrides).as_posix() for p in overrides.rglob("*.png")} if overrides.exists() else set()
    return images, done


def pct(a, b):
    return f"{100 * a / b:.0f} %" if b else "—"


def report(mod, images, done):
    counted = [i for i in images.values() if i.counted]
    games = sorted({i.game for i in counted}, key=lambda g: (g not in factorio.OFFICIAL, g))
    lines = [
        f"# Mod {mod} : couverture",
        "",
        "Fichier généré par `tools/inventory.py` (ne pas éditer à la main). Une ligne = un fichier PNG du jeu",
        "référencé par un prototype ; les fichiers « techniques » (tables de couleurs, bruits, cartes d'effets, reflets)",
        f"sont exclus du décompte ({sum(not i.counted for i in images.values())} fichiers).",
        "",
        "## Par jeu",
        "",
        "| Jeu | Remplacés | Total | Couverture |",
        "|---|---:|---:|---:|",
    ]
    for game in games:
        items = [i for i in counted if i.game == game]
        n = sum(i.rel in done for i in items)
        lines.append(f"| `{game}` | {n} | {len(items)} | {pct(n, len(items))} |")
    replaced = sum(i.rel in done for i in counted)
    lines.append(f"| **Total** | **{replaced}** | **{len(counted)}** | **{pct(replaced, len(counted))}** |")

    lines += ["", "## Par rôle", "", "| Rôle | Remplacés | Total |", "|---|---:|---:|"]
    for role in ORDER[:-1]:
        items = [i for i in counted if i.role == role]
        lines.append(f"| {role} | {sum(i.rel in done for i in items)} | {len(items)} |")

    for game in games:
        lines += ["", f"## `{game}` par famille", "",
                  "Famille = dossier sous la catégorie (pour les icônes : nom de l'objet).", ""]
        by_cat = defaultdict(lambda: defaultdict(list))
        for i in counted:
            if i.game == game:
                by_cat[i.category][i.family].append(i)
        for cat in sorted(by_cat):
            fams = by_cat[cat]
            total = sum(len(v) for v in fams.values())
            n = sum(i.rel in done for v in fams.values() for i in v)
            lines += [f"### {cat} : {n} / {total}", ""]
            if cat in ("icons", "technology"):
                full = sorted(f for f, v in fams.items() if all(i.rel in done for i in v))
                if full:
                    lines.append("Faites : " + ", ".join(f"`{f}`" for f in full) + ".")
                    lines.append("")
                continue
            lines += ["| Famille | Faits | Fichiers | Dont ombres, masques, lumières |", "|---|---:|---:|---:|"]
            for fam in sorted(fams):
                v = fams[fam]
                k = sum(i.rel in done for i in v)
                mark = "✅ " if k == len(v) else ("◐ " if k else "")
                derived = sum(i.role in ("ombre", "masque", "lumiere") for i in v)
                lines.append(f"| {mark}{fam} | {k} | {len(v)} | {derived} |")
            lines.append("")
    path = ROOT / "docs" / mod / "couverture.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path, replaced, len(counted)


def describe(image, done):
    f = image.framing or {}
    size = png_size(factorio.DATA / image.game / "graphics" / image.rel.split("/", 1)[1])
    cut = " ".join(f"{k}={json.dumps(f[k])}" for k in FRAMING_KEYS if k in f)
    users = sorted(f"{t}/{n}" for t, n in image.users)
    more = f" (+{len(users) - 3})" if len(users) > 3 else ""
    state = "FAIT " if image.rel in done else "     "
    dims = f"{size[0]}x{size[1]}" if size else "?"
    return f"{state}{image.role:<9} {dims:>11}  {image.rel}\n{'':26}{cut}\n{'':26}{', '.join(users[:3])}{more}"


def main(argv):
    refresh = "--rafraichir" in argv
    args = [a for a in argv if a != "--rafraichir"]
    mod = args.pop(0) if args and (ROOT / args[0] / "mod").is_dir() else "cartoon"
    images, done = load(mod, refresh)
    command = args.pop(0) if args else "rapport"
    if command == "liste":
        pattern = args[0] if args else ""
        found = sorted((i for i in images.values() if pattern in i.path), key=lambda i: i.path)
        for image in found:
            print(describe(image, done))
        print(f"{len(found)} fichiers, {sum(i.rel in done for i in found)} faits.")
    elif command == "orphelins":
        known = {i.rel for i in images.values()}
        orphans = sorted(done - known)
        print("\n".join(orphans) or "Aucun.")
        print(f"{len(orphans)} images du mod non utilisées par le jeu.")
    else:
        path, n, total = report(mod, images, done)
        print(f"{path.relative_to(ROOT)} : {n} / {total} fichiers remplacés ({pct(n, total)}).")


if __name__ == "__main__":
    main(sys.argv[1:])
