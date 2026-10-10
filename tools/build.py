#!/usr/bin/env python3
"""Produit un lot de sprites et l'installe dans le mod.

Usage :
  python tools/build.py [cartoon] LOT... [--verifier]     LOT : nom de <mod>/lots.py, ou « tous »
  python tools/build.py [cartoon] --liste                 liste des lots

Étapes : chaque commande du lot écrit dans .cache/build/<mod>/<lot>/ (arborescence de graphics/overrides) ;
contrôle des tailles par rapport aux originaux ; comparaison avec les fichiers déjà dans le mod (nouveaux,
modifiés, identiques) ; puis copie dans <mod>/mod/graphics/overrides/, manifeste régénéré, contrôle complet.

--verifier : n'installe rien, signale seulement les différences avec le mod (test de reproductibilité :
un générateur relancé de zéro doit redonner les fichiers du mod). Code de sortie 1 s'il y en a.
"""
import importlib.util
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_manifest  # noqa: E402
import check_mod  # noqa: E402
import factorio  # noqa: E402

ROOT = factorio.ROOT
PYTHON = ROOT / ".venv" / "bin" / "python"
GAMES = ("base", "core", "space-age", "quality", "elevated-rails")
TOLERANCE = 3            # écart max par canal toléré entre deux rendus (bruit d'échantillonnage)


def load_lots(mod):
    spec = importlib.util.spec_from_file_location("lots", ROOT / mod / "lots.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LOTS


def produced_files(out):
    """Fichiers produits, par chemin relatif à graphics/overrides (les dossiers d'aperçu sont ignorés)."""
    return {p.relative_to(out).as_posix(): p for game in GAMES if (out / game).is_dir()
            for p in sorted((out / game).rglob("*.png"))}


def same_image(a, b):
    import cv2
    import numpy as np
    ia, ib = cv2.imread(str(a), cv2.IMREAD_UNCHANGED), cv2.imread(str(b), cv2.IMREAD_UNCHANGED)
    if ia is None or ib is None or ia.shape != ib.shape:
        return False
    return int(np.abs(ia.astype(np.int16) - ib.astype(np.int16)).max()) <= TOLERANCE


def build_lot(mod, lot, commands, verify):
    out = factorio.CACHE / "build" / mod / lot
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    start = time.time()
    for script, args in commands:
        print(f"[{lot}] {script} {' '.join(args)}", flush=True)
        result = subprocess.run([str(PYTHON), str(ROOT / mod / script), str(out), *args], cwd=ROOT,
                                capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout[-2000:], result.stderr[-3000:], sep="\n")
            raise SystemExit(f"[{lot}] échec de {script}")
    files = produced_files(out)
    overrides = ROOT / mod / "mod" / "graphics" / "overrides"
    errors, new, changed, same = [], [], [], []
    for rel, path in files.items():
        game, _, rest = rel.partition("/")
        orig = factorio.DATA / game / "graphics" / rest
        if not orig.exists():
            errors.append(f"ABSENT de l'original : {rel}")
        elif check_mod.png_header(path)[:2] != check_mod.png_header(orig)[:2]:
            errors.append(f"TAILLE {check_mod.png_header(path)[:2]} au lieu de {check_mod.png_header(orig)[:2]} : {rel}")
        current = overrides / rel
        (same if current.exists() and same_image(path, current) else changed if current.exists() else new).append(rel)
    minutes = (time.time() - start) / 60
    print(f"[{lot}] {len(files)} fichiers en {minutes:.1f} min : {len(new)} nouveaux, {len(changed)} modifiés, "
          f"{len(same)} identiques.")
    for rel in new:
        print(f"  nouveau  : {rel}")
    for rel in changed:
        print(f"  modifié  : {rel}")
    if errors:
        print("\n".join(errors))
        raise SystemExit(f"[{lot}] fichiers refusés, rien n'est installé.")
    if not verify:
        for rel in new + changed:
            dest = overrides / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(files[rel], dest)
    return new, changed


def main(argv):
    verify = "--verifier" in argv
    args = [a for a in argv if not a.startswith("--")]
    mod = args.pop(0) if args and (ROOT / args[0] / "lots.py").exists() else "cartoon"
    lots = load_lots(mod)
    if "--liste" in argv or not args:
        for name, commands in lots.items():
            print(f"{name:<14} " + " ; ".join(f"{s} {' '.join(a)}" for s, a in commands))
        return
    names = list(lots) if args == ["tous"] else args
    unknown = [n for n in names if n not in lots]
    if unknown:
        raise SystemExit(f"Lots inconnus : {', '.join(unknown)} (voir --liste)")
    differences = 0
    for name in names:
        new, changed = build_lot(mod, name, lots[name], verify)
        differences += len(new) + len(changed)
    if verify:
        print("Reproductible." if not differences else f"{differences} fichiers diffèrent du mod.")
        sys.exit(1 if differences else 0)
    entries = build_manifest.build_manifest(mod)
    files, errors = check_mod.check_files(mod)
    print(f"Manifeste : {len(entries)} sprites ; contrôle : {len(errors)} problèmes.")
    print("\n".join(errors))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
