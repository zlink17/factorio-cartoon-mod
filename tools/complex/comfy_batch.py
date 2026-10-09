#!/usr/bin/env python3
"""Envoie des images à un ComfyUI local (API HTTP) et récupère les résultats.

Aucune dépendance : bibliothèque standard uniquement.

Principe : tu construis un workflow qui marche dans l'interface de ComfyUI (image de départ +
ControlNet + modèle cartoon), tu l'exportes avec « Save (API Format) », puis ce script le rejoue
sur chaque image d'un dossier en changeant l'image d'entrée, la graine et, si demandé, le prompt.

Exemple (PowerShell, ComfyUI lancé sur le port 8188) :
    py tools\\complex\\comfy_batch.py --workflow workflow_api.json ^
        --input entrees\\ --output sorties\\ --seeds 4 ^
        --prompt "cartoon game sprite, thick dark outline, flat colors, top-down"

Les sorties sont enregistrées sous <sortie>/<nom>__s<graine>.png. Pour les mettre au bon format
(détourage + taille exacte du sprite original), voir postprocess.py.
"""
import argparse
import json
import mimetypes
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")


# --- HTTP ---------------------------------------------------------------------------------
def http(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_json(url, payload=None):
    if payload is None:
        return json.loads(http(url))
    body = json.dumps(payload).encode("utf-8")
    return json.loads(http(url, body, {"Content-Type": "application/json"}))


def upload_image(server, path):
    """Envoie une image dans le dossier input de ComfyUI et renvoie le nom à utiliser."""
    boundary = uuid.uuid4().hex
    name = os.path.basename(path)
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        content = f.read()
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
        f"Content-Type: {ctype}\r\n\r\n".encode(), content, b"\r\n",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{boundary}--\r\n".encode(),
    ]
    resp = json.loads(http(f"{server}/upload/image", b"".join(parts),
                           {"Content-Type": f"multipart/form-data; boundary={boundary}"}))
    return resp["name"] if not resp.get("subfolder") else f"{resp['subfolder']}/{resp['name']}"


# --- Workflow -------------------------------------------------------------------------------
def load_workflow(path):
    with open(path, encoding="utf-8") as f:
        wf = json.load(f)
    if "nodes" in wf and "links" in wf:
        sys.exit("Ce fichier est un workflow « interface ». Exporte-le avec Save (API Format) "
                 "(menu Workflow > Export (API)).")
    return wf


def nodes_of(wf, *class_types):
    return [(nid, n) for nid, n in wf.items() if n.get("class_type") in class_types]


def sampler(wf):
    found = nodes_of(wf, "KSampler", "KSamplerAdvanced")
    if not found:
        sys.exit("Aucun nœud KSampler dans le workflow.")
    return found[0]


def linked_node(wf, ref):
    """ref = ['id', sortie] -> identifiant du nœud relié, sinon None."""
    return str(ref[0]) if isinstance(ref, list) and ref else None


def patch(wf, image_name, seed, prompt=None, negative=None, image_node=None,
          positive_node=None, negative_node=None):
    wf = json.loads(json.dumps(wf))                      # copie profonde
    # image d'entrée
    if image_node is None:
        loaders = nodes_of(wf, "LoadImage")
        if not loaders:
            sys.exit("Aucun nœud LoadImage dans le workflow (ou précise --image-node).")
        image_node = loaders[0][0]
    wf[str(image_node)]["inputs"]["image"] = image_name
    # graine
    sid, snode = sampler(wf)
    key = "noise_seed" if "noise_seed" in snode["inputs"] else "seed"
    snode["inputs"][key] = seed
    # prompts : on suit les liens positive/negative du sampler
    if prompt is not None:
        pid = positive_node or linked_node(wf, snode["inputs"].get("positive"))
        if pid is None or "text" not in wf[str(pid)]["inputs"]:
            sys.exit("Impossible de trouver le nœud du prompt positif (précise --positive-node).")
        wf[str(pid)]["inputs"]["text"] = prompt
    if negative is not None:
        nid = negative_node or linked_node(wf, snode["inputs"].get("negative"))
        if nid is None or "text" not in wf[str(nid)]["inputs"]:
            sys.exit("Impossible de trouver le nœud du prompt négatif (précise --negative-node).")
        wf[str(nid)]["inputs"]["text"] = negative
    return wf


