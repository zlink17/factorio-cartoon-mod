# Mod Pixel

Remplace les textures de Factorio par du pixel art. **Repart de zéro le 11 octobre 2026** : l'ancien travail
(97 images dessinées en code avec Pillow) est abandonné, son code reste dans l'historique git (commit `5e33219`).

- Méthode et plan : [docs/pixel/plan.md](../docs/pixel/plan.md)
- Pièges techniques déjà rencontrés : [docs/pixel/synthese-pixel.md](../docs/pixel/synthese-pixel.md)
- Guide de style : [STYLE.md](STYLE.md)

## Contenu

| Chemin | Rôle |
|---|---|
| `mod/` | Le mod Factorio : `info.json`, `data-final-fixes.lua` (remplacement des chemins listés dans `manifest.lua`, densité des décorations), `settings.lua` (densités par famille, 10 % par défaut), `control.lua` (commande `/pixel-decorations`), `graphics/overrides/` |
| `lots.py` | Les lots de sprites et leurs générateurs (lu par `tools/build.py`) |

## Commandes

```bash
.venv/bin/python tools/build.py pixel <lot>        # produit un lot, l'installe dans mod/, contrôle
.venv/bin/python tools/check_mod.py pixel --jeu    # contrôle complet et test de chargement
tools/install_mod.sh pixel                         # copie le mod dans le jeu de Bastien
```

Le mod est incompatible avec les mods cartoon et cel-shading (mêmes textures) : n'en activer qu'un.
