#!/usr/bin/env python3
"""
MOTIVATION / DISCIPLINE / EGO — animation « cinématique » 9:16 (1080x1920, 30 i/s, 35 s).

Rendu motion design : fond anthracite, projecteurs volumétriques, poussières dans la
lumière, bokeh, grain, personnages épais de profil (membres du fond en gris), flou de
mouvement, secousses + ondes à l'impact, titres monospace tapés à la machine, carte de
fin glitch TikTok + recherche @teamlouise82. Bande-son synthétisée (nappe, pulsation,
impacts, glitch, frappe clavier).

Usage :
    python3 generer_animation.py                 # vidéo complète (+ son)
    python3 generer_animation.py --apercu        # planche de vignettes clés (PNG)
    python3 generer_animation.py --image 12.5    # une image à t = 12,5 s
"""
import argparse
import math
import os
import subprocess
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ================================================================= réglages
W, H = 1080, 1920
FPS = 30
DUREE = 35.0
SS = 2
ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "MOTIVATION_DISCIPLINE_EGO.mp4")
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
INTER_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
PSEUDO = "@teamlouise82"

MARGE, ECART = 54, 36
CW = (W - 2 * MARGE - 2 * ECART) // 3          # 300
YT, YB = 440, 1560
COLS = [MARGE + i * (CW + ECART) for i in range(3)]
CXS = [c + CW / 2 for c in COLS]
TITRES = ["MOTIVATION", "DISCIPLINE", "EGO"]
BAR_Y = YT + 112
SOL = YB - 4

UA, FA = 54.0, 52.0                              # bras, avant-bras
K = 1.4                                          # échelle des personnages
R_TETE = 25.0 * K
LW_N, LW_F = 18.0, 16.0                          # épaisseur membres avant / arrière

T_FIN = 32.0                                     # glitch vers la carte de fin
M_LACHE_1, M_LACHE = 9.35, 9.60
E_LACHE_1, E_LACHE = 18.75, 19.05
G = 5600.0

BLANC = np.array([0.95, 0.95, 0.93], np.float32)
SAUMON = np.array([1.0, 0.52, 0.47], np.float32)
ROUGE_TERNE = np.array([0.80, 0.42, 0.42], np.float32)
ROUGE_COEUR = np.array([1.0, 0.20, 0.18], np.float32)
ROUGE_GLOW = np.array([1.0, 0.09, 0.10], np.float32)
NAVY = np.array([14, 16, 25], np.float32) / 255
CYAN = (37, 244, 238)
ROSE = (254, 44, 85)


# ================================================================= outils
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
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0, _), (t1, v1, e) in zip(keys, keys[1:]):
        if t < t1:
            return v0 + (v1 - v0) * EASES[e]((t - t0) / (t1 - t0))
    return keys[-1][1]


def bruit(t, g, f=1.0):
    s = g * 12.9898
    return (math.sin(t * f * 6.283 + s) * 0.5 + math.sin(t * f * 10.17 + s * 1.7) * 0.3
            + math.sin(t * f * 15.33 + s * 2.3) * 0.2)


def v(x, y):
    return np.array([x, y], dtype=np.float64)


def rotv(d, a):
    c, s = math.cos(a), math.sin(a)
    return v(d[0] * c - d[1] * s, d[0] * s + d[1] * c)


def ik(a, b, L1, L2, pref):
    """Articulation intermédiaire entre a et b ; pref = direction préférée du pli."""
    d = b - a
    n = max(np.linalg.norm(d), 1e-3)
    dist = clamp(n, abs(L1 - L2) + 0.01, L1 + L2 - 0.01)
    u = d / n
    x = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(L1 * L1 - x * x, 0))
    p = v(-u[1], u[0])
    c1, c2 = a + u * x + p * h, a + u * x - p * h
    return c1 if np.dot(c1 - c2, pref) > 0 else c2


CLES = ["tete", "N", "nS", "fS", "hip", "nE", "nH", "fE", "fH", "nK", "nF", "fK", "fF"]


def echelle(P, ancre):
    P.setdefault("nS", P["N"])
    P.setdefault("fS", P["N"])
    R = {c: ancre + K * (P[c] - ancre) for c in CLES}
    R["far"] = P["far"]
    return R


def mix(P, Q, u):
    R = {c: lerp(P[c], Q[c], u) for c in CLES}
    R["far"] = lerp(P["far"], Q["far"], u)
    return R


def translate(P, d):
    R = {c: P[c] + d for c in CLES}
    R["far"] = P["far"]
    return R


# ================================================================= poses
def pose_suspendu(cx, h, t, *, tremble=0.0, balancier=0.0, kick=0.0, lache=False,
                  graine=0, desordre=0.0):
    """Vue de face, mains sur la barre, bras en V. h : 0 bras tendus → 1 menton au-dessus.
    Jambe gauche (gris) croisée derrière la droite pour la profondeur."""
    def nz(g, f, a):
        return a * bruit(t, graine + g, f)
    sx = cx + nz(1, 9, tremble * 3.2) + nz(3, 2.3, desordre * 7)
    sy = BAR_Y + lerp(103, 10, h) + nz(2, 11, tremble * 2.6)
    if lache:
        sx, sy = sx + 13, sy + 7
    N = v(sx, sy)
    P = {"N": N, "far": 0.66, "nS": N + v(14, 3), "fS": N + v(-14, 3)}
    P["tete"] = N + v(nz(4, 13, tremble * 1.5), -37)
    P["nH"] = v(cx + 40, BAR_Y)
    P["nE"] = ik(P["nS"], P["nH"], UA, FA, v(1, 0.25)) + v(nz(5, 12, tremble * 3.5), 0)
    if lache:
        sw = 0.22 * math.sin(t * 7 + graine)
        P["fE"] = P["fS"] + rotv(v(-12, UA - 2), sw)
        P["fH"] = P["fE"] + rotv(v(-5, FA - 1), sw * 1.5)
    else:
        P["fH"] = v(cx - 40, BAR_Y)
        P["fE"] = ik(P["fS"], P["fH"], UA, FA, v(-1, 0.25)) + v(nz(6, 12, tremble * 3.5), 0)
    hip = N + rotv(v(0, 112), balancier)
    P["hip"] = hip
    k = kick

    def r(x, y):
        return rotv(v(x, y), balancier)
    P["nK"] = hip + r(9 + 26 * k, 58 - 30 * k)
    P["nF"] = P["nK"] + r(3 + 16 * k, 56 - 8 * k)
    P["fK"] = hip + r(-9 - 26 * k, 56 - 30 * k)
    P["fF"] = P["fK"] + r(22 - 40 * k, 50 - 6 * k)
    if desordre:
        for c, g, a in (("nK", 7, 9), ("fK", 8, 9), ("nF", 9, 18), ("fF", 10, 18)):
            P[c] = P[c] + v(desordre * a * bruit(t, graine + g, 1.7),
                            desordre * a * 0.6 * bruit(t, graine + g + 20, 2.1))
    return echelle(P, v(cx, BAR_Y))


