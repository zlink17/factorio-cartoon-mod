"""Lots du mod cartoon : les commandes qui produisent chaque famille de sprites (lu par tools/build.py).

Chaque commande est un script (chemin relatif à cartoon/) suivi de ses arguments ; build.py ajoute le dossier
de sortie en premier argument. Un script écrit l'arborescence de graphics/overrides (<jeu>/entity/..., <jeu>/icons/...).
Durées indicatives sur Ryzen 7 5800X (rendu Cycles sur CPU).
"""

LOTS = {
    "assembleurs": [                                     # planches animées, ombres, icônes
        *[("blender/animate.py", [str(tier)]) for tier in (1, 2, 3)],
        *[("blender/assembler_extras.py", [str(tier)]) for tier in (1, 2, 3)],
    ],
    "convoyeurs": [("blender/belt.py", ["tous"])],       # jaune, rouge, bleu, turbo
    "bras": [("blender/inserter.py", ["tous"])],
    "souterrains": [("blender/underground.py", ["tous"])],
    "repartiteurs": [("blender/splitter.py", ["tous"])],
    "pylones": [("blender/pole.py", ["tous"])],          # et câbles (jeu core)
    "minerais": [("blender/ore.py", ["tous"])],
    "objets": [("blender/items.py", ["tous"])],          # icônes des objets intermédiaires (aussi sur les convoyeurs)
    "sols": [("terrain/ground.py", ["toutes"]), ("terrain/masks.py", [])],   # planches et masques de transition
}
