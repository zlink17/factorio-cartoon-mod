# Guide de style cel-shading (brouillon)

Document de référence du mod cel-shading : **tout sprite du mod doit le respecter**. Les valeurs chiffrées vivront
dans `celshading/blender/style.py` ; si on change une règle, on la change ici et dans `style.py`, dans le même commit.

Légende : **[VALIDÉ]** décidé avec Bastien, **[PROVISOIRE]** à confirmer, **[À DÉCIDER]** question ouverte
(voir [docs/celshading/plan.md](../docs/celshading/plan.md), section 4).

## 1. Direction artistique

- Inspiration : Zelda Wind Waker. Cel-shading, couleurs vives et ensoleillées, formes rondes et trapues. **[VALIDÉ]**
- On garde les formes, proportions et la lisibilité de l'original : chaque machine se reconnaît au premier coup
  d'œil (même règle que le mod cartoon). **[PROVISOIRE]**
- Pas de dégradé, de bruit ni de texture réaliste. Les motifs peints en aplats (planches, pierres, rivets) sont
  permis. **[PROVISOIRE]**

## 2. Lumière et ombrage

- Une seule lumière, de haut à gauche, cohérente avec les ombres du jeu (portées vers la droite). **[PROVISOIRE]**
- Deux tons par couleur : éclairé et ombre, à frontière nette qui suit la forme, ombres portées sur l'objet
  lui-même. Troisième ton clair facultatif pour un reflet sur le métal. **[PROVISOIRE]**
- Ombre teintée bleu-violet (multiplication), jamais grise ni noire. **[PROVISOIRE]**

## 3. Contours

- **[À DÉCIDER]** aucun, contour fin de silhouette teinté (recommandé), ou noir chaud.

## 4. Palette

- **[À DÉCIDER]** teintes de Factorio, palette Wind Waker, ou teintes de Factorio saturées et éclaircies (recommandé).

## 5. Projection et format technique

Repris du mod cartoon ([cartoon/STYLE.md](../cartoon/STYLE.md), sections 2 et 6), car imposés par le jeu : vue à
30° alignée sur la grille, sol raccourci par cos(30°), convoyeurs et tuyaux au sol vus de dessus, ombres portées
en sprites séparés, même cadre et même emprise que l'original au pixel près, PNG RGBA. **[VALIDÉ]**

## 6. Ombres au sol

- **[À DÉCIDER]** celles du jeu, ou silhouette à bord net moins opaque (recommandé). Le jeu les dessine en noir
  semi-transparent : pas de teinte possible.

## 7. Effets

- Fumées et vapeur en boules cel-shadées qui finissent en volute ; explosions en nuages ronds ; flammes en
  langues à trois tons. **[PROVISOIRE]**