def pose_accroupi(cx):
    F = SOL
    hip = v(cx - 10, F - 82)
    N = hip + v(18, -104)
    return echelle({"far": 0.55, "hip": hip, "N": N, "tete": N + v(12, -36),
                    "nK": v(cx + 26, F - 54), "nF": v(cx + 12, F - 3),
                    "fK": v(cx + 16, F - 50), "fF": v(cx - 8, F - 3),
                    "nE": N + v(42, 14), "nH": N + v(80, 4), "fE": N + v(-34, 14),
                    "fH": N + v(-64, 30)}, v(cx, F))


def pose_assis(cx, t, t_sol):
    """Motivation : assis au sol de profil, genoux relevés, tête qui pend, souffle lourd."""
    F = SOL
    L = t - t_sol
    amp = lerp(5.0, 2.2, smooth(0, 6, L))
    b = amp * math.sin(2 * math.pi * L / 2.4)
    hip = v(cx - 32, F - 16)
    N = hip + v(36, -100 + b)
    baisse = smooth(0, 3, L)
    nK, fK = v(cx + 18, F - 74), v(cx + 8, F - 70)
    nE = nK + v(-2, -8 + b * 0.4)
    fE = fK + v(-5, -5 + b * 0.4)
    return echelle({"far": 0.52, "hip": hip, "N": N,
                    "tete": N + v(lerp(16, 26, baisse), lerp(-30, -12, baisse) + b * 0.3),
                    "nK": nK, "nF": v(cx + 46, F - 3), "fK": fK, "fF": v(cx + 36, F - 3),
                    "nE": nE, "nH": nE + v(26, 38), "fE": fE, "fH": fE + v(22, 40)}, v(cx, F))


def pose_debout_bras(cx, a, t, b=-0.55, secoue=0.0):
    """Ego : face caméra, bras écartés (a = angle sous l'horizontale)."""
    F = SOL
    N = v(cx, F - 234)
    P = {"far": 0.88, "N": N, "hip": v(cx, F - 122),
         "tete": N + v(secoue * 7 * math.sin(t * 13), -37),
         "nK": v(cx + 21, F - 62), "nF": v(cx + 31, F - 3),
         "fK": v(cx - 21, F - 62), "fF": v(cx - 31, F - 3)}
    for s, e, hd in ((1, "nE", "nH"), (-1, "fE", "fH")):
        P[e] = N + v(s * math.cos(a), math.sin(a)) * UA
        P[hd] = P[e] + v(s * math.cos(a + b), math.sin(a + b)) * FA
    return echelle(P, v(cx, F))


def chute(P0, t_lache, t):
    pied = max(P0["nF"][1], P0["fF"][1])
    t_sol = t_lache + math.sqrt(2 * ((SOL - 3) - pied) / G)
    tau = min(t, t_sol) - t_lache
    u = clamp(tau / (t_sol - t_lache))
    P = translate(P0, v(0, 0.5 * G * tau * tau))
    for c, d in (("nH", v(10, -30)), ("nE", v(6, -14)), ("fH", v(-8, -40)), ("fE", v(-4, -18)),
                 ("nF", v(22, -10)), ("fF", v(-16, -4))):
        P[c] = P[c] + d * u * K
    return P, t_sol


def atterrissage(P_sol, cible, cx, t, t_sol, d1=0.15, d2=0.7):
    L = t - t_sol
    acc = pose_accroupi(cx)
    if L < d1:
        return mix(P_sol, acc, EASES["out"](L / d1))
    return mix(acc, cible, EASES["io"](clamp((L - d1) / d2)))


# ================================================================= personnages
def h_sync(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)          # une traction toutes les 2 s


CLES_M = [(6.00, 0.00, "io"), (7.20, 0.80, "io"), (8.10, 0.10, "io"),
          (9.00, 0.42, "io"), (9.20, 0.33, "io"), (9.45, 0.12, "io"), (9.60, 0.02, "in")]

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


def _halo(P, t, t_sol):
    pts = np.array([P[c] for c in CLES])
    lo, hi = pts.min(0), pts.max(0)
    L = t - t_sol
    I = smooth(0, 0.35, L) * (0.6 + 0.14 * math.sin(2 * math.pi * L / 1.9)) + 0.6 * math.exp(-L * 3.5)
    return {"centre": (lo + hi) / 2, "rx": min((hi[0] - lo[0]) / 2 + 44, CW / 2 - 18),
            "ry": (hi[1] - lo[1]) / 2 + 46, "I": I}


