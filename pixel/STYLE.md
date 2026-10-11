# Guide de style pixel art

**Brouillon, réécrit à partir du 11 octobre 2026** : la charte se fixe sur les premiers lots (étape 1 de
[docs/pixel/plan.md](../docs/pixel/plan.md)). **[VALIDÉ]** décidé avec Bastien, **[PROVISOIRE]** à confirmer en jeu.

## Contrat technique (vérifié par outil)
- **16 px d'art par case** pour le monde entier ; 1 px d'art = 4 × 4 px de fichier, `scale = 0.5` comme l'original. **[VALIDÉ]**
- Pixels d'art alignés sur la grille du monde (1/16 de case). **[VALIDÉ]**
- Images au cadre exact de l'original (taille, nombre d'images) : pas de correction de taille en Lua. **[VALIDÉ]**
- Palette fermée, jamais de noir pur ; pas d'anticrénelage (alpha 0 ou 255) ; ombres au sol en aplat. **[VALIDÉ]**
- Icônes : 32 px d'art (export × 2 dans le cadre de 64 px). **[VALIDÉ]**
- Objets posés au sol et sur les convoyeurs : variante dessinée à 16 px par case (pas l'icône réduite). **[VALIDÉ]**

## Ambiance
- Ce qui a été imaginé pour le Factorio d'origine ne convient pas forcément : décorations à **10 %** de la quantité
  du jeu au départ, une famille retirée si elle surcharge encore (réglages de démarrage du mod). **[PROVISOIRE, à juger en jeu]**

## Direction artistique
- À fixer sur les images cibles des premiers lots. Idées de l'ancien travail, à reprendre ou non : esprit
  *Link's Awakening* / *Minish Cap* (image de référence krank.love), contours teintés, lumière en haut à gauche,
  ombres vers le bleu-violet, formes et couleurs par niveau de Factorio.
