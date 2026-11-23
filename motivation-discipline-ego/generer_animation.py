#!/usr/bin/env python3
"""
MOTIVATION / DISCIPLINE / EGO — animation minimaliste 9:16 (1080x1920, 30 i/s, 35 s).

Fond noir, traits blancs fins, stick figures. Trois cadres côte à côte :
les trois font des tractions ; Motivation lâche (≈9,6 s), Ego lâche (≈19 s),
Discipline ne s'arrête jamais. Carte de fin TikTok + recherche @teamlouise82.

Usage :
    python3 generer_animation.py                 # rend la vidéo complète
    python3 generer_animation.py --apercu        # planche de vignettes clés (PNG)
    python3 generer_animation.py --image 12.5    # une seule image à t = 12,5 s
"""
import argparse
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- réglages
W, H = 1080, 1920
FPS = 30
DUREE = 35.0
SS = 2                      # sur-échantillonnage pour l'anticrénelage
ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "MOTIVATION_DISCIPLINE_EGO.mp4")
POLICE = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
POLICE_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
PSEUDO = "@teamlouise82"

# Mise en page des cadres
MARGE, ECART = 54, 36
CW = (W - 2 * MARGE - 2 * ECART) // 3          # 300 px
YT, YB = 478, 1538                              # haut / bas des cadres
COLS = [MARGE + i * (CW + ECART) for i in range(3)]
TITRES = ["MOTIVATION", "DISCIPLINE", "EGO"]
BAR_Y = YT + 112
SOL = YB - 3                                    # le sol = bas du cadre
K = 1.12                                        # échelle des personnages
LW = 5                                          # épaisseur des traits (px à 1x)
R_TETE = 22 * K
BRAS = 56 * K

# Temps clés (secondes)
T_FIN_ANIM = 32.0           # début du fondu vers la carte de fin
M_LACHE_1, M_LACHE = 9.35, 9.60     # Motivation : une main, puis les deux
E_LACHE_1, E_LACHE = 18.75, 19.05   # Ego : une main, puis les deux
G = 5600.0                  # gravité (px/s²)

ROUGE_COEUR = np.array([1.0, 0.17, 0.17], np.float32)
ROUGE_GLOW = np.array([1.0, 0.08, 0.10], np.float32)


# ---------------------------------------------------------------- outils
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(a, b, t):
    u = clamp((t - a) / (b - a))
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


EASES = {
    "io": lambda u: 0.5 - 0.5 * math.cos(math.pi * u),
    "out": lambda u: 1 - (1 - u) ** 3,
    "in": lambda u: u ** 3,
    "back": lambda u: 1 + 2.70158 * (u - 1) ** 3 + 1.70158 * (u - 1) ** 2,
    "lin": lambda u: u,
}


def keyframes(keys, t):
    """keys = [(t, valeur, easing_du_segment_qui_arrive), ...]"""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0, _), (t1, v1, e) in zip(keys, keys[1:]):
        if t < t1:
            return v0 + (v1 - v0) * EASES[e]((t - t0) / (t1 - t0))
    return keys[-1][1]


def bruit(t, graine, f=1.0):
    """Bruit lisse pseudo-aléatoire dans [-1, 1]."""
    s = graine * 12.9898
    return (math.sin(t * f * 6.283 + s) * 0.5
            + math.sin(t * f * 10.17 + s * 1.7) * 0.3
            + math.sin(t * f * 15.33 + s * 2.3) * 0.2)


def v(x, y):
    return np.array([x, y], dtype=np.float64)


def rot(p, centre, a):
    c, s = math.cos(a), math.sin(a)
    d = p - centre
    return centre + v(d[0] * c - d[1] * s, d[0] * s + d[1] * c)


def ik(epaule, main, cote):
    """Coude d'un bras à deux segments égaux, plié vers l'extérieur."""
    d = main - epaule
    dist = min(np.linalg.norm(d), 2 * BRAS - 0.01)
    dist = max(dist, 1e-3)
    u = d / np.linalg.norm(d)
    a = dist / 2
    h = math.sqrt(max(BRAS * BRAS - a * a, 0))
    perp = v(-u[1], u[0])
    c1, c2 = epaule + u * a + perp * h, epaule + u * a - perp * h
    return c1 if (c1[0] - c2[0]) * cote > 0 else c2


