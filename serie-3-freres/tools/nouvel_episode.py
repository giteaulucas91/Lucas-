"""Prépare le squelette d'un nouvel épisode à partir de l'arc de saison.

Usage : python tools/nouvel_episode.py 11
  -> crée episodes/ep11/episode.json pré-rempli (titre, résumé et cliffhanger tirés de
     bible/ARC_30_EPISODES.md) avec 10 plans vides à compléter.

Règles rappelées dans le fichier : accroche < 2 s, 110-150 mots, 10-12 plans, un rebondissement
au milieu, un cliffhanger, et les clés de personnages en MAJUSCULES dans les prompts.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import RACINE, dossier_episode  # noqa: E402


def lire_arc(num):
    for ligne in open(os.path.join(RACINE, "bible", "ARC_30_EPISODES.md"), encoding="utf-8"):
        m = re.match(rf"\|\s*{num}\s*\|\s*\*\*(.+?)\*\*\s*\|(.+?)\|(.+?)\|", ligne)
        if m:
            return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return f"Épisode {num}", "À écrire.", "À écrire."


def main():
    num = int(sys.argv[1])
    d = dossier_episode(num)
    chemin = os.path.join(d, "episode.json")
    if os.path.exists(chemin):
        sys.exit(f"{chemin} existe déjà.")
    titre, resume, cliff = lire_arc(num)
    musiques = ["mystere", "tension", "tension", "triste", "tension", "espoir", "tension", "mystere", "tension", "tension"]
    ep = {
        "numero": num, "titre": titre, "question": "À écrire : la question que se pose le spectateur",
        "resume": resume, "intrigues_semees": [], "cliffhanger": cliff,
        "_regles": "Accroche < 2 s (plan 1). 110-150 mots au total. 1-2 répliques par plan. "
                   "Personnages en MAJUSCULES dans 'image' (PERE, LUCAS, ENZO, MATHIS, CLARA, KEVIN, SOFIA, OMBRE). "
                   "Préciser l'émotion du visage dans chaque prompt. Dernier plan : 'ecran': 'PARTIE N+1 →'.",
        "scenes": [
            {"id": i + 1, "lieu": "", "plan": "", "image": "", "musique": musiques[i],
             "lignes": [["NARRATEUR", ""]]} for i in range(10)
        ],
    }
    ep["scenes"][-1]["ecran"] = f"PARTIE {num + 1} →"
    os.makedirs(d, exist_ok=True)
    json.dump(ep, open(chemin, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("créé :", chemin)


if __name__ == "__main__":
    main()
