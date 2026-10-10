#!/usr/bin/env bash
# Copie un mod dans le dossier mods de Factorio (Windows, depuis WSL).
# Usage : tools/install_mod.sh [cartoon|pixel] [dossier mods]
#   défaut : cartoon, AppData\Roaming\Factorio\mods
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MOD="${1:-cartoon}"
MODS="${2:-/mnt/c/Users/zlink/AppData/Roaming/Factorio/mods}"
SRC="$ROOT/$MOD/mod"
[ -f "$SRC/info.json" ] || { echo "Mod inconnu : $MOD (pas de $SRC/info.json)" >&2; exit 1; }
NAME="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['name'])" "$SRC/info.json")"
VERSION="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" "$SRC/info.json")"
DEST="$MODS/${NAME}_$VERSION"
python3 "$ROOT/tools/build_manifest.py" "$MOD"
rm -rf "$DEST"
mkdir -p "$DEST"
cp "$SRC"/info.json "$SRC"/data-final-fixes.lua "$SRC"/manifest.lua "$DEST"/
cp -r "$SRC/graphics" "$DEST"/
echo "Installé dans $DEST"
