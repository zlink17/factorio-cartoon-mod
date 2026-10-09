# Mod Pixel

Remplace les textures par une version en pixel art, dessinée en code avec Pillow.
Palette partagée dans `pillow/palette.py` : jamais de noir pur, ombres vers le bleu/violet, lumières vers le jaune/cyan.

## Contenu

| Dossier | Rôle |
|---|---|
| `mod/` | Le mod Factorio (`info.json`, `data-final-fixes.lua`, `manifest.lua`, `graphics/overrides/`). Assembleurs 1 à 3 installés (planches, ombres, icônes), régénérés par `pillow/export_mod.py`. |
| `pillow/` | Sprites dessinés en code. `assembler.py` : assembleur 3×3 à 16 px par case, agrandi ×4, avec animation. |

## Génération

```bash
.venv/bin/python pixel/pillow/assembler.py sortie/ 2  # niveau 1..3 ; assembler.png, _hr, _shadow, preview.png, anim.png, anim.gif, assembler_sheet(.png|_hr.png) = planche 8x4 de 32 images
```

Export vers le mod puis installation (désactiver le mod cartoon dans le jeu : les deux remplacent les mêmes textures) :

```bash
.venv/bin/python pixel/pillow/export_mod.py
tools/install_mod.sh pixel
```

## État

Essai d'assembleur uniquement, 3 niveaux aux couleurs de Factorio (gris-vert, bleu, olive). Pas encore calé sur le cadre de l'original (214 × 226 px, 32 images, 64 px par case)
ni installé dans `mod/graphics/overrides/`. Le style (STYLE.md) du mod pixel reste à écrire.
