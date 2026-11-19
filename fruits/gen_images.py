"""Génère les images de chaque scène (SDXL-Lightning 4 étapes, CPU).

Usage : python gen_images.py story.json dossier_sortie [nb_essais] [ids,separes,par,virgule]
"""
import json
import os
import sys
import time

import torch
from diffusers import EulerDiscreteScheduler, StableDiffusionXLPipeline, UNet2DConditionModel
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

story = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 3
only = set(int(x) for x in sys.argv[4].split(",")) if len(sys.argv) > 4 else None
os.makedirs(out, exist_ok=True)
torch.set_num_threads(os.cpu_count())

base = "stabilityai/stable-diffusion-xl-base-1.0"
unet = UNet2DConditionModel.from_config(base, subfolder="unet").to(torch.bfloat16)
unet.load_state_dict(
    load_file(hf_hub_download("ByteDance/SDXL-Lightning", "sdxl_lightning_4step_unet.safetensors"))
)
pipe = StableDiffusionXLPipeline.from_pretrained(
    base, unet=unet, torch_dtype=torch.bfloat16, variant="fp16"
)
pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")


def expand(desc):
    # remplace les noms de personnages par leur description complète
    for name, d in story["characters"].items():
        desc = desc.replace(name, d)
    return f"{desc}, {story['style']}"


for sc in story["scenes"]:
    if only and sc["id"] not in only:
        continue
    prompt = expand(sc["image"])
    for k in range(n):
        path = os.path.join(out, f"s{sc['id']:02d}_{k}.png")
        if os.path.exists(path):
            continue
        t = time.time()
        img = pipe(
            prompt=prompt, num_inference_steps=4, guidance_scale=0, width=768, height=1344,
            generator=torch.Generator().manual_seed(1000 * sc["id"] + k),
        ).images[0]
        img.save(path)
        print(f"scene {sc['id']} essai {k} : {time.time() - t:.0f}s", flush=True)
