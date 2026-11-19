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
    """Construit le prompt image complet : description de la scène + visuels canoniques + style."""
    perso = perso or charger_personnages()
    # les émotions de la scène sont renforcées pour que les visages ne sourient pas par défaut
    texte = EMOTIONS.sub(lambda m: f"({m.group(0)})1.35", scene["image"])
    # les clés les plus longues d'abord pour éviter les remplacements partiels
    for cle in sorted(perso["personnages"], key=len, reverse=True):
        p = perso["personnages"][cle]
        if "visuel" in p and cle in texte:
            texte = texte.replace(cle, p["visuel"])
    return f"{perso.get('prefixe', '')}, {texte}, {perso['style']}"


EMOTIONS = re.compile(
    r"\b((?:very |extremely )?(?:angry|furious|shocked|surprised|sad|crying|tears|teary|worried|serious|severe|"
    r"cold|coldly|stern|terrified|scared|panicked|guilty|nervous|devastated|exhausted|tired|desperate|"
    r"suspicious|menacing|evil|sly|greedy|excited|happy|joyful|laughing|smiling|smile|determined|"
    r"thoughtful|hesitating|confused|frowning|disgusted|emotional|hopeful|proud|arrogant|cocky|"
    r"mysterious|fear|pale|wide eyes|open mouth|mouth wide open|cheering|hugging)(?: face| expression| eyes| smile)?)\b")
