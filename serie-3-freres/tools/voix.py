"""Génère les voix françaises de chaque réplique + horodatage mot par mot.

Fournisseurs :
  edge        voix neuronales Microsoft Edge (gratuit, sans clé) — PAR DÉFAUT
  elevenlabs  ElevenLabs multilingual v2 (variable ELEVENLABS_API_KEY ; voice_id par personnage
              dans data/personnages.json -> voix.elevenlabs)

Usage : python tools/voix.py --episode 1 [--fournisseur edge]
Sortie : sorties/epXX/voix/sYY_Z.mp3 + lignes.json (texte, personnage, mots horodatés)
"""
import argparse
import asyncio
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import charger_episode, charger_personnages, dossier_travail  # noqa: E402


async def edge(texte, cfg, chemin):
    import edge_tts
    com = edge_tts.Communicate(texte, cfg["edge"], rate=cfg.get("rate", "+0%"),
                               pitch=cfg.get("pitch", "+0Hz"), boundary="WordBoundary",
                               proxy=os.environ.get("HTTPS_PROXY"))
    mots = []
    with open(chemin, "wb") as f:
        async for c in com.stream():
            if c["type"] == "audio":
                f.write(c["data"])
            elif c["type"] == "WordBoundary":
                mots.append({"start": c["offset"] / 1e7,
                             "end": (c["offset"] + c["duration"]) / 1e7, "word": c["text"]})
    return mots


def elevenlabs(texte, cfg, chemin):
    """Renvoie l'audio + l'horodatage par caractère, regroupé en mots."""
    import base64
    vid = cfg["elevenlabs"]
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps",
        json.dumps({"text": texte, "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.5}}).encode(),
        {"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    open(chemin, "wb").write(base64.b64decode(r["audio_base64"]))
    al = r["alignment"]
    mots, cur, deb = [], "", None
    for ch, s, e in zip(al["characters"], al["character_start_times_seconds"],
                        al["character_end_times_seconds"]):
        if ch.isspace():
            if cur:
                mots.append({"start": deb, "end": fin, "word": cur})
            cur, deb = "", None
        else:
            deb = s if deb is None else deb
            cur += ch
            fin = e
    if cur:
        mots.append({"start": deb, "end": fin, "word": cur})
    return mots


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--fournisseur", default=os.environ.get("FOURNISSEUR_VOIX", "edge"))
    a = ap.parse_args()
    ep = charger_episode(a.episode)
    perso = charger_personnages()["personnages"]
    dossier = dossier_travail(a.episode, "voix")
    meta = {}
    for sc in ep["scenes"]:
        for j, ligne in enumerate(sc["lignes"]):
            qui, texte = ligne[0], ligne[1]
            cle = f"s{sc['id']:02d}_{j}"
            chemin = os.path.join(dossier, cle + ".mp3")
            cfg = perso[qui]["voix"]
            if a.fournisseur == "elevenlabs" and "elevenlabs" in cfg:
                mots = elevenlabs(texte, cfg, chemin)
            else:
                mots = await edge(texte, cfg, chemin)
            meta[cle] = {"qui": qui, "texte": texte, "mots": mots}
            print(f"ep{a.episode} {cle} {qui}: {texte}", flush=True)
    json.dump(meta, open(os.path.join(dossier, "lignes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    asyncio.run(main())
