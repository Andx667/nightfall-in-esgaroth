"""Zeichnet die Karten von „Nachtfall in Esgaroth“ (Loremaster- und Spielerfassung) und das Routendiagramm.

Helfer (rough, blob, label, num, frame …) übernommen aus tools/maps.py von Graufieber und der Finsterwacht.

Optional step: the rendered JPGs are committed in assets/maps, so the PDF build
never needs this. Run it only after changing a map:

    pip install playwright pillow && playwright install chromium
    python3 tools/maps.py
"""
import random, math
from playwright.sync_api import sync_playwright

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "assets", "maps") + os.sep
SVG = os.path.join(D, "svg") + os.sep
INK, RED = "#3a2716", "#8a2e1e"
W, H = 800, 600
GM = True


def rough(pts, closed=False, jit=2.2, seg=14, seed=1):
    """Hand-drawn polyline: subdivide each segment and jitter the points."""
    r = random.Random(seed)
    P = pts + ([pts[0]] if closed else [])
    out = []
    for (x1, y1), (x2, y2) in zip(P, P[1:]):
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / seg))
        for i in range(n):
            t = i / n
            out.append((x1 + (x2 - x1) * t + r.uniform(-jit, jit), y1 + (y2 - y1) * t + r.uniform(-jit, jit)))
    out.append(P[-1] if not closed else out[0])
    d = f"M{out[0][0]:.1f} {out[0][1]:.1f}"
    for (ax, ay), (bx, by) in zip(out, out[1:]):
        d += f" Q{ax:.1f} {ay:.1f} {(ax + bx) / 2:.1f} {(ay + by) / 2:.1f}"
    d += f" L{out[-1][0]:.1f} {out[-1][1]:.1f}"
    return d + (" Z" if closed else "")


def blob(cx, cy, rx, ry, irr=0.08, n=28, seed=1, a0=0, a1=360):
    r = random.Random(seed)
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        k = 1 + r.uniform(-irr, irr)
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return pts


def path(d, w=1.6, col=INK, dash=None, fill="none", op=1):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" opacity="{op}"{da}/>'


def label(x, y, txt, size=24, anchor="middle", rot=0, col=INK, style=""):
    tr = f' transform="rotate({rot} {x} {y})"' if rot else ""
    return f'<text x="{x}" y="{y}" font-family="TeX Gyre Chorus" font-size="{size}" fill="{col}" text-anchor="{anchor}"{tr} {style}>{txt}</text>'


def num(x, y, n):
    if not GM:
        return ""
    return (f'<circle cx="{x}" cy="{y}" r="13" fill="#efe2c4" stroke="{RED}" stroke-width="1.6"/>'
            f'<text x="{x}" y="{y + 5.5}" font-family="TeX Gyre Pagella" font-weight="700" font-size="16" fill="{RED}" text-anchor="middle">{n}</text>')


def hachures(pts, out=True, length=12, every=1, seed=3, w=1.1):
    """Short strokes pointing outward from a polygon edge (cliffs, earthworks)."""
    r = random.Random(seed)
    s = ""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    for i, (x1, y1) in enumerate(pts[:-1]):
        x2, y2 = pts[i + 1]
        n = int(math.hypot(x2 - x1, y2 - y1) / 9)
        for j in range(0, n, every):
            t = j / max(n, 1)
            x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            dx, dy = x - cx, y - cy
            L = math.hypot(dx, dy) or 1
            k = length * r.uniform(0.6, 1.25) * (1 if out else -1)
            s += path(f"M{x:.1f} {y:.1f} L{x + dx / L * k:.1f} {y + dy / L * k:.1f}", w)
    return s


def trees(cx, cy, n, spread, seed):
    r = random.Random(seed)
    s = ""
    for _ in range(n):
        x, y = cx + r.uniform(-spread, spread), cy + r.uniform(-spread * 0.6, spread * 0.6)
        s += path(rough([(x - 5, y + 4), (x, y - 6), (x + 5, y + 4)], jit=0.6, seg=5, seed=r.randint(0, 999)), 1.2)
    return s


def compass(x, y):
    return (f'<g transform="translate({x} {y})">'
            + path(rough([(0, -38), (7, 0), (0, 38), (-7, 0)], closed=True, jit=0.7, seg=8, seed=5), 1.4)
            + path("M0 -38 L7 0 L0 0 Z", 0.5, fill=INK, op=0.85)
            + path(rough([(-30, 0), (30, 0)], jit=0.6, seed=6), 1)
            + f'<text x="0" y="-44" font-family="TeX Gyre Pagella" font-weight="700" font-size="16" fill="{INK}" text-anchor="middle">N</text></g>')


