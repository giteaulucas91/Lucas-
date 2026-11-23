# MOTIVATION / DISCIPLINE / EGO

Animation minimaliste 9:16 (1080x1920, 30 i/s, 35 s) : fond noir, traits blancs, stick figures.

- `MOTIVATION_DISCIPLINE_EGO.mp4` : la vidéo finale (piste audio muette, prête pour ajouter un son sur TikTok/Reels).
- `generer_animation.py` : le générateur (Python + Pillow + numpy + ffmpeg).

```bash
python3 generer_animation.py              # rend la vidéo (~1 min 30 sur 4 cœurs)
python3 generer_animation.py --apercu     # planche de 16 vignettes clés
python3 generer_animation.py --image 12.5 # une image à t = 12,5 s
```

## Chronologie

| Temps | Motivation | Discipline | Ego |
|---|---|---|---|
| 0–6 s | tractions synchronisées (2 s/rep) | idem | idem |
| 6–10 s | ralentit, tremble, rouge qui s'intensifie, lâche une main à 9,35 s puis tout à 9,6 s, tombe | rythme constant | reps explosives, poses théâtrales (jambes écartées), balancier |
| 10–16 s | assis au sol, souffle lourd, halo rouge | rythme constant | perd de la hauteur, mouvements désordonnés |
| 16–25 s | au sol | rythme constant | lâche une main à 18,75 s, tombe à 19,05 s, debout bras écartés + halo, gestes « pourquoi ?! » |
| 25–32 s | au sol | rythme constant | en bas, bras qui s'agitent légèrement |
| 32–35 s | fondu → logo + barre de recherche `@teamlouise82` tapée lettre par lettre | | |

Les temps clés sont des constantes en haut du script (`M_LACHE`, `E_LACHE`, `CLES_M`, `CLES_E`…).