CLES = ["tete", "N", "Ls", "Rs", "Le", "Re", "Lh", "Rh", "hip", "Lk", "Rk", "Lf", "Rf"]


def mix(P, Q, u):
    return {c: lerp(P[c], Q[c], u) for c in CLES}


def translate(P, d):
    return {c: P[c] + d for c in CLES}


# ---------------------------------------------------------------- poses
def pose_suspendu(cx, h, *, tremble=0.0, balancier=0.0, ecart=0.0, genoux=0.0,
                  lache=None, t=0.0, graine=0, desordre=0.0):
    """Personnage accroché à la barre. h : 0 = bras tendus, 1 = menton au-dessus."""
    mL, mR = v(cx - 48 * K, BAR_Y), v(cx + 48 * K, BAR_Y)
    sy = BAR_Y + lerp(104, 4, h) * K
    nx = cx
    if lache == "L":
        nx, sy = cx + 16 * K, sy + 8 * K
    elif lache == "R":
        nx, sy = cx - 16 * K, sy + 8 * K
    tx = tremble * 3.2 * K * bruit(t, graine + 1, 9.0)
    ty = tremble * 2.6 * K * bruit(t, graine + 2, 11.0)
    jx = desordre * 6 * K * bruit(t, graine + 3, 2.3)
    N = v(nx + tx + jx, sy + ty)
    P = {"N": N}
    P["Ls"], P["Rs"] = N + v(-13 * K, 0), N + v(13 * K, 0)
    P["tete"] = N + v(tremble * 1.5 * bruit(t, graine + 4, 13), -(10 * K + R_TETE))

    for cote, s, m, lab in ((-1, "Ls", mL, "L"), (1, "Rs", mR, "R")):
        e, hnd = ("Le", "Lh") if lab == "L" else ("Re", "Rh")
        if lache == lab:                                    # bras qui pend
            d1 = v(0.28 * cote, 0.96)
            d2 = v(0.12 * cote, 0.99)
            sw = 0.25 * math.sin(t * 7.0 + graine)
            P[e] = P[s] + rot(d1 * BRAS, v(0, 0), sw)
            P[hnd] = P[e] + rot(d2 * BRAS, v(0, 0), sw * 1.4)
        else:
            P[hnd] = m.copy()
            el = ik(P[s], m, cote)
            el = el + v(tremble * 3.5 * K * bruit(t, graine + 5 + cote, 12), 0)
            P[e] = el

    hip = N + v(0, 112 * K)
    P["hip"] = hip
    ly = (122 - 20 * h) * K
    P["Lk"] = hip + v(-9 * K - ecart * 0.5, (62 - 8 * h) * K - genoux)
    P["Rk"] = hip + v(9 * K + ecart * 0.5, (62 - 8 * h) * K - genoux)
    P["Lf"] = hip + v(-11 * K - ecart, ly - genoux * 1.4)
    P["Rf"] = hip + v(11 * K + ecart, ly - genoux * 1.4)
    if desordre:
        for c, gr in (("Lk", 7), ("Rk", 8), ("Lf", 9), ("Rf", 10)):
            amp = 10 if c[1] == "f" else 5
            P[c] = P[c] + v(desordre * amp * K * bruit(t, graine + gr, 1.7),
                            desordre * amp * 0.6 * K * bruit(t, graine + gr + 20, 2.1))
    for c in ("hip", "Lk", "Rk", "Lf", "Rf"):
        P[c] = rot(P[c], N, balancier)
    return P


