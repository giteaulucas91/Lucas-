"""Fabrique un clip vertical 1080x1920 façon Opus Clip.

- recadrage 9:16 qui suit le visage (mode "face") ou vidéo centrée sur fond flouté (mode "blur")
- sous-titres mot par mot : MAJUSCULES, police très grasse, blanc, contour sombre + ombre

Usage :
  python make_clip.py --src video.mp4 --words transcript.json --start 120.5 --end 175.2 \
      --out clip1.mp4 [--mode face|blur] [--hook "TEXTE D'ACCROCHE"]
"""
import argparse
import json
import os
import re
import subprocess
import tempfile

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
W, H = 1080, 1920
FILLERS = {"euh", "heu", "hum", "hmm", "bah", "ben", "mmh"}


# ---------------------------------------------------------------- sous-titres
def ass_time(t):
    t = max(0.0, t)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def load_words(path, start, end):
    data = json.load(open(path, encoding="utf-8"))
    words = []
    for seg in data["segments"]:
        for w in seg["words"]:
            if re.sub(r"\W", "", w["word"].lower()) in FILLERS:
                continue
            if w["end"] > start and w["start"] < end and w["word"]:
                words.append(
                    {
                        "start": max(0.0, w["start"] - start),
                        "end": min(end, w["end"]) - start,
                        "word": w["word"],
                    }
                )
    return words


def group_words(words, max_words=3, max_chars=16, pause=0.35):
    groups, cur = [], []
    for i, w in enumerate(words):
        if cur:
            text_len = len(" ".join(x["word"] for x in cur + [w]))
            gap = w["start"] - cur[-1]["end"]
            if (
                len(cur) >= max_words
                or text_len > max_chars
                or gap > pause
                or re.search(r"[.!?,;:]$", cur[-1]["word"])
            ):
                groups.append(cur)
                cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def clean(word):
    word = word.upper()
    word = re.sub(r"[.,;:!?…«»\"]", "", word)
    return word.replace("{", "").replace("}", "")


def build_ass(words, duration, sub_y, hook=None, hook_y=330):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,ClipBlack,104,&H00FFFFFF,&H00FFFFFF,&H00252525,&H96000000,0,0,0,0,100,100,1,0,1,7,6,5,70,70,0,1
Style: Hook,ClipBlack,74,&H00FFFFFF,&H00FFFFFF,&H00252525,&H96000000,0,0,0,0,100,100,1,0,1,6,5,5,90,90,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    groups = group_words(words)
    for i, g in enumerate(groups):
        st = g[0]["start"]
        en = g[-1]["end"] + 0.25
        if i + 1 < len(groups):
            en = min(max(en, g[-1]["end"]), groups[i + 1][0]["start"])
        en = min(en, duration)
        if en - st < 0.12:
            en = st + 0.12
        text = " ".join(clean(w["word"]) for w in g)
        anim = r"\fscx82\fscy82\t(0,90,\fscx104\fscy104)\t(90,150,\fscx100\fscy100)"
        lines.append(
            f"Dialogue: 1,{ass_time(st)},{ass_time(en)},Sub,,0,0,0,,"
            f"{{\\an5\\pos({W // 2},{sub_y})\\blur0.8{anim}}}{text}"
        )
    if hook:
        hook_txt = hook.upper().replace("|", r"\N")
        lines.append(
            f"Dialogue: 2,{ass_time(0)},{ass_time(min(3.5, duration))},Hook,,0,0,0,,"
            f"{{\\an5\\pos({W // 2},{hook_y})\\blur0.8\\fad(150,250)}}{hook_txt}"
        )
    return header + "\n".join(lines) + "\n"


