#!/usr/bin/env python3
"""Test de comfy_batch.py contre un faux serveur ComfyUI (aucun vrai ComfyUI nécessaire).

Usage : python tools/complex/test_comfy_batch.py
Vérifie : envoi de l'image, remplacement de l'image / de la graine / des prompts,
attente du résultat, téléchargement, refus d'un workflow non exporté en format API.
"""
import json
import os
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_batch

PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
STATE = {"uploads": [], "prompts": [], "polls": 0}


class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/system_stats"):
            self._send({"devices": [{"name": "FAUX GPU 6 Go"}]})
        elif self.path.startswith("/history/"):
            STATE["polls"] += 1
            if STATE["polls"] % 2:                       # premier appel : pas encore fini
                self._send({})
            else:
                self._send({"p1": {"status": {"status_str": "success", "completed": True},
                                   "outputs": {"9": {"images": [{"filename": "o.png", "subfolder": "", "type": "output"}]}}}})
        elif self.path.startswith("/view"):
            self._send(PNG, "image/png")
        else:
            self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        if self.path == "/upload/image":
            m = re.search(rb'filename="([^"]+)"', body)
            STATE["uploads"].append(m.group(1).decode())
            self._send({"name": m.group(1).decode(), "subfolder": "", "type": "input"})
        elif self.path == "/prompt":
            STATE["prompts"].append(json.loads(body)["prompt"])
            self._send({"prompt_id": "p1"})
        else:
            self.send_error(404)


WORKFLOW = {
    "3": {"class_type": "KSampler", "inputs": {"seed": 1, "steps": 20, "positive": ["6", 0], "negative": ["7", 0]}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "ancien positif"}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "ancien negatif"}},
    "10": {"class_type": "LoadImage", "inputs": {"image": "vieux.png"}},
}


def main():
    srv = HTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    with tempfile.TemporaryDirectory() as d:
        wf = os.path.join(d, "wf.json")
        json.dump(WORKFLOW, open(wf, "w"))
        os.makedirs(os.path.join(d, "in"))
        for name in ("a.png", "b.png"):
            open(os.path.join(d, "in", name), "wb").write(PNG)
        out = os.path.join(d, "out")
        comfy_batch.main(["--workflow", wf, "--input", os.path.join(d, "in"), "--output", out,
                          "--server", url, "--seeds", "2", "--prompt", "cartoon", "--negative", "photo"])
        files = sorted(os.listdir(out))
        assert len(files) == 4, files                                   # 2 images x 2 graines
        assert all(f.endswith(".png") and os.path.getsize(os.path.join(out, f)) == len(PNG) for f in files)
        assert STATE["uploads"] == ["a.png", "b.png"], STATE["uploads"]
        assert len(STATE["prompts"]) == 4
        p = STATE["prompts"][0]
        assert p["10"]["inputs"]["image"] == "a.png"
        assert p["6"]["inputs"]["text"] == "cartoon" and p["7"]["inputs"]["text"] == "photo"
        assert p["3"]["inputs"]["seed"] != 1
        assert WORKFLOW["6"]["inputs"]["text"] == "ancien positif"      # l'original n'est pas modifié
        # un workflow « interface » est refusé avec un message clair
        ui = os.path.join(d, "ui.json")
        json.dump({"nodes": [], "links": []}, open(ui, "w"))
        try:
            comfy_batch.main(["--workflow", ui, "--input", os.path.join(d, "in"), "--output", out, "--server", url])
        except SystemExit as e:
            assert "API Format" in str(e)
        else:
            raise AssertionError("workflow interface accepté")
    # workflow réel avec ControlNet : les prompts sont retrouvés à travers ControlNetApplyAdvanced
    real = comfy_batch.load_workflow(os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows", "sd15_canny_api.json"))
    q = comfy_batch.patch(real, "x.png", 123, prompt="P", negative="N")
    assert q["2"]["inputs"]["image"] == "x.png" and q["10"]["inputs"]["seed"] == 123
    assert q["5"]["inputs"]["text"] == "P" and q["6"]["inputs"]["text"] == "N"
    assert real["5"]["inputs"]["text"] != "P"
    print("TOUS LES TESTS PASSENT")


if __name__ == "__main__":
    main()
