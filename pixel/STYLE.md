# Guide de style pixel art

Référence pour tout sprite du mod pixel. Les couleurs vivent dans `pillow/palette.py` (source de vérité).
**[VALIDÉ]** décidé avec Bastien, **[PROVISOIRE]** à confirmer en jeu.

## Direction artistique
- Pixel art net façon *Link's Awakening* / *Minish Cap* (image de référence : krank.love) : couleurs vives, formes franches, peu de détails fins. **[VALIDÉ]**
- Les formes, proportions et couleurs par niveau restent celles de Factorio (assembleur 1 gris-vert, 2 bleu, 3 olive). **[VALIDÉ]**
- On ajoute des éléments d'assemblage inspirés de Factorio sur le dessus : engrenages, pistons et vérins, moteur, bras articulés. **[VALIDÉ]**

## Résolution
- **16 px par case**, dessinés en code (Pillow, sans anti-aliasing), exportés **x4** (64 px par case) puis affichés avec `scale = 0.5` : 1 px d'art = 2 px de jeu. **[VALIDÉ]**
- Un assembleur 3x3 fait environ 50 px de large en art (1 px de débord de chaque côté de l'emprise). **[PROVISOIRE]**

## Projection
- Vue ~30° : dessus du rebord clair, mur arrière intérieur visible, paroi avant évasée, **flancs gauche et droit visibles** qui s'évasent vers le bas (≈ 4 px de chaque côté). **[VALIDÉ]**
- Chaque objet posé a un dessus clair, une face avant plus sombre et une ombre au sol en aplat. **[VALIDÉ]**

## Couleurs et ombrage
- **Jamais de noir pur** : contours = teinte très sombre de l'objet (contour coloré). **[VALIDÉ]**
- Lumière en haut à gauche, ombre en bas à droite ; dessus = ton clair, face avant = ton moyen, côté droit = ton sombre. **[VALIDÉ]**
- Ombres glissant vers le bleu/violet, lumières vers le jaune/cyan. Reflets blancs : 1 à 2 px par objet au maximum.
- Tramage (damier 1 px) pour la rouille, les grilles et les reflets de vitre. **[VALIDÉ]**
- Ombre portée au sol : sprite séparé, un par image d'animation. **[VALIDÉ]**

## Animation
- 32 images par boucle, planche 8 x 4 comme l'original. Tout mouvement doit se refermer : engrenages à nombre entier de dents par boucle (2), pistons et bras en sinus. **[VALIDÉ]**
- Voyant du moteur qui clignote : indique visuellement que la machine travaille. **[PROVISOIRE]**

## Structures de convoyeurs
- Souterrain : mêmes conventions que le mod cartoon (vérifiées en jeu). Le capot couvre la moitié aval de la case pour une entrée et la moitié amont pour une sortie ; la cellule « sortie » d'une colonne contient le capot de la direction opposée ; rangées 2 et 3 = copies des rangées 0 et 1 pour l'est et l'ouest ; pièces « patch » inchangées. Voûte à plaque de la teinte vive du convoyeur du même niveau et chevrons foncés, bouche (linteau, ouverture sombre visible quand elle regarde le sud) côté tapis, bout enterré plus bas. **[PROVISOIRE, à juger en jeu]**
- Bouts de ligne des convoyeurs (rangées 12 à 19 de la planche) : bande de tapis au bord aval de la case avec un rouleau d'acier qui dépasse de 2 px. Les chevrons avancent dans le sens du flux ; rangées paires (12, 14, 16, 18) animées, impaires fixes. **[VALIDÉ par le mod cartoon]**
- Répartiteur : poteaux d'extrémité, cloison avec nez diviseur côté entrée, rail à trois engrenages (acier, moyeu orange) qui tournent, capots à chevrons de la couleur du niveau côté sortie, deux voyants qui clignotent en alternance. **[PROVISOIRE]**