# ---------------------------------------------------------------- suivi visage
def track_faces(src, start, end, fps, src_w, src_h):
    """Renvoie la position x (centre) du recadrage pour chaque image."""
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    profile = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    cap = cv2.VideoCapture(src)
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    n_frames = int(round((end - start) * fps))
    step = max(1, int(round(fps / 5)))  # ~5 détections / seconde
    scale = 480 / src_w
    samples = []  # (frame_idx, x or None, hist)
    prev_hist = None
    cuts = [0]
    for i in range(n_frames):
        ok = cap.grab()
        if not ok:
            break
        if i % step:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            break
        small = cv2.resize(frame, None, fx=scale, fy=scale)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([small], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3)
        cv2.normalize(hist, hist)
        if prev_hist is not None and cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA) > 0.45:
            cuts.append(i)
        prev_hist = hist
        faces = list(cascade.detectMultiScale(gray, 1.1, 6, minSize=(28, 28)))
        if not faces:
            faces = list(profile.detectMultiScale(gray, 1.1, 6, minSize=(28, 28)))
        x = None
        if faces:
            faces.sort(key=lambda f: f[2] * f[3], reverse=True)
            big = faces[0][2] * faces[0][3]
            cands = [f for f in faces if f[2] * f[3] >= 0.6 * big]
            last = next((s[1] for s in reversed(samples) if s[1] is not None), None)
            if last is not None:
                cands.sort(key=lambda f: abs((f[0] + f[2] / 2) / scale - last))
            fx, fy, fw, fh = cands[0]
            x = (fx + fw / 2) / scale
        samples.append((i, x))
    cap.release()
    n_frames = min(n_frames, i + 1)
    cuts.append(n_frames)

    xs = np.full(n_frames, src_w / 2.0)
    # traitement plan par plan : position stable, lissée, sans tremblement
    for a, b in zip(cuts[:-1], cuts[1:]):
        pts = [(fi, x) for fi, x in samples if a <= fi < b and x is not None]
        if not pts:
            # pas de visage : on garde la dernière position connue ou le centre
            prev = xs[a - 1] if a > 0 else src_w / 2.0
            xs[a:b] = prev
            continue
        fi_arr = np.array([p[0] for p in pts], dtype=float)
        x_arr = np.array([p[1] for p in pts], dtype=float)
        frames = np.arange(a, b)
        interp = np.interp(frames, fi_arr, x_arr)
        win = int(fps * 1.2)
        if len(interp) > 3 and win > 1:
            pad = np.pad(interp, (win, win), mode="edge")
            interp = np.convolve(pad, np.ones(2 * win + 1) / (2 * win + 1), mode="same")[win:-win]
        # zone morte : la caméra ne bouge que si le visage s'éloigne vraiment
        out = np.empty_like(interp)
        cur = interp[0]
        dead = src_w * 0.04
        for k, v in enumerate(interp):
            if abs(v - cur) > dead:
                cur += (v - cur) * 0.08
            out[k] = cur
        xs[a:b] = out
    return xs, n_frames


# ---------------------------------------------------------------- rendu
def probe(src):
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return fps, w, h


def render(args):
    fps, sw, sh = probe(args.src)
    duration = args.end - args.start
    words = load_words(args.words, args.start, args.end)
    tmp = tempfile.mkdtemp()
    ass_path = os.path.join(tmp, "subs.ass")
    sub_y = 1300 if args.mode == "face" else 1530
    hook_y = 300 if args.mode == "face" else 380
    open(ass_path, "w", encoding="utf-8").write(
        build_ass(words, duration, sub_y, args.hook, hook_y)
    )
    ass_filter = f"ass={ass_path}:fontsdir={FONTS}"
    enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]

    if args.mode == "blur":
        fg_h = int(round(W * sh / sw / 2) * 2)
        vf = (
            f"[0:v]split[a][b];"
            f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=30:3,eq=brightness=-0.08[bg];"
            f"[b]scale={W}:{fg_h}[fg];"
            f"[bg][fg]overlay=0:({H}-{fg_h})/2-140,{ass_filter},fps={min(fps, 60)}[v]"
        )
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(args.start), "-t", str(duration),
               "-i", args.src, "-filter_complex", vf, "-map", "[v]", "-map", "0:a?"] + enc + [args.out]
        subprocess.run(cmd, check=True)
        return

    # mode face : recadrage dynamique image par image
    xs, n_frames = track_faces(args.src, args.start, args.end, fps, sw, sh)
    cw = int(round(sh * 9 / 16 / 2) * 2)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-ss", str(args.start), "-t", str(n_frames / fps), "-i", args.src,
        "-map", "0:v", "-map", "1:a?", "-vf", ass_filter, "-shortest",
    ] + enc + [args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cap = cv2.VideoCapture(args.src)
    cap.set(cv2.CAP_PROP_POS_MSEC, args.start * 1000)
    for i in range(n_frames):
        ok, frame = cap.read()
        if not ok:
            break
        x0 = int(np.clip(xs[i] - cw / 2, 0, sw - cw))
        crop = frame[:, x0 : x0 + cw]
        crop = cv2.resize(crop, (W, H), interpolation=cv2.INTER_CUBIC)
        proc.stdin.write(crop.tobytes())
    cap.release()
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg a échoué")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True)
    p.add_argument("--words", required=True)
    p.add_argument("--start", type=float, required=True)
    p.add_argument("--end", type=float, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--mode", choices=["face", "blur"], default="face")
    p.add_argument("--hook", default=None)
    render(p.parse_args())


if __name__ == "__main__":
    main()
