"""Source de vérité du style cartoon (voir cartoon/STYLE.md).

Tout script de rendu doit importer ces valeurs au lieu de les redéfinir.
Les couleurs sont en RGB linéaire (valeurs Blender).
"""

# --- Projection ---------------------------------------------------------
PITCH_BUILDING_DEG = 30   # calé sur l'assembleur 1 original (voir cartoon/STYLE.md)
GROUND_STRETCH = False    # False : le sol est raccourci par cos(pitch), comme dans les sprites originaux
PITCH_ITEM_DEG = 45       # icônes d'objets (plaques, circuits, flacons) : plus inclinées pour montrer leur volume
PITCH_TOPDOWN_DEG = 0     # convoyeurs, tuyaux au sol, rails : vue de dessus
YAW_DEG = 0               # jamais de rotation : alignement sur la grille

# --- Contours -----------------------------------------------------------
OUTLINE_COLOR = (0.05, 0.03, 0.03)
OUTLINE_UNITS = 0.026     # épaisseur en unités du monde (1 case = 1 unité) : ~1,7 px à 64 px/case
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
    "ore_iron": "#6a8fae",
    "ore_copper": "#d9753f",
    "ore_coal": "#5b5b6b",
    "ore_stone": "#cdb078",
    "ore_uranium": "#78c44a",
    "green":  "#6f9a3c",   # bras en vrac
    "tan":    "#dcb878",   # bois clair du petit poteau (ressort sur le sol brun)
    "coral":  "#e5835a",   # poteau moyen : teinte distincte du petit poteau
    "steel_light": "#c3ced2",   # acier clair des pylônes
    "tread":  "#625343",   # stries en relief des convoyeurs (ton sur ton avec la bande)
    # assembleurs 2 et 3 : une teinte de corps par niveau + sa version foncée pour les panneaux avant
    "steel_blue": "#55789b",  # assembleur 2 : acier bleu
    "navy":       "#3d5a78",
    "olive":      "#97a03f",  # assembleur 3 : vert-jaune
    "olive_dark": "#6c7430",
    # objets (icônes) : teintes de l'original, vives pour être reconnues sur les convoyeurs
    "glass":     "#b4bfc4",   # verre des flacons
    "iron":      "#80868c",   # fer brut (engrenage, carters)
    "steel":     "#9aa5ad",   # acier (poutre)
    "dark_grey": "#4e5257",   # boîtiers, combustible solide
    "brass":     "#e0b84a",   # pistes des circuits, laiton vif
    "brick":     "#9a978c",   # brique de pierre
    "bark":      "#7a4e2c",   # écorce
    "wood_cut":  "#d9a35f",   # bois coupé
    "plastic":   "#e2e4e6",   # barre de plastique
    "sulfur":    "#e3cf3a",   # soufre
    "fuel":      "#f0b030",   # carburant de fusée
    "u235":      "#62d63f",   # uranium 235 (vif)
    "u238":      "#3e8a3a",   # uranium 238 (sombre)
    "pcb_green": "#3fa535",   # circuits : vert, rouge, bleu de l'original
    "pcb_red":   "#c8352c",
    "pcb_blue":  "#2f6cc8",
    "sci_red":    "#cf3530",  # packs de science, couleurs de l'original
    "sci_green":  "#4cbf3a",
    "sci_grey":   "#6f757b",
    "sci_blue":   "#3ab0e0",
    "sci_purple": "#9a48d4",
    "sci_yellow": "#e3b83a",
    "sci_white":  "#eeeeee",
    # four en pierre : briques ocre de l'original, pierre grise, suie
    "furnace_brick":      "#c9a83c",
    "furnace_brick_dark": "#a88a30",
    "furnace_stone":      "#b8b2a3",
    "furnace_mortar":     "#6e5a3a",
    "furnace_soot":       "#2a211b",
    # foreuse à charbon : fer sombre légèrement violacé des pieds (original)
    "drill_iron":         "#6e6a7c",
    "drill_auger":        "#4a4c58",
    # foreuse électrique : poutre jaune-orangé, corps de la tête gris-bleu
    "drill_yellow":       "#e3a32e",
    "drill_body":         "#7f9298",
    # coffres : bois ocre de l'original, fer rouillé sombre et couvercle gris rosé, acier mauve clair nervuré
    "chest_wood_frame":   "#cf9d52",
    "chest_wood":         "#a8743a",
    "chest_wood_dark":    "#7e5428",
    "chest_wood_gap":     "#5a3a1c",
    "chest_iron_body":    "#5f5446",
    "chest_iron_lid":     "#a08878",
    "chest_iron_plate":   "#8a7064",
    "chest_steel":        "#c4bac6",
    "chest_steel_rib":    "#7d7282",
    "chest_steel_front":  "#5e534c",
    "chest_steel_frame":  "#9a6a4a",
    "chest_steel_rim":    "#8a8090",
    # chaudière : acier gris-vert de l'original
    "boiler_body":        "#6e7a6c",
    # machine à vapeur : cylindres en tôle claire, pieds rouille, conduites gris clair
    "engine_tank":        "#b5ad98",
    "engine_rust":        "#8a4a2c",
    "engine_pipe":        "#a3a8a6",
    # pompe côtière : réservoir brun sombre à bord jaune, gaines orange annelées
    "pump_yellow":        "#cf9a30",
    "pump_tank":          "#5e4030",
    "pump_hose":          "#d8875a",
    "pump_hose_dark":     "#8e4e30",
    # tuyaux : tôle claire (comme les conduites de la machine à vapeur), bouchons gris
    "pipe":               "#a9aba2",
    "pipe_cap":           "#8a8e88",
}
PALETTE = {k: _lin(v) for k, v in PALETTE_HEX.items()}

# --- Rendu ----------------------------------------------------------------
RENDER_SAMPLES = 4
SUPERSAMPLE = 2           # rendu à 2x puis réduction (bords nets, sans crénelage)
VIEW_TRANSFORM = "Standard"
FILM_TRANSPARENT = True
