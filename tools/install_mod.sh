#!/usr/bin/env bash
# Copie un mod dans le dossier mods de Factorio (Windows, depuis WSL).
# Usage : tools/install_mod.sh [cartoon|pixel|celshading|cartoon-epure|cartoon-galerie] [dossier mods]
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
[ -d "$SRC/graphics" ] && python3 "$ROOT/tools/build_manifest.py" "$MOD"
rm -rf "$DEST"
mkdir -p "$DEST"
cp "$SRC"/info.json "$DEST"/
compgen -G "$SRC/*.lua" > /dev/null && cp "$SRC"/*.lua "$DEST"/
for dir in graphics locale migrations scenarios; do
  [ -d "$SRC/$dir" ] && cp -r "$SRC/$dir" "$DEST"/
done
# Un mod que Factorio découvre est activé d'office : un nouveau mod de textures entrerait en conflit avec celui qui
# est actif (ils sont incompatibles entre eux). On l'inscrit donc désactivé s'il n'est pas encore dans la liste ;
# ensuite, le choix du joueur (activé ou non) est conservé.
python3 - "$MODS/mod-list.json" "$NAME" <<'PY'
import json, sys
path, name = sys.argv[1:]
try:
    data = json.load(open(path, encoding="utf-8"))
except FileNotFoundError:
    sys.exit()
if all(m["name"] != name for m in data["mods"]):
    data["mods"].append({"name": name, "enabled": False})
    json.dump(data, open(path, "w", encoding="utf-8"), indent=2)
    print(f"{name} inscrit désactivé dans mod-list.json (à activer dans le menu Mods)")
PY
echo "Installé dans $DEST"
