#!/usr/bin/env python3
"""Contrôle du scénario « galerie » (mod cartoon-galerie) : le lance dans l'instance isolée et capture chaque zone.

Usage : python tools/galerie.py [--origine] [--delai SECONDES]

Installe cartoon-galerie, le mod cartoon (sauf avec --origine) et le banc d'essai (dont la présence déclenche les
captures) dans l'instance isolée (tools/factorio.py), lance le scénario et attend « fini.txt ».
Captures dans .cache/galerie/<cartoon|origine>/ : une image par zone et « ensemble.png » (vue générale) ;
journal.txt liste les entités impossibles à créer.

Pour jouer la galerie dans son propre jeu : tools/install_mod.sh cartoon-galerie, puis Jeu solo > Scénarios.
"""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench  # noqa: E402
import factorio  # noqa: E402

ROOT = factorio.ROOT
GALERIE = ROOT / "cartoon-galerie" / "mod"


def check_lua():
    import lupa.lua52
    compile_ = lupa.lua52.LuaRuntime().eval("function(src, name) local f, err = load(src, name) return err end")
    errors = [e for e in (compile_(p.read_text(encoding="utf-8"), p.name) for p in sorted(GALERIE.rglob("*.lua"))) if e]
    if errors:
        raise SystemExit("Erreur de syntaxe Lua :\n" + "\n".join(errors))


def main(argv):
    variant = "origine" if "--origine" in argv else "cartoon"
    timeout = int(argv[argv.index("--delai") + 1]) if "--delai" in argv else 300
    check_lua()
    mods = [factorio.install("cartoon-galerie"), bench.install_bench()]
    if variant == "cartoon":
        mods.append(factorio.install("cartoon"))
    produced = factorio.WORK / "write" / "script-output" / "galerie" / variant
    shutil.rmtree(produced, ignore_errors=True)
    factorio.stop()
    (factorio.WORK / "write" / "factorio-current.log").unlink(missing_ok=True)
    print(f"[{variant}] lancement de Factorio...", flush=True)
    factorio.start("--load-scenario", f"{mods[0]}/galerie", "--disable-audio", "--window-size", "1280x720", mods=mods)
    start = time.time()
    try:
        while not (produced / "fini.txt").exists():
            errors = factorio.log_errors() if time.time() - start > 10 else []
            if errors:
                raise RuntimeError("Erreur dans le jeu :\n" + "\n".join(errors))
            if time.time() - start > 30 and not factorio.running():
                raise RuntimeError("Factorio s'est arrêté avant la fin.")
            if time.time() - start > timeout:
                raise RuntimeError(f"Pas de captures après {timeout} s.")
            time.sleep(3)
        time.sleep(2)
    finally:
        factorio.stop()
    target = factorio.CACHE / "galerie" / variant
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(produced, target)
    print(f"[{variant}] {len(list(target.glob('*.png')))} images en {time.time() - start:.0f} s -> "
          f"{target.relative_to(ROOT)}")
    journal = (target / "journal.txt").read_text(encoding="utf-8").strip()
    print(journal or "journal vide : tout a été construit")


if __name__ == "__main__":
    main(sys.argv[1:])
