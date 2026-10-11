# Guide de style cel-shading (brouillon)

Document de référence du mod cel-shading : **tout sprite du mod doit le respecter**. Les valeurs chiffrées vivront
dans `celshading/blender/style.py` ; si on change une règle, on la change ici et dans `style.py`, dans le même commit.

Légende : **[VALIDÉ]** décidé avec Bastien, **[PROVISOIRE]** à confirmer.

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

- Contour **fin**, sur la silhouette seulement (pas sur les arêtes intérieures), de la **teinte foncée de l'objet**,
  jamais noir. **[VALIDÉ]** (épaisseur **[PROVISOIRE]**)

## 4. Palette

- Teintes de Factorio (chaque objet garde sa couleur, pour être reconnu), **plus saturées et plus claires** ; ombres
  bleu-violet. **[VALIDÉ]** (dosage **[PROVISOIRE]**)

## 5. Projection et format technique

Repris du mod cartoon ([cartoon/STYLE.md](../cartoon/STYLE.md), sections 2 et 6), car imposés par le jeu : vue à
30° alignée sur la grille, sol raccourci par cos(30°), convoyeurs et tuyaux au sol vus de dessus, ombres portées
en sprites séparés, même cadre et même emprise que l'original au pixel près, PNG RGBA. **[VALIDÉ]**

## 6. Ombres au sol

- Silhouette à bord net, moins opaque que l'original. Le jeu les dessine en noir semi-transparent : pas de teinte
  possible. **[VALIDÉ]** (opacité **[PROVISOIRE]**)

## 7. Effets

- Fumées et vapeur en boules cel-shadées qui finissent en volute ; explosions en nuages ronds ; flammes en
  langues à trois tons. **[PROVISOIRE]**
