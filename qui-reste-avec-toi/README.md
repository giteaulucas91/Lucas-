# QUI RESTE AVEC TOI JUSQU'EN HAUT ?

Animation stick-figure « cinématique » 9:16 (1080x1920, 30 i/s, 23,5 s), avec bande-son.
Même langage visuel que les vidéos « escalier » : marches en diagonale dans le noir,
projecteurs, personnages étiquetés, boules-obstacles en rouge, caméra qui suit.

- `QUI_RESTE_AVEC_TOI.mp4` : la vidéo finale.
- `generer_histoire.py` : le générateur (Python + Pillow + numpy + ffmpeg), 100 % procédural.

```bash
python3 generer_histoire.py              # vidéo + son (~5 min sur 4 cœurs)
python3 generer_histoire.py --apercu     # planche de 16 vignettes
python3 generer_histoire.py --image 13.3 # une image
```

## Histoire

| Temps | Ce qui se passe |
|---|---|
| 0–2,3 s | Gros plan : TOI monte l'escalier, entouré de LES POTES et L'ARGENT FACILE. |
| 2,3–4 s | Dézoom en plan large, titre tapé : « QUI RESTE AVEC TOI / JUSQU'EN HAUT ? ». LES LIKES en tête ; LA FAMILLE loin derrière, grise et floue, hors de la lumière. |
| 5,0 s | La boule **ÉCHEC** dévale les marches et éjecte LES LIKES (salto arrière dans le vide). |
| 6,3 s | **PAS D'ARGENT** arrive : L'ARGENT FACILE s'évapore dans un glitch avant même l'impact. |
| 7,6 s | LES POTES font demi-tour et redescendent… en croisant LA FAMILLE qui, elle, monte. |
| 10,0 s | **DOUTE** frappe TOI : il recule de trois marches et tombe à genoux. Tout vire au rouge, battements de cœur. |
| 11–12,8 s | LA FAMILLE entre dans la lumière, dépasse TOI, s'arrête et se retourne. |
| 12,8–14,6 s | Elle lui tend la main ; il lève la tête, l'attrape ; elle le relève. La lumière redevient blanche puis chaude. |
| 14,6–19,8 s | Ils montent ensemble. Réponse tapée : « LES LIKES TOMBENT. / LA FAMILLE RESTE. » |
| 19,8–23,5 s | Glitch → carte de fin TikTok, recherche `@teamlouise82` tapée au clavier. |

Les textes (`TITRE`, `REPONSE`), les étiquettes (`nom` dans chaque `etat_*`, `BOULES`) et les temps
clés (`T_HIT_LIKES`, `T_EVAP`, `T_POTES`, `T_DOUTE`, `T_REGARD`…) sont en haut du script.
