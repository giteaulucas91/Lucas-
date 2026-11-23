#!/usr/bin/env python3
"""
QUI TIENT JUSQU'AU BOUT ? — MOTIVATION / DISCIPLINE / EGO, version escalier
Animation stick-figure 9:16 (1080x1920, 30 i/s, 23,5 s).

Escalier en diagonale dans le noir, projecteurs volumétriques, personnages étiquetés qui
montent, boules-obstacles étiquetées en rouge qui dévalent les marches, caméra qui suit
(zoom d'ouverture puis plan large), flou de mouvement, secousses, glitchs, texte monospace
tapé à la machine, carte de fin TikTok + recherche @teamlouise82. Bande-son synthétisée.

Histoire : MOTIVATION part en flèche, EGO frime, DISCIPLINE avance à pas réguliers dans
l'ombre. MOTIVATION s'essouffle, s'arrête et s'évapore face à FATIGUE. EGO vire au rouge,
se met à courir et ÉCHEC l'envoie dans le vide. DOUTE met DISCIPLINE à genoux : il se
relève seul et continue. « LA MOTIVATION S'ÉVAPORE. L'EGO TOMBE. LA DISCIPLINE CONTINUE. »

Usage :
    python3 generer_histoire.py                 # vidéo complète (+ son)
    python3 generer_histoire.py --apercu        # planche de vignettes clés
    python3 generer_histoire.py --image 10.4    # une image
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
DUREE = 23.5
SS = 2
ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "QUI_TIENT_JUSQU_AU_BOUT.mp4")
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
INTER_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
PSEUDO = "@teamlouise82"

TITRE = ["QUI TIENT", "JUSQU'AU BOUT ?"]
REPONSE = ["LA MOTIVATION S'ÉVAPORE.", "L'EGO TOMBE.", "LA DISCIPLINE CONTINUE."]

# escalier (unités monde ; y vers le bas comme l'écran)
SW, SH = 30.0, 19.0
STRIDE = 4 * SW
UA, FA, TH, SHL = 54.0, 52.0, 60.0, 58.0
R_TETE = 25.0
LW_N, LW_F = 15.0, 13.5

T_FIN = 19.8
T_CARTE = T_FIN + 0.35

BLANC = np.array([0.95, 0.95, 0.93], np.float32)
SAUMON = np.array([1.0, 0.50, 0.46], np.float32)
GRIS = np.array([0.55, 0.56, 0.58], np.float32)
ROUGE_TXT = np.array([1.0, 0.30, 0.28], np.float32)
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


def v(x, y):
    return np.array([x, y], dtype=np.float64)


def rotv(d, a):
    c, s = math.cos(a), math.sin(a)
    return v(d[0] * c - d[1] * s, d[0] * s + d[1] * c)


def ik(a, b, L1, L2, pref):
    d = b - a
    n = max(np.linalg.norm(d), 1e-3)
    dist = clamp(n, abs(L1 - L2) + 0.01, L1 + L2 - 0.01)
    u = d / n
    x = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(L1 * L1 - x * x, 0))
    p = v(-u[1], u[0])
    c1, c2 = a + u * x + p * h, a + u * x - p * h
    return c1 if np.dot(c1 - c2, pref) > 0 else c2


def ys(x):
    """Dessus de la marche qui contient x."""
    return -math.floor(x / SW) * SH


def yl(x):
    """Ligne moyenne de l'escalier."""
    return -x * SH / SW


CLES = ["tete", "N", "hip", "nE", "nH", "fE", "fH", "nK", "nF", "fK", "fF"]


def mix(P, Q, u):
    R = {c: lerp(P[c], Q[c], u) for c in CLES}
    R["far"] = lerp(P["far"], Q["far"], u)
    return R


def tourner(P, centre_x, s):
    """Demi-tour : met à l'échelle les x autour de centre_x (s : 1 → -1)."""
    R = {c: v(centre_x + (P[c][0] - centre_x) * s, P[c][1]) for c in CLES}
    R["far"] = P["far"]
    return R


def pivoter(P, centre, a):
    R = {c: centre + rotv(P[c] - centre, a) for c in CLES}
    R["far"] = P["far"]
    return R


def decaler(P, d):
    R = {c: P[c] + d for c in CLES}
    R["far"] = P["far"]
    return R


# ================================================================= poses
def pose_marche(xb, d=1, ph=0.0, bras=1.0, pench=0.0):
    """Montée (d=1, vers la droite) ou descente (d=-1) de l'escalier, cycle de marche."""
    q = xb * d
    P = {"far": 0.55}
    pn = (q / STRIDE + ph) % 1.0
    for cle, p in (("n", pn), ("f", (pn + 0.5) % 1.0)):
        if p < 0.5:
            rel = STRIDE * (0.25 - p)
            x = xb + d * rel
            y = ys(x)
        else:
            u = (p - 0.5) / 0.5
            e = EASES["io"](u)
            rel = STRIDE * (-0.25 + 0.5 * e)
            x = xb + d * rel
            qs = q - (p - 0.5) * STRIDE
            qe = q + (1 - p) * STRIDE
            xs_, xe_ = d * (qs - 0.25 * STRIDE), d * (qe + 0.25 * STRIDE)
            y = lerp(ys(xs_), ys(xe_), e) - 24 * math.sin(math.pi * u)
        P[cle + "F"] = v(x, y)
    hip = v(xb - d * 4, yl(xb) - 98 + 3 * math.cos(4 * math.pi * pn))
    P["hip"] = hip
    for cle in ("n", "f"):
        P[cle + "K"] = ik(hip, P[cle + "F"], TH, SHL, v(d, -0.15))
    N = hip + v(d * (12 + 22 * pench), -110)
    P["N"] = N
    P["tete"] = N + v(d * (8 + 10 * pench), -37)
    a = bras * 0.55 * math.sin(2 * math.pi * pn)
    for cle, ang in (("n", a), ("f", -a)):
        e = N + rotv(v(0, UA), -d * ang)
        P[cle + "E"] = e
        P[cle + "H"] = e + rotv(v(0, FA), -d * (ang + 0.55))
    return P