def cartouche(x, y, title, sub, w=250):
    return (path(rough([(x, y), (x + w, y), (x + w, y + 64), (x, y + 64)], closed=True, jit=1.2, seed=9), 1.5, fill="#efe2c4", op=0.95)
            + path(rough([(x + 6, y + 6), (x + w - 6, y + 6), (x + w - 6, y + 58), (x + 6, y + 58)], closed=True, jit=0.9, seed=10), 0.8)
            + label(x + w / 2, y + 33, title, 30, col=RED)
            + label(x + w / 2, y + 52, sub, 17))


def frame(content, seed):
    r = random.Random(seed)
    edge = []
    for (x1, y1), (x2, y2) in zip([(6, 6), (W - 6, 6), (W - 6, H - 6), (6, H - 6)], [(W - 6, 6), (W - 6, H - 6), (6, H - 6), (6, 6)]):
        n = 40
        for i in range(n):
            t = i / n
            edge.append((x1 + (x2 - x1) * t + r.uniform(-3.5, 3.5), y1 + (y2 - y1) * t + r.uniform(-3.5, 3.5)))
    clip = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in edge) + " Z"
    stains = "".join(
        f'<circle cx="{r.uniform(60, W - 60):.0f}" cy="{r.uniform(60, H - 60):.0f}" r="{r.uniform(30, 90):.0f}" fill="url(#stain)" opacity="{r.uniform(0.25, 0.55):.2f}"/>'
        for _ in range(6))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W * 2}" height="{H * 2}">
<defs>
 <clipPath id="torn"><path d="{clip}"/></clipPath>
 <filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="{seed}"/>
  <feColorMatrix values="0 0 0 0 0.35  0 0 0 0 0.25  0 0 0 0 0.12  0 0 0 0.22 0"/>
 </filter>
 <filter id="blot" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="4" seed="{seed + 3}"/>
  <feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.32  0 0 0 0 0.15  0 0 0 0.55 -0.12"/>
 </filter>
 <filter id="ink" x="-5%" y="-5%" width="110%" height="110%">
  <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" seed="{seed + 7}" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="3" xChannelSelector="R" yChannelSelector="G"/>
 </filter>
 <radialGradient id="vig" cx="50%" cy="50%" r="72%"><stop offset="55%" stop-color="#e8d8b3" stop-opacity="0"/><stop offset="100%" stop-color="#7a5528" stop-opacity="0.55"/></radialGradient>
 <radialGradient id="stain"><stop offset="0%" stop-color="#b08850" stop-opacity="0"/><stop offset="80%" stop-color="#a07840" stop-opacity="0.25"/><stop offset="100%" stop-color="#8a6230" stop-opacity="0"/></radialGradient>
 <radialGradient id="lamp"><stop offset="0%" stop-color="#e8a33a" stop-opacity="0.95"/><stop offset="100%" stop-color="#e8a33a" stop-opacity="0"/></radialGradient>
 <radialGradient id="pale"><stop offset="0%" stop-color="#cfe3e6" stop-opacity="1"/><stop offset="100%" stop-color="#9fc4cc" stop-opacity="0"/></radialGradient>
</defs>
<rect width="{W}" height="{H}" fill="#ffffff"/>
<g clip-path="url(#torn)">
 <rect width="{W}" height="{H}" fill="#e9dbb9"/>
 <rect width="{W}" height="{H}" filter="url(#blot)"/>
 {stains}
 <g filter="url(#ink)" opacity="0.92">{content}</g>
 <rect width="{W}" height="{H}" filter="url(#grain)"/>
 <rect width="{W}" height="{H}" fill="url(#vig)"/>
