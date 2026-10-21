"""Dessine les icônes de l'app (silhouette du Léman) en PNG, sans dépendance externe.

Usage : python3 outils/icones.py   → écrit docs/icons/*.png
"""
import json, math, os, struct, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "docs", "icons")
LAKE = json.load(open(os.path.join(HERE, "data", "lake_pts.json")))

BG = (12, 110, 125)      # bleu-vert du lac (accent de l'app)
FG = (238, 243, 243)     # silhouette claire


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
