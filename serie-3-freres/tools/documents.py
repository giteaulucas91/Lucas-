"""Génère les documents lisibles de chaque épisode à partir de episode.json :

  episodes/epXX/SCENARIO.md   synopsis, dialogues complets, découpage plan par plan,
                              prompts image, musique, textes d'écran
  episodes/INDEX.md           tableau de bord de la saison

Usage : python tools/documents.py            (tous les épisodes)
        python tools/documents.py --episode 3
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import EPISODES, charger_episode, charger_personnages, dossier_episode, prompt_scene  # noqa: E402

MOTS_PAR_SECONDE = 2.6  # débit moyen des voix, pour estimer la durée


def scenario(num, perso):
    ep = charger_episode(num)
    noms = {k: v.get("nom", k) for k, v in perso["personnages"].items()}
    mots = sum(len(l[1].split()) for s in ep["scenes"] for l in s["lignes"])
    duree = mots / MOTS_PAR_SECONDE + 0.65 * len(ep["scenes"])
    o = [f"# LES 3 FRÈRES — Épisode {num} : {ep['titre']}", ""]
    o += [f"> **Question de l'épisode :** {ep['question']}", "",
          f"**Durée estimée :** {duree:.0f} s · **Plans :** {len(ep['scenes'])} · **Mots :** {mots}", "",
          "## Synopsis", "", ep["resume"], "",
          "## Intrigues semées", ""] + [f"- {x}" for x in ep.get("intrigues_semees", [])]
    o += ["", f"## ⚡ Cliffhanger", "", ep["cliffhanger"], "", "---", "", "## Dialogues complets", ""]
    for sc in ep["scenes"]:
        for qui, txt, *_ in sc["lignes"]:
            o.append(f"**{noms.get(qui, qui).upper()}** — {txt}  ")
    o += ["", "---", "", "## Découpage plan par plan", ""]
    for sc in ep["scenes"]:
        o += [f"### Plan {sc['id']} — {sc['lieu']}", "",
              f"- **Cadrage :** {sc.get('plan', '')}",
              f"- **Musique :** `{sc.get('musique', 'mystere')}`"]
        if sc.get("ecran"):
            o.append(f"- **Texte à l'écran :** {sc['ecran']}")
        o.append("- **Répliques :**")
        for qui, txt, *_ in sc["lignes"]:
            o.append(f"  - *{noms.get(qui, qui)}* : « {txt} »")
        o += ["", "<details><summary>Prompt image (généré)</summary>", "", "```", prompt_scene(sc, perso), "```",
              "", "</details>", ""]
    return "\n".join(o), ep, duree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int)
    a = ap.parse_args()
    perso = charger_personnages()
    nums = [a.episode] if a.episode else sorted(
        int(os.path.basename(d)[2:]) for d in glob.glob(os.path.join(EPISODES, "ep*")))
    lignes_index = ["# Saison 1 — tableau de bord", "",
                    "| Ép. | Titre | Question | Durée est. | Cliffhanger |", "|---|---|---|---|---|"]
    for n in nums:
        md, ep, duree = scenario(n, perso)
        open(os.path.join(dossier_episode(n), "SCENARIO.md"), "w", encoding="utf-8").write(md)
        lignes_index.append(f"| {n} | [{ep['titre']}](ep{n:02d}/SCENARIO.md) | {ep['question']} | "
                            f"{duree:.0f} s | {ep['cliffhanger']} |")
        print("écrit", f"ep{n:02d}/SCENARIO.md")
    if not a.episode:
        open(os.path.join(EPISODES, "INDEX.md"), "w", encoding="utf-8").write("\n".join(lignes_index) + "\n")


if __name__ == "__main__":
    main()
