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
import re
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
    # Factorio active tout mod présent dans le dossier mais absent de la liste : on désactive donc explicitement
    # les mods installés (mod cartoon, mod pixel, banc d'essai) qui ne sont pas demandés.
    installed = {re.sub(r"_\d+\.\d+\.\d+(\.zip)?$", "", p.name) for p in (WORK / "mods").iterdir()
                 if p.is_dir() or p.suffix == ".zip"}
    wanted = [*OFFICIAL, *mods]
    mod_list = [{"name": name, "enabled": True} for name in wanted]
    mod_list += [{"name": name, "enabled": False} for name in sorted(installed - set(wanted))]
    (WORK / "mods" / "mod-list.json").write_text(json.dumps({"mods": mod_list}, indent=2), encoding="utf-8")


def run(*args, mods=(), timeout=600):
    """Lance factorio.exe dans l'instance isolée ; renvoie le processus terminé (sortie texte)."""
    prepare(mods)
    cmd = [str(EXE), "--config", winpath(WORK / "config.ini"), "--mod-directory", winpath(WORK / "mods"), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd="/tmp")


def no_steam_relaunch():
    """Lancé hors de Steam, le jeu se fait relancer par Steam, qui demande de confirmer les arguments (dialogue
    « Lancer le jeu avec des arguments personnalisés »). Un steam_appid.txt à côté de l'exécutable l'évite : le jeu
    démarre directement (Steam doit être ouvert), à condition de le lancer depuis son dossier. Sans effet sur un lancement normal depuis Steam ; une vérification
    des fichiers du jeu par Steam peut le supprimer, on le recrée donc à chaque lancement."""
    appid = EXE.parent / "steam_appid.txt"
    if not appid.exists():
        appid.write_text("427520", encoding="ascii")


def start(*args, mods=()):
    """Lance factorio.exe (avec fenêtre) dans l'instance isolée, sans attendre ; voir stop()."""
    no_steam_relaunch()
    prepare(mods)
    cmd = [str(EXE), "--config", winpath(WORK / "config.ini"), "--mod-directory", winpath(WORK / "mods"), *args]
    # Steam cherche steam_appid.txt dans le dossier courant (d'où cwd), et considère comme lancé par lui un processus
    # qui a SteamAppId / SteamGameId dans son environnement (transmis à Windows par WSLENV)
    env = dict(os.environ, SteamAppId="427520", SteamGameId="427520",
               WSLENV=":".join(filter(None, [os.environ.get("WSLENV"), "SteamAppId", "SteamGameId"])))
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=EXE.parent, env=env)


def running():
    """Vrai si une instance isolée tourne (sans steam_appid.txt, Steam relance le jeu et le processus lancé par
    start() ne la suit pas : on cherche donc l'instance par sa ligne de commande)."""
    marker = winpath(WORK / "config.ini").replace("'", "''")
    script = ("@(Get-CimInstance Win32_Process -Filter \"Name='factorio.exe'\" | "
              f"Where-Object {{ $_.CommandLine -like '*{marker}*' }}).Count")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True,
                         cwd="/tmp").stdout.strip()
    return out not in ("", "0")


def stop():
    """Ferme les instances isolées (reconnues à leur config), jamais le jeu du joueur."""
    marker = winpath(WORK / "config.ini").replace("'", "''")
    script = ("Get-CimInstance Win32_Process -Filter \"Name='factorio.exe'\" | "
              f"Where-Object {{ $_.CommandLine -like '*{marker}*' }} | "
              "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, cwd="/tmp")


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
