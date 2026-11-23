# MOTIVATION / DISCIPLINE / EGO

Animation stick-figure « cinématique » 9:16 (1080x1920, 30 i/s, 35 s), avec bande-son.

- `MOTIVATION_DISCIPLINE_EGO.mp4` : la vidéo finale.
- `generer_animation.py` : le générateur (Python + Pillow + numpy + ffmpeg), tout est procédural.

```bash
python3 generer_animation.py              # rend vidéo + son (~10 min sur 4 cœurs)
python3 generer_animation.py --apercu     # planche de 16 vignettes clés
python3 generer_animation.py --image 12.5 # une image à t = 12,5 s
python3 generer_animation.py --son x.wav  # seulement la bande-son
```

## Style

- Fond anthracite, projecteur volumétrique au-dessus de chaque cadre, poussières qui flottent
  dans la lumière, bokeh, grain de film, vignettage, bloom.
- Personnages épais à tête pleine ; membres arrière en gris (profondeur). Flou de mouvement
  automatique quand ça bouge vite.
- Mains et épaules qui brillent en rouge pendant l'effort.
- Titres en monospace, tapés lettre par lettre ; ceux qui tombent passent au rouge avec un glitch.
- À chaque chute : secousse caméra, aberration chromatique, onde de choc, halo rouge, le
  projecteur s'éteint et vire au rouge, ambiance rouge sur les bords.
- Lent travelling avant sur toute la vidéo ; à la fin, seul le projecteur de Discipline reste fort.
- Fin : glitch RGB → carte bleu nuit, logo à décalage cyan/rose, barre de recherche qui
  s'assemble, `@teamlouise82` tapé au clavier.
- Son : nappe grave, pulsation à chaque traction, souffle de tension, sifflement + impact
  aux chutes, glitch, whoosh et frappe clavier.

## Chronologie

| Temps | Motivation | Discipline | Ego |
|---|---|---|---|
| 0–6 s | tractions synchronisées (2 s/rep) | idem | idem |
| 6–10 s | ralentit, tremble, rouge qui s'intensifie, lâche une main (9,35 s) puis tout (9,6 s), tombe | rythme constant | reps explosives, jambes écartées, balancier |
| 10–16 s | assis au sol, souffle lourd, halo rouge | rythme constant | perd de la hauteur, désordonné, vire au rouge |
| 16–25 s | au sol | rythme constant | lâche une main (18,75 s), tombe (19,05 s), debout bras écartés + halo, gestes « pourquoi ?! » |
| 25–32 s | au sol | rythme constant, projecteur principal | en bas, bras qui s'agitent légèrement |
| 32–35 s | glitch → logo + barre de recherche `@teamlouise82` | | |

Les temps clés sont des constantes en haut du script (`M_LACHE`, `E_LACHE`, `CLES_M`, `CLES_E`, `T_FIN`…).
