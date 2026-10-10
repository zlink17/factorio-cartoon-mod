#!/usr/bin/env python3
"""Banc d'essai en jeu : captures de scènes de test, avec et sans le mod, et comparaisons côte à côte.

Usage : python tools/bench.py [cartoon] [--sans-origine] [--delai SECONDES]

Lance Factorio (avec fenêtre) dans une instance isolée (tools/factorio.py) sur le scénario « vitrine » du mod de
test tools/bench/mod : il construit les scènes (catalogue des bâtiments dans les 4 directions, convoyeurs chargés,
usine alimentée, minerais, nature, falaises, décorations, sols, objets, monde généré), les capture et s'arrête.

Résultats dans .cache/vitrine/ :
  origine/<scène>.png   jeu d'origine (refait seulement si absent ou si on ne passe pas --sans-origine)
  <mod>/<scène>.png     avec le mod
  comparaison/<scène>.png   origine à gauche (ou en haut), mod à droite (ou en bas)
Le journal du scénario (entités impossibles à créer...) est dans <variante>/journal.txt.
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import factorio  # noqa: E402

ROOT = factorio.ROOT
BENCH = ROOT / "tools" / "bench" / "mod"
OUT = factorio.CACHE / "vitrine"


def install_bench():
    info = json.loads((BENCH / "info.json").read_text(encoding="utf-8"))
    dest = factorio.WORK / "mods" / f"{info['name']}_{info['version']}"
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(BENCH, dest)
    return info["name"]


def check_lua():
    """Compile les scripts Lua du banc avec Lua 5.2 (celui de Factorio : pas de `//`, pas de `goto` en 5.1...)."""
    import lupa.lua52
    compile_ = lupa.lua52.LuaRuntime().eval("function(src, name) local f, err = load(src, name) return err end")
    errors = [compile_(p.read_text(encoding="utf-8"), p.name) for p in sorted(BENCH.rglob("*.lua"))]
    errors = [e for e in errors if e]
    if errors:
        raise SystemExit("Erreur de syntaxe Lua :\n" + "\n".join(errors))


def capture(variant, mods, timeout):
    """Lance la vitrine avec ces mods ; copie les captures dans OUT/<variant>/."""
    produced = factorio.WORK / "write" / "script-output" / "vitrine" / variant
    shutil.rmtree(produced, ignore_errors=True)
    bench = install_bench()
    factorio.stop()
    (factorio.WORK / "write" / "factorio-current.log").unlink(missing_ok=True)   # sinon on relirait l'ancien
    print(f"[{variant}] lancement de Factorio...", flush=True)
    factorio.start("--load-scenario", f"{bench}/vitrine", "--disable-audio", "--window-size", "1280x720",
                          mods=[bench, *mods])
    start = time.time()
    try:
        while not (produced / "fini.txt").exists():
            errors = factorio.log_errors() if time.time() - start > 10 else []
            if errors:
                raise RuntimeError("Erreur dans le jeu :\n" + "\n".join(errors))
            if time.time() - start > 30 and not factorio.running():
                raise RuntimeError("Factorio s'est arrêté avant la fin. Journal :\n" + "\n".join(factorio.log_errors()))
            if time.time() - start > timeout:
                raise RuntimeError(f"Pas de captures après {timeout} s.")
            time.sleep(3)
    finally:
        factorio.stop()
    target = OUT / variant
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(produced, target)
    shots = sorted(target.glob("*.png"))
    print(f"[{variant}] {len(shots)} images en {time.time() - start:.0f} s -> {target.relative_to(ROOT)}")
    journal = (target / "journal.txt").read_text(encoding="utf-8").strip()
    if journal:
        print(f"[{variant}] journal du scénario : {len(journal.splitlines())} lignes (voir journal.txt)")
    return shots


def pair(a, b):
    """Origine et mod côte à côte (portrait ou carré) ou l'un sous l'autre (paysage), séparés par 8 px."""
    from PIL import Image
    side = a.width <= a.height * 1.2
    size = (a.width + b.width + 8, max(a.height, b.height)) if side else (max(a.width, b.width), a.height + b.height + 8)
    canvas = Image.new("RGB", size, (20, 20, 20))
    canvas.paste(a.convert("RGB"), (0, 0))
    canvas.paste(b.convert("RGB"), (a.width + 8, 0) if side else (0, a.height + 8))
    return canvas


def compare(variant):
    """Une image par capture fixe, un GIF par capture animée (<nom>-f00.png, -f01.png...)."""
    from PIL import Image
    out = OUT / "comparaison"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    animations = {}
    for shot in sorted((OUT / variant).glob("*.png")):
        orig = OUT / "origine" / shot.name
        if not orig.exists():
            continue
        m = re.fullmatch(r"(.+)-f(\d+)\.png", shot.name)
        if m:
            animations.setdefault(m.group(1), []).append((orig, shot))
        else:
            pair(Image.open(orig), Image.open(shot)).save(out / shot.name)
    for name, frames in animations.items():
        images = [pair(Image.open(a), Image.open(b)) for a, b in frames]
        images[0].save(out / f"{name}.gif", save_all=True, append_images=images[1:], duration=100, loop=0)
    print(f"Comparaisons dans {out.relative_to(ROOT)} ({len(animations)} animations)")


def main(argv):
    mod = next((a for a in argv if not a.startswith("-") and (ROOT / a / "mod").is_dir()), "cartoon")
    timeout = int(argv[argv.index("--delai") + 1]) if "--delai" in argv else 600
    check_lua()
    if "--sans-origine" not in argv or not (OUT / "origine").exists():
        capture("origine", [], timeout)
    name = factorio.install(mod)
    capture(mod, [name], timeout)
    compare(mod)


if __name__ == "__main__":
    main(sys.argv[1:])