def pose_accroupi(cx):
    F = SOL
    P = {
        "Lf": v(cx - 32 * K, F - 2), "Rf": v(cx + 32 * K, F - 2),
        "Lk": v(cx - 38 * K, F - 52 * K), "Rk": v(cx + 38 * K, F - 52 * K),
        "hip": v(cx, F - 92 * K),
    }
    N = v(cx, F - 196 * K)
    P.update({"N": N, "Ls": N + v(-13 * K, 0), "Rs": N + v(13 * K, 0),
              "tete": N + v(0, -32 * K)})
    P["Le"], P["Re"] = N + v(-58 * K, -8 * K), N + v(58 * K, -8 * K)
    P["Lh"], P["Rh"] = N + v(-100 * K, -36 * K), N + v(100 * K, -36 * K)
    return P


def pose_assis(cx, t, t_sol):
    """Motivation : assis par terre, genoux relevés, tête basse, souffle lourd."""
    F = SOL
    amp = lerp(4.5, 2.2, smooth(0, 6, t - t_sol)) * K
    b = amp * math.sin(2 * math.pi * (t - t_sol) / 2.4)
    P = {
        "hip": v(cx, F - 14 * K),
        "Lk": v(cx - 44 * K, F - 74 * K), "Rk": v(cx + 44 * K, F - 74 * K),
        "Lf": v(cx - 54 * K, F - 2), "Rf": v(cx + 54 * K, F - 2),
    }
    N = v(cx + 3 * K, F - 112 * K + b)
    tete_baisse = 0.6 + 0.4 * smooth(0, 3, t - t_sol)
    P.update({"N": N, "Ls": N + v(-13 * K, 0), "Rs": N + v(13 * K, 0),
              "tete": N + v(6 * K * tete_baisse, -lerp(32, 24, tete_baisse) * K + b * 0.3)})
    P["Le"] = v(cx - 44 * K, F - 80 * K + b * 0.4)
    P["Re"] = v(cx + 44 * K, F - 80 * K + b * 0.4)
    P["Lh"] = v(cx - 20 * K, F - 34 * K + b * 0.2)
    P["Rh"] = v(cx + 20 * K, F - 34 * K + b * 0.2)
    return P


def pose_debout_bras(cx, a, b=-0.55, secoue=0.0, t=0.0):
    """Ego : debout, bras écartés (a = angle sous l'horizontale)."""
    F = SOL
    P = {
        "Lf": v(cx - 30 * K, F - 2), "Rf": v(cx + 30 * K, F - 2),
        "Lk": v(cx - 20 * K, F - 62 * K), "Rk": v(cx + 20 * K, F - 62 * K),
        "hip": v(cx, F - 122 * K),
    }
    N = v(cx, F - 232 * K)
    P.update({"N": N, "Ls": N + v(-13 * K, 0), "Rs": N + v(13 * K, 0)})
    P["tete"] = N + v(secoue * 7 * K * math.sin(t * 13), -32 * K)
    for cote, s, e, hnd in ((-1, "Ls", "Le", "Lh"), (1, "Rs", "Re", "Rh")):
        P[e] = P[s] + v(cote * math.cos(a), math.sin(a)) * BRAS
        P[hnd] = P[e] + v(cote * math.cos(a + b), math.sin(a + b)) * BRAS
    return P


def chute(P0, t_lache, t):
    """Corps qui tombe depuis la pose de lâcher. Renvoie (pose, t_atterrissage)."""
    pied = max(P0["Lf"][1], P0["Rf"][1])
    dist = (SOL - 2) - pied
    t_sol = t_lache + math.sqrt(2 * dist / G)
    tau = min(t, t_sol) - t_lache
    P = translate(P0, v(0, 0.5 * G * tau * tau))
    # les jambes s'écartent un peu pendant la chute
    u = clamp(tau / max(t_sol - t_lache, 1e-3))
    P["Lf"] = P["Lf"] + v(-8 * K * u, 0)
    P["Rf"] = P["Rf"] + v(8 * K * u, 0)
    return P, t_sol


def atterrissage(P_sol, cible, cx, t, t_sol, d1=0.16, d2=0.7):
    """Impact (flexion) puis transition vers la pose finale."""
    L = t - t_sol
    acc = pose_accroupi(cx)
    if L < d1:
        return mix(P_sol, acc, EASES["out"](L / d1))
    return mix(acc, cible, EASES["io"](clamp((L - d1) / d2)))


