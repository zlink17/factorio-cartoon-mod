# Mod Cel-shading : approche et plan

Rédigé le 11 octobre 2026. **État : dossier créé (`celshading/`), mod vide qui se charge ; questions de la section 4 tranchées (11 octobre :
les quatre recommandations). Étape 0 faite : moteur cel-shading, assembleurs du mod cartoon vus en jeu (essai).
Décision du 11 octobre au soir : modèles refaits de zéro, d'après des images cibles (section 3.3). Étape 1 en cours :
images cibles de l'assembleur 1.**
Règles visuelles : [`celshading/STYLE.md`](../../celshading/STYLE.md) (brouillon).

Objectif : un troisième mod de textures, au style « Wind Waker » : cel-shading (lumière et ombre à bord franc),
couleurs vives et ensoleillées, formes rondes et trapues, fumées en boules à spirale, mer bleu profond à vagues blanches.
Le nom du mod et ses textes publics ne citent ni Zelda ni Wind Waker (marques de Nintendo) : « Cel-Shading ».

---

## 1. Ce qui fait le style, et ce qu'on peut en garder dans Factorio

| Trait de Wind Waker | Traduction dans Factorio | Faisable ? |
|---|---|---|
| **Deux tons par couleur** (éclairé / ombre), frontière nette qui suit la forme : un cylindre a une moitié claire et une moitié sombre, une sphère un croissant d'ombre | Ombrage calculé à partir d'une **vraie direction de lumière**, puis seuillé. C'est la grande différence avec le mod cartoon, dont l'ombrage dépend seulement de l'orientation de la face (dessus, avant, côtés) | Oui (Blender, voir 3.1) |
| **Ombres portées sur l'objet lui-même** (la cheminée projette son ombre sur le toit) | Même rendu, avec ombres de la lumière | Oui |
| **Ombres teintées** : bleu-violet, jamais gris ni noir | Teinte de l'ombre dans le sprite | Oui dans le sprite ; **non pour les ombres au sol** : le jeu dessine les sprites d'ombre en noir semi-transparent, sans couleur (voir section 2) |
| **Peu ou pas de traits noirs** : la silhouette tient par le contraste des couleurs | Contour fin teinté, ou aucun | À décider (question 1) |
| **Couleurs saturées et chaudes**, ciel et mer très bleus, herbe vert vif | Palette propre au mod | À décider (question 2) |
| **Textures peintes simples** : planches, pierres, motifs, sans bruit ni grain | Motifs en aplats sur les modèles (comme les briques du four cartoon) | Oui |
| **Formes rondes et trapues**, proportions un peu exagérées, gros biseaux | Modèles plus ronds que ceux du mod cartoon : le cel-shading a besoin de courbes pour montrer sa frontière | Oui, mais demande de reprendre les modèles (voir 3.2) |
| **Spirales** : fumées en boules qui finissent en volute, vent, nuages, explosions en nuages ronds | Sprites de fumée, de vapeur, d'explosions, de feu | Oui : c'est **la signature** la plus visible, à traiter tôt |
| **Arbres en boules** de feuillage, chacune avec son croissant d'ombre | Arbres en 3D (sphères) plutôt qu'en 2D | Oui (Blender) |
| Mer : bleu profond, écume en lignes blanches dessinées | Bruit de l'eau, textures d'eau, bords | En partie : le shader de l'eau est celui du jeu (même limite que le lot 2.9 cartoon) |

## 2. Contraintes du moteur (connues grâce au mod cartoon)

- **Les ombres au sol sont dessinées par le jeu** : un sprite d'ombre ne fournit qu'une forme ; le jeu l'assombrit
  en noir semi-transparent. Impossible de les teinter en bleu. On peut seulement régler la forme (bord net) et
  l'opacité. Les ombres teintées n'existent donc **que dans les sprites** (ombre propre des objets).
- **La lumière doit venir du même côté que les ombres du jeu** : soleil en haut à gauche, ombres portées vers la
  droite. Dans les sprites : dessus et face gauche éclairés, face droite dans l'ombre. Sinon le monde est incohérent.
- **Mêmes fichiers, même cadre, même emprise** que l'original (règle du mod cartoon, outils de contrôle déjà prêts).
- **Le jeu teinte certains sprites** (feuillages d'arbres, masques d'équipe, décorations) : ils sont dessinés en
  tons neutres, et le cel-shading doit rester lisible après teinte.
