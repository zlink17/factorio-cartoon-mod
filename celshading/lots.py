"""Lots du mod cel-shading : les commandes qui produisent chaque famille de sprites (lu par tools/build.py).

Même format que cartoon/lots.py : chaque commande est un script (chemin relatif à celshading/) suivi de ses
arguments ; build.py ajoute le dossier de sortie en premier argument.
"""

# Modèles du mod cartoon rendus en cel-shading (blender/run_cartoon.py), en attendant des modèles propres au mod.
LOTS = {
    "assembleurs": [                                     # planches animées, ombres, icônes
        *[("blender/run_cartoon.py", ["animate.py", str(tier)]) for tier in (1, 2, 3)],
        *[("blender/run_cartoon.py", ["assembler_extras.py", str(tier)]) for tier in (1, 2, 3)],
    ],
}