def pose_debout(xb, d=1, pench=0.0, main=None):
    """Debout sur les marches ; pench > 0 = se penche vers l'avant ; main = point à atteindre."""
    P = {"far": 0.55}
    P["nF"] = v(xb + d * 16, ys(xb + d * 16))
    P["fF"] = v(xb - d * 14, ys(xb - d * 14))
    hip = v(xb, yl(xb) - 100 + 8 * pench)
    P["hip"] = hip
    for cle in ("n", "f"):
        P[cle + "K"] = ik(hip, P[cle + "F"], TH, SHL, v(d, -0.15))
    N = hip + rotv(v(0, -111), d * (0.08 + 0.45 * pench))
    P["N"] = N
    P["tete"] = N + rotv(v(d * 8, -36), d * 0.35 * pench)
    P["fE"] = N + rotv(v(0, UA), -d * 0.15)
    P["fH"] = P["fE"] + rotv(v(0, FA), -d * 0.5)
    if main is None:
        P["nE"] = N + rotv(v(0, UA), d * 0.1)
        P["nH"] = P["nE"] + rotv(v(0, FA), -d * 0.3)
    else:
        P["nH"] = main
        P["nE"] = ik(N, main, UA, FA, v(0, 1))
    return P


def pose_genou(xk, t, regard=0.0, main=None):
    """TOI à genoux sur les marches, tête basse ; regard → lève la tête ; main → tend le bras."""
    b = 2.5 * math.sin(2 * math.pi * t / 1.6)
    hip = v(xk - 6, ys(xk) - 58 + b * 0.3)
    P = {"far": 0.55, "hip": hip}
    P["nF"] = v(xk + 44, ys(xk + 44))
    P["nK"] = ik(hip, P["nF"], TH, SHL, v(0.6, -1))
    P["fK"] = v(xk - 12, ys(xk - 12))
    P["fF"] = P["fK"] + v(-52, -4)
    N = hip + v(lerp(44, 26, regard), lerp(-94, -104, regard) + b)
    P["N"] = N
    P["tete"] = N + v(lerp(24, 14, regard), lerp(-16, -36, regard))
    P["fE"] = N + v(6, 52)
    P["fH"] = P["fE"] + v(10, 48)
    if main is None:
        P["nE"] = N + v(12, 52)
        P["nH"] = P["nE"] + v(12, 46)
    else:
        P["nH"] = main
        P["nE"] = ik(N, main, UA, FA, v(-0.3, 1))
    return P


# ================================================================= scénario
V = 120.0                                    # pas régulier de DISCIPLINE (unités/s)
V_MOT, V_EGO, V_EGO_RUN = 145.0, 138.0, 195.0
T_MOT_FREINE, D_FREIN = 4.4, 1.2             # MOTIVATION s'essouffle puis s'arrête
T_EVAP = 6.3                                 # MOTIVATION s'évapore (boule FATIGUE)
T_EGO_SPRINT, T_EGO = 5.5, 7.6               # EGO se met à courir, puis ÉCHEC le fait tomber
T_DOUTE = 10.0                               # DOUTE met DISCIPLINE à genoux
X_GENOU = -300 + V * T_DOUTE - 90
T_REGARD, T_TIRE, T_DEBOUT, T_REPART = 11.8, 12.4, 13.3, 13.6
V2 = V
T_POTES = T_EGO_SPRINT                       # (repère sonore : whoosh du sprint d'EGO)


def x_mot(t):
    x0 = 170 + V_MOT * min(t, T_MOT_FREINE)
    if t <= T_MOT_FREINE:
        return x0
    u = min(t - T_MOT_FREINE, D_FREIN)
    return x0 + V_MOT * u - V_MOT * u * u / (2 * D_FREIN)


def x_ego(t):
    if t < T_EGO_SPRINT:
        return 330 + V_EGO * t
    return 330 + V_EGO * T_EGO_SPRINT + V_EGO_RUN * (t - T_EGO_SPRINT)


def x_disc(t):
    if t < T_DOUTE:
        return -300 + V * t
    if t < T_REPART:
        return X_GENOU
    return X_GENOU + V2 * (t - T_REPART)


x_toi = x_disc


def etat_motivation(t):
    """Part en flèche, s'essouffle, s'arrête plié en deux… et s'évapore."""
    gris = smooth(T_MOT_FREINE + 0.2, T_MOT_FREINE + D_FREIN + 0.3, t)
    info = {"nom": "MOTIVATION", "col": BLANC + (GRIS - BLANC) * gris, "alpha": 1.0, "flou": 0.0,
            "lab": BLANC + (GRIS - BLANC) * gris, "glitch": 0.0}
    x = x_mot(t)
    t_stop = T_MOT_FREINE + D_FREIN
    if t < t_stop - 0.3:
        P = pose_marche(x, ph=0.2, pench=0.4 * (1 - gris))
    else:
        u = smooth(t_stop - 0.3, t_stop + 0.2, t)
        souffle = 0.55 + 0.08 * math.sin(2 * math.pi * t / 0.7)
        P = mix(pose_marche(x, ph=0.2), pose_debout(x, 1, souffle), u)
    if t >= T_EVAP:
        u = clamp((t - T_EVAP) / 0.5)
        clign = 1.0 if math.sin(t * 95) > 0 else 0.35
        info["alpha"] = (1 - u) * clign
        info["glitch"] = 0.3 + u
        info["lab"] = ROUGE_TXT
    return P, info


