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

## Automatiser avec ComfyUI (`comfy_batch.py`)

`comfy_batch.py` parle à l'API HTTP d'un ComfyUI local (port 8188 par défaut) et rejoue un workflow
sur chaque image d'un dossier. Il n'a **aucune dépendance** (bibliothèque standard de Python).

1. **Construire le workflow dans l'interface** : charger une image (`Load Image`), un modèle SD 1.5
   de style cartoon (`Load Checkpoint`), un ControlNet de contours ou de lineart, puis un échantillonneur
   en img2img (débruitage autour de 0,5 à 0,6 pour garder la forme). Sur une GTX 1660, lancer ComfyUI avec
   `--force-fp32` (sinon les images peuvent sortir noires).
2. **Exporter** : menu Workflow > Export (API) → `workflow_api.json`. Ce n'est pas le même fichier que
   l'enregistrement normal : le script refuse un workflow « interface ».
3. **Lancer** (ComfyUI ouvert) :
   ```powershell
   py tools\complex\comfy_batch.py --workflow workflow_api.json --input entrees\ --output sorties\ `
       --seeds 4 --prompt "cartoon game sprite, thick dark outline, flat colors"
   ```
   `--seeds 4` produit 4 variantes par image. `--dry-run` affiche le workflow modifié sans l'envoyer.
4. **Mettre au format** les résultats retenus avec `postprocess.py` (détourage, taille exacte).

Le script retrouve seul le nœud d'image, la graine et les prompts (en suivant les liens du `KSampler`).
Si ton workflow est atypique, précise `--image-node`, `--positive-node` ou `--negative-node`.

`test_comfy_batch.py` vérifie la logique contre un faux serveur. **Il n'a jamais tourné contre un vrai
ComfyUI** : le premier essai réel peut demander un ajustement.
