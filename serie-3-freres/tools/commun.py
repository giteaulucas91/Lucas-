"""Fonctions partagées par tous les outils de production."""
import json
import os
import re

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RACINE, "data")
EPISODES = os.path.join(RACINE, "episodes")
SORTIES = os.path.join(RACINE, "sorties")
FONTS = os.path.join(RACINE, "assets", "polices")


def charger_personnages():
    return json.load(open(os.path.join(DATA, "personnages.json"), encoding="utf-8"))


def dossier_episode(num):
    return os.path.join(EPISODES, f"ep{int(num):02d}")


def charger_episode(num):
    return json.load(open(os.path.join(dossier_episode(num), "episode.json"), encoding="utf-8"))


def dossier_travail(num, *sous):
    """Dossier des fichiers générés (images, voix...) d'un épisode — hors Git."""
    d = os.path.join(SORTIES, f"ep{int(num):02d}", *sous)
    os.makedirs(d, exist_ok=True)
    return d


def prompt_scene(scene, perso=None):
    """Construit le prompt image complet : étiquettes d'émotion + visuels canoniques + style."""
    perso = perso or charger_personnages()
    texte = scene["image"]
    for tag, val in perso.get("emotions", {}).items():
        texte = texte.replace("{" + tag + "}", val)
    # les clés les plus longues d'abord pour éviter les remplacements partiels
    for cle in sorted(perso["personnages"], key=len, reverse=True):
        p = perso["personnages"][cle]
        if "visuel" in p:
            texte = re.sub(rf"\b{cle}\b", lambda m: p["visuel"], texte)
    return f"{perso.get('prefixe', '')}, {texte}, {perso['style']}"