# ---------------------------------------------------------------- personnages
def h_sync(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)      # période 2 s


CLES_M = [(6.00, 0.00, "io"), (7.20, 0.80, "io"), (8.10, 0.10, "io"),
          (9.00, 0.42, "io"), (9.20, 0.33, "io"), (9.45, 0.12, "io"),
          (9.60, 0.02, "in")]

CLES_E = [(6.00, 0.00, "io"), (6.30, 1.06, "back"), (6.55, 0.97, "io"),
          (6.85, 1.02, "io"), (7.10, 0.00, "in"), (7.55, 0.06, "io"),
          (7.85, 1.06, "back"), (8.40, 1.00, "io"), (8.62, 0.00, "in"),
          (8.95, 0.98, "back"), (9.30, 0.92, "io"), (9.55, 0.00, "in"),
          (9.95, 0.86, "back"), (10.45, 0.15, "in"), (11.10, 0.70, "out"),
          (11.40, 0.55, "io"), (11.70, 0.63, "io"), (12.05, 0.10, "in"),
          (12.70, 0.55, "out"), (13.10, 0.05, "in"), (13.40, 0.15, "io"),
          (14.10, 0.45, "out"), (14.40, 0.30, "io"), (14.60, 0.40, "io"),
          (15.00, 0.00, "in"), (15.90, 0.32, "out"), (16.30, 0.05, "in"),
          (17.10, 0.22, "out"), (17.40, 0.02, "in"), (18.20, 0.15, "out"),
          (18.60, 0.00, "io"), (19.05, 0.00, "lin")]


def etat_motivation(t):
    cx = COLS[0] + CW / 2
    info = {"mains": [], "halo": None}
    if t < M_LACHE:
        h = h_sync(t) if t < 6 else keyframes(CLES_M, t)
        tr = smooth(6.6, 9.6, t)
        lache = "L" if t >= M_LACHE_1 else None
        P = pose_suspendu(cx, h, tremble=tr, lache=lache, t=t, graine=3)
        I = 0.8 + 0.15 * h if t < 6 else 0.85 + 0.75 * smooth(6.3, 9.5, t)
        I *= 1 + 0.12 * tr * math.sin(t * 40)          # le rouge « vibre »
        pts = [P["Ls"], P["Rs"], P["Rh"]] + ([] if lache else [P["Lh"]])
        info["mains"] = [(p, I) for p in pts]
        return P, info
    P0 = pose_suspendu(cx, keyframes(CLES_M, M_LACHE), tremble=1.0, lache="L",
                       t=M_LACHE, graine=3)
    Pc, t_sol = chute(P0, M_LACHE, t)
    if t < t_sol:
        return Pc, info
    P = atterrissage(Pc, pose_assis(cx, t, t_sol), cx, t, t_sol, 0.16, 0.75)
    info["halo"] = halo(P, t, t_sol)
    return P, info


def etat_discipline(t):
    cx = COLS[1] + CW / 2
    h = h_sync(t)                                      # rythme constant, sans fin
    P = pose_suspendu(cx, h, t=t, graine=7)
    I = 0.8 + 0.15 * h
    return P, {"mains": [(P[c], I) for c in ("Ls", "Rs", "Lh", "Rh")], "halo": None}


def balancier_ego(t):
    if t < 6:
        return 0.0
    if t < 10:
        kip = 0.16 * math.sin(2 * math.pi * (t - 7.1) / 0.9) * smooth(7.1, 7.25, t) \
            * (1 - smooth(7.7, 7.9, t))
        return kip + 0.04 * math.sin(2 * math.pi * t / 1.3)
    a = lerp(0.05, 0.2, smooth(10, 18, t))
    return a * (math.sin(2 * math.pi * t / 1.4) + 0.6 * math.sin(2 * math.pi * t / 0.63 + 1))