</g>
<path d="{clip}" fill="none" stroke="#6b4a24" stroke-width="1.2" opacity="0.5"/>
</svg>'''




BROWN = "#6b4a24"
WATER = "#c9c8b0"


def reeds(cx, cy, n, sx, sy, seed, col=INK, w=0.9):
    """Schilfbüschel: kurze, leicht geneigte Striche mit Kolben."""
    r = random.Random(seed)
    s = ""
    for _ in range(n):
        x, y = cx + r.uniform(-sx, sx), cy + r.uniform(-sy, sy)
        h = r.uniform(9, 16)
        lean = r.uniform(-3, 3)
        s += path(f"M{x:.1f} {y:.1f} Q{x + lean / 2:.1f} {y - h / 2:.1f} {x + lean:.1f} {y - h:.1f}", w, col=col)
        if r.random() < 0.35:
            s += f'<ellipse cx="{x + lean:.1f}" cy="{y - h:.1f}" rx="1.3" ry="2.8" fill="{col}" transform="rotate({lean * 4:.0f} {x + lean:.1f} {y - h:.1f})"/>'
    return s


def waves(x0, y0, x1, y1, n, seed, op=0.45):
    """Wasser: kurze Wellenstriche verteilt über ein Rechteck."""
    r = random.Random(seed)
    s = ""
    for _ in range(n):
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        L = r.uniform(10, 22)
        s += path(f"M{x:.1f} {y:.1f} q{L / 4:.1f} -3 {L / 2:.1f} 0 t{L / 2:.1f} 0", 0.8, op=op)
    return s


def willows(cx, cy, n, spread, seed):
    """Weiden: runde Krone mit hängenden Strichen."""
    r = random.Random(seed)
    s = ""
    for _ in range(n):
        x, y = cx + r.uniform(-spread, spread), cy + r.uniform(-spread * 0.6, spread * 0.6)
        s += path(rough(blob(x, y, 9, 7, irr=0.15, n=10, seed=r.randint(0, 999), a0=180, a1=360), jit=0.6, seg=4, seed=r.randint(0, 999)), 1.1)
        for k in range(4):
            dx = -7 + k * 4.6
            s += path(f"M{x + dx:.1f} {y - 2:.1f} q1 6 {r.uniform(-1, 1):.1f} {r.uniform(9, 13):.1f}", 0.8)
    return s


def house(x, y, w, h, seed, fill="#d9c69e", lw=2.2):
    return path(rough([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], closed=True, jit=1.0, seed=seed), lw, fill=fill)


def piles(x0, x1, y, seed, step=9):
    """Pfahlreihe unter einem Steg oder Haus: kurze senkrechte Striche ins Wasser."""
    r = random.Random(seed)
    s = ""
    x = x0
    while x <= x1:
        s += path(f"M{x:.1f} {y:.1f} l{r.uniform(-0.6, 0.6):.1f} {r.uniform(5, 8):.1f}", 0.9, op=0.75)
        x += step
    return s


def walk(pts, seed, w=10):
    """Bohlensteg: zwei parallele Linien mit Querbohlen."""
    s = ""
    (x1, y1), (x2, y2) = pts
    L = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / L * w / 2, (x2 - x1) / L * w / 2
    s += path(rough([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny)], jit=0.7, seed=seed), 1.3)
    s += path(rough([(x1 - nx, y1 - ny), (x2 - nx, y2 - ny)], jit=0.7, seed=seed + 1), 1.3)
    n = int(L / 7)
    for k in range(1, n):
        t = k / n
        cx, cy = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        s += path(f"M{cx + nx:.1f} {cy + ny:.1f} L{cx - nx:.1f} {cy - ny:.1f}", 0.6, op=0.7)
    return s


def mountain(x, y, w, h, seed):
    s = path(rough([(x - w / 2, y), (x - w / 8, y - h * 0.9), (x, y - h), (x + w / 7, y - h * 0.85), (x + w / 2, y)], jit=1.0, seed=seed), 1.6, fill="#ddcca4")
    r = random.Random(seed)
    for k in range(7):
        t = r.uniform(0.15, 0.85)
        sx = x - w / 2 + w * t
        s += path(f"M{sx:.1f} {y - 3:.1f} l{r.uniform(-4, 4):.1f} {-h * r.uniform(0.2, 0.45):.1f}", 0.8, op=0.6)
    return s


def deadtree(x, y, h, seed, col=INK):
    r = random.Random(seed)
    s = path(rough([(x, y), (x + r.uniform(-3, 3), y - h)], jit=0.8, seg=6, seed=seed), 2.0, col=col)
    for k in range(4):
        by = y - h * r.uniform(0.35, 0.9)
        d = r.choice((-1, 1))
        s += path(f"M{x:.1f} {by:.1f} q{d * 6:.1f} -4 {d * r.uniform(10, 16):.1f} {-r.uniform(6, 12):.1f}", 1.1, col=col)
    return s


def web(cx, cy, rad, seed, op=0.55, spokes=9, rings=4):
    r = random.Random(seed)
    s = ""
    ang = [2 * math.pi * k / spokes + r.uniform(-0.2, 0.2) for k in range(spokes)]
    for a in ang:
        s += path(f"M{cx:.1f} {cy:.1f} L{cx + rad * math.cos(a):.1f} {cy + rad * math.sin(a):.1f}", 0.6, op=op)
    for k in range(1, rings + 1):
        rr = rad * k / (rings + 0.4)
        pts = [(cx + rr * math.cos(a), cy + rr * math.sin(a)) for a in ang]
        d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}" + "".join(
            f" Q{cx + rr * 0.8 * math.cos((a1 + a2) / 2):.1f} {cy + rr * 0.8 * math.sin((a1 + a2) / 2):.1f} {p[0]:.1f} {p[1]:.1f}"
            for (a1, a2, p) in zip(ang, ang[1:] + [ang[0] + 2 * math.pi], pts[1:] + [pts[0]]))
        s += path(d, 0.5, op=op)
    return s


# ---------------- Esgaroth ----------------
def esgaroth():
    s = f'<rect x="0" y="0" width="{W}" height="{H}" fill="{WATER}" opacity="0.4"/>'
    s += waves(10, 10, 790, 590, 150, 1200)
    # Westufer mit Schilf am linken Rand
    shore = [(0, 0), (70, 0), (84, 120), (66, 260), (80, 400), (62, 600), (0, 600)]
    s += path(rough(shore, closed=True, jit=1.4, seed=1201), 1.6, fill="#e3d2ab")
    s += reeds(70, 110, 30, 14, 90, 1202) + reeds(72, 470, 30, 14, 100, 1203) + trees(30, 160, 6, 22, 1204)
    s += label(36, 560, "Westufer", 18, rot=-90)
    # Die Brücke zum Westufer, mit Tor am Stadtende
    s += walk([(76, 300), (236, 300)], 1210, w=12) + piles(84, 232, 307, 1211, step=12)
    gate_col = RED if GM else INK
    s += path(rough([(232, 288), (232, 312)], jit=0.4, seed=1212), 4.0, col=gate_col)
    s += path(rough([(240, 288), (240, 312)], jit=0.4, seed=1213), 4.0, col=gate_col)
    s += label(156, 286, "die Brücke", 18)
    # Stadtplattform
    town = [(240, 156), (300, 146), (380, 152), (470, 140), (548, 146), (596, 204), (600, 300), (592, 430),
            (540, 468), (440, 472), (330, 466), (262, 462), (238, 400), (244, 300)]
    s += path(rough(town, closed=True, jit=1.6, seed=1220), 2.0, fill="#e7d8b4")
    s += piles(250, 590, 468, 1221, step=10)
    # Der Platz mit der Großen Halle
    s += path(rough([(340, 250), (470, 250), (470, 350), (340, 350)], closed=True, jit=0.9, seed=1230), 0.9, dash="3 3")
    s += label(405, 342, "der Platz", 15, col=BROWN)
    s += house(360, 262, 92, 46, 1231, fill="#d9c69e", lw=2.6)
    for k in range(6):
        s += path(f"M{368 + k * 15} 266 l0 38", 0.5, op=0.5)
    s += label(406, 244, "Große Halle", 18)
    # Häuser dicht an dicht, aber nicht über Beschriftungen, Nummern, Platz und Gassen
    keep_out = [(330, 222, 482, 358), (266, 240, 340, 300), (540, 270, 600, 330), (420, 380, 520, 424),
                (240, 290, 262, 312), (250, 426, 500, 462), (376, 196, 436, 232), (560, 196, 610, 232),
                (470, 290, 540, 314), (300, 196, 330, 236)]
    def free(x, y, w, h):
        return all(x + w < a or x > c or y + h < b or y > d for a, b, c, d in keep_out)
    rr = random.Random(1240)
    placed = 0
    for row in range(14):
        y = 162 + row * 21
        x = 252 + rr.uniform(0, 10)
        while x < 580:
            w, h = rr.uniform(13, 22), rr.uniform(10, 14)
            xx, yy = x, y + rr.uniform(-3, 3)
            inside = 248 < xx and xx + w < 590 and 156 < yy and yy + h < 456
            if inside and free(xx, yy, w, h) and rr.random() < 0.8:
                s += house(xx, yy, w, h, 1300 + placed, lw=1.1)
                placed += 1
            x += w + rr.uniform(3, 9)
    # Gasse der Netzflicker (Süden) und Halvars Haus
    s += path(rough([(270, 434), (500, 440)], jit=1.0, seed=1250), 0.8, dash="2 3")
    s += label(380, 458, "Gasse der Netzflicker", 15, col=BROWN)
    for k in range(4):
        s += path(f"M{290 + k * 40} 444 l14 0 M{290 + k * 40} 449 l14 0", 0.6, op=0.7)
    s += house(430, 394, 24, 18, 1255, fill="#cdb78c", lw=1.8)
    if GM:
        s += label(462, 408, "Halvars Haus", 14, anchor="start", col=RED)
    # Totenhaus nahe der Halle (Westseite)
    s += house(282, 262, 36, 26, 1256, lw=1.6)
    s += label(300, 254, "Totenhaus", 14)
    # Brückentor über der Stadt beschriften
    s += label(204, 334, "Brückentor", 15, col=gate_col)
    # Hafenbecken im Osten mit Kette
    s += path(rough([(600, 210), (700, 200), (720, 260)], jit=1.0, seed=1260), 3.0)
    s += path(rough([(590, 420), (700, 440), (724, 380)], jit=1.0, seed=1261), 3.0)
    s += piles(604, 700, 214, 1262) + piles(596, 700, 436, 1263)
    chain_col = RED if GM else INK
    s += path(rough([(720, 262), (724, 378)], jit=2.6, seg=6, seed=1264), 1.6, col=chain_col, dash="2 4")
    s += label(744, 322, "Hafenkette", 15, rot=90, col=chain_col)
    s += label(650, 330, "Hafen", 20, col=BROWN)
    for k, (bx, by) in enumerate([(630, 270), (660, 380), (640, 300)]):
        s += path(rough([(bx - 16, by), (bx + 16, by), (bx + 9, by + 8), (bx - 9, by + 8)], closed=True, jit=0.6, seg=6, seed=1265 + k), 1.2, fill="#cdb78c")
    s += house(556, 296, 30, 22, 1268, lw=1.6) + label(571, 288, "Hafenwache", 14)
    # Turm mit den Raben
    s += f'<circle cx="590" cy="214" r="8" fill="#d9c69e" stroke="{INK}" stroke-width="1.6"/>'
    s += label(604, 188, "Rabenturm", 14, anchor="start")
    # Flößerkai im Norden mit Floß
    s += walk([(420, 140), (420, 70)], 1270, w=10) + piles(412, 428, 130, 1271, step=8)
    s += path(rough([(436, 60), (520, 56), (522, 84), (438, 88)], closed=True, jit=0.8, seed=1272), 1.3, fill="#cdb78c")
    for k in range(8):
        s += path(f"M{444 + k * 10} 62 l1 22", 0.7)
    s += label(530, 78, "Flößerkai", 15, anchor="start")
    if GM:
        s += num(406, 212, 1) + num(262, 432, 2) + num(442, 372, 3) + num(586, 318, 4) + num(316, 216, 5) + num(392, 92, 6)
    s += compass(735, 520)
    s += cartouche(28, 24, "Esgaroth", "die Seestadt, Winterfilth TA 2966" if GM else "auf dem Langen See", 270)
    s += label(772, 588, "Skizze für den Loremaster · nicht maßstabsgetreu" if GM else "nach einer Zeichnung der Hafenwache", 15, anchor="end", col=BROWN)
    return frame(s, 71)


# ---------------- Der Lange See (nur Spieler) ----------------
def see():
    s = ""
    MI = 28  # Karteneinheiten je Meile: Esgaroth – Mündung etwa 5 Meilen
    lake = [(330, 110), (420, 96), (520, 120), (560, 200), (590, 320), (620, 450), (640, 600),
            (330, 600), (350, 470), (318, 360), (300, 300), (312, 220)]
    s += path(rough(lake, closed=True, jit=2.2, seed=1300), 1.8, fill=WATER, op=0.55)
    s += waves(340, 150, 600, 590, 80, 1301)
    s += label(470, 470, "Der Lange See", 30, col=BROWN, rot=72)
    # Lonely Mountain und River Running
    s += mountain(610, 104, 170, 62, 1310) + label(610, 34, "Erebor", 22)
    s += path(rough([(596, 106), (566, 116), (520, 118)], jit=1.0, seed=1311), 1.2)
    s += path(rough([(606, 108), (574, 126), (530, 128)], jit=1.0, seed=1312), 1.2)
    s += label(574, 160, "River Running", 17, anchor="start")
    for k, (x, y) in enumerate([(720, 120), (732, 114), (742, 124)]):
        s += house(x - 5, y - 4, 10, 8, 1315 + k, lw=1.1)
    s += label(732, 150, "Dale", 17)
    # Forest River von Westen, Mündung, Langsümpfe
    s += path(rough([(0, 186), (110, 200), (220, 190), (306, 210)], jit=1.4, seed=1320), 1.4)
    s += path(rough([(0, 204), (110, 218), (220, 208), (304, 226)], jit=1.4, seed=1321), 1.4)
    s += label(130, 182, "Forest River", 18)
    marsh = blob(255, 300, 60, 70, irr=0.18, n=26, seed=1322)
    s += path(rough(marsh, closed=True, jit=1.2, seed=1323), 0.8, fill=WATER, op=0.35, dash="3 3")
    s += reeds(260, 300, 90, 55, 65, 1324) + reeds(300, 190, 30, 30, 20, 1325)
    s += label(232, 400, "Langsümpfe", 20)
    # Mirkwood im Westen
    for k in range(5):
        s += trees(70 + (k % 2) * 40, 260 + k * 60, 12, 40, 1330 + k)
    s += trees(100, 120, 10, 50, 1336)
    s += label(64, 450, "Mirkwood", 28, rot=-90, col=BROWN)
    # Esgaroth mit Brücke zum Westufer
    s += path(rough([(396, 290), (436, 286), (442, 316), (400, 320)], closed=True, jit=0.8, seed=1340), 1.6, fill="#e3d2ab")
    for k, (x, y) in enumerate([(406, 296), (420, 300), (412, 310), (428, 306)]):
        s += house(x - 4, y - 3, 8, 6, 1341 + k, lw=1.0)
    s += walk([(318, 305), (396, 304)], 1345, w=6)
    s += label(450, 288, "Esgaroth", 22, anchor="start")
    # Straße nach Süden vom Brückenkopf
    s += path(rough([(318, 305), (300, 400), (316, 520), (300, 600)], jit=1.2, seed=1346), 0.9, dash="4 4")
    s += label(286, 540, "nach Süden", 15, rot=-84)
    # Wo das Licht stand
    s += f'<circle cx="244" cy="248" r="18" fill="url(#pale)"/>'
    s += path("M236 240 L252 256 M252 240 L236 256", 1.8)
    s += label(200, 236, "hier stand das Licht", 16, anchor="end")
    # Maßstab
    x0, y0 = 470, 560
    s += path(f"M{x0} {y0} L{x0 + 5 * MI} {y0}", 1.6)
    for m in (0, 1, 2, 3, 4, 5):
        s += path(f"M{x0 + m * MI} {y0 - 5} L{x0 + m * MI} {y0 + 5}", 1.2)
    for m in (0, 5):
        s += label(x0 + m * MI, y0 + 22, f"{m}", 15)
    s += label(x0 + 5 * MI + 10, y0 + 5, "Meilen", 15, anchor="start")
    s += compass(745, 470)
    s += cartouche(28, 24, "Der Lange See", "Esgaroth, die Langsümpfe und der Saum von Mirkwood", 380)
    return frame(s, 83)


# ---------------- Das Nest ----------------
def nest():
    s = ""
    # Priel am unteren Rand, Schlammufer
    s += path(rough([(0, 470), (200, 490), (420, 476), (640, 500), (800, 488), (800, 600), (0, 600)], closed=True, jit=1.6, seed=1400), 1.5, fill=WATER, op=0.55)
    s += waves(20, 510, 780, 590, 40, 1401)
    s += reeds(120, 470, 50, 120, 14, 1402) + reeds(680, 480, 40, 110, 14, 1403)
    # Senke
    hollow = blob(400, 290, 230, 150, irr=0.1, n=30, seed=1410)
    s += path(rough(hollow, closed=True, jit=1.4, seed=1411), 1.3, dash="6 4")
    s += hachures(hollow + [hollow[0]], out=False, length=10, seed=1412, w=0.8)
    # Tote Erlen rund um die Senke
    rr = random.Random(1420)
    for k in range(18):
        a = 2 * math.pi * k / 18 + rr.uniform(-0.1, 0.1)
        x, y = 400 + 270 * math.cos(a) * rr.uniform(0.9, 1.1), 290 + 185 * math.sin(a) * rr.uniform(0.9, 1.1)
        if y < 470:
            s += deadtree(x, y, rr.uniform(26, 40), 1421 + k)
    # Gespinst über der Senke
    s += web(400, 250, 150, 1430, op=0.35, spokes=12, rings=5)
    s += web(250, 180, 60, 1431, op=0.4) + web(560, 200, 70, 1432, op=0.4)
    # Die beiden Erlen mit den Kokons
    s += deadtree(330, 330, 120, 1440) + deadtree(470, 330, 120, 1441)
    s += path(rough([(334, 236), (468, 232)], jit=0.8, seed=1442), 0.9)
    for k, (x, rx, ry, glow) in enumerate([(360, 9, 18, False), (400, 11, 20, True), (438, 7, 13, False)]):
        s += path(f"M{x} 234 L{x} 248", 0.8)
        if glow:
            s += f'<circle cx="{x}" cy="{268}" r="26" fill="url(#pale)"/>'
        s += f'<ellipse cx="{x}" cy="{268}" rx="{rx}" ry="{ry}" fill="#e9e3d4" stroke="{INK}" stroke-width="1.3"/>'
        for j in range(4):
            s += path(f"M{x - rx} {256 + j * 7} q{rx} 4 {2 * rx} 0", 0.5, op=0.7)
    s += label(400, 312, "Kokons", 17)
    if GM:
        s += label(352, 222, "Halvar", 13, col=RED) + label(400, 222, "Stein", 13, col=RED) + label(448, 222, "Signy", 13, col=RED)
    # Brutkammer: hohler Stumpf
    s += f'<circle cx="560" cy="350" r="22" fill="#cdb78c" stroke="{INK}" stroke-width="2"/><circle cx="560" cy="350" r="10" fill="#7a6a4a" opacity="0.7"/>'
    s += label(560, 316, "hohler Stumpf", 15)
    # Schilfpfad von links unten
    s += path(rough([(40, 600), (120, 520), (190, 440), (250, 380)], jit=1.0, seed=1450), 1.0, dash="2 4")
    s += label(150, 556, "Schilfpfad", 16, rot=-42)
    # Erlensteg über den Priel rechts
    s += path(rough([(700, 520), (640, 430)], jit=0.6, seed=1451), 5.0, col="#8a6a3a")
    s += path(rough([(700, 520), (640, 430)], jit=0.6, seed=1452), 1.2)
    s += label(700, 414, "umgestürzte Erle", 15, anchor="middle")
    # Ufer
    s += label(400, 545, "Priel", 18, col=BROWN)
    if GM:
        s += num(206, 432, 1) + num(674, 474, 2) + num(400, 196, 3) + num(516, 362, 4) + num(300, 478, 5) + num(110, 176, 6)
        s += path(rough([(330, 240), (250, 190), (150, 150), (60, 110)], jit=1.0, seed=1460), 1.2, dash="4 4", col=RED)
        s += label(140, 112, "Fluchtweg in die Kronen", 15, col=RED)
        s += path(rough([(160, 455), (186, 450), (210, 446)], jit=0.4, seed=1461), 0.8, col=RED)
        s += label(150, 438, "Stolperfäden", 13, anchor="middle", col=RED)
    s += compass(735, 92)
    s += cartouche(28, 24, "Das Nest", "am Saum von Mirkwood, Winterfilth TA 2966", 330)
    s += label(772, 588, "Skizze für den Loremaster · nicht maßstabsgetreu", 15, anchor="end", col=BROWN)
    return frame(s, 97)


# ---------------- Routendiagramm (Überblick) ----------------
def route():
    """Senkrechter Stapel der Stationen, Zeiten an den Pfeilen, Höhepunkt rot,
    Skirfirs Verfolgung gestrichelt rot. Sauber gezeichnet, nicht von Hand."""
    font = "font-family=\"TeX Gyre Pagella\""
    grey, line, red, ink = "#6f665c", "#9a9088", "#7a2a1f", "#2b2420"
    bw, bh, gap, x0, top = 250, 40, 22, 40, 12
    stages = [("Die Halle am See", "Fest · Finsternis · Hornboris Tod"),
              ("Der Eid", "in eigenen Worten · Rabe nach Erebor"),
              ("Die Spur", "Knoten · Schuh · Licht am Westufer"),
              ("Der Kai", "Rat · Elben · stehlen oder nehmen"),
              ("Die Überfahrt", "See · Langsümpfe · Stimme im Schilf"),
              ("Das Nest", "zwei Uhren · Stein oder Gefangene"),
              ("Rechenschaft", "vor Skirfir, Hornboris Sohn")]
    legs = ["dieselbe Nacht", "Tag 2", "Abend, Tag 2", "Nacht oder Morgen", "Dämmerung, Tag 3", "Heimkehr"]
    Hs = top * 2 + len(stages) * bh + (len(stages) - 1) * gap
    Ws = 420
    cx = x0 + bw / 2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Ws} {Hs}" width="{Ws * 4}" height="{Hs * 4}">',
           '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
           f'<path d="M0 0L10 5L0 10z" fill="{line}"/></marker>'
           '<marker id="r" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
           f'<path d="M0 0L10 5L0 10z" fill="{red}"/></marker></defs>',
           f'<rect width="{Ws}" height="{Hs}" fill="#ffffff"/>']
    ys = [top + i * (bh + gap) for i in range(len(stages))]
    for i, ((name, sub), y) in enumerate(zip(stages, ys)):
        climax = name == "Das Nest"
        out.append(f'<rect x="{x0}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{"#f6e7e3" if climax else "#f7f1e6"}" '
                   f'stroke="{red if climax else line}" stroke-width="{1.8 if climax else 1.1}"/>')
        out.append(f'<text x="{cx}" y="{y + 17}" {font} font-weight="700" font-size="13.5" fill="{red if climax else ink}" text-anchor="middle">{name}</text>')
        out.append(f'<text x="{cx}" y="{y + 32}" {font} font-size="10.5" fill="{grey}" text-anchor="middle">{sub}</text>')
        if i < len(legs):
            out.append(f'<path d="M{cx} {y + bh} V{y + bh + gap - 2}" stroke="{line}" stroke-width="1.2" marker-end="url(#a)"/>')
            out.append(f'<text x="{cx + 8}" y="{y + bh + gap / 2 + 4}" {font} font-style="italic" font-size="10.5" fill="{grey}">{legs[i]}</text>')
    y1, y5 = ys[1] + bh / 2, ys[5] + bh / 2
    px = x0 + bw + 50
    out.append(f'<path d="M{x0 + bw} {y1} H{px} V{y5} H{x0 + bw + 3}" fill="none" stroke="{red}" stroke-width="1.2" stroke-dasharray="5 4" marker-end="url(#r)"/>')
    out.append(f'<text x="{px + 8}" y="{(y1 + y5) / 2 - 4}" {font} font-style="italic" font-size="11" fill="{red}">Skirfir</text>')
    out.append(f'<text x="{px + 8}" y="{(y1 + y5) / 2 + 10}" {font} font-style="italic" font-size="11" fill="{red}">folgt</text>')
    out.append("</svg>")
    return "\n".join(out), Ws * 4, Hs * 4


if __name__ == "__main__":
    os.makedirs(SVG, exist_ok=True)
    jobs = []
    for gm in (True, False):
        GM = gm
        suf = "" if gm else "-players"
        jobs.append(("map-esgaroth" + suf, esgaroth()))
    GM = True
    jobs.append(("map-nest", nest()))
    GM = False
    jobs.append(("map-see-players", see()))
    from PIL import Image
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W * 2, "height": H * 2})
        for name, svg in jobs:
            open(SVG + name + "-de.svg", "w").write(svg)
            pg.set_content(f'<html><body style="margin:0;background:#fff">{svg}</body></html>', wait_until="load")
            pg.screenshot(path=D + name + "-de.png", clip={"x": 0, "y": 0, "width": W * 2, "height": H * 2})
        svg, rw, rh = route()
        open(os.path.join(ROOT, "assets", "route-de.svg"), "w").write(svg)
        pg.set_viewport_size({"width": rw, "height": rh})
        pg.set_content(f'<html><body style="margin:0;background:#fff">{svg}</body></html>', wait_until="load")
        pg.screenshot(path=os.path.join(ROOT, "assets", "route-de.png"), clip={"x": 0, "y": 0, "width": rw, "height": rh})
        b.close()
    for name, _ in jobs:
        Image.open(D + name + "-de.png").convert("RGB").save(D + name + "-de.jpg", quality=88)
        os.remove(D + name + "-de.png")
    print("ok")