def etat_motivation(t):
    cx = CXS[0]
    info = {"mains": [], "halo": None, "couleur": BLANC, "sol": None}
    if t < M_LACHE:
        h = h_sync(t) if t < 6 else keyframes(CLES_M, t)
        tr = smooth(6.6, 9.6, t)
        lache = t >= M_LACHE_1
        P = pose_suspendu(cx, h, t, tremble=tr, kick=0.1 * h, lache=lache, graine=3)
        I = (0.8 + 0.15 * h) if t < 6 else 0.85 + 0.75 * smooth(6.3, 9.5, t)
        I *= 1 + 0.12 * tr * math.sin(t * 40)
        info["mains"] = [(p, I) for p in [P["nS"], P["fS"], P["nH"]] + ([] if lache else [P["fH"]])]
        return P, info
    P0 = pose_suspendu(cx, keyframes(CLES_M, M_LACHE), M_LACHE, tremble=1.0, lache=True, graine=3)
    Pc, t_sol = chute(P0, M_LACHE, t)
    info["sol"] = t_sol
    if t < t_sol:
        return Pc, info
    P = atterrissage(Pc, pose_assis(cx, t, t_sol), cx, t, t_sol, 0.15, 0.75)
    info["halo"] = _halo(P, t, t_sol)
    info["couleur"] = BLANC + (ROUGE_TERNE - BLANC) * smooth(t_sol, t_sol + 1.2, t)
    return P, info


def etat_discipline(t):
    h = h_sync(t)
    P = pose_suspendu(CXS[1], h, t, kick=0.18 * h, graine=7)
    I = 0.8 + 0.15 * h
    return P, {"mains": [(P[c], I) for c in ("nS", "fS", "nH", "fH")], "halo": None,
               "couleur": BLANC, "sol": None}


def balancier_ego(t):
    if t < 6:
        return 0.0
    if t < 10:
        kip = 0.22 * math.sin(2 * math.pi * (t - 7.1) / 0.9) * smooth(7.1, 7.25, t) * (1 - smooth(7.7, 7.9, t))
        return kip + 0.05 * math.sin(2 * math.pi * t / 1.3)
    a = lerp(0.06, 0.24, smooth(10, 18, t))
    return a * (math.sin(2 * math.pi * t / 1.4) + 0.6 * math.sin(2 * math.pi * t / 0.63 + 1))


def etat_ego(t):
    cx = CXS[2]
    info = {"mains": [], "halo": None, "couleur": BLANC, "sol": None}
    chauffe = smooth(10, 19, t)
    if t < E_LACHE:
        h = h_sync(t) if t < 6 else keyframes(CLES_E, t)
        flair = 0.0
        for a, b in ((6.2, 6.95), (7.8, 8.45), (8.9, 9.35), (9.9, 10.3)):
            flair = max(flair, smooth(a, a + 0.12, t) * (1 - smooth(b - 0.12, b, t)))
        desordre = smooth(9.8, 12.5, t) * (0.6 + 0.6 * smooth(12.5, 18.5, t))
        lache = t >= E_LACHE_1
        P = pose_suspendu(cx, h, t, balancier=balancier_ego(t), kick=max(flair, 0.1 * h),
                          lache=lache, graine=11, desordre=desordre,
                          tremble=smooth(14, 19, t) * 0.6)
        I = (0.8 + 0.15 * h) if t < 6 else 0.85 + 0.55 * chauffe
        info["mains"] = [(p, I) for p in [P["nS"], P["fS"], P["nH"]] + ([] if lache else [P["fH"]])]
        info["couleur"] = BLANC + (SAUMON - BLANC) * chauffe
        return P, info
    P0 = etat_ego(E_LACHE - 1e-6)[0]
    Pc, t_sol = chute(P0, E_LACHE, t)
    info["sol"] = t_sol
    info["couleur"] = SAUMON
    if t < t_sol:
        return Pc, info
    a = 0.55
    for tp in (20.7, 22.3, 23.9):
        u = t - tp
        if 0 <= u < 1.0:
            a -= 0.6 * (EASES["out"](u / 0.2) if u < 0.2 else 1 - EASES["io"]((u - 0.2) / 0.8))
    secoue = 0.0
    if t >= 25:
        a += 0.07 * math.sin(2 * math.pi * (t - 25) / 1.7)
    else:
        secoue = smooth(20.0, 20.4, t) * (1 - smooth(24.3, 24.8, t)) * 0.5
    P = atterrissage(Pc, pose_debout_bras(cx, a, t, secoue=secoue), cx, t, t_sol, 0.15, 0.6)
    info["halo"] = _halo(P, t, t_sol)
    return P, info


ETATS = (etat_motivation, etat_discipline, etat_ego)
T_SOL_M = etat_motivation(12.0)[1]["sol"]
T_SOL_E = etat_ego(22.0)[1]["sol"]
IMPACTS = [T_SOL_M, T_SOL_E]


# ================================================================= éléments statiques (par process)
_cache = {}


def police(chemin, taille):
    cle = (chemin, int(taille))
    if cle not in _cache:
        _cache[cle] = ImageFont.truetype(chemin, int(taille))
    return _cache[cle]


