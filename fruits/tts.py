"""Génère les voix (edge-tts) + horodatage mot par mot pour chaque réplique.

Usage : python tts.py story.json dossier_sortie
"""
import asyncio
import json
import os
import sys

import edge_tts

story = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
proxy = os.environ.get("HTTPS_PROXY")


async def say(text, cfg, path):
    com = edge_tts.Communicate(
        text, cfg["voice"], rate=cfg["rate"], pitch=cfg["pitch"],
        boundary="WordBoundary", proxy=proxy,
    )
    words = []
    with open(path, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "start": chunk["offset"] / 1e7,
                    "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                    "word": chunk["text"],
                })
    return words


async def main():
    meta = {}
    for sc in story["scenes"]:
        for j, (who, text) in enumerate(sc["lines"]):
            key = f"s{sc['id']:02d}_{j}"
            path = os.path.join(out, key + ".mp3")
            words = await say(text, story["voices"][who], path)
            meta[key] = {"who": who, "text": text, "words": words}
            print(key, who, len(words), "mots", flush=True)
    json.dump(meta, open(os.path.join(out, "lines.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


asyncio.run(main())
