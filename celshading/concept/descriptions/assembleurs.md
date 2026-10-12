# Assembleurs 1 à 3 : descriptions (original, puis cel-shading)

Étape « description » de la méthode (voir [docs/methode-images-cibles.md](../../../docs/methode-images-cibles.md)).
L'assembleur 1 a été fait d'après les images cibles e-11 et e-15 (`../cibles/`) et validé le 12 octobre ; les 2 et 3 en
dérivent (`celshading/blender/assembler.py`, pièces communes dans `blender/kit.py`).

Communs aux trois :
- **Original** : machine de 3 x 3 cases, corps en tronc de pyramide sur un socle, tablier avant en quatre panneaux
  rivetés, plateau de cuivre rouillé couvert de mécanique ; à gauche, un bloc moteur et un cylindre blanc ; animation
  de 32 images. **Les pièces mobiles se multiplient d'un niveau à l'autre** (cartes de mouvement des planches) :
  1 : un coin seulement (engrenages, levier) ; 2 : large zone (bras articulés, engrenages) ; 3 : gros bloc animé,
  avec de grands pistons verticaux qui dépassent au-dessus de la machine.
- **Cel-shading** : la famille de l'assembleur 1 (corps trapu aux coins coupés, tablier, plateau à rebord, moteur à
  « œil » jaune, tambour cuivré et son piston, cheminée de laiton, engrenages debout à l'arrière) ; la couleur du
  corps dit le niveau, comme l'original ; à droite, la mécanique propre au niveau. Pièces mobiles grosses et peu
  nombreuses ; **mouvements dans un plan penché vers l'arrière** : la caméra regarde presque d'en haut, un mouvement
  vertical n'y paraît qu'à moitié.

---

## 1 — Assembleur 1

**Original.** Corps gris-vert, plateau de cuivre ; engrenages qui tournent au fond, levier à l'arrière gauche,
rangée d'engrenages couchés.

**Cel-shading.** Corps rouille pâle (la rouille de l'original, en pastel ; vert sauge jusqu'au 12 octobre), plateau bleu. À droite : grand entonnoir de laiton couché, long arbre, paire
d'engrenages couchés. Mobiles : piston du tambour (une course par boucle), engrenages debout et couchés.

## 2 — Assembleur 2

**Original.** Corps et panneaux bleus. Deux bras articulés en acier sombre, à plusieurs segments, balaient le
plateau ; engrenages au fond ; deux cylindres blancs.

**Cel-shading.** Corps bleu clair, plateau brun cuivré (contraste chaud avec le bleu). À droite : **deux genouillères
croisées**, comme les bras de l'original (pas de pince : essayée le 12 octobre, écartée par Bastien) : barres plates
d'acier à bouts arrondis, axes de laiton ; chacune, menée par une manivelle de laiton (un tour par boucle), plie et
déplie son genou entre la manivelle et un pivot fixe sur le plateau ; les deux travaillent en opposition. Mobiles :
genouillères, manivelles, piston du tambour, engrenages du fond (plus bas qu'au 1 : le cadre de l'original est moins
haut).

## 3 — Assembleur 3

**Original.** Corps vert olive, tablier vert. Les bras articulés de l'assembleur 2, et trois ou quatre grands
pistons verticaux (chemise, tige argentée, tête blanche) qui montent et descendent en décalé, au-dessus de la machine.

**Cel-shading.** Corps vert sauge (l'ancien vert de l'assembleur 1), plateau bleu. Les genouillères de l'assembleur 2, plus **trois grands pistons** à l'arrière (chemise de
cuivre, bague de laiton, tige d'acier, tête blanche), décalés d'un tiers de boucle, qui dépassent au-dessus de la
machine (le cadre de l'original est plus haut, pour eux).
