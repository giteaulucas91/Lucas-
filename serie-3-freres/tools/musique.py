"""Ambiances musicales de secours, synthétisées (100 % libres de droits).

Si un fichier assets/musique/<humeur>.mp3 (ou .wav) existe, il est utilisé à la place :
déposez-y des pistes libres de droits pour un rendu plus « pro ».

Humeurs : mystere, tension, luxe, triste, espoir

Usage : python tools/musique.py   -> génère assets/musique/_synth/<humeur>.wav (60 s chacune)
"""
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import RACINE  # noqa: E402

SR = 44100
DUREE = 60.0
HUMEURS = ["mystere", "tension", "luxe", "triste", "espoir"]
DOSSIER = os.path.join(RACINE, "assets", "musique")


def note(n):
    """Numéro MIDI -> fréquence."""
    return 440.0 * 2 ** ((n - 69) / 12)


def t_axis(d):
    return np.arange(int(d * SR)) / SR


def pad(freqs, d, detune=0.15, brillance=3):
    """Nappe douce : plusieurs oscillateurs légèrement désaccordés."""
    t = t_axis(d)
    s = np.zeros_like(t)
    for f in freqs:
        for dv in (-detune, 0, detune):
            for h in range(1, brillance + 1):
                s += np.sin(2 * np.pi * (f + dv) * h * t + h) / (h * h)
    env = np.minimum(1, t / 1.5) * np.minimum(1, (d - t) / 1.5)
    return s * env / max(1, len(freqs) * 3)


def pluck(f, d=2.5, decay=2.2):
    """Note pincée façon piano/harpe."""
    t = t_axis(d)
    s = sum(np.sin(2 * np.pi * f * h * t) * (0.6 ** (h - 1)) for h in range(1, 6))
    return s * np.exp(-decay * t) * np.minimum(1, t / 0.005)


def kick(d=0.5):
    t = t_axis(d)
    f = 50 + 90 * np.exp(-25 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-7 * t)


def hat(d=0.06):
    t = t_axis(d)
    return np.random.default_rng(1).standard_normal(len(t)) * np.exp(-60 * t) * 0.25


def place(buf, son, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(son))
    buf[i:j] += son[: j - i] * gain


def reverb(x, taps=((0.031, 0.5), (0.047, 0.4), (0.073, 0.32), (0.11, 0.25), (0.17, 0.18), (0.23, 0.12))):
    y = x.copy()
    for dly, g in taps:
        n = int(dly * SR)
        y[n:] += x[:-n] * g
    return y


def generer(humeur):
    buf = np.zeros(int(DUREE * SR))
    rng = np.random.default_rng(len(humeur))
    if humeur == "mystere":
        place(buf, pad([note(33), note(40)], DUREE, brillance=2), 0, 0.6)
        notes = [69, 72, 76, 74, 71, 68]
        for k, t0 in enumerate(np.arange(1, DUREE - 3, 3.2)):
            place(buf, pluck(note(notes[k % len(notes)]), 3, 1.2), t0, 0.12)
    elif humeur == "tension":
        place(buf, pad([note(36), note(37), note(43)], DUREE, detune=0.4, brillance=4), 0, 0.5)
        for t0 in np.arange(0, DUREE, 0.85):     # battement de cœur
            place(buf, kick(), t0, 0.7)
            place(buf, kick(), t0 + 0.22, 0.4)
        for t0 in np.arange(0, DUREE, 0.2125):   # ostinato aigu
            place(buf, pluck(note(60 if int(t0 / 0.2125) % 2 else 61), 0.3, 12), t0, 0.06)
    elif humeur == "luxe":
        bpm = 72
        b = 60 / bpm
        accords = [[57, 60, 64], [53, 57, 60], [55, 59, 62], [52, 55, 59]]
        for k, t0 in enumerate(np.arange(0, DUREE, 4 * b)):
            place(buf, pad([note(n) for n in accords[k % 4]], 4 * b + 0.5, brillance=4), t0, 0.35)
            place(buf, pad([note(accords[k % 4][0] - 24)], 4 * b, brillance=1), t0, 0.8)
        for t0 in np.arange(0, DUREE, b):
            place(buf, kick(), t0, 0.9 if int(t0 / b) % 2 == 0 else 0.0)
        for t0 in np.arange(0, DUREE, b / 4):
            place(buf, hat(), t0, 0.5 + 0.5 * rng.random())
    elif humeur == "triste":
        accords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
        for k, t0 in enumerate(np.arange(0, DUREE, 4.0)):
            ac = accords[k % 4]
            place(buf, pad([note(ac[0] - 12)], 4.5, brillance=2), t0, 0.3)
            for j, n in enumerate(ac + [ac[1] + 12]):
                place(buf, pluck(note(n), 3.5, 1.0), t0 + j * 0.5, 0.18)
    elif humeur == "espoir":
        accords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
        for k, t0 in enumerate(np.arange(0, DUREE, 3.0)):
            ac = accords[k % 4]
            place(buf, pad([note(n) for n in ac], 3.4, brillance=3), t0, 0.3)
            place(buf, pad([note(ac[0] - 24)], 3.0, brillance=1), t0, 0.5)
            for j in range(6):
                place(buf, pluck(note(ac[j % 3] + 12), 1.5, 2.5), t0 + j * 0.5, 0.1)
    buf = reverb(buf)
    buf = buf / np.abs(buf).max() * 0.8
    return buf.astype(np.float32)


def chemin_humeur(humeur):
    """Piste à utiliser pour une humeur : fichier utilisateur s'il existe, sinon synthèse."""
    for ext in ("mp3", "wav", "m4a", "ogg"):
        p = os.path.join(DOSSIER, f"{humeur}.{ext}")
        if os.path.exists(p):
            return p
    p = os.path.join(DOSSIER, "_synth", f"{humeur}.wav")
    if not os.path.exists(p):
        ecrire(humeur)
    return p


def ecrire(humeur):
    os.makedirs(os.path.join(DOSSIER, "_synth"), exist_ok=True)
    p = os.path.join(DOSSIER, "_synth", f"{humeur}.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1",
                    "-i", "-", p], input=generer(humeur).tobytes(), check=True)
    print("musique", humeur, "->", p)


if __name__ == "__main__":
    for h in HUMEURS:
        ecrire(h)
