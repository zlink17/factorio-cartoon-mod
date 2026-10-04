# Approche complexe : assets refaits par IA

Les sprites sont regénérés par un modèle d'image (Gemini) à partir de l'original, puis remis au bon format.
Ils sont rangés dans `graphics/overrides/` et **ont la priorité** sur ceux de l'approche simple.

## Workflow

1. Générer une planche de référence du style (voir `style_guide.md`) et la garder pour toutes les générations.
2. Pour chaque sprite : envoyer l'original + la planche de référence + le prompt de `style_guide.md`.
3. Sauvegarder l'image obtenue, puis la préparer :
   ```bash
   python tools/complex/postprocess.py --input sortie.png \
     --reference "<data>/base/graphics/entity/foo/foo.png" \
     --mod base --path entity/foo/foo.png
   ```
4. Le script détoure le fond, redimensionne à la taille exacte et met à jour `manifest.lua`.
5. Commit de `graphics/overrides/` (ces fichiers sont versionnés, contrairement à `graphics/generated/`).

## Limites connues

- Les planches d'animation (plusieurs frames dans un PNG) sont à générer frame par frame ou à traiter à part.
- Le détourage par couleur de fond demande un fond uni dans le prompt.
- Garder la même planche de référence pour que le style reste cohérent.

## Priorités de remplacement

Les assets les plus visibles d'abord : assembleurs, convoyeurs, bras robotiques, fours, personnage, minerais.
