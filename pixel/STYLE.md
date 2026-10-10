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
- Souterrain : capot en voûte de 14 px de large sur 13 de long, d'après les souterrains de Factorio. Entrée et sortie sont des miroirs l'une de l'autre : un bout fermé (mur plein à rivets) du côté enterré, une bouche ouverte du côté du tapis (tunnel qui s'assombrit avec le chevron du tapis qui entre ou qui sort), entre les deux une voûte à plaque de la teinte vive du convoyeur du même niveau et chevrons foncés. Face avant sombre de 3 px et ombre portée. **[PROVISOIRE, à juger en jeu]**
- Répartiteur : poteaux d'extrémité, cloison avec nez diviseur côté entrée, rail à trois engrenages (acier, moyeu orange) qui tournent, capots à chevrons de la couleur du niveau côté sortie, deux voyants qui clignotent en alternance. **[PROVISOIRE]**
