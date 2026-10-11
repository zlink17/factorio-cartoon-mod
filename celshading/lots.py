"""Lots du mod cel-shading : les commandes qui produisent chaque famille de sprites (lu par tools/build.py).

Même format que cartoon/lots.py : chaque commande est un script (chemin relatif à celshading/) suivi de ses
arguments ; build.py ajoute le dossier de sortie en premier argument.
"""

LOTS = {
    "assembleurs": [("blender/assembler.py", ["tout"])],   # assembleur 1 : planche animée, ombre, icône
}