def etat_ego(t):
    """Frime, vire au rouge, se met à courir… et ÉCHEC l'envoie dans le vide."""
    chauffe = smooth(3.5, 5.5, t)
    info = {"nom": "EGO", "col": BLANC + (SAUMON - BLANC) * chauffe, "alpha": 1.0, "flou": 0.0,
            "lab": BLANC + (ROUGE_TXT - BLANC) * chauffe}
    sprint = smooth(T_EGO_SPRINT - 0.2, T_EGO_SPRINT + 0.3, t)
    if t < T_EGO:
        return pose_marche(x_ego(t), ph=0.55, bras=1.0 + 0.5 * sprint, pench=0.6 * sprint), info
    tau = t - T_EGO                                          # éjecté : salto arrière dans le vide
    P0 = pose_marche(x_ego(T_EGO), ph=0.55, bras=1.5, pench=0.6)
    P = decaler(P0, v(-170 * tau, -330 * tau + 0.5 * 2400 * tau * tau))
    P = pivoter(P, P["hip"], -7.5 * tau)
    info["alpha"] = 1 - smooth(0.45, 1.1, tau)
    return P, info


def etat_discipline(t):
    """Pas régulier, d'abord dans l'ombre. Mis à genoux par DOUTE, se relève SEUL et repart."""
    lum = smooth(5.5, 8.5, t)
    rouge = smooth(T_DOUTE, T_DOUTE + 0.2, t) * (1 - smooth(T_TIRE, T_REPART, t))
    base = GRIS + (BLANC - GRIS) * lum
    info = {"nom": "DISCIPLINE", "col": base + (SAUMON - base) * rouge, "alpha": 1.0,
            "flou": 3.0 * (1 - lum), "lab": base + (ROUGE_TXT - base) * rouge}
    if t < T_DOUTE:
        return pose_marche(x_disc(t), ph=0.8), info
    if t < T_DOUTE + 0.75:                                   # renversé, recule de 3 marches
        u = (t - T_DOUTE) / 0.75
        x_hit = x_disc(T_DOUTE - 1e-6)
        P0 = pose_marche(x_hit, ph=0.8)
        x = lerp(x_hit, X_GENOU, EASES["out"](u))
        Pc = decaler(P0, v(x - x_hit, yl(x) - yl(x_hit) - 45 * math.sin(math.pi * u)))
        Pc = pivoter(Pc, Pc["hip"], -1.3 * math.sin(math.pi * min(u * 1.2, 1)))
        return mix(Pc, pose_genou(X_GENOU, t), smooth(0.45, 1.0, u)), info
    if t < T_REGARD:
        return pose_genou(X_GENOU, t), info
    if t < T_TIRE:                                           # relève la tête, main sur le genou
        u = smooth(T_REGARD, T_TIRE, t)
        Pg = pose_genou(X_GENOU, t, regard=u)
        return pose_genou(X_GENOU, t, regard=u, main=lerp(Pg["nH"], Pg["nK"] + v(-4, -8), u)), info
    if t < T_DEBOUT:                                         # pousse sur sa jambe et se relève
        u = EASES["io"]((t - T_TIRE) / (T_DEBOUT - T_TIRE))
        Pg = pose_genou(X_GENOU, t, regard=1)
        Pg = pose_genou(X_GENOU, t, regard=1, main=Pg["nK"] + v(-4, -8))
        return mix(Pg, pose_debout(X_GENOU, 1, 0.15 * (1 - u)), u), info
    if t < T_REPART:
        u = smooth(T_DEBOUT, T_REPART, t)
        return mix(pose_debout(X_GENOU, 1, 0), pose_marche(x_disc(t), ph=0.8), u), info
    return pose_marche(x_disc(t), ph=0.8), info


etat_toi = etat_discipline
PERSOS = [etat_ego, etat_motivation, etat_discipline]

# obstacles : (texte, rayon, t_impact, x_impact, vitesse, mode) ; mode "roule" ou "tombe" (du ciel)
BOULES = [
    ("FATIGUE", 30, T_EVAP + 0.35, x_mot(T_EVAP) + 4, 330, "tombe"),
    ("ÉCHEC", 34, T_EGO, x_ego(T_EGO) + 28, 360, "roule"),
    ("DOUTE", 44, T_DOUTE, x_disc(T_DOUTE - 1e-6) + 36, 380, "roule"),
]
IMPACTS = [b[2] for b in BOULES]


def etat_boule(b, t):
    nom, r, th, xh, vb, mode = b
    if t < th and mode == "tombe":
        d = th - t
        return xh, yl(xh) - r - 150 - 0.5 * 2600 * d * d, 3 * t, 1.0, 1.0
    if t < th:
        x = xh + vb * (th - t)
        y = yl(x) - r - 6 - 7 * abs(math.sin(math.pi * x / SW))
        return x, y, -x / r, 1.0, 1.0
    tau = t - th
    x = xh + 70 * tau
    y = yl(xh) - r - 6 - 380 * tau + 0.5 * 2600 * tau * tau
    return x, y, -xh / r - 6 * tau, 1 - smooth(0.35, 0.9, tau), 1 + 0.7 * tau


# ================================================================= caméra
def cible_cam(t):
    if t < 2.3:
        return x_mot(t) + 60
    vivants = [x_disc(t)]
    if t < T_EVAP + 0.4:
        vivants.append(x_mot(t))
    if t < T_EGO + 0.5:
        vivants.append(x_ego(t))
    return (min(vivants) + max(vivants)) / 2 + (70 if len(vivants) == 1 else 0)


def camera(t):
    xs = np.mean([cible_cam(max(t - k * 0.1, 0)) for k in range(10)])
    z = keyframes([(0, 2.15, "lin"), (2.3, 2.0, "io"), (4.0, 0.9, "io"), (8.0, 0.9, "io"),
                   (9.2, 1.08, "io"), (10.05, 1.28, "out"), (10.6, 1.18, "io"), (11.8, 1.22, "io"),
                   (13.3, 1.42, "io"), (14.0, 1.38, "io"), (17.0, 1.0, "io"), (19.8, 1.06, "io")], t)
    return v(xs, yl(xs) - 150), z


ANCRE = v(W * 0.47, H * 0.58)


def ecran(p, cam):
    c, z = cam
    return (p - c) * z + ANCRE


