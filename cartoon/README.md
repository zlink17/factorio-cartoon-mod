# Mod Cartoon

Remplace les textures par une version cartoon : aplats de couleur, gros contours noir chaud, ombrage à trois tons.
**Toutes les règles visuelles sont dans [STYLE.md](STYLE.md)** (à respecter pour tout sprite).

## Contenu

| Dossier | Rôle |
|---|---|
| `mod/` | Le mod Factorio (`info.json`, `data-final-fixes.lua`, `manifest.lua`, `graphics/overrides/`). |
| `blender/` | Rendus 3D toon avec `bpy` : technique principale. Valeurs du style dans `blender/style.py`. |
| `ai/` | Génération par IA (ComfyUI, SD 1.5 + ControlNet). Testée sur l'assembleur 1 : n'apporte rien de net par rapport à Blender, voir [ai/README.md](ai/README.md). |

## Installation de l'environnement (une fois)

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r cartoon/blender/requirements.txt
```

## Cycle de travail (depuis la racine du repo)

Un **lot** est une famille de sprites produite par un ou plusieurs générateurs ; la liste est dans [lots.py](lots.py).
La méthode complète (cadrage, prototype, production, contrôle, vérification en jeu) est dans
[docs/cartoon/plan.md](../docs/cartoon/plan.md).

```bash
# 1. cadrage : fichiers du jeu à refaire pour un lot, avec tailles, découpage et prototypes qui les utilisent
.venv/bin/python tools/inventory.py cartoon liste entity/stone-furnace

# 2. production : génère dans .cache/build/, contrôle les tailles, installe dans mod/graphics/overrides/,
#    régénère le manifeste et contrôle le mod ; affiche les fichiers nouveaux et modifiés
.venv/bin/python tools/build.py cartoon --liste
.venv/bin/python tools/build.py cartoon convoyeurs

# 3. contrôle complet, dont le chargement du mod dans une instance isolée de Factorio (peut tourner jeu ouvert)
.venv/bin/python tools/check_mod.py cartoon --jeu

# 4. vérification en jeu : captures de scènes de test (catalogue des bâtiments, convoyeurs, usine, minerais,
#    nature, sols, objets...) avec et sans le mod ; comparaisons côte à côte dans .cache/vitrine/comparaison/
#    (ouvre une fenêtre Factorio isolée ~40 s par passe ; --sans-origine réutilise les captures d'origine)
.venv/bin/python tools/bench.py cartoon --sans-origine

# 5. couverture (docs/cartoon/couverture.md), à régénérer avant de commiter un lot
.venv/bin/python tools/inventory.py cartoon

# installer le mod dans le Factorio du joueur
tools/install_mod.sh cartoon

# reproductibilité : relance des générateurs de zéro et comparaison avec le mod, sans rien installer
.venv/bin/python tools/build.py cartoon tous --verifier
```

Chaque générateur peut aussi se lancer seul : `<script> <sortie> [arguments]` écrit dans `<sortie>` l'arborescence de
`graphics/overrides` (`base/entity/<nom>/...`, `base/icons/...`, `core/...`), plus des aperçus dans `<sortie>/_apercu/`.
Exemple : `.venv/bin/python cartoon/blender/belt.py sortie/ transport-belt 4` (4 images par rangée, pour tester).
`blender/assembler.py sortie/ 0 1 2` rend une seule image d'assembleur (phase, facteur de taille, niveau).

## État

Le suivi détaillé est dans [docs/cartoon/plan.md](../docs/cartoon/plan.md) et [couverture.md](../docs/cartoon/couverture.md).


- [x] Assembleurs 1, 2 et 3 : planches animées de 32 images, ombres et icônes (à vérifier en jeu)
- [ ] Tuyaux des assembleurs 2 et 3 (`-pipe-N/E/S/W.png`, encore ceux d'origine)
- [x] Convoyeurs jaune, rouge et bleu : droits, courbes, bouts de ligne, icônes (à vérifier en jeu)
- [x] Bras robotisés : à charbon, de base, à longue portée, rapide, en vrac (à vérifier en jeu)
- [x] Souterrains et répartiteurs, trois niveaux (à vérifier en jeu : capot, ordre des directions, pièces « patch » des souterrains vides)
- [x] Convoyeur turbo (Space Age) : convoyeur, souterrain, répartiteur (le patch « gelé » d'Aquilo reste d'origine)
- [x] Pylônes (poteau, poteau moyen, pylône, sous-station) et câbles ; les points d'attache des câbles tombent sur ceux de l'original
- [ ] Chargeurs (loaders), lecteur de convoyeur, paratonnerre
- [x] Minerais : fer, cuivre, charbon, pierre, uranium (gisements et icônes)
- [x] Sols de Nauvis (herbe, terre, sable, désert rouge)
- [ ] Fours, personnage
- [ ] Icônes et interface (GUI)
