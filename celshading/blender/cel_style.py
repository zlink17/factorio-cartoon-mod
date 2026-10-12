"""Source de vérité du style cel-shading (voir celshading/STYLE.md).

Nommé cel_style (et non style) pour ne pas masquer le module style du mod cartoon, dont on réutilise les modèles.
La projection et le format technique sont imposés par le jeu : ils viennent de cartoon/blender/style.py.
"""
import math

# --- Lumière --------------------------------------------------------------------------------------------------
# Direction d'où vient la lumière (x vers la droite, y vers le fond, z vers le haut) : haut à gauche, un peu de face,
# comme le soleil des ombres du jeu (portées vers la droite). Dessus, gauche et avant éclairés, droite dans l'ombre.
_L = (-0.55, -0.40, 0.73)
LIGHT_DIR = tuple(c / math.sqrt(sum(v * v for v in _L)) for c in _L)

# Paliers de lumière : éclairement (cosinus entre la normale et la lumière, ombres portées comprises) -> ton.
# En dessous de SHADOW_BELOW : ombre ; au-dessus de HIGHLIGHT_ABOVE : ton clair (dessus des objets).
SHADOW_BELOW = 0.22
HIGHLIGHT_ABOVE = 0.66

# Teintes (multiplicateurs RGB en sRGB) : ombre bleu-violet, ton clair un peu chaud.
SHADOW_TINT = (0.56, 0.58, 0.80)
HIGHLIGHT_TINT = (1.10, 1.08, 1.02)

# --- Rendu -----------------------------------------------------------------------------------------------------
# Échantillons Cycles par pixel (le mod cartoon en prend 4) : à 4, contours et frontières d'ombre granuleux, des
# points parasites dans les aplats (12 octobre) ; à 16, nets, pour ~1 s de plus par image.
RENDER_SAMPLES = 16

# --- Palette --------------------------------------------------------------------------------------------------
# Les modèles donnent les teintes de Factorio (palette cartoon) ; mat() les avive : saturation et valeur (HSV).
SATURATION_GAIN = 1.30
VALUE_GAIN = 1.10

# --- Contours ---------------------------------------------------------------------------------------------------
OUTLINE_UNITS = 0.016      # épaisseur en unités du monde : ~1 px à 64 px par case (cartoon : 0,026)
OUTLINE_DARKEN = 0.38      # couleur du contour = couleur de l'objet (avivée) x OUTLINE_DARKEN, en sRGB
OUTLINE_BLUE = 1.25        # ... avec un peu plus de bleu, comme les ombres

# --- Ombres au sol ----------------------------------------------------------------------------------------------
# Le jeu dessine les sprites d'ombre en noir (couleur ignorée) ; les originaux sont opaques. Alpha plus bas :
# ombre plus légère. Bord net (pas de flou).
GROUND_SHADOW_ALPHA = 0.85     # 0,70 au départ : trop pâle en jeu (12 octobre)
