"""Montage automatique d'un épisode -> MP4 vertical 1080x1920 prêt pour TikTok.

Entrées :
  episodes/epXX/episode.json         scénario
  episodes/epXX/choix.json           (optionnel) image retenue par scène : {"1": 0, "2": 2, ...}
  sorties/epXX/images/sYY_K.png      images générées (tools/images.py)
  sorties/epXX/voix/                 voix + horodatage (tools/voix.py)
Sorties :
  sorties/epXX/LES_3_FRERES_EPXX.mp4
  episodes/epXX/sous-titres.srt      (sous-titres phrase par phrase, à importer dans TikTok/CapCut)

Usage : python tools/montage.py --episode 1
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import FONTS, charger_episode, dossier_episode, dossier_travail  # noqa: E402
from musique import chemin_humeur  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 44100
PAUSE_REPLIQUE, PAUSE_SCENE, DEBUT, FIN = 0.25, 0.40, 0.10, 1.2
VOL_MUSIQUE, VOL_MUSIQUE_SOUS_VOIX = 0.30, 0.12


def lire_audio(chemin):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", chemin, "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], check=True, capture_output=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def ts_ass(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"


def ts_srt(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def whoosh(d=0.45):
    t = np.arange(int(d * SR)) / SR
    bruit = np.random.default_rng(3).standard_normal(len(t))
    # bruit filtré dont la « couleur » monte puis descend
    k = np.convolve(bruit, np.ones(12) / 12, mode="same")
    env = np.sin(np.pi * t / d) ** 2
    return (k * env * 0.35).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--sans-musique", action="store_true")
    a = ap.parse_args()
    ep = charger_episode(a.episode)
    num = ep["numero"]
    d_img = dossier_travail(num, "images")
    d_voix = dossier_travail(num, "voix")
    lignes = json.load(open(os.path.join(d_voix, "lignes.json"), encoding="utf-8"))
    f_choix = os.path.join(dossier_episode(num), "choix.json")
    choix = json.load(open(f_choix)) if os.path.exists(f_choix) else {}

    # ---------------------------------------------------------------- minutage
    voix = [np.zeros(int(DEBUT * SR), np.float32)]
    t = DEBUT
    mots, phrases, plans = [], [], []
    for i, sc in enumerate(ep["scenes"]):
        t0 = 0.0 if i == 0 else t
        for j in range(len(sc["lignes"])):
            cle = f"s{sc['id']:02d}_{j}"
            s = lire_audio(os.path.join(d_voix, cle + ".mp3"))
            nz = np.nonzero(np.abs(s) > 0.008)[0]
            if len(nz):
                s = s[max(0, nz[0] - int(0.03 * SR)): nz[-1] + int(0.06 * SR)]
                decal = max(0, nz[0] - int(0.03 * SR)) / SR
            else:
                decal = 0
            for m in lignes[cle]["mots"]:
                mots.append({"start": t + m["start"] - decal, "end": t + m["end"] - decal, "word": m["word"]})
            phrases.append((t, t + len(s) / SR, lignes[cle]["texte"]))
            voix.append(s)
            t += len(s) / SR
            pause = PAUSE_REPLIQUE if j < len(sc["lignes"]) - 1 else PAUSE_SCENE
            voix.append(np.zeros(int(pause * SR), np.float32))
            t += pause
        plans.append({"scene": sc, "t0": t0, "t1": t})
    total = t + FIN
    plans[-1]["t1"] = total
    voix.append(np.zeros(int(FIN * SR) + SR, np.float32))
    voix = np.concatenate(voix)[: int(total * SR)]
    voix = voix / max(1e-6, np.abs(voix).max()) * 0.95

    # ---------------------------------------------------------------- musique + bruitages
    mix = voix.copy()
    if not a.sans_musique:
        musique = np.zeros_like(voix)
        cache = {}
        for p in plans:
            h = p["scene"].get("musique", "mystere")
            if h not in cache:
                cache[h] = lire_audio(chemin_humeur(h))
            src = cache[h]
            i0, i1 = int(p["t0"] * SR), int(p["t1"] * SR)
            n = i1 - i0
            reps = int(np.ceil((i1 + SR) / len(src))) + 1
            seg = np.tile(src, reps)[i0: i0 + n + int(0.5 * SR)]   # continuité temporelle
            fondu = int(0.5 * SR)
            env = np.ones(len(seg), np.float32)
            env[:fondu] = np.linspace(0, 1, fondu)
            env[-fondu:] = np.linspace(1, 0, fondu)
            fin_ = min(len(musique), i0 + len(seg))
            musique[i0:fin_] += (seg * env)[: fin_ - i0]
        # « ducking » : la musique baisse quand quelqu'un parle
        actif = np.convolve((np.abs(voix) > 0.02).astype(np.float32), np.ones(int(0.25 * SR)) / int(0.25 * SR),
                            mode="same")
        actif = np.clip(actif * 4, 0, 1)
        gain = VOL_MUSIQUE - (VOL_MUSIQUE - VOL_MUSIQUE_SOUS_VOIX) * actif
        mix += musique * gain
        w = whoosh()
        for p in plans[1:]:
            i = max(0, int((p["t0"] - 0.22) * SR))
            mix[i: i + len(w)] += w[: len(mix) - i]
    mix = mix / max(1e-6, np.abs(mix).max()) * 0.95

    tmp = tempfile.mkdtemp()
    wav = os.path.join(tmp, "mix.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", wav],
                   input=mix.astype(np.float32).tobytes(), check=True)

    # ---------------------------------------------------------------- sous-titres
    ass = [f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Mot,ClipBlack,104,&H00FFFFFF,&H00FFFFFF,&H00101010,&H99000000,0,0,0,0,100,100,1,0,1,7,4,5,40,40,0,1
Style: Ecran,ClipBlack,84,&H00FFFFFF,&H00FFFFFF,&H00101010,&H99000000,0,0,0,0,100,100,3,0,1,6,3,5,40,40,0,1
Style: Titre,ClipBlack,92,&H0000D7FF,&H00FFFFFF,&H00101010,&H99000000,0,0,0,0,100,100,2,0,1,6,3,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""]
    # 1 mot à la fois, comme les séries de fruits virales
    for i, m in enumerate(mots):
        fin = m["end"] + 0.15
        if i + 1 < len(mots):
            fin = min(fin, mots[i + 1]["start"]) if mots[i + 1]["start"] - m["end"] < 0.3 else fin
        txt = re.sub(r"[.,;:…\"«»]", "", m["word"].upper()).strip()
        if txt:
            ass.append(f"Dialogue: 1,{ts_ass(m['start'])},{ts_ass(max(fin, m['start'] + 0.1))},Mot,,0,0,0,,"
                       f"{{\\an5\\pos({W // 2},1450)\\blur0.6\\fscx86\\fscy86\\t(0,70,\\fscx100\\fscy100)}}{txt}")
    # titre de série au début
    ass.append(f"Dialogue: 2,{ts_ass(0)},{ts_ass(2.8)},Titre,,0,0,0,,"
               f"{{\\an5\\pos({W // 2},260)\\fad(200,300)}}LES 3 FRÈRES\\N{{\\fs64\\c&HFFFFFF&}}PARTIE {num}")
    # textes d'écran (ANNÉE 3, PARTIE 2 →...)
    for p in plans:
        e = p["scene"].get("ecran")
        if not e:
            continue
        if "PARTIE" in e:
            debut = max(p["t0"], total - 2.6)
            ass.append(f"Dialogue: 2,{ts_ass(debut)},{ts_ass(total)},Ecran,,0,0,0,,"
                       f"{{\\an5\\pos({W // 2},300)\\fad(250,0)\\c&H00D7FF&}}{e}")
        else:
            debut = p["t0"] + (0.0 if p["t0"] > 3 else 2.9)
            ass.append(f"Dialogue: 2,{ts_ass(debut)},{ts_ass(min(p['t1'], debut + 2.5))},Ecran,,0,0,0,,"
                       f"{{\\an5\\pos({W // 2},300)\\fad(200,200)}}{e}")
    f_ass = os.path.join(tmp, "sous-titres.ass")
    open(f_ass, "w", encoding="utf-8").write("\n".join(ass) + "\n")

    with open(os.path.join(dossier_episode(num), "sous-titres.srt"), "w", encoding="utf-8") as f:
        for k, (d, fn, txt) in enumerate(phrases, 1):
            f.write(f"{k}\n{ts_srt(d)} --> {ts_srt(fn)}\n{txt}\n\n")

    # ---------------------------------------------------------------- image animée
    sortie = os.path.join(dossier_travail(num), f"LES_3_FRERES_EP{num:02d}.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
           "-vf", f"ass={f_ass}:fontsdir={FONTS}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", sortie]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n_total = int(round(total * FPS))
    for k, p in enumerate(plans):
        sid = p["scene"]["id"]
        img = cv2.imread(os.path.join(d_img, f"s{sid:02d}_{choix.get(str(sid), 0)}.png"))
        ih, iw = img.shape[:2]
        cw = min(iw, int(ih * 9 / 16))
        img = img[:, (iw - cw) // 2:(iw - cw) // 2 + cw]
        marge = 1.12
        grand = cv2.resize(img, (int(W * marge), int(H * marge)), interpolation=cv2.INTER_LANCZOS4)
        grand = cv2.detailEnhance(grand, sigma_s=6, sigma_r=0.08)   # léger gain de netteté
        bh, bw = grand.shape[:2]
        f0, f1 = int(round(p["t0"] * FPS)), int(round(p["t1"] * FPS))
        plan = p["scene"].get("plan", "")
        zoom_avant = "gros plan" in plan or k % 2 == 0
        sens = [-1, 1, 0][k % 3]
        for f in range(f0, min(f1, n_total)):
            x = (f - f0) / max(1, f1 - f0 - 1)
            x = x * x * (3 - 2 * x)
            z = 1.0 + 0.09 * (x if zoom_avant else 1 - x)
            cx = bw / 2 + sens * 0.05 * bw * (x - 0.5)
            cy = bh / 2
            M = np.array([[z, 0, W / 2 - z * cx], [0, z, H / 2 - z * cy]], np.float32)
            image = cv2.warpAffine(grand, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            if f - f0 < 4 and k > 0:   # petit flash blanc de transition
                image = cv2.addWeighted(image, 1 - 0.18 * (4 - (f - f0)) / 4, np.full_like(image, 255),
                                        0.18 * (4 - (f - f0)) / 4, 0)
            proc.stdin.write(image.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg a échoué")
    print(f"OK {sortie} — {total:.1f} s, {len(plans)} plans, {len(mots)} mots")


if __name__ == "__main__":
    main()