def etat_ego(t):
    cx = COLS[2] + CW / 2
    info = {"mains": [], "halo": None}
    if t < E_LACHE:
        h = h_sync(t) if t < 6 else keyframes(CLES_E, t)
        # poses « théâtrales » : écart de jambes en haut des tractions
        flair = 0.0
        for a, b in ((6.35, 6.95), (7.95, 8.45), (9.0, 9.35), (10.0, 10.3)):
            flair = max(flair, smooth(a, a + 0.12, t) * (1 - smooth(b - 0.12, b, t)))
        desordre = smooth(9.8, 12.5, t) * (0.6 + 0.6 * smooth(12.5, 18.5, t))
        lache = "R" if t >= E_LACHE_1 else None
        P = pose_suspendu(cx, h, balancier=balancier_ego(t), ecart=flair * 44 * K,
                          genoux=flair * 26 * K, lache=lache, t=t, graine=11,
                          desordre=desordre, tremble=smooth(14, 19, t) * 0.6)
        I = 0.8 + 0.15 * h if t < 6 else 0.85 + 0.55 * smooth(10, 19, t)
        pts = [P["Ls"], P["Rs"], P["Lh"]] + ([] if lache else [P["Rh"]])
        info["mains"] = [(p, I) for p in pts]
        return P, info
    P0 = etat_ego(E_LACHE - 1e-6)[0]
    Pc, t_sol = chute(P0, E_LACHE, t)
    if t < t_sol:
        return Pc, info
    # bras écartés : « pourquoi ?! » — gestes de frustration, puis impuissance
    a = 0.42
    for tp in (20.7, 22.3, 23.9):
        u = t - tp
        if 0 <= u < 1.0:
            a -= 0.6 * (EASES["out"](u / 0.2) if u < 0.2 else 1 - EASES["io"]((u - 0.2) / 0.8))
    secoue = 0.0
    if t >= 25:
        a += 0.07 * math.sin(2 * math.pi * (t - 25) / 1.7)
    else:
        secoue = smooth(20.0, 20.4, t) * (1 - smooth(24.3, 24.8, t)) * 0.5
    cible = pose_debout_bras(cx, a, secoue=secoue, t=t)
    P = atterrissage(Pc, cible, cx, t, t_sol, 0.16, 0.6)
    info["halo"] = halo(P, t, t_sol)
    return P, info


def halo(P, t, t_sol):
    pts = np.array([P[c] for c in CLES])
    lo, hi = pts.min(0), pts.max(0)
    centre = (lo + hi) / 2
    L = t - t_sol
    flash = math.exp(-L * 3.5)
    I = smooth(0, 0.35, L) * (0.6 + 0.14 * math.sin(2 * math.pi * L / 1.9)) + 0.6 * flash
    return {
        "centre": centre,
        "rx": min((hi[0] - lo[0]) / 2 + 40 * K, CW / 2 - 28),
        "ry": (hi[1] - lo[1]) / 2 + 46 * K,
        "I": I,
        "onde": L if L < 0.7 else None,
        "sol": SOL,
    }


# ---------------------------------------------------------------- dessin
_polices = {}


def police(chemin, taille):
    cle = (chemin, taille)
    if cle not in _polices:
        _polices[cle] = ImageFont.truetype(chemin, taille)
    return _polices[cle]


def texte_espace(d, cx, y, txt, f, esp, fill):
    larg = [d.textlength(c, font=f) for c in txt]
    total = sum(larg) + esp * (len(txt) - 1)
    x = cx - total / 2
    for c, l in zip(txt, larg):
        d.text((x, y), c, font=f, fill=fill)
        x += l + esp


def taille_titre():
    d = ImageDraw.Draw(Image.new("L", (10, 10)))
    for s in range(120, 20, -1):
        f = police(POLICE, s * SS)
        if d.textlength("MOTIVATION", font=f) + 5 * SS * 9 <= (CW - 18) * SS:
            return s
    return 40


TAILLE_TITRE = taille_titre()


def segment(d, a, b, w):
    a, b = a * SS, b * SS
    d.line([tuple(a), tuple(b)], fill=255, width=int(w * SS))
    r = w * SS / 2
    for p in (a, b):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=255)


