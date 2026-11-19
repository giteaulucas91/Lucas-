# Clipper — clips viraux façon Opus Clip

1. `python transcribe.py video.mp4 transcript.json` (Whisper, mots horodatés)
2. Choisir les meilleurs moments dans `transcript.json`
3. `python make_clip.py --src video.mp4 --words transcript.json --start 120 --end 175 --out clip1.mp4 --hook "ACCROCHE|SUR 2 LIGNES"`
   - `--mode face` (défaut) : recadrage 9:16 qui suit le visage
   - `--mode blur` : vidéo entière centrée sur fond flouté

Sous-titres : MAJUSCULES, Montserrat Black (police `fonts/ClipBlack.ttf`, licence OFL), blanc, contour sombre + ombre, 1 à 3 mots, petite animation « pop ».
Nécessite ffmpeg avec libass.
