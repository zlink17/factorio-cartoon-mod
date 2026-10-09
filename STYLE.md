# Guide de style des sprites

Document de référence : **tout sprite du mod (filtre, Blender, IA ou dessin) doit le respecter**.
Les valeurs chiffrées vivent dans `tools/blender/style.py` (source de vérité pour les rendus Blender).
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
- Les ombres portées sont des sprites séparés, comme dans le jeu (pas d'ombre dans le sprite principal). **[PROVISOIRE]**

> Correction : une première version de ce guide disait « sol non raccourci, 35° ». Les mesures sur le sprite original ont montré que c'était faux.

## 3. Contours

- Noir chaud (RGB linéaire 0.05, 0.03, 0.03), jamais noir pur. **[VALIDÉ]**
- Épaisseur : 2,2 px pour un rendu de 256 px, proportionnelle à la taille du rendu. **[VALIDÉ]**
- Contour sur la silhouette, les arêtes et les bords internes, pas sur les détails minuscules. **[VALIDÉ]**

## 4. Ombrage à trois tons

Chaque couleur de base est multipliée selon l'orientation de la face :

| Face | Multiplicateur |
|---|---|
| Dessus | 1,10 |
| Face avant | 0,88 |
| Côtés | 0,68 |

Pas d'autre ombrage : pas de dégradé, pas de reflets. **[VALIDÉ]**

## 5. Palette

Couleurs vives et saturées, peu de teintes par objet (3 maximum + contour). Valeurs exactes dans `style.py` (`PALETTE`). **[VALIDÉ]**

| Nom | Usage |
|---|---|
| orange, yellow | machines, convoyeurs, éléments de signalisation |
| blue | socles, structures |
| grey, dark | métal, fours, intérieurs |
| brown | bois, coffres, poteaux |
| red | zones chaudes, alertes |
| white | engrenages, détails clairs |
| ore_iron | minerai de fer |

À définir : cuivre, charbon, pierre, uranium, fluides. **[PROVISOIRE]**

## 6. Format technique

- PNG RGBA, **fond transparent**. **[VALIDÉ]**
- Même dimensions en pixels et même alignement que le sprite original, pour remplacer le fichier sans toucher au reste du mod. **[VALIDÉ]**
- Rendu Blender : moteur Cycles CPU, 4 échantillons, transformation de vue « Standard », matériaux en émission (aplats, sans éclairage). **[VALIDÉ]**
- Les sprites refaits vont dans `graphics/overrides/<mod>/...` avec le même chemin que l'original. **[VALIDÉ]**

## 7. Règles par type d'objet

- **Machines** : corps en tronc de pyramide sur un socle sombre, dessus ouvert avec un mécanisme visible (engrenages), grande plaque avant, un ou deux éléments qui dépassent (tuyau, cheminée) pour casser la symétrie. Fibre « punk » : tôle, tuyauterie apparente, bande de danger, mais toujours en aplats.
- **Taille des détails** : à la taille du jeu, tout détail de moins de 6 px est avalé par les contours. Pas de petits rivets ni de petites jauges : peu de gros éléments.
- **Convoyeurs** : bande sombre, chevrons clairs régulièrement espacés, bords colorés.
- **Minerais** : tas bas et étalé, une teinte par ressource. **[PROVISOIRE]** (le premier test est trop « cristal »)
- **Poteaux et fins éléments** : assez épais pour rester lisibles à la taille du jeu. **[PROVISOIRE]**

## 8. Approche IA (si utilisée)

Même règles : mêmes contours, même palette, même projection. Voir `tools/complex/style_guide.md` pour le prompt. Tout sprite généré doit être comparé à une planche de référence rendue par Blender avant d'être accepté.

## 9. Checklist avant de valider un sprite

- [ ] Projection correcte (grille, pas de rotation, 30°, parois en tronc de pyramide, convoyeurs vus de dessus)
- [ ] Contours noir chaud, épaisseur proportionnelle
- [ ] Trois tons d'ombrage uniquement
- [ ] Couleurs prises dans la palette
- [ ] Fond transparent, dimensions identiques à l'original
- [ ] Reconnaissable à côté de l'original et cohérent avec les autres sprites déjà validés