# --- Exécution ------------------------------------------------------------------------------
def run(server, wf, timeout):
    """Lance le workflow, attend la fin et renvoie la liste des images produites."""
    try:
        resp = http_json(f"{server}/prompt", {"prompt": wf, "client_id": uuid.uuid4().hex})
    except urllib.error.HTTPError as e:
        sys.exit(f"ComfyUI a refusé le workflow ({e.code}) : {e.read().decode('utf-8', 'replace')[:800]}")
    pid = resp["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = http_json(f"{server}/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                sys.exit(f"Erreur dans ComfyUI : {json.dumps(status.get('messages', ''))[:800]}")
            images = []
            for out in entry.get("outputs", {}).values():
                images += out.get("images", [])
            if images or status.get("completed"):
                return images
        time.sleep(1.0)
    sys.exit(f"Délai dépassé ({timeout} s) pour le travail {pid}.")


def fetch(server, info):
    q = urllib.parse.urlencode({"filename": info["filename"], "subfolder": info.get("subfolder", ""),
                                "type": info.get("type", "output")})
    return http(f"{server}/view?{q}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflow", required=True, help="Workflow exporté avec Save (API Format)")
    ap.add_argument("--input", required=True, help="Image ou dossier d'images d'entrée")
    ap.add_argument("--output", required=True, help="Dossier des résultats")
    ap.add_argument("--server", default="http://127.0.0.1:8188")
    ap.add_argument("--seeds", type=int, default=1, help="Nombre de variantes par image")
    ap.add_argument("--seed", type=int, help="Graine fixe (avec --seeds 1)")
    ap.add_argument("--prompt", help="Remplace le prompt positif")
    ap.add_argument("--negative", help="Remplace le prompt négatif")
    ap.add_argument("--image-node", help="Id du nœud LoadImage (sinon le premier)")
    ap.add_argument("--positive-node", help="Id du nœud de prompt positif (sinon suivi depuis le KSampler)")
    ap.add_argument("--negative-node", help="Id du nœud de prompt négatif")
    ap.add_argument("--timeout", type=int, default=900, help="Secondes max par image")
    ap.add_argument("--dry-run", action="store_true", help="Affiche le workflow modifié sans l'envoyer")
    a = ap.parse_args(argv)

    wf = load_workflow(a.workflow)
    if os.path.isdir(a.input):
        files = sorted(os.path.join(a.input, f) for f in os.listdir(a.input) if f.lower().endswith(IMAGE_EXT))
    else:
        files = [a.input]
    if not files:
        sys.exit("Aucune image d'entrée.")
    os.makedirs(a.output, exist_ok=True)

    if not a.dry_run:
        try:
            stats = http_json(f"{a.server}/system_stats")
        except Exception as e:
            sys.exit(f"ComfyUI ne répond pas sur {a.server} ({e}). Est-il lancé ?")
        devs = ", ".join(d.get("name", "?") for d in stats.get("devices", []))
        print(f"Connecté à ComfyUI ({devs}).")

    total = 0
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        name = None if a.dry_run else upload_image(a.server, path)
        for k in range(a.seeds):
            seed = a.seed if (a.seed is not None and a.seeds == 1) else random.randint(0, 2**32 - 1)
            patched = patch(wf, name or os.path.basename(path), seed, a.prompt, a.negative,
                            a.image_node, a.positive_node, a.negative_node)
            if a.dry_run:
                print(json.dumps(patched, indent=1, ensure_ascii=False))
                continue
            t0 = time.time()
            images = run(a.server, patched, a.timeout)
            for j, info in enumerate(images):
                suffix = f"_{j}" if len(images) > 1 else ""
                out = os.path.join(a.output, f"{stem}__s{seed}{suffix}.png")
                with open(out, "wb") as f:
                    f.write(fetch(a.server, info))
                total += 1
                print(f"OK {out} ({time.time() - t0:.0f} s)")
    print(f"Terminé : {total} image(s).")


if __name__ == "__main__":
    main()
