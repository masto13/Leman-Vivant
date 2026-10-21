"""Dessine les icônes de l'app (silhouette du Léman) en PNG, sans dépendance externe.

Usage : python3 outils/icones.py   → écrit docs/icons/*.png
"""
import json, math, os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "docs", "icons")
LAKE = json.load(open(os.path.join(HERE, "data", "lake_pts.json")))

BG = (46, 122, 123)      # turquoise du Léman (accent de l'app)
FG = (243, 245, 239)     # silhouette claire


def png(path, size, pixels):
    raw = b"".join(b"\x00" + bytes(row) for row in pixels)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(data)


def draw(size, margin):
    kx = math.cos(math.radians(46.37))
    pts = [((lon - 6.14) * kx, -(lat - 46.36)) for lon, lat in LAKE]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    s = size * (1 - 2 * margin) / max(w, h)
    ox = (size - w * s) / 2 - min(xs) * s
    oy = (size - h * s) / 2 - min(ys) * s
    poly = [(x * s + ox, y * s + oy) for x, y in pts]
    ss = 4  # suréchantillonnage pour des bords lisses
    rows = []
    for py in range(size):
        cover = [0] * size
        for sub in range(ss):
            y = py + (sub + 0.5) / ss
            xs_hit = []
            for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
                if (y1 <= y < y2) or (y2 <= y < y1):
                    xs_hit.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xs_hit.sort()
            for a, b in zip(xs_hit[::2], xs_hit[1::2]):
                for px in range(max(0, int(a)), min(size, int(b) + 1)):
                    left, right = max(a, px), min(b, px + 1)
                    if right > left:
                        cover[px] += (right - left) / ss
        row = []
        for c in cover:
            c = min(1, c)
            row += [round(BG[i] + (FG[i] - BG[i]) * c) for i in range(3)]
        rows.append(row)
    return rows


os.makedirs(OUT, exist_ok=True)
for name, size, margin in [("icon-192.png", 192, 0.12), ("icon-512.png", 512, 0.12),
                           ("maskable-512.png", 512, 0.22), ("apple-touch-icon.png", 180, 0.14)]:
    png(os.path.join(OUT, name), size, draw(size, margin))
    print("écrit", name)


# ---------- image d'aperçu pour les partages (1200 × 630) ----------
def apercu(path, W=1200, H=630):
    import random
    hexc = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    SKY_T, SKY_B = hexc("#d6e6e3"), hexc("#eef3ef")
    R1, R2, R3, SNOW, EAU, ACC = (hexc(c) for c in ("#c3d3d4", "#9db6b9", "#6f9095", "#f7faf8", "#c5dcd8", "#2e7a7b"))

    def ridge(seed, base, amp, rough, n=11):
        rnd = random.Random(seed).random
        pts = [(i * W / n, base - amp * (0.25 + 0.75 * rnd())) for i in range(n + 1)]
        spread = amp * 0.7
        for _ in range(7):
            nxt = []
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                nxt += [(x1, y1), ((x1 + x2) / 2, (y1 + y2) / 2 + (rnd() - 0.55) * spread)]
            pts = nxt + [pts[-1]]; spread *= rough
        ys = []
        j = 0
        for x in range(W):
            while pts[j + 1][0] < x: j += 1
            (x1, y1), (x2, y2) = pts[j], pts[j + 1]
            ys.append(y1 + (y2 - y1) * (x - x1) / (x2 - x1))
        return ys

    h1, h2, h3 = ridge(9871, 500, 150, .55), ridge(4242, 530, 95, .52), ridge(777, 556, 40, .5)
    lake_top = 555
    # silhouette du Léman dans le ciel
    kx = math.cos(math.radians(46.37))
    pts = [((lon - 6.14) * kx, -(lat - 46.36)) for lon, lat in LAKE]
    xs, ys_ = [p[0] for p in pts], [p[1] for p in pts]
    s = 380 / (max(xs) - min(xs))
    ox = (W - (max(xs) - min(xs)) * s) / 2 - min(xs) * s
    oy = 56 - min(ys_) * s
    poly = [(x * s + ox, y * s + oy) for x, y in pts]
    rows = []
    for py in range(H):
        hits = []
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            if (y1 <= py + .5 < y2) or (y2 <= py + .5 < y1):
                hits.append(x1 + (py + .5 - y1) * (x2 - x1) / (y2 - y1))
        hits.sort()
        inside = lambda x: any(a <= x + .5 <= b for a, b in zip(hits[::2], hits[1::2]))
        t = py / H
        sky = tuple(round(SKY_T[i] + (SKY_B[i] - SKY_T[i]) * t) for i in range(3))
        row = []
        for x in range(W):
            if py >= lake_top:
                c = EAU
                if (py - lake_top) % 13 == 6 and (x * 7 + py * 3) % 160 < 60:
                    c = SKY_B
            elif py >= h3[x]: c = R3
            elif py >= h2[x]: c = R2
            elif py >= h1[x]: c = SNOW if py < 395 and py < h1[x] + 18 else R1
            elif hits and inside(x): c = ACC
            else: c = sky
            row += c
        rows.append(row)
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    print("écrit og.png")


apercu(os.path.join(os.path.dirname(OUT), "og.png"))
