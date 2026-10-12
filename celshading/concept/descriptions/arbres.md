# Arbres de Nauvis : descriptions (original, puis cel-shading)

Étape « description » de la méthode (12 octobre, voir [docs/methode-images-cibles.md](../../../docs/methode-images-cibles.md)) :
avant le premier rendu Blender, on décrit le sprite original en détail, puis on décline la description dans le style du
mod. La version cel-shading guide le prototype (`celshading/blender/tree.py`) ; elle peut aussi servir de texte pour
ComfyUI si le prototype ne colle pas (à traduire en anglais).

Communs à toutes les espèces :
- **Original** : rendu 3D réaliste, vue de trois quarts haute (30°), lumière d'en haut à gauche, longue ombre portée
  vers la droite ; feuillage en milliers de petites feuilles, teint par le jeu (une couleur tirée au hasard par arbre) ;
  le calque « tronc » monte jusqu'en haut avec ses branches (on le voit quand le feuillage est abîmé) ; trois états du
  feuillage (plein, abîmé, presque nu).
- **Cel-shading** : peu de grosses formes, cernées d'un trait foncé teinté (une touffe = un trait, pas de trait
  entre ses bosses) ; trois tons francs (dessus clair, ton moyen, ombre bleutée à droite) ; feuillage en tons neutres
  pour la teinte du jeu ; tronc brun chaud, toujours visible sous le feuillage ; racines courtes et arrondies.

---

## 01 — Sapin

**Original.** Conifère élancé, silhouette en cône étroit et régulier, pointe fine. Feuillage bleu-vert dense, en
aiguilles, porté par des branches horizontales étagées qui se recouvrent, bord dentelé. Tronc court, brun foncé, à
peine visible sous les branches basses, pied un peu évasé. Tronc seul : fût droit et fuselé jusqu'à la pointe,
petites branches horizontales courtes tout du long.

**Cel-shading.** Sapin stylisé en **trois étages** de cônes nets empilés, le plus bas le plus large, le dernier en
pointe effilée. Chaque étage clair à gauche, ombré à droite, cerné de son trait ; pas d'ombre portée d'un étage sur
l'autre (les étages restent lisibles). Tronc brun bien visible sous le premier étage, pied évasé, racines courtes.

**Dans Blender.** `sapin` : 3 cônes sans disque dessous (lissage juste), rayon décroissant de la largeur du bas de la
silhouette à une pointe, pointe à la hauteur de l'original, tronc dégagé (`FIR_TRUNK`).

## 02 — Grand arbre ovale

**Original.** Feuillu haut et étroit, couronne ovale dense qui descend bas, feuilles vert vif. Tronc droit, brun-rouge,
visible à la base sous la couronne. Tronc seul : fût droit couvert de petites branches courtes.

**Cel-shading.** Couronne ovale en étages de grosses touffes « chou-fleur » (deux côte à côte, une devant un étage sur
deux), chacune cernée ; tronc visible sous la couronne. (Validé par Bastien, image de référence
`cibles/arbre-bastien.jpg`.)

**Dans Blender.** `chou-fleur` (dessin par défaut).

## 03 — Arbre noueux et large

**Original.** Couronne large et aérée, irrégulière, vert olive tirant sur le jaune, avec des trous où l'on voit des
branches tordues. Tronc épais, noueux, qui se divise en Y en deux grosses branches ; base très évasée, rougeâtre,
racines visibles. Tronc seul : un Y noueux d'où partent des branches fines ramifiées.

**Cel-shading.** Couronne large faite de touffes chou-fleur **séparées par des trous** ; on voit, entre elles, les
deux grosses branches du Y. Tronc épais, un peu tordu, fourche en Y bien lisible, pied large.

**Dans Blender.** `noueux` : touffes calées sur la silhouette, environ un tiers retiré (trous) ; tronc qui s'arrête
à la fourche, deux grosses branches coniques vers la gauche et la droite de la couronne.

## 04 — Arbre élancé et sombre

**Original.** Grand arbre au tronc haut et droit, gris-brun clair, visible sur près de la moitié de la hauteur.
Feuillage vert sombre bleuté, en paquets irréguliers accrochés le long du tronc et au sommet, asymétrique. Base
évasée avec racines. Tronc seul : fût haut et clair, quelques branches fines.

**Cel-shading.** Tronc haut et clair très lisible ; **une touffe par étage, alternée gauche / droite**, plus une au
sommet : silhouette aérée, en zigzag.

**Dans Blender.** `elance` : écorce claire ; étages remontés ; une touffe par étage, décalée d'un côté puis de l'autre.

## 05 — Arbre rond et trapu

**Original.** Arbre bas, couronne ronde et large en dôme, dense, vert moyen. Tronc court qui se divise vite en
plusieurs branches montantes ; racines au sol. Tronc seul : court, fourche en trois ou quatre branches.

**Cel-shading.** Un **gros dôme de boules lisses** (la première variante en boules, que Bastien avait aimée), chaque
boule cernée et marquée d'un croissant d'ombre ; tronc court visible dessous.

**Dans Blender.** `dome` : boules lisses (pas de chou-fleur), un peu plus grosses, calées sur la silhouette.

## 06 — Saule mort

**Original.** Petit arbre penché, presque sans feuilles. Tronc tordu brun-rouge, nombreuses branches fines qui
retombent en filaments ; quelques feuilles translucides vert pâle qui pendent ; racines apparentes.

**Cel-shading.** Tronc penché et tordu ; **trois ou quatre branches nues arquées** qui montent puis retombent ; au
bout de chacune, quelques **filaments fins** qui pendent (le feuillage, teint par le jeu) et une très petite touffe.
Peu de feuillage : c'est la silhouette des branches qui fait l'arbre.

**Dans Blender.** `saule` : tronc penché ; branches en deux segments (montée, puis retombée) ; filaments fins (cônes
pointe en bas) au bout des branches.

## 07 — Arbre en masses superposées

**Original.** Couronne haute faite de plusieurs masses arrondies superposées, teinte orange-brun (automne). Tronc qui
se divise en deux ou trois grosses branches montantes, visibles entre les masses ; base évasée.

**Cel-shading.** **Deux ou trois grosses masses** de touffes chou-fleur, nettement séparées, l'une au-dessus de
l'autre, décalées ; entre elles, les grosses branches du tronc.

**Dans Blender.** `masses` : trois amas de touffes, à trois hauteurs, alternés gauche / droite.

## 08 — Arbre en parasol

**Original.** Tronc fin, droit, clair, assez haut ; couronne large et aplatie, vert vif, portée par des branches qui
s'écartent en éventail.

**Cel-shading.** Couronne **aplatie en parasol** : un anneau de touffes chou-fleur sur toute la largeur, une plus petite
couche au-dessus ; tronc fin et clair, branches en éventail visibles dessous.

**Dans Blender.** `parasol` : écorce claire, tronc fin ; touffes sur deux couches seulement, à la largeur maximale de
la silhouette.

## 09 — Arbre géant

**Original.** Énorme arbre aux troncs massifs soudés et tordus, base racinaire très large ; couronne immense, jaune
doré, irrégulière, qui déborde sur les côtés.

**Cel-shading.** **Trois troncs massifs** qui s'écartent, chacun cerné ; grande couronne de touffes chou-fleur.

**Dans Blender.** `geant` : trois troncs coniques, touffes plus grosses (`R_CAP`), pied reculé (`FOOT_BACK`).