def dessiner_personnage(d, P):
    os_ = [("Ls", "Rs"), ("N", "hip"), ("Ls", "Le"), ("Le", "Lh"), ("Rs", "Re"),
           ("Re", "Rh"), ("hip", "Lk"), ("Lk", "Lf"), ("hip", "Rk"), ("Rk", "Rf")]
    for a, b in os_:
        segment(d, P[a], P[b], LW)
    tete, N = P["tete"], P["N"]
    u = (N - tete) / max(np.linalg.norm(N - tete), 1e-3)
    segment(d, N, tete + u * R_TETE, LW)
    c, r = tete * SS, R_TETE * SS
    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=0, outline=255, width=int(LW * SS))


def dessiner_decor(d):
    f = police(POLICE, TAILLE_TITRE * SS)
    asc = f.getbbox("M")
    for x0, titre in zip(COLS, TITRES):
        d.rectangle([x0 * SS, YT * SS, (x0 + CW) * SS, YB * SS], outline=255, width=3 * SS)
        hy = (YT - 34) * SS - asc[3]
        texte_espace(d, (x0 + CW / 2) * SS, hy, titre, f, 5 * SS, 255)
        # barre de traction + montants
        d.line([(x0 * SS, BAR_Y * SS), ((x0 + CW) * SS, BAR_Y * SS)], fill=255, width=6 * SS)


