"""Chaîne complète pour un ou plusieurs épisodes : voix -> images -> documents -> montage.

Usage :
  python tools/produire.py 1            # épisode 1
  python tools/produire.py 1-10         # épisodes 1 à 10
  python tools/produire.py 3 --essais 3 # 3 propositions d'image par plan

Les étapes déjà faites sont sautées (images/voix existantes). Après la génération, regardez
sorties/epXX/planche.jpg et notez dans episodes/epXX/choix.json l'image retenue par plan,
puis relancez uniquement le montage : python tools/montage.py --episode X
"""
import argparse
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import charger_episode, dossier_travail  # noqa: E402

OUTILS = os.path.dirname(os.path.abspath(__file__))


def lancer(*args):
    print(">>", " ".join(args), flush=True)
    subprocess.run([sys.executable, *args], check=True)


def planche(num):
    """Planche-contact de toutes les propositions d'images (pour choisir)."""
    import cv2
    import numpy as np
    ep = charger_episode(num)
    d = dossier_travail(num, "images")
    rangees = []
    for sc in ep["scenes"]:
        fs = sorted(glob.glob(os.path.join(d, f"s{sc['id']:02d}_*.png")))
        vignettes = []
        for f in fs:
            im = cv2.resize(cv2.imread(f), (180, 320))
            cv2.putText(im, os.path.basename(f)[:-4], (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            vignettes.append(im)
        if vignettes:
            rangees.append(np.hstack(vignettes + [np.zeros_like(vignettes[0])] * (4 - len(vignettes))))
    if rangees:
        cv2.imwrite(os.path.join(dossier_travail(num), "planche.jpg"), np.vstack(rangees))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episodes")
    ap.add_argument("--essais", type=int, default=2)
    a = ap.parse_args()
    if "-" in a.episodes:
        d, f = map(int, a.episodes.split("-"))
        nums = range(d, f + 1)
    else:
        nums = [int(a.episodes)]
    for n in nums:
        if not os.path.exists(os.path.join(dossier_travail(n, "voix"), "lignes.json")):
            lancer(os.path.join(OUTILS, "voix.py"), "--episode", str(n))
        lancer(os.path.join(OUTILS, "images.py"), "--episode", str(n), "--essais", str(a.essais))
        planche(n)
        lancer(os.path.join(OUTILS, "documents.py"), "--episode", str(n))
        lancer(os.path.join(OUTILS, "montage.py"), "--episode", str(n))


if __name__ == "__main__":
    main()
