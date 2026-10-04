# factorio-cartoon-mod

Mod Factorio (2.0) qui remplace les textures du jeu par une version au style cartoon.

## Principe

1. `tools/cartoonize.py` lit les sprites de ton installation de Factorio et applique un filtre cartoon (lissage, réduction des couleurs, saturation, contours noirs). Le canal alpha est conservé.
2. Les images converties sont écrites dans `graphics/<mod>/...` et la liste des fichiers est écrite dans `converted_paths.lua`.
3. `data-final-fixes.lua` remplace, dans tous les prototypes, les chemins `__base__/graphics/...` par les versions converties.

## Utilisation

```bash
pip install -r tools/requirements.txt
# test sur 20 sprites
python tools/cartoonize.py --data "<dossier Factorio>/data" --limit 20
# conversion complète (base + Space Age par exemple)
python tools/cartoonize.py --data "<dossier Factorio>/data" --mods base space-age
```

Puis copier ou lier ce dossier dans le dossier `mods/` de Factorio (renommé `factorio-cartoon-mod_0.0.1`).

## Notes

- Les textures générées ne sont pas versionnées (`graphics/` est ignoré) car elles dérivent des assets de Factorio.
- Les paramètres du filtre (nombre de couleurs, épaisseur des contours) sont à ajuster dans `tools/cartoonize.py`.

## À faire

- [ ] Tester le filtre sur quelques sprites et ajuster le rendu
- [ ] Gérer les icônes et l'interface (GUI)
- [ ] Remplacer à la main les assets les plus visibles (assembleurs, convoyeurs, personnage)