def rendre_scene(t):
    traits = Image.new("L", (W * SS, H * SS), 0)
    coeur = Image.new("L", (W * SS, H * SS), 0)
    serre = Image.new("L", (W // 2, H // 2), 0)
    large = Image.new("L", (W // 2, H // 2), 0)
    dt, dc = ImageDraw.Draw(traits), ImageDraw.Draw(coeur)
    ds, dl = ImageDraw.Draw(serre), ImageDraw.Draw(large)
    dessiner_decor(dt)

    for etat in (etat_motivation, etat_discipline, etat_ego):
        P, info = etat(t)
        hl = info["halo"]
        if hl:
            hm = Image.new("L", (W // 2, H // 2), 0)
            dh = ImageDraw.Draw(hm)
            c, rx, ry = hl["centre"] / 2, hl["rx"] / 2, hl["ry"] / 2
            g = int(clamp(hl["I"] * 0.48) * 170)
            dh.ellipse([c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry], fill=g)
            g2 = int(clamp(hl["I"] * 0.35) * 170)
            dh.ellipse([c[0] - rx * 1.15, c[1] - ry * 1.15, c[0] + rx * 1.15, c[1] + ry * 1.15],
                       outline=g2, width=8)
            # le halo reste à l'intérieur du cadre (le flou le fait juste déborder)
            x0 = COLS[[etat_motivation, etat_discipline, etat_ego].index(etat)]
            boite = (x0 // 2, YT // 2, (x0 + CW) // 2, SOL // 2)
            large.paste(ImageChops.lighter(large.crop(boite), hm.crop(boite)), boite[:2])
            if hl["onde"] is not None:                 # onde de choc à l'impact
                u = hl["onde"] / 0.7
                rr = lerp(20, 150, EASES["out"](u)) * K / 2
                sy = hl["sol"] / 2
                gi = int((1 - u) ** 1.5 * 170)
                ds.ellipse([c[0] - rr, sy - rr * 0.22, c[0] + rr, sy + rr * 0.22],
                           outline=gi, width=2)
        dessiner_personnage(dt, P)
        for p, I in info["mains"]:
            r = 7 * K * (0.85 + 0.25 * clamp(I - 0.8, 0, 1))
            cs = p * SS
            dc.ellipse([cs[0] - r * SS, cs[1] - r * SS, cs[0] + r * SS, cs[1] + r * SS],
                       fill=int(clamp(0.55 + 0.45 * I) * 255))
            q = p / 2
            rs = r * 0.9
            ds.ellipse([q[0] - rs, q[1] - rs, q[0] + rs, q[1] + rs], fill=int(clamp(I / 1.6) * 170))
            rl = r * (1.6 + 1.0 * clamp(I - 0.8, 0, 1))
            dl.ellipse([q[0] - rl, q[1] - rl, q[0] + rl, q[1] + rl], fill=int(clamp(I / 1.6) * 120))

    Wt = np.asarray(traits.resize((W, H), Image.LANCZOS), np.float32) / 255
    C = np.asarray(coeur.resize((W, H), Image.LANCZOS), np.float32) / 255
    Gs = np.asarray(serre.filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR),
                    np.float32) / 170
    Gl = np.asarray(large.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR),
                    np.float32) / 170
    Gtot = Gs * 1.3 + Gl * 1.25
    img = Wt[..., None] * (1 - C[..., None]) + C[..., None] * ROUGE_COEUR
    img = img + Gtot[..., None] * ROUGE_GLOW
    # légère montée vers le blanc au cœur du glow le plus intense
    img = img + np.clip(Gs - 0.8, 0, 1)[..., None] * 0.25
    return np.clip(img, 0, 1)


# ---------------------------------------------------------------- carte de fin
def masque_note(taille):
    """Masque L (en px SS) d'une note de musique façon logo TikTok, centrée."""
    u = taille / 200.0 * SS
    m = Image.new("L", (int(260 * u), int(280 * u)), 0)
    d = ImageDraw.Draw(m)
    ox, oy = 130 * u, 140 * u

    def box(cx, cy, r):
        return [ox + (cx - r) * u, oy + (cy - r) * u, ox + (cx + r) * u, oy + (cy + r) * u]
    # drapeau (quart d'anneau en haut à droite)
    d.pieslice(box(20, -28, 72), 270, 360, fill=255)
    d.pieslice(box(20, -28, 44), 270, 360, fill=0)
    # boule
    d.ellipse(box(-10, 46, 58), fill=255)
    d.ellipse(box(-10, 46, 28), fill=0)
    # hampe
    d.rectangle([ox + 20 * u, oy - 75 * u, ox + 48 * u, oy + 46 * u], fill=255)
    return m


def rendre_fin(t):
    L = t - (T_FIN_ANIM + 0.45)
    img = np.zeros((H, W, 3), np.float32)
    if L < 0:
        return img
    toile = Image.new("RGB", (W * SS, H * SS), (0, 0, 0))
    # --- logo
    a_logo = clamp(L / 0.35)
    ech = EASES["back"](clamp(L / 0.45)) if L < 0.45 else 1.0
    taille = 230 * max(ech, 0.05)
    m = masque_note(taille)
    cx, cy = W / 2 * SS, 700 * SS
    dec = 7 * taille / 230 * SS
    for col, (dx, dy) in (((37, 244, 238), (-dec, -dec * 0.7)),
                          ((254, 44, 85), (dec, dec * 0.7)),
                          ((255, 255, 255), (0, 0))):
        couche = Image.new("RGB", m.size, col)
        toile.paste(couche, (int(cx - m.size[0] / 2 + dx), int(cy - m.size[1] / 2 + dy)), m)
    d = ImageDraw.Draw(toile)
    fw = police(POLICE, 96 * SS)
    texte_espace(d, cx, 870 * SS, "TikTok", fw, 0, (255, 255, 255))
    logo = np.asarray(toile.resize((W, H), Image.LANCZOS), np.float32) / 255 * a_logo

    # --- barre de recherche
    Lb = L - 0.45
    if Lb > 0:
        a_bar = EASES["out"](clamp(Lb / 0.4))
        glisse = (1 - a_bar) * 60
        barre = Image.new("RGB", (W * SS, H * SS), (0, 0, 0))
        db = ImageDraw.Draw(barre)
        bx0, bx1 = 110, W - 110
        by0 = 1110 + glisse
        by1 = by0 + 124
        db.rounded_rectangle([bx0 * SS, by0 * SS, bx1 * SS, by1 * SS], radius=62 * SS,
                             fill=(241, 241, 242))
        # loupe
        lx, ly, lr = (bx0 + 70) * SS, (by0 + 58) * SS, 22 * SS
        db.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], outline=(120, 120, 128), width=6 * SS)
        db.line([(lx + 15 * SS, ly + 15 * SS), (lx + 33 * SS, ly + 33 * SS)],
                fill=(120, 120, 128), width=7 * SS)
        # bouton « Rechercher »
        fr = police(POLICE, 44 * SS)
        lab = "Rechercher"
        lw_ = db.textlength(lab, font=fr)
        rx = (bx1 - 40) * SS - lw_
        db.line([(rx - 30 * SS, (by0 + 30) * SS), (rx - 30 * SS, (by1 - 30) * SS)],
                fill=(205, 205, 210), width=3 * SS)
        db.text((rx, (by0 + 62) * SS), lab, font=fr, fill=(254, 44, 85), anchor="lm")
        # pseudo tapé lettre par lettre + curseur
        ft = police(POLICE, 54 * SS)
        n = int(clamp((Lb - 0.45) / 0.9) * len(PSEUDO) + 1e-6) if Lb > 0.45 else 0
        txt = PSEUDO[:n]
        tx = (bx0 + 118) * SS
        db.text((tx, (by0 + 62) * SS), txt, font=ft, fill=(22, 24, 35), anchor="lm")
        if (Lb < 0.45) or (int(Lb * 2.4) % 2 == 0) or n < len(PSEUDO):
            cxr = tx + db.textlength(txt, font=ft) + 5 * SS
            db.line([(cxr, (by0 + 34) * SS), (cxr, (by1 - 34) * SS)], fill=(254, 44, 85),
                    width=5 * SS)
        img_b = np.asarray(barre.resize((W, H), Image.LANCZOS), np.float32) / 255 * a_bar
        logo = logo + img_b
    return np.clip(logo, 0, 1)


# ---------------------------------------------------------------- image finale
def image(t):
    if t < T_FIN_ANIM + 0.45:
        f = 1 - smooth(T_FIN_ANIM, T_FIN_ANIM + 0.45, t)
        out = rendre_scene(t) * f
    else:
        out = rendre_fin(t)
    return (out * 255 + 0.5).astype(np.uint8)


def image_n(i):
    return image(i / FPS).tobytes()


def rendre_video():
    n = int(round(DUREE * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-map", "0:v", "-map", "1:a", "-shortest",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
           "-tune", "animation", "-c:a", "aac", "-b:a", "96k",
           "-movflags", "+faststart", SORTIE]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, data in enumerate(pool.imap(image_n, range(n), chunksize=3)):
            ff.stdin.write(data)
            if i % 60 == 0:
                print(f"  {i / FPS:5.1f} s / {DUREE:.0f} s", flush=True)
    ff.stdin.close()
    ff.wait()
    print("Vidéo :", SORTIE)


def apercu(chemin):
    temps = [1.0, 2.0, 6.8, 8.6, 9.45, 9.8, 11.0, 13.0, 15.5,
             18.9, 19.3, 21.0, 24.0, 28.0, 32.2, 34.6]
    vw, vh = W // 4, H // 4
    planche = Image.new("RGB", (vw * 4, vh * 4), (40, 40, 40))
    d = ImageDraw.Draw(planche)
    for k, t in enumerate(temps):
        im = Image.fromarray(image(t)).resize((vw, vh), Image.LANCZOS)
        planche.paste(im, ((k % 4) * vw, (k // 4) * vh))
        d.text(((k % 4) * vw + 6, (k // 4) * vh + 4), f"{t:.2f}s", fill=(255, 255, 0))
    planche.save(chemin)
    print("Aperçu :", chemin)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apercu", nargs="?", const=os.path.join(ICI, "apercu.png"))
    ap.add_argument("--image", type=float)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.image is not None:
        p = a.out or os.path.join(ICI, f"image_{a.image:05.2f}.png")
        Image.fromarray(image(a.image)).save(p)
        print(p)
    elif a.apercu:
        apercu(a.apercu)
    else:
        rendre_video()
