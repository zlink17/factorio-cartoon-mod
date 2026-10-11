"""Images cibles par ComfyUI : SDXL (DreamShaper XL Turbo) guidé par la profondeur et les contours de l'original
(ControlNet Union, guides de prepare.py) et, si on en donne, par des images de style (IP-Adapter). Sert d'image
cible pour modéliser dans Blender, pas de sprite final. Serveur ComfyUI local (127.0.0.1:8188), voir README.

Usage : python -I tools/concept/concept.py <guides> <sortie> <graines> [--recette <mod>/concept/recette.json]
        [--base-prompt "..."] [--prompt ...] [--depth 0.6] [--edges 0.35] [--styles a.png,b.png --style 0.55]
        [--init image --denoise 0.7] [--tag v]
--recette : réglages propres à un mod (JSON : clés = noms des options, ex. "base_prompt", "neg", "styles", "style",
            "cfg") ; les options passées sur la ligne de commande l'emportent. Le texte de l'objet va dans --prompt.
Taille de génération : celle de guide-original.png (prepare.py), sauf --w/--h.
Écrit <sortie>/<tag>-<graine>.png ; ComfyUI est partagé entre les sessions : une génération à la fois.
"""
import argparse, json, os, time, urllib.request, uuid

API = "http://127.0.0.1:8188"

ap = argparse.ArgumentParser()
ap.add_argument("guides")
ap.add_argument("out")
ap.add_argument("seeds", type=lambda s: [int(x) for x in s.split(",")])
ap.add_argument("--prompt", default="")
ap.add_argument("--neg", default="photo, realistic, photorealistic, texture, noise, grain, rust, dirt, scratches, "
                "gradient, blurry, text, watermark, signature, perspective, 3/4 view, isometric")
ap.add_argument("--w", type=int)
ap.add_argument("--h", type=int)
ap.add_argument("--steps", type=int, default=8)
ap.add_argument("--cfg", type=float, default=2.0)
ap.add_argument("--depth", type=float, default=0.65)
ap.add_argument("--edges", type=float, default=0.45)
ap.add_argument("--style", type=float, default=0.8)
ap.add_argument("--tag", default="v")
ap.add_argument("--init", help="image de départ (img2img) ; sinon génération libre")
ap.add_argument("--denoise", type=float, default=1.0)
ap.add_argument("--edges-file", default="guide-contours.png", help="dans le dossier des guides")
ap.add_argument("--depth-file", default="guide-profondeur.png")
ap.add_argument("--styles", default="", help="références de style (chemins relatifs aux guides, ou absolus) ; aucune par défaut")
ap.add_argument("--ckpt", default="DreamShaperXL_Turbo_v2_1.safetensors", help="modèle (models/checkpoints)")
ap.add_argument("--lora", action="append", default=[], help="LoRA (models/loras) : nom.safetensors:poids, répétable")
ap.add_argument("--sampler", default="dpmpp_sde")
ap.add_argument("--scheduler", default="karras")
ap.add_argument("--base-prompt", help="style du mod (souvent dans la recette)")
ap.add_argument("--recette", help="réglages du mod (JSON)")
pre, _ = ap.parse_known_args()
if pre.recette:
    ap.set_defaults(**json.load(open(pre.recette)))
a = ap.parse_args()
if not a.base_prompt:
    ap.error("--base-prompt (ou une recette qui le donne) est obligatoire")
if not (a.w and a.h):
    from struct import unpack
    with open(os.path.join(a.guides, "guide-original.png"), "rb") as fh:     # en-tête PNG : largeur, hauteur
        a.w, a.h = unpack(">II", fh.read(24)[16:24])


