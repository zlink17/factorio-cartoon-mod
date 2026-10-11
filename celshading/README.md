# Mod Cel-shading

Remplace les textures par une version en cel-shading, inspirée de Zelda Wind Waker : lumière et ombre à bord franc,
ombres teintées, couleurs vives, fumées en volutes. **Rien n'est encore dessiné** : le mod se charge mais ne
remplace aucune texture.

- Approche, questions de style ouvertes et feuille de route : [docs/celshading/plan.md](../docs/celshading/plan.md).
- Règles visuelles (brouillon) : [STYLE.md](STYLE.md).

## Contenu

| Chemin | Rôle |
|---|---|
| `mod/` | Le mod Factorio (`factorio-celshading-mod`) : `info.json`, `data-final-fixes.lua`, `manifest.lua`, `graphics/overrides/`. Incompatible avec les mods cartoon et pixel. |
| `lots.py` | Lots de production, lus par `tools/build.py` (vide pour l'instant). |
| `blender/` | (à venir) rendus 3D cel-shading, `style.py` et `lib.py`. |
| `terrain/` | (à venir) sols, décorations et eau en procédural 2D. |

## Commandes (depuis la racine du repo)

Les outils communs prennent le nom du dossier du mod, comme pour le mod cartoon ([cartoon/README.md](../cartoon/README.md)) :

```bash
.venv/bin/python tools/build.py celshading --liste
.venv/bin/python tools/check_mod.py celshading --jeu
.venv/bin/python tools/inventory.py celshading
tools/install_mod.sh celshading
```
