# État de production — saison 1

Toutes ces vidéos ont **réellement été générées** dans ce dépôt (images SDXL-Turbo en local, voix Edge TTS, musique synthétisée, montage FFmpeg), au format 1080x1920, 30 i/s.

| Ép. | Titre | Durée | Fichiers | Remarques qualité |
|---|---|---|---|---|
| 1 | Le Pacte | 59.2 s | [MP4](../videos/LES_3_FRERES_EP01.mp4) · [SRT](ep01/sous-titres.srt) | Plan 11 (les 3 frères de dos) approximatif. |
| 2 | La vie de rêve | 45.7 s | [MP4](../videos/LES_3_FRERES_EP02.mp4) · [SRT](ep02/sous-titres.srt) | Plan 5 (Lucas + Kevin) : personnages fusionnés banane/ananas. |
| 3 | 500 euros | 49.3 s | [MP4](../videos/LES_3_FRERES_EP03.mp4) · [SRT](ep03/sous-titres.srt) | Sofia parfois trop humaine au plan 7. |
| 4 | La vie parfaite | 47.5 s | [MP4](../videos/LES_3_FRERES_EP04.mp4) · [SRT](ep04/sous-titres.srt) | Clara instable : cerise sans corps (plans 4-8), visage humain au nez-cerise (plan 10). À refaire en priorité avec un service à référence de personnage. |
| 5 | L'Ombre | 45.3 s | [MP4](../videos/LES_3_FRERES_EP05.mp4) · [SRT](ep05/sous-titres.srt) | Bon. |
| 6 | Le premier piège | 49.2 s | [MP4](../videos/LES_3_FRERES_EP06.mp4) · [SRT](ep06/sous-titres.srt) | Bon. |
| 7 | Le mariage | 47.8 s | [MP4](../videos/LES_3_FRERES_EP07.mp4) · [SRT](ep07/sous-titres.srt) | Mariée humaine aux plans 1 et 7 ; plan 9 (Clara) en cerise sans corps. |
| 8 | L'investisseur fantôme | 50.3 s | [MP4](../videos/LES_3_FRERES_EP08.mp4) · [SRT](ep08/sous-titres.srt) | Bon. |
| 9 | Le médaillon | 56.5 s | [MP4](../videos/LES_3_FRERES_EP09.mp4) · [SRT](ep09/sous-titres.srt) | Bon (Clara cerise furieuse réussie). |
| 10 | Les retrouvailles | 49.7 s | [MP4](../videos/LES_3_FRERES_EP10.mp4) · [SRT](ep10/sous-titres.srt) | Plan 1 : une Lamborghini en trop. |

## Limites connues (version gratuite)
- **Cohérence des personnages imparfaite** : le fruit et la tenue sont respectés la plupart du temps, mais pas le visage exact. Clara (cerise) est la plus instable.
- **Plans à plusieurs personnages** souvent fusionnés.
- **Animation** limitée à des mouvements de caméra (zoom, panoramique) : pas de mouvements de lèvres.
- **Musique** synthétique de type « maquette » : à remplacer par un son tendance dans TikTok.

## Pour passer à la version « pro »
Voir `docs/AUTOMATISATION.md` : FLUX (`--fournisseur fal`) avec les portraits de référence, puis Kling ou Runway pour animer chaque plan, et ElevenLabs pour les voix. Les scénarios, choix de plans, voix et montage restent identiques : il suffit de régénérer les images (`tools/images.py --episode N --fournisseur fal`) puis de relancer `tools/montage.py --episode N`.
