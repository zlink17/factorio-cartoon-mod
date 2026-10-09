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
OUTLINE_PX_AT_256 = 1.6   # épaisseur pour un rendu de 256 px ; à mettre à l'échelle
OUTLINE_CREASE_DEG = 110  # seules les arêtes vives (> 70° d'écart) sont contournées

# --- Ombrage à trois tons (multiplicateurs de la couleur de base) ----------
SHADE_SIDE = 0.62         # côtés
SHADE_FRONT = 0.85        # face avant  (0.62 + 0.23)
SHADE_TOP = 1.12          # dessus      (0.62 + 0.50)

# --- Palette (teintes mesurées sur l'assembleur 1 original) -----------------------
def _lin(hex_):
    """#rrggbb (sRGB) -> RGB linéaire pour Blender."""
    out = []
    for k in (1, 3, 5):
        v = int(hex_[k:k + 2], 16) / 255.0
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(round(x, 4) for x in out)


PALETTE_HEX = {
    "grey":   "#7d8573",   # tôle gris-vert des parois
    "blue":   "#5b6e6a",   # acier verdi (socles, structures froides)
    "dark":   "#3a3126",   # fer sombre, moteurs, intérieurs
    "brown":  "#7a5238",   # cuivre rouillé (plaque du dessus, tuyaux)
    "orange": "#c07a45",   # cuivre clair, pièces chaudes
    "yellow": "#c9a24a",   # laiton (engrenages, finitions)
    "white":  "#d9d0bc",   # métal clair, reflets
    "red":    "#a8462f",   # rouge brique, braises
    "ore_iron": "#5f7f9a",
}
PALETTE = {k: _lin(v) for k, v in PALETTE_HEX.items()}

# --- Rendu ----------------------------------------------------------------
RENDER_SAMPLES = 4
SUPERSAMPLE = 2           # rendu à 2x puis réduction (bords nets, sans crénelage)
VIEW_TRANSFORM = "Standard"
FILM_TRANSPARENT = True
