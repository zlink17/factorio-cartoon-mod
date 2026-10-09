"""Source de vérité du style cartoon (voir STYLE.md à la racine du repo).

Tout script de rendu doit importer ces valeurs au lieu de les redéfinir.
Les couleurs sont en RGB linéaire (valeurs Blender).
"""

# --- Projection ---------------------------------------------------------
PITCH_BUILDING_DEG = 30   # calé sur l'assembleur 1 original (voir STYLE.md)
GROUND_STRETCH = False    # False : le sol est raccourci par cos(pitch), comme dans les sprites originaux
PITCH_TOPDOWN_DEG = 0     # convoyeurs, tuyaux au sol, rails : vue de dessus
YAW_DEG = 0               # jamais de rotation : alignement sur la grille

# --- Contours -----------------------------------------------------------
OUTLINE_COLOR = (0.05, 0.03, 0.03)
OUTLINE_PX_AT_256 = 2.2   # épaisseur pour un rendu de 256 px ; à mettre à l'échelle

# --- Ombrage à trois tons (multiplicateurs de la couleur de base) ----------
SHADE_SIDE = 0.68         # côtés
SHADE_FRONT = 0.88        # face avant  (0.68 + 0.20)
SHADE_TOP = 1.10          # dessus      (0.68 + 0.42)

# --- Palette -------------------------------------------------------------
PALETTE = {
    "orange": (0.95, 0.50, 0.10),
    "yellow": (1.00, 0.78, 0.20),
    "blue":   (0.20, 0.40, 0.85),
    "white":  (0.95, 0.95, 0.95),
    "grey":   (0.55, 0.62, 0.70),
    "dark":   (0.30, 0.32, 0.38),
    "brown":  (0.70, 0.40, 0.15),
    "red":    (0.95, 0.20, 0.15),
    "ore_iron": (0.35, 0.55, 0.90),
}

# --- Rendu ----------------------------------------------------------------
RENDER_SAMPLES = 4
VIEW_TRANSFORM = "Standard"
FILM_TRANSPARENT = True
