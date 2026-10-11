"""Bibliothèque commune du mod pixel : palette fermée, passe pixel, cadrage dans le cadre de l'original.

Tout générateur du mod (Pillow ou Blender) produit son art à 16 px par case, puis :
    a = passe.passe(art)                        # palette, contours, nettoyage
    big = cadre.place(a, ancre, (W, H), shift)  # cadre exact de l'original, aligné sur la grille du monde
    cadre.save(big, out, "base/entity/x/x.png")
"""
