"""Monte la vidéo finale 1080x1920 : images animées (zoom lent), voix, sous-titres mot par mot.

Usage : python assemble.py story.json dossier_voix choix.json sortie.mp4
  choix.json : {"1": "chemin/image_scene1.png", "2": ...}
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "clipper", "fonts")
W, H, FPS, SR = 1080, 1920, 30, 44100
GAP_LINE, GAP_SCENE, HEAD = 0.30, 0.45, 0.15

story = json.load(open(sys.argv[1], encoding="utf-8"))
voix = sys.argv[2]
choice = json.load(open(sys.argv[3], encoding="utf-8"))
out = sys.argv[4]
lines = json.load(open(os.path.join(voix, "lines.json"), encoding="utf-8"))


def load_audio(path):
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


# ------------------------------------------------ piste audio + minutage
audio = [np.zeros(int(HEAD * SR), np.float32)]
t = HEAD
words, scenes = [], []
for sc in story["scenes"]:
    s0 = t if scenes else 0.0
    for j in range(len(sc["lines"])):
        key = f"s{sc['id']:02d}_{j}"
        a = load_audio(os.path.join(voix, key + ".mp3"))
        # coupe le silence de fin ajouté par le moteur vocal
        nz = np.nonzero(np.abs(a) > 0.01)[0]
        a = a[: nz[-1] + int(0.08 * SR)] if len(nz) else a
        for w in lines[key]["words"]:
            words.append({"start": t + w["start"], "end": t + w["end"], "word": w["word"]})
        audio.append(a)
        t += len(a) / SR
        gap = GAP_LINE if j < len(sc["lines"]) - 1 else GAP_SCENE
        audio.append(np.zeros(int(gap * SR), np.float32))
        t += gap
    scenes.append((sc["id"], s0, t))
total = t + 0.6
audio.append(np.zeros(int(0.6 * SR), np.float32))
audio = np.concatenate(audio)
audio = audio / max(1e-6, np.abs(audio).max()) * 0.9

tmp = tempfile.mkdtemp()
wav = os.path.join(tmp, "voix.wav")
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", wav],
    input=audio.tobytes(), check=True,
)


# ------------------------------------------------ sous-titres (1 mot à la fois)
def ts(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"


ass = [f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Mot,ClipBlack,92,&H00FFFFFF,&H00FFFFFF,&H00101010,&H90000000,0,0,0,0,100,100,1,0,1,6,4,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""]
for i, w in enumerate(words):
    end = w["end"] + 0.12
    if i + 1 < len(words):
        end = min(end if words[i + 1]["start"] - w["end"] > 0.25 else words[i + 1]["start"],
                  words[i + 1]["start"])
    txt = re.sub(r"[.,;:…\"«»]", "", w["word"].upper()).strip()
    if not txt:
        continue
    ass.append(
        f"Dialogue: 0,{ts(w['start'])},{ts(max(end, w['start'] + 0.1))},Mot,,0,0,0,,"
        f"{{\\an5\\pos({W // 2},1440)\\blur0.6\\fscx88\\fscy88\\t(0,70,\\fscx100\\fscy100)}}{txt}"
    )
ass_path = os.path.join(tmp, "subs.ass")
open(ass_path, "w", encoding="utf-8").write("\n".join(ass) + "\n")

# ------------------------------------------------ images animées
cmd = [
    "ffmpeg", "-v", "error", "-y",
    "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", wav, "-map", "0:v", "-map", "1:a",
    "-vf", f"ass={ass_path}:fontsdir={FONTS}",
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out,
]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
n_total = int(round(total * FPS))
for k, (sid, s0, s1) in enumerate(scenes):
    e = s1 if k + 1 < len(scenes) else total
    img = cv2.imread(choice[str(sid)])
    # recadre au ratio 9:16 puis agrandit avec marge pour le zoom
    ih, iw = img.shape[:2]
    cw = int(ih * 9 / 16)
    x0 = (iw - cw) // 2
    img = img[:, x0:x0 + cw] if cw <= iw else img
    big = cv2.resize(img, (int(W * 1.12), int(H * 1.12)), interpolation=cv2.INTER_LANCZOS4)
    bh, bw = big.shape[:2]
    f0, f1 = int(round(s0 * FPS)), int(round(e * FPS))
    zoom_in = k % 2 == 0
    pan = [-1, 1, 0][k % 3]
    for f in range(f0, min(f1, n_total)):
        p = (f - f0) / max(1, f1 - f0 - 1)
        p = p * p * (3 - 2 * p)
        a = 1.0 + 0.08 * (p if zoom_in else 1 - p)  # zoom (l'image a déjà 12 % de marge)
        cx = bw / 2 + pan * 0.05 * bw * (p - 0.5)
        cy = bh / 2
        M = np.array([[a, 0, W / 2 - a * cx], [0, a, H / 2 - a * cy]], np.float32)
        frame = cv2.warpAffine(big, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        proc.stdin.write(frame.tobytes())
proc.stdin.close()
if proc.wait() != 0:
    raise SystemExit("ffmpeg a échoué")
print(f"OK {out} ({total:.1f}s, {len(scenes)} scènes, {len(words)} mots)")
