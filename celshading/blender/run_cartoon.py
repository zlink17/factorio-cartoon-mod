"""Rend un générateur du mod cartoon en cel-shading, sans le modifier.

Usage : python celshading/blender/run_cartoon.py <dossier_sortie> <script de cartoon/blender> [arguments...]
Exemple : python celshading/blender/run_cartoon.py sortie/ animate.py 1   (planche de l'assembleur 1)

Le générateur importe `lib` : on lui donne celshading/blender/lib.py (mêmes fonctions, matières et rendu
cel-shading). Ses modèles, sa palette (avivée par mat) et ses cadrages restent ceux du mod cartoon.
"""
import os, runpy, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

sys.modules["lib"] = lib
out, script, *args = sys.argv[1:]
path = os.path.join(lib.CARTOON, script)
sys.argv = [path, out, *args]
runpy.run_path(path, run_name="__main__")
