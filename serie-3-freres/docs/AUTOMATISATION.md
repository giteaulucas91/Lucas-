# Étude des outils d'automatisation

Objectif : passer d'un `episode.json` à une vidéo TikTok 9:16 avec un minimum d'intervention humaine.

## Ce qui tourne AUJOURD'HUI dans ce dépôt (gratuit, sans clé API)

| Étape | Outil intégré | Statut |
|---|---|---|
| Images | **SDXL-Turbo** en local (`tools/images.py --fournisseur local`), prompts pondérés avec *Compel* et étiquettes d'émotion | ✅ Fonctionne (environ 18 s par image sur CPU 4 cœurs, environ 1 s sur GPU) |
| Animation | Zoom/panoramique lent (« Ken Burns ») + flash de transition (`tools/montage.py`) | ✅ Fonctionne |
| Voix FR | **Edge TTS** (voix neuronales Microsoft), une voix par personnage, horodatage mot par mot | ✅ Fonctionne |
| Synchronisation | Horodatage natif des voix → sous-titres au mot près | ✅ Fonctionne |
| Sous-titres | Incrustés (ASS/libass, un mot à la fois) + fichier `.srt` par épisode | ✅ Fonctionne |
| Musique | Ambiances synthétisées par humeur (`tools/musique.py`), baisse automatique sous les voix | ✅ Fonctionne (qualité « maquette ») |
| Assemblage + export | FFmpeg, H.264 1080x1920, 30 i/s, AAC | ✅ Fonctionne |

**Limites honnêtes de la version gratuite :**
- **Cohérence des personnages :** SDXL-Turbo respecte le fruit et la couleur, mais pas toujours la tenue ni le visage d'une image à l'autre. On génère donc 2 à 3 propositions par plan et on choisit (`choix.json`).
- **Plans à 3 personnages ou plus :** souvent approximatifs.
- **Pas de vraie animation des personnages** (bouches, gestes) : seulement des mouvements de caméra.

## Pour passer au niveau « pro » (services externes, clés à fournir)

Aucune clé n'est incluse. Copiez `.env.example` en `.env`, remplissez, puis `export $(cat .env | xargs)`.

### 1. Images avec cohérence des personnages

| Service | Pourquoi | Variable | Intégration |
|---|---|---|---|
| **fal.ai — FLUX 1.1 Pro** | Meilleure fidélité au prompt, rendu très proche des séries de fruits virales | `FAL_KEY` | ✅ `--fournisseur fal` |
| **Replicate — FLUX 1.1 Pro** | Même modèle, autre facturation | `REPLICATE_API_TOKEN` | ✅ `--fournisseur replicate` |
| **OpenAI — gpt-image-1** | Très bon sur les scènes à plusieurs personnages | `OPENAI_API_KEY` | ✅ `--fournisseur openai` |
| FLUX Kontext / Ideogram Character / Midjourney `--cref` | **Référence de personnage** : on donne l'image officielle du personnage et le modèle la respecte | — | À ajouter : utiliser les portraits de `assets/personnages/` comme référence |

> Les intégrations fal/Replicate/OpenAI sont écrites selon la documentation publique de ces API, mais **n'ont pas pu être testées sans clé**. À vérifier au premier lancement.

### 2. Animation vidéo (image → vidéo)

Pour animer chaque plan (personnage qui parle, tourne la tête, pleure), on envoie l'image générée plus une consigne de mouvement :

| Service | Qualité | Prix indicatif | Accès |
|---|---|---|---|
| **Kling AI** (1.6 / 2.x) | Excellent sur les personnages cartoon 3D | ~0,25 à 0,50 $ / 5 s | API officielle, ou via fal.ai |
| **Runway Gen-4** | Très cinématographique | ~0,50 $ / 5 s | API Runway |
| **Luma Dream Machine (Ray 2)** | Bon rapport qualité/prix | ~0,30 $ / 5 s | API Luma |
| **Hailuo / MiniMax** | Très bonnes expressions faciales | ~0,25 $ / 6 s | API MiniMax, ou fal.ai |
| **Hedra / Kling Lip-Sync** | Synchronisation labiale sur l'audio | variable | API |

Coût estimé d'un épisode de 11 plans animés : **3 à 6 $**. Dans `episode.json`, le champ `plan` (« gros plan », « plan large »…) sert de base à la consigne de mouvement. Pour brancher l'animation, ajoutez un `tools/animation.py` qui transforme `sorties/epXX/images/sYY_K.png` en `sorties/epXX/videos/sYY.mp4` ; le montage devra alors prendre la vidéo à la place de l'image fixe (seule la boucle d'images de `tools/montage.py` est à adapter).

### 3. Voix plus émotionnelles

| Service | Pourquoi | Variable | Intégration |
|---|---|---|---|
| **ElevenLabs** (multilingual v2) | Voix très expressives (colère, larmes, chuchotement), voix clonées possibles | `ELEVENLABS_API_KEY` + `voix.elevenlabs` (voice_id) dans `data/personnages.json` | ✅ `tools/voix.py --fournisseur elevenlabs` (horodatage inclus) |
| Azure Speech (SSML) | Mêmes voix qu'Edge, mais avec des styles d'émotion | `AZURE_SPEECH_KEY` | Non intégré |

### 4. Musique

- **Le plus viral :** ajouter le *son tendance* directement dans TikTok au moment de publier (volume bas, 10 à 15 %). Exportez alors avec `--sans-musique`.
- Bibliothèques libres de droits : Pixabay Music, YouTube Audio Library, Uppbeat. Déposez les fichiers dans `assets/musique/<humeur>.mp3`.
- Génération IA : Suno / Udio (vérifier les droits commerciaux de votre abonnement).

### 5. Publication

L'API TikTok « Content Posting » permet de publier automatiquement, mais elle exige une application TikTok validée. Recommandation : publication manuelle ou programmée dans TikTok Studio, avec le `.srt` pour les sous-titres natifs et le titre et les hashtags de la bible.

## Chaîne cible entièrement automatique

```
episode.json ──► voix.py ──► images.py (FLUX + référence perso) ──► animation.py (Kling)
                    │                                                    │
                    └──────────────► montage.py ◄────────────────────────┘
                                         │
                               MP4 9:16 + .srt ──► TikTok
```