- **La nuit** : le jeu assombrit tout ; des ombres déjà bleues risquent de rendre la nuit très bleue. À vérifier en jeu.
- **Petite taille** : 64 px par case. Les leçons du cartoon valent ici : tout détail de moins de 6 px disparaît ;
  vérifier au format final et **en jeu**, jamais sur un montage Python.

## 3. Approche technique recommandée

### 3.1 Rendu cel-shading dans Blender (technique principale)

On garde Blender (`bpy`, Cycles sur CPU, déjà installé dans le `.venv`) : c'est ce qui a rendu le mod cartoon
cohérent, animable et reproductible. Le changement est dans le **matériau** :

1. Une lampe « soleil » à bord dur (angle 0) dans la direction fixée par le style.
2. Rendu en passes : couleur de base (albedo) et lumière directe diffuse (ombres comprises).
3. Seuil sur la lumière : au-dessus, ton éclairé ; en dessous, ton d'ombre (couleur multipliée par la teinte
   d'ombre bleutée). Éventuellement un troisième palier, très clair, pour un reflet sur le métal.
4. Assemblage dans le compositeur de Blender : pas de retouche externe, résultat identique à chaque relance.

Variante plus simple pour un premier essai : seuil sur le produit scalaire normale·lumière directement dans le
matériau (en émission, comme aujourd'hui). Pas d'ombres portées sur l'objet, mais quelques lignes de code. Le
prototype dira si les ombres portées valent la complexité (je pense que oui : c'est très Wind Waker).

Pas de rendu EEVEE (le nœud « Shader to RGB » qui fait le toon dans les tutoriels) : il demande un contexte
graphique, fragile en ligne de commande sous WSL.

### 3.2 Réutiliser les modèles du mod cartoon, puis les arrondir (abandonné le 11 octobre, voir 3.3)

Les générateurs cartoon (`cartoon/blender/*.py`) importent leurs briques depuis `lib.py` (`mat`, `box`, `cyl`,
`gear`, `render_scene`...). Si `celshading/blender/lib.py` offre **les mêmes fonctions** avec le rendu cel-shading,
on peut rendre un modèle cartoon existant en cel-shading sans le réécrire : un aperçu de 9 lots de machines pour
le prix d'une bibliothèque. Ensuite, objet par objet, on arrondit les formes (biseaux plus gros, cylindres au lieu
de boîtes) dans des copies propres au mod, pour ne jamais casser le mod cartoon.

### 3.3 Vision et méthode retenues (11 octobre, soir)

Vu en jeu, le rendu des modèles cartoon en cel-shading est trop discret : boîtes à faces plates, une seule bande
d'ombre sur le flanc droit. Bastien veut **repartir de zéro pour les modèles**, avec sa vision : **Wind Waker pour le
rendu, l'esprit industriel et steampunk de Factorio pour le fond, un peu comme Metal Slug** (machines trapues,
exagérées, rivets, boulons, tuyaux). Machines réinterprétées mais reconnaissables, peu de grosses formes.

Méthode par objet :
1. **Guides** tirés du sprite original : `celshading/concept/prepare.py` (contours, profondeur, cadrage).
2. **Images cibles** : `celshading/concept/concept.py` (ComfyUI : SDXL Turbo guidé par ControlNet, sans référence
   de style pour l'instant), plusieurs graines et deux dosages des guides (proche de l'original / plus libre).
