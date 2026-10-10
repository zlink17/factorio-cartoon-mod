#!/usr/bin/env python3
"""Pilote Factorio (Windows) depuis WSL, dans une instance isolée.

L'instance utilise sa propre configuration, son propre dossier d'écriture et son propre dossier de mods
(dans le Temp de Windows) : elle ne touche ni aux parties, ni aux mods, ni à la config du joueur,
et peut tourner pendant que le jeu est ouvert.

Chemins réglables par variables d'environnement :
  FACTORIO_DIR   dossier d'installation (défaut : Steam)
  FACTORIO_WORK  dossier de travail de l'instance isolée, côté WSL (défaut : Temp de Windows)
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTORIO_DIR = Path(os.environ.get("FACTORIO_DIR", "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio"))
DATA = FACTORIO_DIR / "data"
EXE = FACTORIO_DIR / "bin" / "x64" / "factorio.exe"
WORK = Path(os.environ.get("FACTORIO_WORK", "/mnt/c/Users/zlink/AppData/Local/Temp/factorio-cartoon-tools"))
CACHE = ROOT / ".cache"

# Jeux fournis avec Factorio (base et extensions officielles), tous activés dans l'instance isolée.
OFFICIAL = ["base", "elevated-rails", "quality", "space-age"]


def winpath(path):
    """Chemin WSL -> chemin Windows (C:\\...)."""
    return subprocess.run(["wslpath", "-w", str(path)], capture_output=True, text=True, check=True).stdout.strip()


def prepare(mods=()):
    """Crée l'instance isolée avec les jeux officiels et les mods donnés (noms déjà installés dans WORK/mods)."""
    (WORK / "mods").mkdir(parents=True, exist_ok=True)
    (WORK / "write").mkdir(parents=True, exist_ok=True)
    (WORK / "config.ini").write_text(
        "[path]\nread-data=__PATH__executable__/../../data\n"
        f"write-data={winpath(WORK / 'write')}\n", encoding="utf-8")
    mod_list = [{"name": name, "enabled": True} for name in [*OFFICIAL, *mods]]
    (WORK / "mods" / "mod-list.json").write_text(json.dumps({"mods": mod_list}, indent=2), encoding="utf-8")


def run(*args, mods=(), timeout=600):
    """Lance factorio.exe dans l'instance isolée ; renvoie le processus terminé (sortie texte)."""
    prepare(mods)
    cmd = [str(EXE), "--config", winpath(WORK / "config.ini"), "--mod-directory", winpath(WORK / "mods"), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd="/tmp")


def log_errors():
    """Lignes d'erreur du dernier journal de l'instance isolée."""
    log = WORK / "write" / "factorio-current.log"
    if not log.exists():
        return []
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    return [line for line in lines if "Error" in line or "error" in line.split(":", 1)[0]]


def dump(mods=()):
    """Lance --dump-data avec les mods donnés ; renvoie le chemin du data-raw-dump.json produit (lève si échec)."""
    produced = WORK / "write" / "script-output" / "data-raw-dump.json"
    produced.unlink(missing_ok=True)
    result = run("--dump-data", mods=mods)
    if result.returncode != 0 or not produced.exists():
        raise RuntimeError("factorio --dump-data a échoué :\n" + result.stdout[-3000:])
    return produced


def install(mod):
    """Installe <mod>/mod du repo dans l'instance isolée ; renvoie le nom du mod (info.json)."""
    subprocess.run([str(ROOT / "tools" / "install_mod.sh"), mod, str(WORK / "mods")], check=True,
                   capture_output=True)
    return json.loads((ROOT / mod / "mod" / "info.json").read_text(encoding="utf-8"))["name"]


def dump_data(refresh=False):
    """Chemin de data-raw-dump.json du jeu d'origine (base, Space Age, qualité, rails surélevés), mis en cache."""
    target = CACHE / "data-raw-dump.json"
    version = (DATA / "base" / "info.json").read_text(encoding="utf-8")
    stamp = CACHE / "data-raw-dump.version"
    if target.exists() and not refresh and stamp.exists() and stamp.read_text(encoding="utf-8") == version:
        return target
    produced = dump()
    CACHE.mkdir(exist_ok=True)
    shutil.copyfile(produced, target)
    stamp.write_text(version, encoding="utf-8")
    return target


if __name__ == "__main__":
    print(dump_data(refresh=True))
