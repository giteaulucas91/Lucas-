# QUI TIENT JUSQU'AU BOUT ? — Motivation / Discipline / Ego (version escalier)

Animation stick-figure « cinématique » 9:16 (1080x1920, 30 i/s, 23,5 s), avec bande-son.
Même langage visuel que les vidéos « escalier » : marches en diagonale dans le noir,
projecteurs, personnages étiquetés, boules-obstacles en rouge, caméra qui suit, glitchs.

- `QUI_TIENT_JUSQU_AU_BOUT.mp4` : la vidéo finale.
- `generer_histoire.py` : le générateur (Python + Pillow + numpy + ffmpeg), 100 % procédural.

```bash
python3 generer_histoire.py              # vidéo + son (~5 min sur 4 cœurs)
python3 generer_histoire.py --apercu     # planche de 16 vignettes
python3 generer_histoire.py --image 12.9 # une image
```

## Histoire

| Temps | Ce qui se passe |
|---|---|
| 0–2,3 s | Gros plan : MOTIVATION part en flèche dans l'escalier, EGO juste devant. |
| 2,3–4 s | Dézoom en plan large, titre tapé : « QUI TIENT / JUSQU'AU BOUT ? ». DISCIPLINE loin derrière, gris et flou, hors de la lumière, à pas réguliers. |
| 3,5–5,5 s | EGO vire au rouge. MOTIVATION ralentit, devient gris, s'arrête plié en deux, essoufflé. |
| 5,5 s | EGO se met à courir pour frimer. |
| 6,3–6,8 s | La boule **FATIGUE** tombe du ciel : MOTIVATION s'évapore dans un glitch. |
| 7,6 s | **ÉCHEC** dévale les marches et envoie EGO dans le vide (salto arrière). |
| 5,5–8,5 s | DISCIPLINE entre dans la lumière, toujours au même rythme. |
| 10,0 s | **DOUTE** frappe DISCIPLINE : il recule de trois marches et tombe à genoux. Tout vire au rouge, battements de cœur. |
| 11,8–13,6 s | Il relève la tête, pose la main sur son genou et se relève SEUL. La lumière redevient blanche puis chaude. |
| 13,6–19,8 s | Il repart au même pas. Réponse tapée : « LA MOTIVATION S'ÉVAPORE. / L'EGO TOMBE. / LA DISCIPLINE CONTINUE. » |
| 19,8–23,5 s | Glitch → carte de fin TikTok, recherche `@teamlouise82` tapée au clavier. |

Les textes (`TITRE`, `REPONSE`), les obstacles (`BOULES`) et les temps clés (`T_EVAP`, `T_EGO`,
`T_DOUTE`, `T_REGARD`…) sont en haut du script.