3. **Bastien choisit** (ou combine, ou commente), éventuellement une seconde passe en img2img sur l'image choisie.
4. **Modèle Blender** propre au mod (`celshading/blender/`), qui s'approche de l'image cible ; rendu avec le moteur.
5. Vérification en jeu (banc d'essai), comme pour tout lot.

`run_cartoon.py` et le lot « assembleurs » actuel ne servent plus que d'essai du moteur : ils seront remplacés par
les nouveaux modèles.

### 3.4 Le reste

- **Sols, décorations, eau** : procédural 2D (OpenCV, comme `cartoon/terrain/`), avec la palette du mod. Les sols
  plats n'ont pas d'ombrage : ce sont les motifs peints (touffes en virgules, taches) qui donnent le style.
- **Arbres** : en 3D (boules de feuillage cel-shadées) plutôt qu'en 2D ; le cel-shading 2D d'une boule est faux.
- **Fumées, vapeur, explosions, feu** : boules 3D cel-shadées pour les nuages, volutes en 2D vectoriel.
- **Images cibles** : ComfyUI est déjà installé (`~/workspace/comfyui`) ; on peut s'en servir pour des images
  d'ambiance (« cel-shading, couleurs vives » guidé par le sprite original), comme cible à atteindre en Blender,
  **pas** comme production.

### 3.5 Outils communs, déjà prêts

Les outils de `tools/` prennent le nom du dossier du mod : `build.py celshading <lot>`, `inventory.py celshading`,
`check_mod.py celshading --jeu`, `bench.py celshading`, `install_mod.sh celshading`. Seule la galerie est propre
au cartoon (à rendre paramétrable, étape 0).

---

## 4. Questions de style (tranchées le 11 octobre : les quatre recommandations, retenues par Bastien)

1. **Contours** : (a) aucun, comme Wind Waker ; (b) **contour fin de silhouette, teinte foncée de l'objet**
   (recommandé : lisible sur une usine chargée, sans ressembler au mod cartoon) ; (c) contour noir chaud.
2. **Palette** : (a) teintes de Factorio conservées (comme le cartoon) ; (b) palette Wind Waker franche ;
   (c) **teintes de Factorio pour reconnaître chaque objet, mais plus saturées et plus claires, avec des ombres
   bleu-violet** (recommandé).
3. **Ombres au sol** : (a) celles du jeu, d'origine ; (b) **silhouette à bord net, moins opaque** (recommandé ;
   le jeu les dessine en noir quoi qu'on fasse).
4. **Par quoi commencer** : (a) **le trio d'essai de l'étape 1** (recommandé) ; (b) directement les machines,
   en réutilisant les modèles cartoon.

## 5. Feuille de route

Même méthode que le mod cartoon ([docs/cartoon/plan.md](../cartoon/plan.md), section 2) : un lot = cadrage,
prototype, production, contrôle, vérification en jeu, commit.

### Étape 0 : fondations
- [x] Dossier `celshading/`, mod vide (`celshading/mod/`) incompatible avec les mods cartoon et pixel.
- [x] `celshading/blender/cel_style.py` et `lib.py` : lumière, paliers, teinte d'ombre, contour de silhouette teinté,
      ombres au sol allégées ; mêmes fonctions que la bibliothèque cartoon (reprise telle quelle sauf `mat` et
      `render_scene`). Rendu en deux passes Cycles (couleurs, puis lumière d'un soleil à ombres dures), assemblées
      avec numpy : pas de compositeur Blender. Éclairement calibré (dessus plat = composante verticale de la lumière).
- [x] Essai de faisabilité (`blender/essai.py`) : boîte, cylindre, sphère, tore : frontière d'ombre nette qui suit
      la forme, croissant d'ombre, ombres portées sur l'objet.
- [x] `blender/run_cartoon.py` : rend un générateur du mod cartoon en cel-shading sans le modifier (lot
      « assembleurs » : les trois assembleurs, planches, ombres et icônes, en 1 min).
- [ ] Galerie : rendre `tools/galerie.py` paramétrable (`--mod celshading`) et ajouter le mod en dépendance facultative.

### Étape 1 : charte visuelle, sur trois objets vus en jeu
Trois objets qui couvrent les trois familles de rendu, posés ensemble dans le banc d'essai, chacun par la méthode
de la section 3.3 (image cible, puis modèle) :
- [ ] **Assembleur 1** (machine, surfaces dures) : nouveau modèle.
- [ ] **Arbre** (organique) : boules de feuillage.
- [ ] **Four en pierre avec sa fumée** (effets) : la volute de fumée.
- [ ] Plus **l'herbe** comme fond.

Fin d'étape : `STYLE.md` passe de « brouillon » à des règles **[VALIDÉ]**, avec leurs valeurs dans `style.py`.

### Étape 2 : production, ce qui donne l'ambiance d'abord
Ordre proposé : sols et décorations de Nauvis, eau, arbres, fumées et feu (ce qu'on voit sur tout l'écran),
puis les lots du début de partie dans l'ordre du mod cartoon (convoyeurs, bras, assembleurs, fours, foreuses,
coffres, énergie vapeur, tuyaux, petits bâtiments, objets), puis personnage.
