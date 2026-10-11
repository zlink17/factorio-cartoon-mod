# Images cibles par ComfyUI (essai sur le propulseur, octobre 2026)

Méthode à l'essai : **ComfyUI produit l'image cible, Blender produit le sprite**. L'IA ne fait pas le sprite final :
elle propose des formes et des couleurs, guidée par la silhouette de l'original et par le style de nos sprites ;
Bastien choisit une variante, et le modèle Blender la reproduit (animations, cadrage, reproductibilité).

## Installation (faite le 11 octobre 2026, hors du repo)

- ComfyUI dans WSL : `~/workspace/comfyui`, environnement `.venv` (Python 3.12, torch cu128).
  Lancer : `cd ~/workspace/comfyui && .venv/bin/python main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch`
- Modèles (`~/workspace/comfyui/models/`) : DreamShaper XL Turbo v2.1 (openrail++), ControlNet Union SDXL promax de
  xinsir (Apache 2.0), IP-Adapter plus SDXL ViT-H et son encodeur CLIP ViT-H (Apache 2.0) ; nœuds
  `custom_nodes/ComfyUI_IPAdapter_plus`. Depth Anything V2 small (via `transformers`) pour la profondeur.
- GTX 1660 Super : environ 1 min 30 par image de 640 x 1280 en 8 pas.

## Scripts

| Script | Rôle |
|---|---|
| `prepare.py` | Guides depuis le sprite original : contours, profondeur, masque, cadre ; références de style (5 sprites du mod). Chemins du propulseur en dur. À lancer avec l'environnement de ComfyUI. |
| `concept.py` | Envoie le graphe à ComfyUI (profondeur + contours par ControlNet, style par IP-Adapter), une image par graine. `--init` + `--denoise` : part d'une image (mélange de deux variantes). Bibliothèque standard seulement. |
| `planche.py` | Planche de variantes avec leurs identifiants, en grand et à la taille du jeu sur une plateforme. |
| `compare.py` | Original, cible et rendu Blender côte à côte. |
| `run-mix.sh` | Exemple : dessin de la variante a-13, couleurs de la b-22. |

Réglages qui ont plu : `--style 0.55 --depth 0.7 --edges 0.35 --cfg 2.5` (couleurs vives) ; mélange en img2img
`--denoise 0.7 --edges 0.7` avec le trait de l'image de départ (`m70-42`, retenue pour le propulseur).

Résultats de l'essai (non versionnés) : `.cache/essai-propulseur/` ; modèle : `cartoon/blender/thruster.py`.