# ================================================================= statique
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
    d = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.3) / H) ** 2)
    base = 0.07 * np.clip(1 - d * 1.4, 0, 1) ** 1.5 + 0.012
    _cache["bg"] = np.stack([base * 0.97, base * 0.98, base * 1.06], -1).astype(np.float32)
    vig = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    _cache["vig"] = np.clip(1.15 - vig ** 2.2 * 0.75, 0.25, 1).astype(np.float32)
    _cache["bord"] = np.clip(vig - 0.5, 0, 1).astype(np.float32)
    rng = np.random.default_rng(7)
    _cache["grain"] = [rng.standard_normal((H // 2, W // 2)).astype(np.float32) for _ in range(6)]
    n = 150
    _cache["dust"] = np.stack([rng.uniform(0, W, n), rng.uniform(0, H, n), rng.uniform(6, 26, n),
                               rng.uniform(0.6, 2.3, n), rng.uniform(0, 6.28, n), rng.uniform(0.3, 1, n)], 1)
    _cache["bokeh"] = np.stack([rng.uniform(0, W, 14), rng.uniform(200, H - 100, 14),
                                rng.uniform(20, 64, 14), rng.uniform(0.02, 0.06, 14),
                                rng.uniform(0, 6.28, 14)], 1)
    _cache["stries"] = np.stack([rng.uniform(-400, W + 400, 26), rng.uniform(0, H, 26),
                                 rng.uniform(80, 260, 26), rng.uniform(0.05, 0.16, 26)], 1)
    _cache["note"] = masque_note(200)
    return _cache


# ================================================================= décor
def ambiance(t):
    """(rouge, chaleur) de la lumière."""
    rouge = smooth(T_DOUTE, T_DOUTE + 0.3, t) * (1 - smooth(T_TIRE, T_DEBOUT + 0.4, t))
    chaud = smooth(T_TIRE, T_REPART + 0.5, t)
    return rouge, chaud


def couche_escaliers(t, cam):
    """Escalier principal (masse sombre + arêtes) + escalier lointain en parallaxe."""
    c, z = cam
    q = 1
    m_masse = Image.new("L", (W * SS, H * SS), 0)
    m_aretes = Image.new("L", (W * SS, H * SS), 0)
    dm, da = ImageDraw.Draw(m_masse), ImageDraw.Draw(m_aretes)
    # escalier lointain (parallaxe 0,55, plus haut)
    cam_bg = (c * 0.55 + v(-260, -520), z * 0.8)
    for camx, coef, aretes in ((cam_bg, 0.10, 60), (cam, 1.0, 255)):
        cc, zz = camx
        x0 = (cc[0] - (ANCRE[0] + 200) / zz)
        x1 = (cc[0] + (W - ANCRE[0] + 200) / zz)
        k0, k1 = int(math.floor(x0 / SW)), int(math.ceil(x1 / SW))
        pts = []
        for k in range(k0, k1 + 1):
            xa = k * SW
            y = -k * SH
            pts.append(tuple(ecran(v(xa, y + SH), camx) * SS))
            pts.append(tuple(ecran(v(xa, y), camx) * SS))
        bas = (pts[-1][0], (H + 400) * SS)
        poly = pts + [bas, (pts[0][0], (H + 400) * SS)]
        if coef == 1.0:
            dm.polygon(poly, fill=255)
        w = max(1, int(2 * zz * SS * 0.9))
        for i in range(0, len(pts) - 1, 2):
            da.line([pts[i], pts[i + 1]], fill=int(aretes * 0.45), width=w)       # contremarche
            if i + 2 < len(pts):
                da.line([pts[i + 1], pts[i + 2]], fill=aretes, width=w)          # dessus
    M = np.asarray(m_masse.resize((W, H), Image.BILINEAR), np.float32) / 255
    A = np.asarray(m_aretes.resize((W, H), Image.LANCZOS), np.float32) / 255
    return M, A


def couche_spots(t, cam):
    q = 4
    c, z = cam
    rouge, chaud = ambiance(t)
    m = Image.new("L", (W // q, H // q), 0)
    d = ImageDraw.Draw(m)
    xcen = c[0]
    k0 = int((xcen - 1400) // 520)
    for k in range(k0, k0 + 7):
        xc = 240 + k * 520
        base = yl(xc)
        sb = ecran(v(xc, base), cam)
        # cône vertical depuis le haut de l'écran
        larg_b, larg_h = 190 * z, 40 * z
        d.polygon([((sb[0] - larg_h) / q, -50 / q), ((sb[0] + larg_h) / q, -50 / q),
                   ((sb[0] + larg_b) / q, (sb[1] + 30) / q), ((sb[0] - larg_b) / q, (sb[1] + 30) / q)], fill=120)
        d.polygon([((sb[0] - larg_h * 0.3) / q, -50 / q), ((sb[0] + larg_h * 0.3) / q, -50 / q),
                   ((sb[0] + larg_b * 0.45) / q, (sb[1] + 30) / q), ((sb[0] - larg_b * 0.45) / q, (sb[1] + 30) / q)], fill=210)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
    yy = np.linspace(0, 1, H // q, dtype=np.float32)[:, None]
    m = m * np.clip(0.3 + yy * 0.9, 0, 1)
    col = np.array([0.86, 0.88, 0.93], np.float32)
    col = lerp(col, np.array([0.95, 0.15, 0.13], np.float32), rouge * 0.85)
    col = lerp(col, np.array([1.0, 0.9, 0.74], np.float32), chaud * 0.6)
    fl = 1 + 0.03 * math.sin(t * 7.1) + 0.02 * math.sin(t * 17.3)
    up = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    lum = np.asarray(up, np.float32) / 255
    return lum[..., None] * col * 0.22 * fl, m


def couche_atmo(t, lum_q, st):
    q = 4
    dust = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(dust)
    for x0, y0, vit, taille, ph, a in st["dust"]:
        y = (y0 - vit * t) % H
        x = (x0 + 10 * math.sin(t * 0.6 + ph)) % W
        li = lum_q[int(clamp(y / q, 0, H / q - 1)), int(clamp(x / q, 0, W / q - 1))]
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
    out = np.asarray(dust, np.float32) / 255 * 0.5 + np.asarray(bok, np.float32) / 255 / 3
    # stries diagonales de lumière (montent en intensité dans la 2e moitié)
    ks = smooth(9.5, 11, t) * 0.6 + smooth(14.6, 16, t) * 0.6
    if ks > 0:
        st_im = Image.new("L", (W, H), 0)
        ds = ImageDraw.Draw(st_im)
        for x0, y0, L, a in st["stries"]:
            y = (y0 + 520 * t) % (H + 400) - 200
            x = x0 - 0.6 * y * 0 + ((520 * t * 0.75) % (W + 800)) * 0 + x0 * 0
            xx = (x0 + 390 * t) % (W + 800) - 400
            ds.line([(xx, y), (xx - L * 0.8, y - L * 0.6 * -1)], fill=int(a * 255 * ks), width=2)
        out += np.asarray(st_im.filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255 * 0.5
    return out


# ================================================================= personnages
def _seg(d, a, b, w):
    a, b = tuple(a * SS), tuple(b * SS)
    d.line([a, b], fill=255, width=int(w * SS))
    r = w * SS / 2
    for p in (a, b):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=255)


def dessiner(Ps, near, far, z, origine):
    dn, df = ImageDraw.Draw(near), ImageDraw.Draw(far)
    P = {c: Ps[c] - origine for c in CLES}
    for a, b in (("N", "fE"), ("fE", "fH"), ("hip", "fK"), ("fK", "fF")):
        _seg(df, P[a], P[b], LW_F * z)
    for a, b in (("N", "hip"), ("hip", "nK"), ("nK", "nF"), ("N", "nE"), ("nE", "nH")):
        _seg(dn, P[a], P[b], LW_N * z)
    tete, N = P["tete"], P["N"]
    _seg(dn, N, lerp(N, tete, 0.6), LW_N * z * 0.85)
    c, r = tete * SS, R_TETE * z * SS
    dn.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=255)


def couche_perso(etat, t, cam):
    P, info = etat(t)
    if info["alpha"] <= 0.01:
        return None
    z = cam[1]
    Ps = {c: ecran(P[c], cam) for c in CLES}
    P_av, _ = etat(max(t - 1 / FPS, 0))
    cam_av = camera(max(t - 1 / FPS, 0))
    vit = max(np.linalg.norm(Ps[c] - ecran(P_av[c], cam_av)) for c in CLES)
    nsub = 1 if vit < 6 else (3 if vit < 20 else 5)
    pts = np.array([Ps[c] for c in CLES])
    marge = 60 * z + 40
    x0, y0 = pts.min(0) - marge - (vit if nsub > 1 else 0)
    x1, y1 = pts.max(0) + marge + (vit if nsub > 1 else 0)
    x0, y0 = int(max(x0, -200)), int(max(y0, -200))
    x1, y1 = int(min(x1, W + 200)), int(min(y1, H + 200))
    bw, bh = x1 - x0, y1 - y0
    if bw <= 4 or bh <= 4:
        return None
    o = v(x0, y0)
    acc_n = np.zeros((bh, bw), np.float32)
    acc_f = np.zeros((bh, bw), np.float32)
    filt = Image.BILINEAR if nsub > 1 else Image.LANCZOS
    for j in range(nsub):
        if j == 0:
            Pj = Ps
        else:
            tj = t - (j / (nsub - 1)) * 0.55 / FPS
            Pr, _ = etat(tj)
            cj = camera(tj)
            Pj = {c: ecran(Pr[c], cj) for c in CLES}
            Pj["far"] = Pr["far"]
        near = Image.new("L", (bw * SS, bh * SS), 0)
        far = Image.new("L", (bw * SS, bh * SS), 0)
        dessiner(Pj, near, far, z, o)
        if info["flou"] > 0.2:
            near = near.filter(ImageFilter.GaussianBlur(info["flou"] * SS))
            far = far.filter(ImageFilter.GaussianBlur(info["flou"] * SS))
        acc_n += np.asarray(near.resize((bw, bh), filt), np.float32)
        acc_f += np.asarray(far.resize((bw, bh), filt), np.float32)
    an, af = acc_n / (255 * nsub), acc_f / (255 * nsub)
    col = info["col"]
    rgb = an[..., None] * col + (af * (1 - an))[..., None] * col * P["far"]
    alpha = np.clip(an + af * (1 - an), 0, 1)
    a = info["alpha"]
    rgb, alpha = rgb * a, alpha * a
    g = info.get("glitch", 0.0)
    if g > 0:                                              # évaporation glitch
        rng = np.random.default_rng(int(t * 1000))
        for _ in range(int(4 + 10 * g)):
            yb = rng.integers(0, max(bh - 10, 1))
            hb = int(rng.integers(3, 18))
            dx = int(rng.integers(-40, 40) * g)
            rgb[yb:yb + hb] = np.roll(rgb[yb:yb + hb], dx, 1)
            alpha[yb:yb + hb] = np.roll(alpha[yb:yb + hb], dx, 1)
        k = int(6 * g)
        rgb[..., 0] = np.roll(rgb[..., 0], k, 1)
        rgb[..., 2] = np.roll(rgb[..., 2], -k, 1)
    tete = Ps["tete"]
    return rgb, alpha, x0, y0, info, (tete[0], tete[1] - R_TETE * z - 30)


def couche_boule(b, t, cam):
    nom, r = b[0], b[1]
    x, y, rot_, alpha, ech = etat_boule(b, t)
    p = ecran(v(x, y), cam)
    z = cam[1]
    R = r * z * ech
    if p[0] < -R - 50 or p[0] > W + R + 50 or p[1] > H + R or alpha <= 0.01:
        return None
    taille = int(R * 2 + 30)
    im = Image.new("RGBA", (taille * SS, taille * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = taille / 2 * SS
    Rs = R * SS
    d.ellipse([cx - Rs, cy - Rs, cx + Rs, cy + Rs], fill=(18, 18, 22, 255))
    # reflet
    d.ellipse([cx - Rs * 0.7, cy - Rs * 0.75, cx + Rs * 0.1, cy - Rs * 0.05], fill=(48, 48, 56, 255))
    d.ellipse([cx - Rs * 0.45, cy - Rs * 0.62, cx - Rs * 0.15, cy - Rs * 0.35], fill=(90, 90, 98, 255))
    # fissures qui tournent
    for k in range(2):
        a0 = rot_ + k * math.pi
        pts = [(cx + Rs * 0.55 * math.cos(a0 + s * 0.6) * (1 - 0.3 * s), cy + Rs * 0.55 * math.sin(a0 + s * 0.6) * (1 - 0.3 * s))
               for s in np.linspace(0, 1.6, 6)]
        d.line(pts, fill=(110, 110, 118, 255), width=max(1, int(2 * z * SS)))
    d.ellipse([cx - Rs, cy - Rs, cx + Rs, cy + Rs], outline=(150, 150, 160, 255), width=max(1, int(2.2 * z * SS)))
    im = im.resize((taille, taille), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    return a[..., :3] * alpha, a[..., 3] * alpha, int(p[0] - taille / 2), int(p[1] - taille / 2), nom, \
        (p[0], p[1] - R - 26), alpha


def coller_rgba(img, rgb, alpha, x0, y0):
    h_, w_ = alpha.shape
    xa, ya = max(x0, 0), max(y0, 0)
    xb, yb = min(x0 + w_, W), min(y0 + h_, H)
    if xb <= xa or yb <= ya:
        return
    a = alpha[ya - y0:yb - y0, xa - x0:xb - x0, None]
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - a) + rgb[ya - y0:yb - y0, xa - x0:xb - x0]


# ================================================================= textes
def texte_tape(txt, prog, t, glitch=True):
    n = int(clamp(prog) * len(txt))
    s = txt[:n]
    if glitch and 0 < n < len(txt):
        rng = np.random.default_rng(int(t * 60))
        s += "".join(rng.choice(list("#%&$}^*!<>/"), size=int(rng.integers(1, 3))))
    return s


def dessiner_textes(img, t, labels):
    """Étiquettes au-dessus des têtes / boules + titre et réponse en haut."""
    calque = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    f = police(MONO, 21 * SS)
    for txt, (x, y), col, a in labels:
        if a <= 0.02 or not (-200 < x < W + 200 and -100 < y < H + 100):
            continue
        c = tuple(int(255 * k) for k in col) + (int(255 * clamp(a)),)
        tl = d.textlength(txt, font=f) + 3 * SS * (len(txt) - 1)
        xx = x * SS - tl / 2
        for ch in txt:
            d.text((xx, y * SS), ch, font=f, fill=c, anchor="ls")
            xx += d.textlength(ch, font=f) + 3 * SS
    ft = police(MONO, 40 * SS)
    lignes = []
    gris_titre = 1 - 0.45 * smooth(14.6, 15.2, t)
    for i, txt in enumerate(TITRE):
        prog = (t - 2.6 - i * 0.75) / 0.7
        lignes.append((texte_tape(txt, prog, t), 170 + 58 * i, (gris_titre,) * 3))
    for i, txt in enumerate(REPONSE):
        prog = (t - 14.8 - i * 1.0) / 0.8
        col = (0.78, 0.78, 0.8) if i < 2 else (1.0, 0.86, 0.66)
        lignes.append((texte_tape(txt, prog, t), 320 + 62 * i, col))
    for txt, y, col in lignes:
        if not txt:
            continue
        c = tuple(int(255 * k) for k in col) + (255,)
        esp = 7 * SS
        tl = sum(d.textlength(ch, font=ft) for ch in txt) + esp * (len(txt) - 1)
        xx = W / 2 * SS - tl / 2
        for ch in txt:
            d.text((xx, y * SS), ch, font=ft, fill=c, anchor="ls")
            xx += d.textlength(ch, font=ft) + esp
    a = np.asarray(calque.resize((W, H), Image.LANCZOS), np.float32) / 255
    al = a[..., 3:4]
    return img * (1 - al) + a[..., :3]


# ================================================================= scène
def secousse(t):
    sx = sy = ab = flash = 0.0
    for ti in IMPACTS:
        u = t - ti
        if 0 <= u < 0.6:
            e = math.exp(-u * 7)
            fort = 1.6 if ti == T_DOUTE else 1.0
            sx += 10 * fort * e * math.sin(u * 63)
            sy += 8 * fort * e * math.sin(u * 51 + 1)
            ab += 6 * fort * math.exp(-u * 6)
            flash += 0.4 * fort * math.exp(-u * 5)
    u = t - T_EVAP
    if 0 <= u < 0.5:
        ab += 5 * (1 - u / 0.5)
    return sx, sy, ab, flash


def rendre_scene(t):
    st = statique()
    cam = camera(t)
    img = st["bg"].copy()
    M, A = couche_escaliers(t, cam)
    img = img * (1 - M[..., None] * 0.75)
    img += A[..., None] * np.array([0.30, 0.30, 0.32], np.float32)
    spots, lum_q = couche_spots(t, cam)
    img += spots
    img += couche_atmo(t, lum_q, st)[..., None] * np.array([0.85, 0.87, 0.92], np.float32)

    labels = []
    anneaux = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(anneaux)
    for b in BOULES:
        res = couche_boule(b, t, cam)
        if res:
            rgb, al, x0, y0, nom, pos, a = res
            coller_rgba(img, rgb, al, x0, y0)
            labels.append((nom, pos, ROUGE_TXT, a))
        u = t - b[2]
        if 0 <= u < 0.55:                                    # anneaux d'impact
            x, y, *_ = etat_boule(b, b[2])
            p = ecran(v(x, y), cam)
            for k, (r0, r1) in enumerate(((20, 150), (10, 90))):
                rr = lerp(r0, r1, EASES["out"](clamp(u / 0.55 * (1 + 0.4 * k)))) * cam[1]
                g = int(255 * (1 - u / 0.55) ** 1.4 * (0.85 - 0.3 * k))
                dr.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], outline=g, width=3)
    # halo rouge sous TOI quand il est à genoux
    rouge, chaud = ambiance(t)
    if rouge > 0.01 or chaud > 0.01:
        P, _ = etat_toi(t)
        c = ecran((P["hip"] + P["tete"]) / 2, cam)
        hal = Image.new("L", (W // 4, H // 4), 0)
        r_ = 115 * cam[1] / 4
        ImageDraw.Draw(hal).ellipse([c[0] / 4 - r_, c[1] / 4 - r_ * 1.2, c[0] / 4 + r_, c[1] / 4 + r_ * 1.2], fill=255)
        hal = np.asarray(hal.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR), np.float32) / 255
        img += hal[..., None] * (np.array([0.9, 0.08, 0.08], np.float32) * rouge * 0.28
                                 + np.array([0.5, 0.4, 0.25], np.float32) * chaud * 0.12)

    for etat in PERSOS:
        res = couche_perso(etat, t, cam)
        if res is None:
            continue
        rgb, al, x0, y0, info, pos = res
        coller_rgba(img, rgb, al, x0, y0)
        nom = info["nom"]
        if info.get("glitch", 0) > 0:
            rng = np.random.default_rng(int(t * 40))
            nom = "".join(ch if rng.random() > info["glitch"] * 0.6 else rng.choice(list("#$%&?")) for ch in nom)
        labels.append((nom, pos, info["lab"], info["alpha"]))
    img += (np.asarray(anneaux.filter(ImageFilter.GaussianBlur(1.1)), np.float32) / 255)[..., None] * 0.85
    img = dessiner_textes(img, t, labels)
    return img


def post(img, t, i_frame):
    st = statique()
    sx, sy, ab, flash = secousse(t)
    rouge, chaud = ambiance(t)
    r = flash + 0.5 * rouge
    img = img + (st["bord"] * r)[..., None] * np.array([0.6, 0.03, 0.04], np.float32)
    img = img + (st["bord"] * chaud * 0.25)[..., None] * np.array([0.35, 0.22, 0.08], np.float32)
    u8 = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    b = np.asarray(u8.resize((W // 4, H // 4), Image.BOX), np.float32) / 255
    b = Image.fromarray((np.clip((b - 0.45) * 1.8, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))
    img = img + np.asarray(b.resize((W, H), Image.BILINEAR), np.float32) / 255 * 0.35
    img = img * st["vig"][..., None]
    g = st["grain"][i_frame % len(st["grain"])]
    img = img + np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None] * 0.02
    out = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    if sx or sy:
        out = out.transform((W, H), Image.AFFINE, (1, 0, -sx, 0, 1, -sy), Image.BICUBIC)
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


def rendre_fin(t, i_frame):
    L = t - T_CARTE
    st = statique()
    navy = tuple(int(c * 255) for c in NAVY)
    toile = Image.new("RGB", (W * SS, H * SS), navy)
    rng = np.random.default_rng(i_frame)
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
    Lb = L - 0.3
    if Lb >= 0:
        bw, bh = 600, 92
        x0, y0 = (W - bw) / 2, 1040
        u = EASES["out"](clamp(Lb / 0.45))
        dxr, dxc, ep = lerp(-90, -8, u), lerp(90, 8, u), lerp(26, 6, u)
        rr = 14 * SS
        d.rounded_rectangle([(x0 + dxr) * SS, (y0 - ep) * SS, (x0 + bw + dxr) * SS, (y0 + bh - 6) * SS], radius=rr, fill=ROSE)
        d.rounded_rectangle([(x0 + dxc) * SS, (y0 + 6) * SS, (x0 + bw + dxc) * SS, (y0 + bh + ep) * SS], radius=rr, fill=CYAN)
        d.rounded_rectangle([x0 * SS, y0 * SS, (x0 + bw) * SS, (y0 + bh) * SS], radius=rr, fill=(255, 255, 255))
        d.rounded_rectangle([(x0 + 11) * SS, (y0 + 11) * SS, (x0 + bw - 11) * SS, (y0 + bh - 11) * SS], radius=10 * SS, fill=navy)
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
    if L < 0.45:
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
    rng = np.random.default_rng(5)

    def env(a, b, c, d):
        return np.clip((t - a) / max(b - a, 1e-3), 0, 1) * np.clip((d - t) / max(d - c, 1e-3), 0, 1)

    def nappe(freqs, e, g):
        for f in freqs:
            for det, pan in ((-0.3, 0.3), (0.35, 0.7)):
                ph = 2 * np.pi * (f + det) * t
                s = (0.6 * np.sin(ph) + 0.1 * (2 * ((ph / (2 * np.pi)) % 1) - 1)) * e * g
                out[:, 0] += s * (1 - pan)
                out[:, 1] += s * pan

    # sombre (la mineur) → tendu (ré mineur grave) → chaud (fa majeur → do majeur)
    nappe((55.0, 110.0, 130.81, 164.81), env(0, 2.0, T_DOUTE - 0.3, T_DOUTE + 0.3), 0.06)
    nappe((36.71, 73.42, 87.31, 110.0), env(T_DOUTE - 0.1, T_DOUTE + 0.4, T_TIRE - 0.4, T_TIRE + 0.6), 0.07)
    nappe((87.31, 174.61, 220.0, 261.63, 349.23), env(T_TIRE - 0.2, T_TIRE + 1.0, 16.8, 17.6), 0.05)
    nappe((65.41, 130.81, 196.0, 261.63, 329.63, 392.0), env(16.6, 17.8, T_FIN - 0.4, T_FIN + 0.2), 0.05)

    def ajoute(sig, t0, g=1.0, pan=0.5):
        i0 = int(t0 * SR)
        if i0 >= n or i0 < 0:
            return
        m = min(len(sig), n - i0)
        out[i0:i0 + m, 0] += sig[:m] * g * (1 - pan) * 2
        out[i0:i0 + m, 1] += sig[:m] * g * pan * 2

    def ton(dur, f0, f1, dec):
        tt = np.arange(int(dur * SR)) / SR
        f = f1 + (f0 - f1) * np.exp(-tt * 22)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * dec)

    # pas de TOI (2 par cycle de marche)
    def pas(t0, t1, vit, ph=0.0):
        per = STRIDE / vit / 2
        k = 0
        while t0 + ph + k * per < t1:
            tt = np.arange(int(0.06 * SR)) / SR
            s = rng.standard_normal(len(tt)) * np.exp(-tt * 90)
            s = np.convolve(s, np.ones(12) / 12, "same")
            ajoute(s * 0.5 + ton(0.06, 140, 90, 60) * 0.3, t0 + ph + k * per, 0.18, 0.45 + 0.1 * (k % 2))
            k += 1
    pas(0.0, T_DOUTE, V)
    pas(T_REPART, T_FIN, V2, 0.1)
    # roulement des boules + impacts
    for nom, r, th, xh, vb, mode in BOULES:
        d0 = th - 1.6
        tt = np.arange(int(1.6 * SR)) / SR
        bump = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * (vb / SW) * tt))
        s = np.convolve(rng.standard_normal(len(tt)), np.ones(60) / 60, "same") * bump * (tt / 1.6) ** 1.5
        ajoute(s * 0.9, d0, 0.35, 0.65)
        tt = np.arange(int(1.4 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(36 + 80 * np.exp(-tt * 10)) / SR) * np.exp(-tt * 3)
        crack = rng.standard_normal(len(tt)) * np.exp(-tt * 30)
        fort = 0.75 if nom == "DOUTE" else 0.45
        ajoute(boom * 0.9 + crack * 0.35, th, fort)
    # évaporation de L'ARGENT FACILE : glitch numérique
    tt = np.arange(int(0.5 * SR)) / SR
    gl = np.sign(np.sin(2 * np.pi * 320 * tt * (1 + 2 * tt))) * (rng.random(len(tt)) > 0.4) * np.exp(-tt * 4)
    ajoute(gl * 0.12, T_EVAP, 0.5, 0.6)
    # EGO se met à courir : « swish »
    tt = np.arange(int(0.35 * SR)) / SR
    sw = np.convolve(rng.standard_normal(len(tt)), np.ones(30) / 30, "same") * np.sin(np.pi * tt / 0.35) ** 2
    ajoute(sw * 0.6, T_POTES, 0.4, 0.35)
    # battements de cœur pendant qu'il est à genoux
    k = 0
    while T_DOUTE + 0.8 + k * 0.85 < T_TIRE:
        tb = T_DOUTE + 0.8 + k * 0.85
        ajoute(ton(0.25, 75, 40, 12), tb, 0.5)
        ajoute(ton(0.22, 65, 38, 14), tb + 0.22, 0.32)
        k += 1
    # main tendue : scintillement montant
    tt = np.arange(int(1.6 * SR)) / SR
    sh = sum(np.sin(2 * np.pi * f * tt) for f in (523.25, 659.25, 783.99, 1046.5)) * (tt / 1.6) * np.exp(-(tt - 1.2) ** 2 * 4)
    ajoute(sh * 0.04, T_REGARD, 1.0)
    # frappe des textes
    for (t0, txts, durees) in ((2.6, TITRE, (0.7, 0.7)), (14.8, REPONSE, (0.8, 0.8, 0.8))):
        for i, (txt, du) in enumerate(zip(txts, durees)):
            dec = 0.75 if t0 < 5 else 1.0
            for c in range(len(txt)):
                tt = np.arange(int(0.025 * SR)) / SR
                ajoute(rng.standard_normal(len(tt)) * np.exp(-tt * 300) * 0.22,
                       t0 + i * dec + c * du / len(txt), 0.5, 0.45 + 0.1 * (c % 2))
    # glitch de fin, whoosh, frappe du pseudo
    tt = np.arange(int(0.4 * SR)) / SR
    gl = np.sign(np.sin(2 * np.pi * 180 * tt)) * (rng.random(len(tt)) > 0.5) * np.exp(-tt * 3)
    ajoute(np.round(gl * 4) / 4 * 0.18, T_FIN, 0.6)
    tt = np.arange(int(0.5 * SR)) / SR
    wh = np.convolve(rng.standard_normal(len(tt)) * np.sin(np.pi * tt / 0.5) ** 2, np.ones(25) / 25, "same")
    ajoute(wh * 0.5, T_CARTE + 0.3, 0.5)
    for c in range(len(PSEUDO)):
        tt = np.arange(int(0.03 * SR)) / SR
        ajoute(rng.standard_normal(len(tt)) * np.exp(-tt * 260) * 0.25,
               T_CARTE + 0.85 + c * 0.85 / len(PSEUDO), 0.5, 0.45 + 0.1 * (c % 2))
    fin = env(T_FIN + 0.3, T_FIN + 1.0, DUREE - 0.8, DUREE)
    for f in (261.63, 329.63, 392.0):
        s = np.sin(2 * np.pi * f * t) * fin * 0.022
        out[:, 0] += s
        out[:, 1] += s
    out = np.tanh(out * 1.5) * 0.85
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
           "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "14M", "-bufsize", "28M",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", SORTIE]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, data in enumerate(pool.imap(image_n, range(n), chunksize=2)):
            ff.stdin.write(data)
            if i % 60 == 0:
                print(f"  {i / FPS:5.1f} s / {DUREE:.1f} s", flush=True)
    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    print("Vidéo :", SORTIE)


def apercu(chemin):
    temps = [0.8, 3.0, 4.6, 5.9, 6.5, 7.3, 7.75, 9.9,
             10.3, 11.5, 12.3, 12.9, 14.2, 17.8, 20.0, 23.0]
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
    ap.add_argument("--son")
    ap.add_argument("--out")
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