def upload(path):
    name = f"{uuid.uuid4().hex[:8]}-{os.path.basename(path)}"
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + open(path, "rb").read() + \
           f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(API + "/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.load(urllib.request.urlopen(req))["name"]


def call(path, data=None):
    req = urllib.request.Request(API + path, json.dumps(data).encode() if data else None,
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


depth = upload(os.path.join(a.guides, a.depth_file))
edges = upload(os.path.join(a.guides, a.edges_file))
styles = [upload(os.path.join(a.guides, p)) for p in a.styles.split(",") if p]

positive = a.base_prompt + " " + a.prompt

g = {
    "ckpt": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": a.ckpt}},
    "cn": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "controlnet-union-sdxl-promax.safetensors"}},
    "cn_d": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["cn", 0], "type": "depth"}},
    "cn_e": {"class_type": "SetUnionControlNetType",
             "inputs": {"control_net": ["cn", 0], "type": "canny/lineart/anime_lineart/mlsd"}},
    "img_d": {"class_type": "LoadImage", "inputs": {"image": depth}},
    "img_e": {"class_type": "LoadImage", "inputs": {"image": edges}},
    "app_d": {"class_type": "ControlNetApplyAdvanced",
              "inputs": {"positive": ["pos", 0], "negative": ["neg", 0], "control_net": ["cn_d", 0],
                         "image": ["img_d", 0], "strength": a.depth, "start_percent": 0.0, "end_percent": 0.8,
                         "vae": ["ckpt", 2]}},
    "app_e": {"class_type": "ControlNetApplyAdvanced",
              "inputs": {"positive": ["app_d", 0], "negative": ["app_d", 1], "control_net": ["cn_e", 0],
                         "image": ["img_e", 0], "strength": a.edges, "start_percent": 0.0, "end_percent": 0.6,
                         "vae": ["ckpt", 2]}},
    "ipa": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}},
    "clipv": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}},
}
# LoRA en chaîne sur le modèle et l'encodeur de texte
unet, clip = ["ckpt", 0], ["ckpt", 1]
for i, spec in enumerate(a.lora):
    name, _, weight = spec.rpartition(":")
    g[f"lora{i}"] = {"class_type": "LoraLoader", "inputs": {"model": unet, "clip": clip, "lora_name": name,
                                                           "strength_model": float(weight), "strength_clip": float(weight)}}
    unet, clip = [f"lora{i}", 0], [f"lora{i}", 1]
g["pos"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": positive}}
g["neg"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip, "text": a.neg}}
prev = None
for i, s in enumerate(styles):
    g[f"st{i}"] = {"class_type": "LoadImage", "inputs": {"image": s}}
    if prev is None:
        prev = [f"st{i}", 0]
    else:
        g[f"bt{i}"] = {"class_type": "ImageBatch", "inputs": {"image1": prev, "image2": [f"st{i}", 0]}}
        prev = [f"bt{i}", 0]
model = unet
if styles:
    g["ip"] = {"class_type": "IPAdapterAdvanced",
               "inputs": {"model": unet, "ipadapter": ["ipa", 0], "image": prev, "weight": a.style,
                          "weight_type": "style transfer", "combine_embeds": "average", "start_at": 0.0,
                          "end_at": 1.0, "embeds_scaling": "V only", "clip_vision": ["clipv", 0]}}
    model = ["ip", 0]
else:
    del g["ipa"], g["clipv"]
if a.init:
    g["init"] = {"class_type": "LoadImage", "inputs": {"image": upload(a.init)}}
    g["init_s"] = {"class_type": "ImageScale", "inputs": {"image": ["init", 0], "upscale_method": "lanczos",
                                                         "width": a.w, "height": a.h, "crop": "disabled"}}
    g["lat"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["init_s", 0], "vae": ["ckpt", 2]}}
else:
    g["lat"] = {"class_type": "EmptyLatentImage", "inputs": {"width": a.w, "height": a.h, "batch_size": 1}}
g["ks"] = {"class_type": "KSampler",
           "inputs": {"model": model, "positive": ["app_e", 0], "negative": ["app_e", 1], "latent_image": ["lat", 0],
                      "seed": 0, "steps": a.steps, "cfg": a.cfg, "sampler_name": a.sampler, "scheduler": a.scheduler,
                      "denoise": a.denoise}}
g["dec"] = {"class_type": "VAEDecode", "inputs": {"samples": ["ks", 0], "vae": ["ckpt", 2]}}
g["save"] = {"class_type": "SaveImage", "inputs": {"images": ["dec", 0], "filename_prefix": "concept"}}

os.makedirs(a.out, exist_ok=True)
for seed in a.seeds:
    g["ks"]["inputs"]["seed"] = seed
    t0 = time.time()
    pid = call("/prompt", {"prompt": g, "client_id": "concept"})["prompt_id"]
    while True:
        h = call(f"/history/{pid}")
        if pid in h:
            break
        time.sleep(2)
    st = h[pid]["status"]
    if st.get("status_str") != "success":
        raise SystemExit(json.dumps(st, indent=1)[:3000])
    img = h[pid]["outputs"]["save"]["images"][0]
    data = urllib.request.urlopen(f"{API}/view?filename={img['filename']}&subfolder={img['subfolder']}&type=output").read()
    dst = f"{a.out}/{a.tag}-{seed}.png"
    open(dst, "wb").write(data)
    print(dst, f"{time.time() - t0:.0f} s", flush=True)