def statique():
    if "bg" in _cache:
        return _cache
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.32) / H) ** 2)
    base = 0.075 * np.clip(1 - d * 1.5, 0, 1) ** 1.6 + 0.012
    bg = np.stack([base * 0.97, base * 0.98, base * 1.06], -1).astype(np.float32)
    ray = np.zeros_like(base)
    for x0, wdt, a in ((140, 50, 0.018), (420, 30, 0.012), (780, 70, 0.016), (980, 40, 0.01)):
        ray += a * np.exp(-((xx - x0 - (yy * 0.32)) / wdt) ** 2)
    bg += (ray * (yy < H * 0.75))[..., None]
    _cache["bg"] = bg
    vig = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    _cache["vig"] = np.clip(1.15 - vig ** 2.2 * 0.75, 0.25, 1).astype(np.float32)
    _cache["bord"] = np.clip(vig - 0.55, 0, 1).astype(np.float32)
    rng = np.random.default_rng(7)
    _cache["grain"] = [rng.standard_normal((H // 2, W // 2)).astype(np.float32) for _ in range(6)]
    n = 170
    _cache["dust"] = np.stack([rng.uniform(0, W, n), rng.uniform(0, H, n), rng.uniform(6, 28, n),
                               rng.uniform(0.6, 2.4, n), rng.uniform(0, 6.28, n),
                               rng.uniform(0.3, 1, n)], 1)
    _cache["bokeh"] = np.stack([rng.uniform(0, W, 16), rng.uniform(150, H - 150, 16),
                                rng.uniform(18, 60, 16), rng.uniform(0.02, 0.06, 16),
                                rng.uniform(0, 6.28, 16)], 1)
    _cache["note"] = masque_note(200)
    return _cache


# ================================================================= lumière
def intensites_spots(t):
    def fl(g):
        return 1 + 0.035 * math.sin(t * 7.3 + g) + 0.02 * math.sin(t * 17.1 + g * 2)
    m = 0.75 * fl(1)
    if 8.2 < t < M_LACHE + 0.4:
        m *= 0.75 + 0.25 * (math.sin(t * 43) > -0.2)
    m = lerp(m, 0.18, smooth(M_LACHE + 0.2, M_LACHE + 0.8, t))
    e = 0.75 * fl(2)
    if 14.5 < t < E_LACHE + 0.4:
        e *= 0.7 + 0.3 * (math.sin(t * 37 + 1) > -0.1 * (t - 14))
    e = lerp(e, 0.2, smooth(E_LACHE + 0.2, E_LACHE + 0.8, t))
    d = 0.75 * fl(3) + 0.4 * smooth(24, 28, t)
    rouge = [smooth(M_LACHE + 0.2, M_LACHE + 0.8, t), 0.0, smooth(E_LACHE + 0.2, E_LACHE + 0.8, t)]
    return [m, d, e], rouge


def couche_spots(t):
    q = 4
    I, rouge = intensites_spots(t)
    out = np.zeros((H // q, W // q, 3), np.float32)
    masques = []
    yy = np.linspace(-0.1, 1.0, H // q, dtype=np.float32)[:, None]
    for cx, s, r in zip(CXS, I, rouge):
        m = Image.new("L", (W // q, H // q), 0)
        d = ImageDraw.Draw(m)
        top, bas = -120, SOL + 10
        d.polygon([((cx - 26) / q, top / q), ((cx + 26) / q, top / q),
                   ((cx + 150) / q, bas / q), ((cx - 150) / q, bas / q)], fill=110)
        d.polygon([((cx - 8) / q, top / q), ((cx + 8) / q, top / q),
                   ((cx + 70) / q, bas / q), ((cx - 70) / q, bas / q)], fill=200)
        d.ellipse([(cx - 135) / q, (SOL - 22) / q, (cx + 135) / q, (SOL + 22) / q], fill=255)
        m = np.asarray(m.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
        m = m * np.clip(0.25 + yy * 0.9, 0, 1)
        col = lerp(np.array([0.85, 0.87, 0.92], np.float32), np.array([0.9, 0.12, 0.12], np.float32), r)
        out += m[..., None] * (0.26 * s) * col
        masques.append(m * s)
    up = np.asarray(Image.fromarray(np.clip(out * 255 * 2, 0, 255).astype(np.uint8))
                    .resize((W, H), Image.BILINEAR), np.float32) / 255 / 2
    return up, masques


def couche_atmosphere(t, masques, st):
    q = 4
    lum = np.maximum.reduce(masques)
    dust = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(dust)
    for x0, y0, vit, taille, ph, a in st["dust"]:
        y = (y0 - vit * t) % H
        x = x0 + 10 * math.sin(t * 0.6 + ph)
        li = lum[int(clamp(y / q, 0, H / q - 1)), int(clamp(x / q, 0, W / q - 1))]
        g = int(255 * clamp(a * (0.12 + 1.3 * li)) * (0.7 + 0.3 * math.sin(t * 2 + ph)))
        d.ellipse([x - taille, y - taille, x + taille, y + taille], fill=g)
    dust = dust.filter(ImageFilter.GaussianBlur(0.8))
    bok = Image.new("L", (W // q, H // q), 0)
    db = ImageDraw.Draw(bok)
    for x0, y0, r, a, ph in st["bokeh"]:
        x = x0 + 25 * math.sin(t * 0.15 + ph)
        y = y0 + 18 * math.cos(t * 0.11 + ph)
        db.ellipse([(x - r) / q, (y - r) / q, (x + r) / q, (y + r) / q], fill=int(a * 255 * 3))
    bok = bok.filter(ImageFilter.GaussianBlur(2.2)).resize((W, H), Image.BILINEAR)
    return np.asarray(dust, np.float32) / 255 * 0.55 + np.asarray(bok, np.float32) / 255 / 3


# ================================================================= décor (cadres, barres, titres)
def decor(t):
    deco = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(deco)
    for x0 in COLS:
        d.rectangle([x0 * SS, YT * SS, (x0 + CW) * SS, YB * SS], outline=95, width=3 * SS)
        c = 26
        for xa, ya, sx, sy in ((x0, YT, 1, 1), (x0 + CW, YT, -1, 1), (x0, YB, 1, -1), (x0 + CW, YB, -1, -1)):
            d.line([(xa * SS, ya * SS), ((xa + sx * c) * SS, ya * SS)], fill=200, width=3 * SS)
            d.line([(xa * SS, ya * SS), (xa * SS, (ya + sy * c) * SS)], fill=200, width=3 * SS)
        d.line([((x0 + 3) * SS, (BAR_Y + 4) * SS), ((x0 + CW - 3) * SS, (BAR_Y + 4) * SS)], fill=70, width=5 * SS)
        d.line([((x0 + 3) * SS, BAR_Y * SS), ((x0 + CW - 3) * SS, BAR_Y * SS)], fill=225, width=7 * SS)
        d.line([((x0 + 3) * SS, (BAR_Y - 2) * SS), ((x0 + CW - 3) * SS, (BAR_Y - 2) * SS)], fill=255, width=2 * SS)
        d.line([((x0 + 3) * SS, SOL * SS), ((x0 + CW - 3) * SS, SOL * SS)], fill=120, width=2 * SS)
    deco = np.asarray(deco.resize((W, H), Image.LANCZOS), np.float32) / 255

    f = police(MONO, 30 * SS)
    titres = []
    for i, titre in enumerate(TITRES):
        im = Image.new("L", ((CW + 40) * SS, 70 * SS), 0)
        dt = ImageDraw.Draw(im)
        n = int(clamp((t - 0.15 - 0.12 * i) / 0.75) * len(titre))
        esp = 5 * SS
        larg = [dt.textlength(ch, font=f) for ch in titre]
        total = sum(larg) + esp * (len(titre) - 1)
        x = (CW + 40) * SS / 2 - total / 2
        for ch, l in zip(titre[:n], larg):
            dt.text((x, 18 * SS), ch, font=f, fill=255)
            x += l + esp
        if n < len(titre) or (t < 2.2 and int(t * 3) % 2 == 0):
            dt.rectangle([x, 20 * SS, x + 16 * SS, 52 * SS], fill=255)
        titres.append(np.asarray(im.resize((CW + 40, 70), Image.LANCZOS), np.float32) / 255)
    return deco, titres


def couleur_titre(i, t):
    lache = {0: M_LACHE, 2: E_LACHE}.get(i)
    if lache is None or t < lache:
        return BLANC, 0
    if t - lache < 0.5:
        glitch = int(t * 30) % 2
        return (ROUGE_COEUR if glitch else BLANC), (8 if glitch else -5)
    return np.array([1.0, 0.32, 0.30], np.float32), 0


# ================================================================= personnages : dessin
BOX_PAD_X, BOX_Y0, BOX_Y1 = 70, YT - 60, YB + 30


def _seg(d, a, b, w, ox, oy):
    a = ((a[0] - ox) * SS, (a[1] - oy) * SS)
    b = ((b[0] - ox) * SS, (b[1] - oy) * SS)
    d.line([a, b], fill=255, width=int(w * SS))
    r = w * SS / 2
    for p in (a, b):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=255)


def dessiner(P, ox, oy, near, far):
    dn, df = ImageDraw.Draw(near), ImageDraw.Draw(far)
    for a, b in (("fS", "fE"), ("fE", "fH"), ("hip", "fK"), ("fK", "fF")):
        _seg(df, P[a], P[b], LW_F, ox, oy)
    for a, b in (("N", "hip"), ("hip", "nK"), ("nK", "nF"), ("fS", "nS"), ("nS", "nE"), ("nE", "nH")):
        _seg(dn, P[a], P[b], LW_N, ox, oy)
    tete, N = P["tete"], P["N"]
    _seg(dn, N, lerp(N, tete, 0.6), LW_N * 0.85, ox, oy)
    c = ((tete[0] - ox) * SS, (tete[1] - oy) * SS)
    r = R_TETE * SS
    dn.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=255)


def couche_personnage(i, t):
    """(rgb, alpha, x0, y0, pose, info) pour la colonne i, avec flou de mouvement."""
    etat = ETATS[i]
    ox, oy = COLS[i] - BOX_PAD_X, BOX_Y0
    bw, bh = CW + 2 * BOX_PAD_X, BOX_Y1 - BOX_Y0
    P, info = etat(t)
    P_av, _ = etat(max(t - 1 / FPS, 0))
    vit = max(np.linalg.norm(P[c] - P_av[c]) for c in CLES)
    nsub = 1 if vit < 5 else (3 if vit < 18 else 5)
    acc_n = np.zeros((bh, bw), np.float32)
    acc_f = np.zeros((bh, bw), np.float32)
    filt = Image.BILINEAR if nsub > 1 else Image.LANCZOS
    for j in range(nsub):
        Pj = P if j == 0 else etat(t - (j / (nsub - 1)) * 0.55 / FPS)[0]
        near = Image.new("L", (bw * SS, bh * SS), 0)
        far = Image.new("L", (bw * SS, bh * SS), 0)
        dessiner(Pj, ox, oy, near, far)
        acc_n += np.asarray(near.resize((bw, bh), filt), np.float32)
        acc_f += np.asarray(far.resize((bw, bh), filt), np.float32)
    an, af = acc_n / (255 * nsub), acc_f / (255 * nsub)
    col = info["couleur"]
    rgb = an[..., None] * col + (af * (1 - an))[..., None] * col * P["far"]
    alpha = np.clip(an + af * (1 - an), 0, 1)
    return rgb, alpha, ox, oy, P, info


# ================================================================= rendu d'une image de scène
def rendre_scene(t):
    st = statique()
    img = st["bg"].copy()
    spots, masques = couche_spots(t)
    img += spots
    img += couche_atmosphere(t, masques, st)[..., None] * np.array([0.85, 0.87, 0.92], np.float32)

    deco, titres = decor(t)
    img = img * (1 - deco[..., None]) + deco[..., None] * np.array([0.92, 0.92, 0.9], np.float32)
    for i, m in enumerate(titres):
        col, dx = couleur_titre(i, t)
        x0, y0 = COLS[i] - 20 + dx, YT - 78
        sl = img[y0:y0 + 70, x0:x0 + CW + 40]
        sl[:] = sl * (1 - m[..., None]) + m[..., None] * col

    serre = Image.new("L", (W // 2, H // 2), 0)
    large = Image.new("L", (W // 2, H // 2), 0)
    anneau = Image.new("L", (W, H), 0)
    ds, dl, da = ImageDraw.Draw(serre), ImageDraw.Draw(large), ImageDraw.Draw(anneau)
    coeurs, persos = [], []
    for i in range(3):
        rgb, alpha, ox, oy, P, info = couche_personnage(i, t)
        persos.append((rgb, alpha, ox, oy))
        hl = info["halo"]
        if hl:
            c, rx, ry = hl["centre"] / 2, hl["rx"] / 2, hl["ry"] / 2
            hm = Image.new("L", (W // 2, H // 2), 0)
            ImageDraw.Draw(hm).ellipse([c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry],
                                       fill=int(clamp(hl["I"] * 0.5) * 170))
            boite = (COLS[i] // 2, YT // 2, (COLS[i] + CW) // 2, SOL // 2)
            large.paste(Image.fromarray(np.maximum(np.asarray(large.crop(boite)),
                                                   np.asarray(hm.crop(boite)))), boite[:2])
        if info["sol"] is not None and 0 <= t - info["sol"] < 0.6:
            u = (t - info["sol"]) / 0.6
            cx, cy = CXS[i], SOL - 80
            for k, (r0, r1) in enumerate(((20, 150), (10, 95))):
                rr = lerp(r0, r1, EASES["out"](clamp(u * (1.0 + 0.4 * k))))
                g = int(255 * (1 - u) ** 1.4 * (0.8 - 0.3 * k))
                da.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=g, width=3)
        for p, I in info["mains"]:
            r = 8 * K * (0.85 + 0.25 * clamp(I - 0.8, 0, 1))
            coeurs.append((p, r, I))
            q = p / 2
            ds.ellipse([q[0] - r * 0.9, q[1] - r * 0.9, q[0] + r * 0.9, q[1] + r * 0.9],
                       fill=int(clamp(I / 1.6) * 170))
            rl = r * (1.7 + 1.0 * clamp(I - 0.8, 0, 1))
            dl.ellipse([q[0] - rl, q[1] - rl, q[0] + rl, q[1] + rl], fill=int(clamp(I / 1.6) * 120))

    Gl = np.asarray(large.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR), np.float32) / 170
    img += Gl[..., None] * ROUGE_GLOW * 1.2

    for rgb, alpha, ox, oy in persos:
        h_, w_ = alpha.shape
        x0, y0 = max(ox, 0), max(oy, 0)
        x1, y1 = min(ox + w_, W), min(oy + h_, H)
        a = alpha[y0 - oy:y1 - oy, x0 - ox:x1 - ox, None]
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + rgb[y0 - oy:y1 - oy, x0 - ox:x1 - ox]

    if coeurs:
        cm = Image.new("L", (W * SS, H * SS), 0)
        dc = ImageDraw.Draw(cm)
        for p, r, I in coeurs:
            c = p * SS
            dc.ellipse([c[0] - r * SS, c[1] - r * SS, c[0] + r * SS, c[1] + r * SS],
                       fill=int(clamp(0.55 + 0.45 * I) * 255))
        C = np.asarray(cm.resize((W, H), Image.LANCZOS), np.float32)[..., None] / 255
        img = img * (1 - C) + C * ROUGE_COEUR
    Gs = np.asarray(serre.filter(ImageFilter.GaussianBlur(4)).resize((W, H), Image.BILINEAR), np.float32) / 170
    img += Gs[..., None] * ROUGE_GLOW * 1.3 + np.clip(Gs - 0.8, 0, 1)[..., None] * 0.25
    img += (np.asarray(anneau.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255)[..., None] * 0.9
    return img


# ================================================================= post-production
def secousse(t):
    sx = sy = ab = flash = 0.0
    for ti in IMPACTS:
        u = t - ti
        if 0 <= u < 0.6:
            e = math.exp(-u * 7)
            sx += 11 * e * math.sin(u * 63)
            sy += 9 * e * math.sin(u * 51 + 1)
            ab += 7 * math.exp(-u * 6)
            flash += 0.35 * math.exp(-u * 5)
    return sx, sy, ab, flash


def teinte_rouge(t):
    r = 0.0
    for ti in IMPACTS:
        if t >= ti:
            r += 0.55 * math.exp(-(t - ti) * 1.6)
    r += 0.18 * smooth(T_SOL_M, T_SOL_M + 1, t) * (1 - 0.5 * smooth(24, 28, t))
    r += 0.22 * smooth(12, 19, t) * (1 - 0.6 * smooth(24, 28, t))
    return r


def post(img, t, i_frame):
    st = statique()
    sx, sy, ab, flash = secousse(t)
    r = teinte_rouge(t) + flash
    img = img + (st["bord"] * r)[..., None] * np.array([0.55, 0.03, 0.04], np.float32)
    u8 = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    b = np.asarray(u8.resize((W // 4, H // 4), Image.BOX), np.float32) / 255
    b = np.clip((b - 0.45) * 1.8, 0, 1)
    b = Image.fromarray((b * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))
    img = img + np.asarray(b.resize((W, H), Image.BILINEAR), np.float32) / 255 * 0.35
    img = img * st["vig"][..., None]
    g = st["grain"][i_frame % len(st["grain"])]
    img = img + np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None] * 0.018
    out = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    z = 1.0 + 0.055 * smooth(0, 31, t)                      # lent travelling avant
    cx, cy = W / 2, 1000
    out = out.transform((W, H), Image.AFFINE,
                        (1 / z, 0, cx - cx / z - sx, 0, 1 / z, cy - cy / z - sy), Image.BICUBIC)
    a = np.asarray(out).copy()
    k = int(round(ab))
    if k:
        a[..., 0] = np.roll(a[..., 0], k, 1)
        a[..., 2] = np.roll(a[..., 2], -k, 1)
    return a


# ================================================================= carte de fin
def masque_note(taille):
    u = taille / 200.0 * SS
    m = Image.new("L", (int(260 * u), int(280 * u)), 0)
    d = ImageDraw.Draw(m)
    ox, oy = 130 * u, 140 * u

    def box(cx, cy, r):
        return [ox + (cx - r) * u, oy + (cy - r) * u, ox + (cx + r) * u, oy + (cy + r) * u]
    d.pieslice(box(20, -28, 72), 270, 360, fill=255)
    d.pieslice(box(20, -28, 44), 270, 360, fill=0)
    d.ellipse(box(-10, 46, 58), fill=255)
    d.ellipse(box(-10, 46, 28), fill=0)
    d.rectangle([ox + 20 * u, oy - 75 * u, ox + 48 * u, oy + 46 * u], fill=255)
    return m


def coller(toile, m, x, y, col):
    toile.paste(Image.new("RGB", m.size, col), (int(x - m.size[0] / 2), int(y - m.size[1] / 2)), m)


T_CARTE = T_FIN + 0.35


def rendre_fin(t, i_frame):
    L = t - T_CARTE
    st = statique()
    navy = tuple(int(c * 255) for c in NAVY)
    toile = Image.new("RGB", (W * SS, H * SS), navy)
    rng = np.random.default_rng(i_frame)
    # ---- logo (glitch à l'apparition)
    gl = math.exp(-L * 5)
    ech = EASES["back"](clamp(L / 0.4)) if L < 0.4 else 1.0
    m = st["note"] if ech == 1.0 else masque_note(200 * max(ech, 0.05))
    cx, cy = W / 2 * SS, 740 * SS

    def jit():
        return rng.uniform(-1, 1) * 22 * gl * SS
    d0 = 5 * SS
    coller(toile, m, cx - d0 + jit(), cy - d0 * 0.7 + jit() * 0.3, CYAN)
    coller(toile, m, cx + d0 + jit(), cy + d0 * 0.7 + jit() * 0.3, ROSE)
    coller(toile, m, cx + jit() * 0.4, cy, (255, 255, 255))
    d = ImageDraw.Draw(toile)
    fw = police(INTER_XB, 82 * SS)
    for col, dx in ((CYAN, -3), (ROSE, 3), ((255, 255, 255), 0)):
        d.text((W / 2 * SS + dx * SS * (1 + 3 * gl), 900 * SS), "TikTok", font=fw, fill=col, anchor="mm")
    # ---- barre de recherche : blocs rose / cyan qui glissent puis se figent
    Lb = L - 0.3
    if Lb >= 0:
        bw, bh = 600, 92
        x0, y0 = (W - bw) / 2, 1040
        u = EASES["out"](clamp(Lb / 0.45))
        dxr, dxc, ep = lerp(-90, -8, u), lerp(90, 8, u), lerp(26, 6, u)
        rr = 14 * SS
        d.rounded_rectangle([(x0 + dxr) * SS, (y0 - ep) * SS, (x0 + bw + dxr) * SS, (y0 + bh - 6) * SS],
                            radius=rr, fill=ROSE)
        d.rounded_rectangle([(x0 + dxc) * SS, (y0 + 6) * SS, (x0 + bw + dxc) * SS, (y0 + bh + ep) * SS],
                            radius=rr, fill=CYAN)
        d.rounded_rectangle([x0 * SS, y0 * SS, (x0 + bw) * SS, (y0 + bh) * SS], radius=rr, fill=(255, 255, 255))
        d.rounded_rectangle([(x0 + 11) * SS, (y0 + 11) * SS, (x0 + bw - 11) * SS, (y0 + bh - 11) * SS],
                            radius=10 * SS, fill=navy)
        if Lb > 0.35:
            a = clamp((Lb - 0.35) / 0.2)
            blanc = tuple(int(255 * a + navy[k] * (1 - a)) for k in range(3))
            lx, ly, lr = (x0 + 52) * SS, (y0 + bh / 2 - 3) * SS, 14 * SS
            d.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], outline=blanc, width=5 * SS)
            d.line([(lx + 10 * SS, ly + 10 * SS), (lx + 21 * SS, ly + 21 * SS)], fill=blanc, width=6 * SS)
            mi = masque_note(34)
            nx, ny = (x0 + bw - 46) * SS, (y0 + bh / 2) * SS
            coller(toile, mi, nx - 2 * SS, ny - 1 * SS, CYAN)
            coller(toile, mi, nx + 2 * SS, ny + 1 * SS, ROSE)
            coller(toile, mi, nx, ny, blanc)
            ft = police(INTER_SB, 40 * SS)
            n = int(clamp((Lb - 0.55) / 0.85) * len(PSEUDO) + 1e-6)
            txt = PSEUDO[:n]
            tx = (x0 + 88) * SS
            d.text((tx, (y0 + bh / 2) * SS), txt, font=ft, fill=(255, 255, 255), anchor="lm")
            if n < len(PSEUDO) or int(Lb * 2.4) % 2 == 0:
                cxr = tx + d.textlength(txt, font=ft) + 5 * SS
                d.line([(cxr, (y0 + 26) * SS), (cxr, (y0 + bh - 26) * SS)], fill=ROSE, width=4 * SS)
    a = np.asarray(toile.resize((W, H), Image.LANCZOS)).copy()
    if L < 0.45:                                          # tranches glitch à l'apparition
        for _ in range(int(8 * (1 - L / 0.45))):
            y = rng.integers(0, H - 60)
            hh = rng.integers(6, 50)
            a[y:y + hh] = np.roll(a[y:y + hh], int(rng.integers(-80, 80)), 1)
    g = st["grain"][i_frame % len(st["grain"])]
    a = np.clip(a.astype(np.float32) + np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None] * 4, 0, 255)
    return a.astype(np.uint8)


def glitch_transition(a, t, i_frame):
    u = clamp((t - T_FIN) / (T_CARTE - T_FIN))
    rng = np.random.default_rng(1000 + i_frame)
    a = a.copy()
    k = int(4 + 30 * u)
    a[..., 0] = np.roll(a[..., 0], k, 1)
    a[..., 2] = np.roll(a[..., 2], -k, 1)
    for _ in range(int(6 + 20 * u)):
        y = rng.integers(0, H - 80)
        hh = rng.integers(4, 80)
        a[y:y + hh] = np.roll(a[y:y + hh], int(rng.integers(-160, 160) * (0.3 + u)), 1)
    f = 1 - u ** 1.5
    return (a.astype(np.float32) * f + NAVY * 255 * (1 - f)).astype(np.uint8)


# ================================================================= image finale
def image(t, i_frame=0):
    if t < T_CARTE:
        a = post(rendre_scene(min(t, T_FIN)), t, i_frame)
        return glitch_transition(a, t, i_frame) if t >= T_FIN else a
    return rendre_fin(t, i_frame)


def image_n(i):
    return image(i / FPS, i).tobytes()


# ================================================================= bande-son
SR = 44100


def bande_son(chemin):
    n = int(DUREE * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float64)
    rng = np.random.default_rng(3)

    def env(a, b, c, d):
        return np.clip((t - a) / max(b - a, 1e-3), 0, 1) * np.clip((d - t) / max(d - c, 1e-3), 0, 1)

    # nappe sombre (la mineur), légèrement désaccordée
    for f, g in ((55.0, 0.5), (110.0, 0.35), (130.81, 0.22), (164.81, 0.2), (220.0, 0.12)):
        for det, pan in ((-0.3, 0.3), (0.35, 0.7)):
            ph = 2 * np.pi * (f + det) * t
            s = 0.6 * np.sin(ph) + 0.12 * (2 * ((ph / (2 * np.pi)) % 1) - 1)
            out[:, 0] += s * g * (1 - pan)
            out[:, 1] += s * g * pan
    pad_env = env(0, 2.5, T_FIN - 0.4, T_FIN + 0.2) * (0.55 + 0.25 * np.sin(2 * np.pi * t / 8) ** 2)
    out *= (0.09 * pad_env)[:, None]

    def ajoute(sig, t0, g=1.0, pan=0.5):
        i0 = int(t0 * SR)
        if i0 >= n:
            return
        m = min(len(sig), n - i0)
        out[i0:i0 + m, 0] += sig[:m] * g * (1 - pan) * 2
        out[i0:i0 + m, 1] += sig[:m] * g * pan * 2

    def kick(dur=0.35, f0=110, f1=42):
        tt = np.arange(int(dur * SR)) / SR
        f = f1 + (f0 - f1) * np.exp(-tt * 22)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)

    # pulsation « cœur » au rythme des tractions de Discipline
    for k in range(16):
        tb = 2.0 * k + 0.05
        if tb < T_FIN:
            ajoute(kick(), tb, 0.32)
            ajoute(kick(0.25, 90, 40), tb + 0.28, 0.16)
    # tension : souffle qui monte avant chaque lâcher
    bruit_b = rng.standard_normal(n)
    for a, b in ((6.5, M_LACHE), (14.0, E_LACHE)):
        s = bruit_b * env(a, b, b, b + 0.08) ** 2
        s = s - np.convolve(s, np.ones(40) / 40, "same")
        out[:, 0] += s * 0.035
        out[:, 1] += s * 0.035
    # chutes : sifflement descendant + impact grave
    for tl, tsol in ((M_LACHE, T_SOL_M), (E_LACHE, T_SOL_E)):
        dur = tsol - tl
        tt = np.arange(int(dur * SR)) / SR
        f = 900 * np.exp(-tt * 3) + 200
        ajoute(np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15 * (tt / dur), tl, 0.4)
        tt = np.arange(int(1.4 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-tt * 10)) / SR) * np.exp(-tt * 3.2)
        crack = rng.standard_normal(len(tt)) * np.exp(-tt * 28)
        ajoute(boom * 0.9 + crack * 0.35, tsol, 0.55)
    # glitch de fin
    tt = np.arange(int(0.4 * SR)) / SR
    gl = np.sign(np.sin(2 * np.pi * 180 * tt)) * (rng.random(len(tt)) > 0.5) * np.exp(-tt * 3)
    ajoute(np.round(gl * 4) / 4 * 0.18, T_FIN, 0.6)
    # carte de fin : whoosh + frappe clavier
    tt = np.arange(int(0.5 * SR)) / SR
    wh = np.convolve(rng.standard_normal(len(tt)) * np.sin(np.pi * tt / 0.5) ** 2, np.ones(25) / 25, "same")
    ajoute(wh * 0.5, T_CARTE + 0.3, 0.5)
    t_type = T_CARTE + 0.3 + 0.55
    for k in range(len(PSEUDO)):
        tt = np.arange(int(0.03 * SR)) / SR
        ajoute(rng.standard_normal(len(tt)) * np.exp(-tt * 260) * 0.25,
               t_type + k * 0.85 / len(PSEUDO), 0.5, 0.45 + 0.1 * (k % 2))
    fin = env(T_FIN + 0.3, T_FIN + 1.0, DUREE - 0.8, DUREE)
    for f in (220.0, 329.63, 440.0):
        s = np.sin(2 * np.pi * f * t) * fin * 0.025
        out[:, 0] += s
        out[:, 1] += s
    out = np.tanh(out * 1.4) * 0.85
    out *= env(0, 0.05, DUREE - 0.3, DUREE)[:, None]
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


# ================================================================= sorties
def rendre_video():
    wav = os.path.join(ICI, "_bande_son.wav")
    print("Bande-son…", flush=True)
    bande_son(wav)
    n = int(round(DUREE * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-map", "0:v", "-map", "1:a", "-shortest",
           "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", SORTIE]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, data in enumerate(pool.imap(image_n, range(n), chunksize=2)):
            ff.stdin.write(data)
            if i % 60 == 0:
                print(f"  {i / FPS:5.1f} s / {DUREE:.0f} s", flush=True)
    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    print("Vidéo :", SORTIE)


def apercu(chemin):
    temps = [0.6, 1.0, 6.8, 8.6, 9.45, 9.8, 10.15, 13.0, 15.5,
             18.9, 19.6, 21.0, 26.0, 32.15, 32.6, 34.6]
    vw, vh = W // 4, H // 4
    planche = Image.new("RGB", (vw * 4, vh * 4), (40, 40, 40))
    d = ImageDraw.Draw(planche)
    for k, t in enumerate(temps):
        im = Image.fromarray(image(t, int(t * FPS))).resize((vw, vh), Image.LANCZOS)
        planche.paste(im, ((k % 4) * vw, (k // 4) * vh))
        d.text(((k % 4) * vw + 6, (k // 4) * vh + 4), f"{t:.2f}s", fill=(255, 255, 0))
    planche.save(chemin)
    print("Aperçu :", chemin)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apercu", nargs="?", const=os.path.join(ICI, "apercu.png"))
    ap.add_argument("--image", type=float)
    ap.add_argument("--son", help="écrit seulement la bande-son (wav)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.son:
        bande_son(a.son)
    elif a.image is not None:
        p = a.out or os.path.join(ICI, f"image_{a.image:05.2f}.png")
        Image.fromarray(image(a.image, int(a.image * FPS))).save(p)
        print(p)
    elif a.apercu:
        apercu(a.apercu)
    else:
        rendre_video()
