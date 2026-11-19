# 🍌🍏🍊 LES 3 FRÈRES — 10 ANS POUR RÉUSSIR

Série TikTok de fruits humanisés en 3D. Un milliardaire impose à ses trois fils dix ans de vies opposées pour désigner son héritier… mais l'expérience cache bien plus.

## Organisation du dépôt

```
serie-3-freres/
├── bible/
│   ├── BIBLE.md                 univers, règles visuelles, structure d'un épisode, SECRETS de la saison
│   ├── ARC_30_EPISODES.md       les 30 épisodes de la saison 1 (titre, résumé, cliffhanger)
│   └── personnages/*.md         fiches détaillées (père, Lucas, Enzo, Mathis, Clara, Kevin, Sofia, l'Ombre)
├── data/personnages.json        SOURCE DE VÉRITÉ visuelle et vocale (prompts officiels, voix)
├── episodes/
│   ├── INDEX.md                 tableau de bord de la saison
│   └── epXX/
│       ├── episode.json         scénario structuré (plans, prompts, répliques, musique)  ← on écrit ici
│       ├── SCENARIO.md          généré : synopsis, dialogues, découpage, prompts
│       ├── choix.json           image retenue par plan
│       └── sous-titres.srt      généré au montage
├── tools/
│   ├── produire.py              ⭐ tout en une commande : voix → images → documents → montage
│   ├── images.py                génération d'images (local SDXL-Turbo | fal | replicate | openai)
│   ├── voix.py                  voix FR + horodatage mot à mot (Edge TTS | ElevenLabs)
│   ├── musique.py               ambiances musicales par humeur
│   ├── montage.py               montage 9:16, sous-titres, musique, export MP4
│   ├── documents.py             génère SCENARIO.md + INDEX.md
│   └── nouvel_episode.py        crée le squelette de l'épisode suivant depuis l'arc
├── docs/
│   ├── AUTOMATISATION.md        étude des outils et API (images, animation, voix, musique)
│   └── VOIX_ET_MONTAGE.md       instructions de voix, sous-titres, montage, checklist
├── assets/                      polices, portraits de référence, musiques
└── sorties/                     (non versionné) images, voix, vidéos générées
```

## Installation

```bash
sudo apt install ffmpeg            # avec libass (sous-titres)
pip install torch --index-url https://download.pytorch.org/whl/cpu   # ou la version CUDA si vous avez un GPU
pip install diffusers transformers accelerate compel edge-tts "opencv-python-headless<5" numpy
```

Au premier lancement, le modèle SDXL-Turbo (~7 Go) est téléchargé depuis Hugging Face.

## Produire un épisode

```bash
cd serie-3-freres
python tools/produire.py 1 --essais 3       # voix + 3 images par plan + documents + vidéo
# regardez sorties/ep01/planche.jpg, notez vos choix dans episodes/ep01/choix.json
python tools/montage.py --episode 1         # remontage avec vos choix
# → sorties/ep01/LES_3_FRERES_EP01.mp4
```

## Écrire l'épisode suivant

```bash
python tools/nouvel_episode.py 12           # squelette pré-rempli depuis bible/ARC_30_EPISODES.md
# complétez episodes/ep12/episode.json (plans, prompts avec PERE/LUCAS/..., répliques)
python tools/documents.py                   # met à jour SCENARIO.md et INDEX.md
python tools/produire.py 12
```

## Règles d'or
1. **Les personnages ne changent jamais d'apparence** : dans les prompts, écrivez `LUCAS`, `PERE`…, jamais une description libre.
2. **Une question par épisode, aucune réponse dans le même épisode.**
3. **Les secrets suivent le calendrier** de `bible/BIBLE.md` §6.
