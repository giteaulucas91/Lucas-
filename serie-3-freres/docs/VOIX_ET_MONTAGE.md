# Instructions : voix, sous-titres, montage

## Voix françaises

Chaque personnage a une voix fixe (`data/personnages.json` → `voix`). **Ne jamais changer une voix en cours de saison.**

| Personnage | Voix Edge | Réglage | Intention |
|---|---|---|---|
| Narrateur | fr-FR-HenriNeural | -4 %, -6 Hz | Voix de bande-annonce, posée |
| Augustin (père) | fr-FR-HenriNeural | -5 %, -14 Hz | Grave, lente, autoritaire |
| Lucas | fr-FR-RemyMultilingualNeural | +6 % | Rapide, frimeur |
| Enzo | fr-CH-FabriceNeural | — | Posé, précis |
| Mathis | en-US-BrianMultilingualNeural | +2 % | Chaleureux (voix multilingue au français naturel) |
| Clara | fr-FR-DeniseNeural | +2 %, -2 Hz | Douce |
| Kevin | fr-BE-GerardNeural | +6 % | Charmeur |
| Sofia | fr-FR-VivienneMultilingualNeural | +4 %, +3 Hz | Pétillante |
| L'Ombre | fr-CA-SylvieNeural | -8 %, -8 Hz | Froide, lente |

**Règles d'écriture pour la voix :**
- Les points de suspension `…` créent une vraie pause, ce qui est idéal avant une révélation.
- Les nombres s'écrivent en lettres (« cinq cents euros ») pour une prononciation correcte.
- Une réplique ne dépasse pas 15 mots.

Commande : `python tools/voix.py --episode N` (ou `--fournisseur elevenlabs`).

## Sous-titres

Deux formats sont produits automatiquement :
1. **Incrustés dans la vidéo**, un mot à la fois, en MAJUSCULES, police Montserrat Black, blanc avec contour noir, à 75 % de la hauteur. C'est le style des séries de fruits virales.
2. **`episodes/epXX/sous-titres.srt`**, phrase par phrase, à importer dans TikTok, CapCut ou YouTube.

S'y ajoutent :
- **le titre de série** « LES 3 FRÈRES / PARTIE N » en haut pendant 2,8 s ;
- **les textes d'écran** (champ `ecran` : « ANNÉE 3 », « 10 ANS PLUS TARD »…) en haut de l'image ;
- **« PARTIE N+1 → »** en jaune sur les 2,6 dernières secondes.

## Montage (automatique : `python tools/montage.py --episode N`)

| Élément | Réglage |
|---|---|
| Format | 1080x1920, 30 i/s, H.264 CRF 18, AAC 192 kb/s |
| Durée d'un plan | Exactement la durée de ses répliques + 0,4 s |
| Mouvement | Zoom lent de 9 % (avant ou arrière en alternance) + léger panoramique |
| Transition | Coupe sèche + flash blanc de 4 images + « whoosh » discret |
| Musique | Humeur par plan (`musique`), fondu de 0,5 s, baisse automatique sous les voix (30 % → 12 %) |
| Fin | 1,2 s de silence sur le dernier plan, avec « PARTIE N+1 → » |

### Choisir les images
1. `python tools/produire.py N --essais 3` génère 3 propositions par plan et une planche-contact `sorties/epXX/planche.jpg`.
2. Notez le meilleur numéro par plan dans `episodes/epXX/choix.json`, par exemple `{"1": 0, "2": 2, "3": 1}`.
3. Si aucune image ne convient : modifiez le champ `image` de la scène (ou ajoutez `"graine": 7` pour d'autres tirages), supprimez `sorties/epXX/images/sYY_*` et relancez `python tools/images.py --episode N --scenes YY --essais 3`.
4. `python tools/montage.py --episode N`.

### Finitions recommandées dans CapCut (optionnel, 5 min)
- Remplacer certains plans fixes par leur version animée (Kling, Runway…).
- Ajouter le son tendance de TikTok.
- Ajouter des bruitages ponctuels : tonnerre (ép. 1), caisse enregistreuse (ép. 2), vibration de téléphone (ép. 7, 9).

## Checklist avant publication
- [ ] Accroche audible et lisible dans les 2 premières secondes
- [ ] Aucun visage caché par les sous-titres
- [ ] Chaque personnage est reconnaissable (bon fruit, bonne couleur, bonne tenue)
- [ ] Durée de 45 à 65 s
- [ ] « PARTIE N+1 → » visible à la fin
- [ ] Titre : `LES 3 FRÈRES — Partie N : <question de l'épisode>`
- [ ] Commentaire épinglé : « Quel frère a raison ? 🍌🍎🍊 »
