# Mod Cartoon

Remplace les textures par une version cartoon : aplats de couleur, gros contours noir chaud, ombrage à trois tons.
**Toutes les règles visuelles sont dans [STYLE.md](STYLE.md)** (à respecter pour tout sprite).

## Contenu

| Dossier | Rôle |
|---|---|
| `mod/` | Le mod Factorio (`info.json`, `data-final-fixes.lua`, `manifest.lua`, `graphics/overrides/`). |
| `blender/` | Rendus 3D toon avec `bpy` : technique principale. Valeurs du style dans `blender/style.py`. |
| `ai/` | Génération par IA (ComfyUI, SD 1.5 + ControlNet). Testée sur l'assembleur 1 : n'apporte rien de net par rapport à Blender, voir [ai/README.md](ai/README.md). |

## Génération (depuis la racine du repo, avec le `.venv`)

```bash
# une image d'un assembleur : sortie, phase 0..1, facteur de taille, niveau 1..3
.venv/bin/python cartoon/blender/assembler.py sortie/ 0 1 2

# planche de 32 images + aperçu GIF
.venv/bin/python cartoon/blender/animate.py sortie/ 2

# ombre et icône d'un assembleur
.venv/bin/python cartoon/blender/assembler_extras.py sortie/ 2

# convoyeurs : planches (20 rangées) et icônes ; "tous" ou un nom, puis un nombre d'images max pour tester
.venv/bin/python cartoon/blender/belt.py sortie/ tous

# bras robotisés : plateformes, mains, ombres, icônes (burner, de base, longue portée, rapide, en vrac)
.venv/bin/python cartoon/blender/inserter.py sortie/ tous

# souterrains et répartiteurs (trois niveaux chacun)
.venv/bin/python cartoon/blender/underground.py sortie/ tous
.venv/bin/python cartoon/blender/splitter.py sortie/ tous

# pylônes électriques (4 modèles) et câbles ; le convoyeur turbo (Space Age) est dans belt.py, underground.py et splitter.py
.venv/bin/python cartoon/blender/pole.py sortie/ tous

# contrôle : chaque sprite du mod doit avoir la taille de l'original, sinon Factorio ne démarre pas
.venv/bin/python tools/check_sizes.py cartoon
```

Ensuite, copier les fichiers produits dans `mod/graphics/overrides/base/...` (entité, ombre, `icons/`), puis
`tools/install_mod.sh cartoon`.

## État

- [x] Assembleurs 1, 2 et 3 : planches animées de 32 images, ombres et icônes (à vérifier en jeu)
- [ ] Tuyaux des assembleurs 2 et 3 (`-pipe-N/E/S/W.png`, encore ceux d'origine)
- [x] Convoyeurs jaune, rouge et bleu : droits, courbes, bouts de ligne, icônes (à vérifier en jeu)
- [x] Bras robotisés : à charbon, de base, à longue portée, rapide, en vrac (à vérifier en jeu)
- [x] Souterrains et répartiteurs, trois niveaux (à vérifier en jeu : capot, ordre des directions, pièces « patch » des souterrains vides)
- [x] Convoyeur turbo (Space Age) : convoyeur, souterrain, répartiteur (le patch « gelé » d'Aquilo reste d'origine)
- [x] Pylônes (poteau, poteau moyen, pylône, sous-station) et câbles ; les points d'attache des câbles tombent sur ceux de l'original
- [ ] Chargeurs (loaders), lecteur de convoyeur, paratonnerre
- [ ] Fours, personnage, minerais
- [ ] Icônes et interface (GUI)
