"""Génération des images de scènes.

Fournisseurs :
  local      SDXL-Lightning 4 étapes sur CPU/GPU (gratuit, aucune clé) — PAR DÉFAUT
  fal        FLUX via fal.ai                         (variable FAL_KEY)
  replicate  FLUX via Replicate                      (variable REPLICATE_API_TOKEN)
  openai     gpt-image-1 via OpenAI                  (variable OPENAI_API_KEY)

Usage :
  python tools/images.py --episode 1 [--essais 2] [--scenes 1,4] [--fournisseur local]
  python tools/images.py --portraits            # images de référence des personnages
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import RACINE, charger_episode, charger_personnages, dossier_travail, prompt_scene  # noqa: E402

LARGEUR, HAUTEUR = 768, 1344  # 9:16 environ, recadré au montage


# ------------------------------------------------------------------ local
class Local:
    def __init__(self):
        import torch
        from compel import Compel, ReturnedEmbeddingsType
        from diffusers import EulerDiscreteScheduler, StableDiffusionXLPipeline, UNet2DConditionModel
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file

        self.torch = torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if dev == "cuda" else torch.bfloat16
        torch.set_num_threads(os.cpu_count())
        base = "stabilityai/stable-diffusion-xl-base-1.0"
        unet = UNet2DConditionModel.from_config(base, subfolder="unet").to(dtype)
        unet.load_state_dict(load_file(
            hf_hub_download("ByteDance/SDXL-Lightning", "sdxl_lightning_4step_unet.safetensors")))
        pipe = StableDiffusionXLPipeline.from_pretrained(base, unet=unet, torch_dtype=dtype, variant="fp16")
        pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
        self.pipe = pipe.to(dev)
        # Compel : prompts longs (> 77 tokens) sans troncature
        self.compel = Compel(
            tokenizer=[pipe.tokenizer, pipe.tokenizer_2],
            text_encoder=[pipe.text_encoder, pipe.text_encoder_2],
            returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
            requires_pooled=[False, True], truncate_long_prompts=False,
        )

    def generer(self, prompt, graine, chemin):
        cond, pooled = self.compel(prompt)
        img = self.pipe(
            prompt_embeds=cond, pooled_prompt_embeds=pooled, num_inference_steps=4,
            guidance_scale=0, width=LARGEUR, height=HAUTEUR,
            generator=self.torch.Generator().manual_seed(graine),
        ).images[0]
        img.save(chemin)


# ------------------------------------------------------------------ API externes
def _post(url, donnees, entetes):
    req = urllib.request.Request(url, json.dumps(donnees).encode(), entetes)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def _telecharger(url, chemin):
    urllib.request.urlretrieve(url, chemin)


class Fal:
    """https://fal.ai/models/fal-ai/flux-pro — clé dans FAL_KEY."""
    def __init__(self):
        self.cle = os.environ["FAL_KEY"]

    def generer(self, prompt, graine, chemin):
        r = _post("https://fal.run/fal-ai/flux-pro/v1.1",
                  {"prompt": prompt, "seed": graine, "image_size": "portrait_16_9",
                   "num_images": 1, "safety_tolerance": "2"},
                  {"Authorization": f"Key {self.cle}", "Content-Type": "application/json"})
        _telecharger(r["images"][0]["url"], chemin)


class Replicate:
    """https://replicate.com/black-forest-labs/flux-1.1-pro — clé dans REPLICATE_API_TOKEN."""
    def __init__(self):
        self.cle = os.environ["REPLICATE_API_TOKEN"]

    def generer(self, prompt, graine, chemin):
        r = _post("https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions",
                  {"input": {"prompt": prompt, "seed": graine, "aspect_ratio": "9:16",
                             "output_format": "png"}},
                  {"Authorization": f"Bearer {self.cle}", "Content-Type": "application/json",
                   "Prefer": "wait"})
        sortie = r["output"]
        _telecharger(sortie if isinstance(sortie, str) else sortie[0], chemin)


class OpenAI:
    """gpt-image-1 — clé dans OPENAI_API_KEY."""
    def __init__(self):
        self.cle = os.environ["OPENAI_API_KEY"]

    def generer(self, prompt, graine, chemin):
        r = _post("https://api.openai.com/v1/images/generations",
                  {"model": "gpt-image-1", "prompt": prompt, "size": "1024x1536", "n": 1},
                  {"Authorization": f"Bearer {self.cle}", "Content-Type": "application/json"})
        open(chemin, "wb").write(base64.b64decode(r["data"][0]["b64_json"]))


FOURNISSEURS = {"local": Local, "fal": Fal, "replicate": Replicate, "openai": OpenAI}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int)
    ap.add_argument("--essais", type=int, default=2)
    ap.add_argument("--scenes", default=None)
    ap.add_argument("--fournisseur", default=os.environ.get("FOURNISSEUR_IMAGES", "local"))
    ap.add_argument("--portraits", action="store_true")
    a = ap.parse_args()
    moteur = FOURNISSEURS[a.fournisseur]()
    perso = charger_personnages()

    if a.portraits:
        dossier = os.path.join(RACINE, "assets", "personnages")
        for i, (cle, p) in enumerate(perso["personnages"].items()):
            if "visuel" not in p:
                continue
            for k in range(a.essais):
                chemin = os.path.join(dossier, f"{cle.lower()}_{k}.png")
                if os.path.exists(chemin):
                    continue
                prompt = (f"full body portrait of {p['visuel']}, standing, neutral studio background, "
                          f"{perso['style']}")
                t = time.time()
                moteur.generer(prompt, 777 + 10 * i + k, chemin)
                print(f"portrait {cle} {k} : {time.time() - t:.0f}s", flush=True)
        return

    ep = charger_episode(a.episode)
    dossier = dossier_travail(a.episode, "images")
    garder = set(int(x) for x in a.scenes.split(",")) if a.scenes else None
    for sc in ep["scenes"]:
        if garder and sc["id"] not in garder:
            continue
        prompt = prompt_scene(sc, perso)
        for k in range(a.essais):
            chemin = os.path.join(dossier, f"s{sc['id']:02d}_{k}.png")
            if os.path.exists(chemin):
                continue
            t = time.time()
            moteur.generer(prompt, a.episode * 10000 + sc["id"] * 100 + k + sc.get("graine", 0), chemin)
            print(f"ep{a.episode} scène {sc['id']} essai {k} : {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
