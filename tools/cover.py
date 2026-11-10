#!/usr/bin/env python3
"""Malt das Titelbild von „Nachtfall in Esgaroth“: Nacht über dem Langen See, Esgaroth auf
seinen Pfählen, über der Großen Halle eine schwarze Finsternis, die die Lampen frisst. Am
fernen Westufer ein bleiches Licht im Schilf, darüber der dunkle Saum von Mirkwood, im
Norden der Lonely Mountain. Vorn ein Boot mit vier Zwergen, das auf das Licht zuhält.
Rein prozedural (numpy, OpenCV), anschließend malerisch nachbearbeitet.
Helfer (noise, blend, poly_mask, strokes) übernommen aus tools/cover.py von Graufieber.

    python3 tools/cover.py            # -> assets/cover-de.jpg
"""
import os
import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "cover-de.jpg")
W, H = 2400, 1600
HZ = int(H * 0.53)                      # Horizont (Seeufer)
rng = np.random.default_rng(29)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def C(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def noise(scale, octaves=5, seed=0, w=W, h=H, pers=0.5, stretch=1.0):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        cw = max(2, int(w / scale * 2 ** o / stretch)); ch = max(2, int(h / scale * 2 ** o))
        out += amp * cv2.resize(r.random((ch, cw)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp; amp *= pers
    out /= tot
    return np.clip((out - out.min()) / (out.max() - out.min() + 1e-6), 0, 1)


def lerp(a, b, t):
    return a + (b - a) * t


def blend(img, col, mask):
    return img * (1 - mask[..., None]) + col * mask[..., None]


def poly_mask(polys, ss=2):
    m = np.zeros((H * ss, W * ss), np.uint8)
    for p in polys:
        cv2.fillPoly(m, [np.round(np.array(p) * ss).astype(np.int32)], 255, cv2.LINE_AA)
    return cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255


img = np.zeros((H, W, 3), np.float32)

# ======================= Himmel =======================
t = np.clip(yy / HZ, 0, 1)
sky = lerp(C("#141c25"), C("#2a3946"), np.clip(t / 0.7, 0, 1)[..., None])
sky = lerp(sky, C("#4a5864"), np.clip((t - 0.7) / 0.3, 0, 1)[..., None] ** 1.4)
# verhangener Mond hinter den Wolken, oben links
moon = np.exp(-(((xx - W * 0.30) / 260) ** 2 + ((yy - H * 0.13) / 200) ** 2))
sky = blend(sky, C("#7d8f9a"), np.clip(moon * 0.55, 0, 1))
c1 = noise(600, 6, 1, stretch=3.0); c2 = noise(240, 6, 2, stretch=3.5)
clouds = np.clip((0.65 * c1 + 0.35 * c2 - 0.42) * 2.6, 0, 1)
sky = blend(sky, C("#080b10"), clouds * 0.75)
rim = np.clip((0.65 * c1 + 0.35 * c2 - 0.38) * 6, 0, 1) * (1 - clouds)
sky = blend(sky, C("#4a5866"), rim * 0.25 * (1 - t))
# Sterne in den Wolkenlücken
for k in range(420):
    sx, sy = int(rng.random() * W), int(rng.random() * HZ * 0.85)
    if clouds[sy, sx] < 0.15:
        b = rng.random() ** 3
        cv2.circle(sky, (sx, sy), 1 if b < 0.85 else 2, (C("#d8e2e8") * (0.4 + 0.6 * b)).tolist(), -1, cv2.LINE_AA)
img[:HZ] = sky[:HZ]

# ======================= Lonely Mountain (fern, rechts) =======================
mx = W * 0.80
ml = HZ - 6 - 330 * np.clip(1 - np.abs(np.arange(W) - mx) / (W * 0.30), 0, 1) ** 1.25
ml -= 18 * noise(80, 3, 4, w=W, h=1)[0] * (ml < HZ - 20)
mm = ((yy > ml[None, :]) & (yy <= HZ)).astype(np.float32)
img = blend(img, C("#1c242b"), mm * 0.9)
img = blend(img, C("#3a4652"), mm * np.clip((ml[None, :] + 40 - yy) / 40, 0, 1) * 0.35)

# ======================= Westufer und Mirkwood (links) =======================
fl = HZ - 70 - 60 * noise(400, 4, 5, w=W, h=1)[0] - 26 * noise(30, 3, 6, w=W, h=1)[0]
fl = np.where(np.arange(W) < W * 0.42, fl, HZ - 8 + 0 * fl)
fl = np.minimum(fl, HZ - 8 - np.clip(W * 0.42 - np.arange(W), 0, None) * 0.0)
taper = np.clip((W * 0.46 - np.arange(W)) / (W * 0.10), 0, 1)
fl = HZ - 8 - (HZ - 8 - fl) * taper
fm = ((yy > fl[None, :]) & (yy <= HZ)).astype(np.float32)
img = blend(img, C("#0b1013"), fm * 0.96)
# Baumspitzen
for k in range(260):
    tx = rng.random() * W * 0.44
    ty = fl[int(tx)] + 4
    th = 30 + 70 * rng.random() * (1 - tx / (W * 0.5))
    tw = th * 0.28
    cv2.fillPoly(img, [np.array([[tx - tw, ty], [tx, ty - th], [tx + tw, ty]], np.int32)], C("#0b1013").tolist(), cv2.LINE_AA)

# ======================= Das bleiche Licht im Schilf =======================
lx, ly = W * 0.22, HZ - 10
gl = np.exp(-(((xx - lx) / 70) ** 2 + ((yy - ly) / 48) ** 2))
gl2 = np.exp(-(((xx - lx) / 420) ** 2 + ((yy - ly) / 220) ** 2))
img = blend(img, C("#2c3d48"), np.clip(gl2 * 0.55, 0, 1))
img = blend(img, C("#cfe4ea"), np.clip(gl * 1.2, 0, 1))
cv2.circle(img, (int(lx), int(ly)), 7, C("#f2fbff").tolist(), -1, cv2.LINE_AA)

# ======================= Wasser =======================
refl = cv2.resize(img[:HZ][::-1], (W, H - HZ))
refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=2, sigmaY=16)
water = refl * 0.55 + C("#0e151b") * 0.45
rip = cv2.resize(noise(20, 3, 21, w=W // 2, h=(H - HZ) // 10), (W, H - HZ))
water *= (0.85 + 0.30 * rip[..., None])
img[HZ:] = water
# Lichtbahn des bleichen Lichts auf dem Wasser
lb = np.exp(-((xx - lx) / (20 + (yy - HZ).clip(0) * 0.20)) ** 2) * (yy > HZ) * np.exp(-((yy - HZ) / (H * 0.30)))
lbn = cv2.resize(noise(10, 2, 23, w=W // 3, h=H // 28), (W, H))
img = blend(img, C("#b9d3da"), np.clip(lb * (0.2 + 0.8 * lbn) * 0.85, 0, 1))
# Wellenglanz
for k in range(520):
    wy = int(HZ + (H - HZ) * rng.random() ** 1.6)
    wx = int(W * rng.random()); wl = int(10 + 120 * (wy - HZ) / (H - HZ) * rng.random() + 6)
    c = C("#3d505c") if rng.random() < 0.6 else C("#05080b")
    cv2.line(img, (wx, wy), (wx + wl, wy), c.tolist(), 1, cv2.LINE_AA)

# Schilf am fernen Ufer um das Licht
for k in range(360):
    rx = lx + rng.normal(0, 260)
    if rx < 0 or rx > W * 0.5:
        continue
    ry = HZ + rng.random() * 14
    rh = 20 + 50 * rng.random()
    cv2.line(img, (int(rx), int(ry)), (int(rx + rng.normal(0, 4)), int(ry - rh)), C("#06090b").tolist(), 2, cv2.LINE_AA)

# ======================= Esgaroth auf Pfählen (Mitte rechts) =======================
base = int(HZ + 120)
ex0, ex1 = W * 0.47, W * 0.93
r2 = np.random.default_rng(11)
houses, wins = [], []
x = ex0
while x < ex1:
    w_ = r2.uniform(50, 110); h_ = r2.uniform(46, 90); roof = r2.uniform(26, 52)
    yb = base - r2.uniform(0, 6)
    houses.append([(x, yb), (x, yb - h_), (x + w_ / 2, yb - h_ - roof), (x + w_, yb - h_), (x + w_, yb)])
    if r2.random() < 0.55:
        wins.append((x + r2.uniform(10, w_ - 14), yb - r2.uniform(14, h_ - 10)))
    x += w_ + r2.uniform(-18, 6)
# Große Halle
hx = W * 0.64
hall = [(hx, base), (hx, base - 130), (hx + 170, base - 230), (hx + 340, base - 130), (hx + 340, base)]
deck = [(ex0 - 30, base), (ex1 + 30, base), (ex1 + 30, base + 18), (ex0 - 30, base + 18)]
town = poly_mask(houses + [hall, deck])
pil = np.zeros((H, W), np.float32)
px = ex0 - 20
while px < ex1 + 20:
    cv2.line(pil, (int(px), base + 18), (int(px + r2.normal(0, 2)), base + 80), 1.0, 5, cv2.LINE_AA)
    px += r2.uniform(26, 44)
town = np.maximum(town, pil)
# Brücke nach links zum Westufer
bridge = poly_mask([[(W * 0.30, base + 2), (ex0, base - 2), (ex0, base + 12), (W * 0.30, base + 18)]])
bpx = W * 0.31
while bpx < ex0:
    cv2.line(bridge, (int(bpx), base + 12), (int(bpx), base + 60), 1.0, 4, cv2.LINE_AA)
    bpx += 48
town = np.maximum(town, bridge)
img = blend(img, C("#06080a"), town * 0.97)
# Lampen: rechts noch an, über der Halle von der Finsternis verschluckt
glow = np.zeros((H, W), np.float32)
for wx, wy in wins:
    if abs(wx - (hx + 170)) < 330:
        continue
    cv2.rectangle(img, (int(wx), int(wy)), (int(wx + 6), int(wy + 9)), C("#f0b45c").tolist(), -1)
    cv2.circle(glow, (int(wx + 3), int(wy + 4)), 8, 1.0, -1)
img = blend(img, C("#d58a3c"), np.clip(cv2.GaussianBlur(glow, (0, 0), 18) * 2.4, 0, 1))
# Spiegelung der Lampen
gr = cv2.GaussianBlur(glow, (0, 0), 6)
grf = np.zeros_like(gr)
grf[base + 30:] = gr[base - (H - base - 30):base][::-1][:H - base - 30]
grf = cv2.GaussianBlur(grf, (0, 0), sigmaX=4, sigmaY=30)
img = blend(img, C("#c07a34"), np.clip(grf * 1.6 * (yy > base + 20), 0, 1))

# ======================= Die Finsternis über der Halle =======================
# kriechender schwarzer Dunst: flach, breit, aus der Halle über Dächer und Wasser
fn = noise(140, 5, 40, stretch=2.4)
fn2 = noise(50, 4, 41, stretch=1.6)
cxh, cyh = hx + 170, base - 120
core = np.exp(-(((xx - cxh) / 360) ** 2 + ((yy - cyh) / 150) ** 2))
spread = np.exp(-(((xx - cxh) / 900) ** 2 + ((yy - (base + 10)) / 90) ** 2))
rise = np.exp(-(((xx - cxh - 0.25 * (cyh - yy).clip(0)) / (220 + 0.6 * (cyh - yy).clip(0))) ** 2)) * np.clip(1 - (cyh - yy) / 520, 0, 1) * (yy < cyh)
dens = np.maximum(np.maximum(core, spread * 0.8), rise * 0.8)
dark = np.clip(dens * (0.65 + 1.0 * (0.6 * fn + 0.4 * fn2)) - 0.05, 0, 1)
dark = cv2.GaussianBlur(dark, (0, 0), 6)
img = blend(img, C("#010203"), dark * 0.96)
# kalter Rand, wo der Dunst die Lampen erstickt
dedge = np.clip(cv2.GaussianBlur(dark, (0, 0), 14) - dark, 0, 1)
img = blend(img, C("#3b4b56"), np.clip(dedge * 2.0, 0, 1) * 0.35)

# ======================= Boot mit vier Zwergen (vorn) =======================
bx, by = W * 0.42, H * 0.86
# Bug nach links, zum Licht
hull = [(bx + 260, by - 30), (bx - 230, by - 36), (bx - 300, by - 72), (bx - 250, by + 14), (bx + 220, by + 22), (bx + 290, by - 50)]
figs = poly_mask([hull])
fig_mask = np.zeros((H, W), np.float32)
for k, fx in enumerate((bx - 160, bx - 50, bx + 60, bx + 170)):
    fy = by - 40
    hood = [(fx - 34, fy), (fx - 30, fy - 62), (fx - 18, fy - 94), (fx - 4, fy - 108), (fx + 16, fy - 96), (fx + 32, fy - 60), (fx + 36, fy)]
    cv2.fillPoly(fig_mask, [np.array(hood, np.int32)], 1.0, cv2.LINE_AA)
    if k == 0:  # der Vorderste hält die Axt
        cv2.line(fig_mask, (int(fx - 6), int(fy - 60)), (int(fx - 60), int(fy - 160)), 1.0, 6, cv2.LINE_AA)
        cv2.fillPoly(fig_mask, [np.array([(fx - 60, fy - 160), (fx - 92, fy - 170), (fx - 86, fy - 136), (fx - 50, fy - 140)], np.int32)], 1.0, cv2.LINE_AA)
# Ruder, je eins an jeder Seite, schräg nach hinten ins Wasser
for ox, ex in ((bx + 10, bx + 150), (bx + 120, bx + 260)):
    cv2.line(fig_mask, (int(ox), int(by - 50)), (int(ex), int(by + 60)), 1.0, 6, cv2.LINE_AA)
figs = np.maximum(figs, fig_mask)
img = blend(img, C("#030405"), figs * 0.98)
# kalter Saum vom Licht links an den Gestalten
fedge = np.clip(figs - np.roll(figs, 4, axis=1), 0, 1)
img = blend(img, C("#7f9aa4"), fedge * 0.55)
# Kielwasser
for k in range(30):
    wy = int(by + 20 + rng.random() * 40)
    wx = int(bx + 220 + rng.random() * 420)
    cv2.line(img, (wx, wy), (wx + int(20 + 60 * rng.random()), wy + int(rng.normal(0, 3))), C("#2a3a44").tolist(), 2, cv2.LINE_AA)

# ======================= Malerische Nachbearbeitung =======================
img = np.clip(img, 0, 1)


def strokes(src, n, length, width, seed, protect):
    """Pinselstriche entlang der Bildstruktur (Strukturtensor), Farbe aus dem geglätteten Bild."""
    r = np.random.default_rng(seed)
    g = cv2.cvtColor((src * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx_ = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=5); gy_ = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=5)
    jxx = cv2.GaussianBlur(gx_ * gx_, (0, 0), 9); jyy = cv2.GaussianBlur(gy_ * gy_, (0, 0), 9); jxy = cv2.GaussianBlur(gx_ * gy_, (0, 0), 9)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-3)
    smooth = cv2.GaussianBlur(src, (0, 0), width * 0.5)
    canvas = src.copy()
    for _ in range(n):
        x, y = int(r.random() * W), int(r.random() * H)
        if protect[y, x] > 0.2:
            continue
        a = theta[y, x] if coh[y, x] > 0.25 else 0.0
        L = length * r.uniform(0.6, 1.3)
        dx, dy = np.cos(a) * L / 2, np.sin(a) * L / 2
        col = smooth[y, x] * r.uniform(0.94, 1.06)
        cv2.line(canvas, (int(x - dx), int(y - dy)), (int(x + dx), int(y + dy)), col.tolist(), int(max(1, width * r.uniform(0.7, 1.2))), cv2.LINE_AA)
    return canvas


light = np.clip(gl * 3, 0, 1)
protect = np.clip(cv2.dilate(np.maximum(np.maximum(figs, town), light), np.ones((9, 9), np.uint8)), 0, 1)
img = strokes(img, 150000, 26, 7, 91, protect)
img = lerp(img, strokes(img, 200000, 12, 3, 92, protect), 0.7)
u8 = (img * 255).astype(np.uint8)
try:
    paint = cv2.xphoto.oilPainting(cv2.cvtColor(u8, cv2.COLOR_RGB2BGR), 6, 1, cv2.COLOR_BGR2Lab)
    paint = cv2.cvtColor(paint, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
except AttributeError:  # ohne opencv-contrib
    paint = cv2.bilateralFilter(img, 9, 0.1, 6)
detail = np.maximum(np.maximum(figs, town), light)
p = lerp(paint, img, np.clip(0.30 + 0.55 * cv2.GaussianBlur(detail, (0, 0), 3), 0, 1)[..., None])
cv = noise(3, 2, 60) - 0.5
p *= (1 + 0.035 * cv[..., None])
lum = p.mean(axis=2, keepdims=True)
p = lerp(lum, p, 0.85)
p += (C("#101c24") - lum) * (1 - lum) * 0.10 + (C("#e6f0f0") - lum) * lum ** 2 * 0.08
p = np.clip(p * 1.12, 0, 1) ** 0.95
v = 1 - 0.50 * (((xx - W * 0.45) / (W * 0.66)) ** 2 + ((yy - H * 0.55) / (H * 0.80)) ** 2)
p *= np.clip(v, 0.35, 1)[..., None]
p += rng.normal(0, 0.010, p.shape).astype(np.float32)
out = (np.clip(p, 0, 1) * 255).astype(np.uint8)
cv2.imwrite(OUT, cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
print("ok", OUT)
