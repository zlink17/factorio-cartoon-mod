# Guide de style cel-shading (brouillon)

Document de référence du mod cel-shading : **tout sprite du mod doit le respecter**. Les valeurs chiffrées vivront
dans `celshading/blender/style.py` ; si on change une règle, on la change ici et dans `style.py`, dans le même commit.

Légende : **[VALIDÉ]** décidé avec Bastien, **[PROVISOIRE]** à confirmer.

## 1. Direction artistique

- **Deux sources** (11 octobre) : **Zelda Wind Waker pour le rendu** (cel-shading, couleurs vives et ensoleillées,
  ombres bleutées) et **l'esprit de Factorio pour le fond** : industriel, steampunk, mécanique. Un peu comme **Metal
  Slug** : machines trapues, exagérées, pleines de caractère (tôles rivetées, gros boulons, tuyaux, engrenages),
  l'aspect industriel qui n'existe pas dans Zelda. **[VALIDÉ]**
- **Modèles propres au mod, refaits de zéro** (ceux du mod cartoon ne servent que d'essai du moteur). Machines
  **réinterprétées mais reconnaissables** : même emprise et mêmes repères que l'original (moteur, engrenages, bras de
  l'assembleur...), formes redessinées, arrondies, trapues, proportions un peu exagérées. **[VALIDÉ]**
- **Peu de grosses formes** : quelques volumes ronds bien lisibles (le cel-shading se lit sur les courbes ; tout
  détail de moins de 6 px disparaît à la taille du jeu). **[VALIDÉ]**
- **Méthode** : pour chaque objet, des images cibles (ComfyUI, guidées par la silhouette de l'original) ; Bastien
  choisit ou commente ; puis modèle Blender qui s'en approche. **[VALIDÉ]**
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

## 8. Ambiance : moins de sprites que l'original

- Factorio a été pensé pour des sprites très détaillés, et il lui en faut énormément (décorations, taches, petites
  plantes, variantes). Le cel-shading vit de **grandes formes lisibles** : tout reprendre surchargerait l'image.
  Pour chaque famille, on se demande d'abord **garder, alléger ou retirer ?** Les décorations ne seront
  probablement pas toutes gardées, ou en quantité réduite (réglages de démarrage du mod, comme le sous-mod
  `cartoon-epure`) ; même question pour le nombre de variantes (espèces d'arbres, variantes par espèce, rochers).
  **[VALIDÉ]** (12 octobre ; les quantités se jugent en jeu, famille par famille : **[PROVISOIRE]**)
