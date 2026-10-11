# Guide de style des sprites

Document de référence : **tout sprite du mod (filtre, Blender, IA ou dessin) doit le respecter**.
Les valeurs chiffrées vivent dans `cartoon/blender/style.py` (source de vérité pour les rendus Blender).
Si on change une règle, on la change ici *et* dans `style.py`, dans le même commit.

Légende : **[VALIDÉ]** décidé avec Bastien, **[PROVISOIRE]** à confirmer ou à caler.

## 1. Direction artistique

- Style cartoon simple et lisible : formes arrondies, aplats de couleur vives, gros contours. **[VALIDÉ]**
- On garde les formes, proportions et lisibilité de l'original : un joueur doit reconnaître chaque machine au premier coup d'œil. **[VALIDÉ]**
- Pas de dégradés, de bruit ni de texture réaliste (rouille, rayures, poussière). **[VALIDÉ]**

## 2. Projection (calée sur l'assembleur 1 original)

- **Bâtiments alignés sur la grille, aucune rotation** (jamais de vue à 45°). **[VALIDÉ]**
- **Vue presque du dessus, inclinée de 30°** : le dessus occupe l'essentiel du sprite, la face avant est une bande en bas. Le sol est **raccourci** par cos(30°) (mesuré sur l'original : la bande avant fait environ 0,8 case de haut). **[CALÉ]** (`PITCH_BUILDING_DEG`, `GROUND_STRETCH = False`)
- **Parois en tronc de pyramide** : les machines sont plus larges en bas qu'en haut (2,6 → 2,15 pour un assembleur), donc les côtés gauche et droit restent visibles. **[CALÉ]**
- **Silhouette** : une machine 3x3 mesure environ 2,6 cases de large (pas 3), centrée dans son emprise. **[CALÉ]**
- **Convoyeurs, tuyaux au sol, rails : vue directement du dessus**, jamais inclinés. **[VALIDÉ]**
- Les ombres portées sont des sprites séparés, comme dans le jeu (pas d'ombre dans le sprite principal). Ombre noire unie, soleil en haut à gauche : chaque point est projeté au sol de (0,3 x hauteur) vers la droite, sans décalage vertical (`SUN_SHEAR`). **[CALÉ]**

> Correction : une première version de ce guide disait « sol non raccourci, 35° ». Les mesures sur le sprite original ont montré que c'était faux.

## 3. Contours

- Noir chaud (brun très foncé), jamais noir pur. **[VALIDÉ]**
- Épaisseur définie **en unités du monde** : 0,026 case (`OUTLINE_UNITS`), soit environ 1,7 px à 64 px par case, la taille des fichiers de Factorio. Le même contour s'applique donc à tout objet, quelle que soit la taille de rendu. **[CALÉ]** (0,038 était trop épais à cette échelle : les parois de 14 px de large étaient recouvertes)
- Seules les arêtes vives sont contournées (angle d'écart > 70°) : pas de trait sur les biseaux ni sur les arrondis. **[CALÉ]**
- Contour sur la silhouette, les bords et les arêtes vives, pas sur les détails minuscules. **[VALIDÉ]**

## 4. Ombrage à trois tons

Chaque couleur de base est multipliée selon l'orientation de la face :

| Face | Multiplicateur |
|---|---|
| Dessus | 1,12 |
| Face avant | 0,85 |
| Côtés | 0,62 |

Pas d'autre ombrage : pas de dégradé, pas de reflets. **[VALIDÉ]**

## 5. Palette

**Couleurs de l'assembleur 1 original, conservées** (les assembleurs 2 et 3 gardent leur teinte d'origine : bleu et vert-jaune) : dominante gris-vert (parois), cuivre rouillé (plaques, tuyaux), fer sombre et laiton. Le style cartoon vient des aplats et des contours, pas d'un changement de teintes. 3 teintes maximum par objet. Valeurs dans `style.py` (`PALETTE_HEX`). **[VALIDÉ]**

| Nom | Hex | Usage |
|---|---|---|
| grey | #7d8573 | tôle gris-vert des parois |
| blue | #5b6e6a | acier verdi (panneaux, structures froides) |
| dark | #3a3126 | fer sombre, moteurs, intérieurs, socles |
| brown | #7a5238 | cuivre rouillé (plaque du dessus, tuyaux) |
| orange | #c07a45 | cuivre clair, pièces chaudes |
| yellow | #c9a24a | laiton (engrenages, finitions) |
| white | #d9d0bc | métal clair, reflets |
| red | #a8462f | rouge brique, braises |
| ore_iron | #6a8fae | minerai de fer |
| ore_copper | #d9753f | minerai de cuivre |
| ore_coal | #5b5b6b | charbon |
| ore_stone | #cdb078 | pierre |
| ore_uranium | #78c44a | uranium |
| steel_blue | #55789b | corps de l'assembleur 2 |
| navy | #3d5a78 | panneaux avant de l'assembleur 2 |
| olive | #97a03f | corps de l'assembleur 3 |
| olive_dark | #6c7430 | panneaux avant de l'assembleur 3 |
| green | #6f9a3c | bras en vrac |
| tan | #dcb878 | petit poteau électrique (clair pour ressortir sur le sol) |
| coral | #e5835a | poteau électrique moyen |
| steel_light | #c3ced2 | grand pylône électrique |
| glass, iron, steel, dark_grey, brass, brick, bark, wood_cut, plastic, sulfur, fuel, u235, u238 | voir `style.py` | objets (icônes) |
| pcb_green, pcb_red, pcb_blue | #3fa535, #c8352c, #2f6cc8 | circuits électronique, avancé, processeur |
| sci_red, sci_green, sci_grey, sci_blue, sci_purple, sci_yellow, sci_white | voir `style.py` | packs de science |

À définir : fluides. **[PROVISOIRE]**

## 6. Format technique

- PNG RGBA, **fond transparent**. **[VALIDÉ]**
- **Même cadre et même emprise que le sprite original**, au pixel près, pour remplacer le fichier sans toucher au reste du mod. L'assembleur 1 est calé automatiquement : cadre 214 × 226 px, pixels opaques de (25, 2) à (188, 199), recouvrement de silhouette de 92 %. `assembler.py` règle lui-même l'échelle et le décalage de la caméra par mesure. **[VALIDÉ]**
- Les fichiers de Factorio sont des planches : l'assembleur 1 contient 32 images d'animation (8 colonnes × 4 lignes de 214 × 226 px). **[CALÉ]**
- Rendu Blender : moteur Cycles CPU, 4 échantillons, sur-échantillonnage 2x puis réduction (bords nets), transformation de vue « Standard », matériaux en émission (aplats, sans éclairage). **[VALIDÉ]**
- Les sprites refaits vont dans `cartoon/mod/graphics/overrides/<jeu>/...` avec le même chemin que l'original. **[VALIDÉ]**

## 7. Règles par type d'objet

- **Machines** : corps en tronc de pyramide sur un socle sombre, dessus ouvert avec un mécanisme visible (engrenages), grande plaque avant, un ou deux éléments qui dépassent (tuyau, cheminée) pour casser la symétrie. Fibre « punk » : tôle, tuyauterie apparente, bande de danger, mais toujours en aplats.
- **Taille des détails** : à la taille du jeu, tout détail de moins de 6 px est avalé par les contours, et les bandes étroites (parois latérales : ~14 px) ne supportent ni nervures ni rivets. Peu de gros éléments, vérifiés **au format final** et pas seulement en grand.
- **Convoyeurs** : bande sombre, chevrons clairs régulièrement espacés, bords colorés.
- **Minerais** : tas bas et étalé, une teinte par ressource. **[PROVISOIRE]** (le premier test est trop « cristal »)
- **Icônes** : le modèle 3D de l'objet, vu comme les bâtiments (30°, convoyeurs vus de dessus), cadré pour que sa
  plus grande dimension fasse 60 px sur 64 (58 pour un objet compact : bras, tas de minerai), contour d'icône
  (`outline_px` 0,5, environ 1,2 px), suivi de ses réductions à 32, 16 et 8 px (fichier de 120 x 64, comme l'original).
  Générées par `lib.save_icon`. **[CALÉ]**
- **Icônes d'objets** (plaques, circuits, flacons... : tout ce qui n'est pas un bâtiment) : vue plus inclinée, à 45°
  (`PITCH_ITEM_DEG`), pour montrer le volume, et **rotation libre** comme dans les icônes d'origine. Les plaques de fer
  et de cuivre sont tournées en sens inverse (−35° et +35°), comme dans l'original, pour les distinguer d'un coup
  d'œil. Teintes vives de l'original (circuits vert, rouge, bleu ; packs de science à leurs couleurs), ajoutées à la
  palette. Cadrage 58 px, contour 0,45. Générées par `blender/items.py`. **[VALIDÉ]**
- **Décorations** (touffes, buissons, rameaux, cailloux, taches au sol) : procédural 2D (`terrain/decoratives.py`),
  à la place et à l'emprise des éléments de l'original (lus dans son canal alpha, sans son ombre intégrée). Seule
  la silhouette est contournée (pas chaque brin), d'un **contour teinté** (version foncée de la plante) : la
  végétation reste en arrière-plan, les bâtiments ressortent. **Une touffe sur cinq** seulement (l'original en
  couvre la carte ; en aplats, toutes les garder fait un tapis). Ombre à plat portée vers la droite. Taches au sol en
  aplat de la teinte moyenne de l'original, bord plus sombre, **à 60 % d'opacité**, sans contour ni ombre. **[VALIDÉ]**
- **Arbres** (procédural 2D, `terrain/trees.py`) : feuillage en **gros lobes ronds** (30 px dans le fichier ; sapin :
  étages pointus de 25 px ; saule : aplat suivant ses filaments) posés sur le feuillage de l'original, état par état
  (plein, abîmé, presque nu). Dessiné en tons neutres car **le jeu le teinte** (couleur tirée au hasard par arbre).
  Seuls les lobes du bord bas-droit sont sombres. Troncs, souches et arbres morts en aplat brun, trois tons tirés de
  la luminosité de l'original (on garde les troncs multiples, les racines). Normales plates sous le feuillage. Ombres
  d'origine conservées (noires, unies, même silhouette). Contour teinté. **[VALIDÉ]**
- **Gros rochers** (procédural 2D, `terrain/rocks.py`) : **blocs prismatiques** posés sur la silhouette de l'original,
  de l'arrière vers l'avant : colonnes hexagonales hautes pour `big-rock` et `huge-rock` (comme les colonnes de
  l'original), gros blocs bas à 8 pans pour le grès (`big-sand-rock`). Dessus clair, faces gauche et avant moyennes,
  face droite sombre, trait fin entre blocs, contour noir chaud. Teintes sombres proches de l'original (brun-roux ;
  grès olive, qui ressort sur le sable). Ombre de l'original en aplat. **[VALIDÉ]**
- **Poissons** : silhouette nette (fuseau et queue en V) à la place de la tache floue, même teinte et même opacité,
  sans contour (ils sont sous l'eau). **[VALIDÉ]**
- **Four en pierre** (`blender/furnace.py`) : pyramide tronquée de briques ocre (texture de briques procédurale,
  joints sombres, sans relief), bandeau et cheminée en pierre grise, bouche encadrée de pierre. Flammes en aplats à
  trois tons (rouge, orange, jaune), langues en gouttes qui ondulent en boucle de 48 images, sans contour, limitées
  à l'ouverture de la bouche. Halos lumineux d'origine. **[VALIDÉ]**
- **Foreuse à charbon** (`blender/burner_drill.py`) : quatre pieds arqués en fer sombre violacé (poutres d'un
  seul maillage), plateau à ailes, carter sombre et engrenages de laiton, vrille hélicoïdale, foyer gris-bleu,
  goulotte cuivre vers la sortie. Courbe des pieds ajustée sur la silhouette de l'original (4 directions).
  Animation : engrenages, vrille, piston. **[VALIDÉ]**
- **Poteaux et fins éléments** : assez épais pour rester lisibles à la taille du jeu. **[PROVISOIRE]**

## 8. Approche IA (si utilisée)

Même règles : mêmes contours, même palette, même projection. Voir `cartoon/ai/prompt.md` pour le prompt. Tout sprite généré doit être comparé à une planche de référence rendue par Blender avant d'être accepté.

## 9. Checklist avant de valider un sprite

- [ ] Projection correcte (grille, pas de rotation, 30°, parois en tronc de pyramide, convoyeurs vus de dessus)
- [ ] Contours noir chaud, épaisseur proportionnelle
- [ ] Trois tons d'ombrage uniquement
- [ ] Couleurs prises dans la palette
- [ ] Fond transparent, dimensions identiques à l'original
- [ ] Reconnaissable à côté de l'original et cohérent avec les autres sprites déjà validés
