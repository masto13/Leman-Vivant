"""Actualise les données de Léman Vivant et reconstruit la page.

Usage : python3 outils/actualiser.py            (récupère les données et reconstruit tout)
        python3 outils/actualiser.py --build    (reconstruit seulement, avec les données existantes)
- Récupère la température (Alplakes / Eawag) et la faune (GBIF) pour chaque zone.
- Si une source ne répond pas, garde les données précédentes de cette zone.
- Écrit outils/data/zones.json puis reconstruit leman-vivant.html à côté du dossier outils.
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "zones.json")
LAKE = os.path.join(HERE, "data", "lake_pts.json")
TEMPLATE = os.path.join(HERE, "template.html")
PAGE = os.path.join(os.path.dirname(HERE), "leman-vivant.html")
WEB = os.path.join(os.path.dirname(HERE), "docs", "index.html")

# id, rectangle GBIF (lat min, lat max, lon min, lon max), point de température (lat, lon)
ZONES = [
    ("geneve", (46.20, 46.30, 6.13, 6.28), (46.25, 6.20)),
    ("cote", (46.36, 46.48, 6.22, 6.45), (46.40, 6.32)),
    ("lausanne", (46.48, 46.54, 6.48, 6.70), (46.49, 6.60)),
    ("lavaux", (46.44, 46.50, 6.70, 6.91), (46.45, 6.82)),
    ("rhone", (46.37, 46.42, 6.84, 6.95), (46.40, 6.89)),
    ("evian", (46.37, 46.42, 6.46, 6.72), (46.42, 6.60)),
    ("chablais", (46.30, 46.38, 6.28, 6.46), (46.35, 6.36)),
    ("large", (46.42, 46.48, 6.45, 6.75), (46.45, 6.55)),
]
GROUPS = {"oiseaux": "classKey=212", "insectes": "classKey=216", "amphibiens": "classKey=131",
          "mollusques": "phylumKey=52", "plantes": "kingdomKey=6",
          # les poissons n'ont pas de classe unique dans GBIF : on additionne les ordres présents dans le lac
          "poissons": "&".join(f"orderKey={k}" for k in [1313, 1153, 587, 548, 549, 708, 495, 590])}
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]


def get(url):
    for i in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "leman-vivant-beta/0.2"})
            with urllib.request.urlopen(req, timeout=60) as r:
                time.sleep(0.25)
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(5 * (i + 1))
    raise RuntimeError("source indisponible : " + url)


species = {}
def sp(key):
    if key not in species:
        s = get(f"https://api.gbif.org/v1/species/{key}")
        v = get(f"https://api.gbif.org/v1/species/{key}/vernacularNames?limit=100")["results"]
        fr = [x["vernacularName"] for x in v if x.get("language") == "fra"]
        try:
            iucn = get(f"https://api.gbif.org/v1/species/{key}/iucnRedListCategory").get("code")
        except Exception:
            iucn = None
        species[key] = {"sci": s.get("canonicalName"), "fr": fr[0] if fr else "", "iucn": iucn,
                        "class": s.get("class") or s.get("order", "")}
    return species[key]


def faune(box):
    a, b, c, d = box
    base = f"https://api.gbif.org/v1/occurrence/search?decimalLatitude={a},{b}&decimalLongitude={c},{d}&limit=0"
    out = {"total": get(base)["count"], "counts": {g: get(base + "&" + q)["count"] for g, q in GROUPS.items()}}
    fs = get(base + "&" + GROUPS["poissons"] + "&facet=speciesKey&facetLimit=8")
    out["fish"] = [{**sp(f["name"]), "n": f["count"]} for f in (fs["facets"][0]["counts"] if fs["facets"] else [])]
    th = get(base + "&kingdomKey=1&iucnRedListCategory=CR&iucnRedListCategory=EN"
             "&iucnRedListCategory=VU&iucnRedListCategory=NT&facet=speciesKey&facetLimit=14")
    out["threatened"] = [{**sp(f["name"]), "n": f["count"]}
                         for f in (th["facets"][0]["counts"] if th["facets"] else [])
                         if sp(f["name"])["iucn"] in ("CR", "EN", "VU", "NT")]
    return out


def temperature(lat, lon, now):
    start = (now - datetime.timedelta(days=7)).strftime("%Y%m%d0000")
    end = now.strftime("%Y%m%d0000")
    res = {}
    for depth in [1, 10, 30]:
        t = get(f"https://alplakes-api.eawag.ch/simulations/point/delft3d-flow/geneva/{start}/{end}/{depth}/{lat}/{lon}")
        vals = t["variables"]["temperature"]["data"]
        r = lambda v: round(v, 2) if v is not None else None
        res[str(depth)] = {"time": t["time"][::8], "val": [r(v) for v in vals[::8]], "last": r(vals[-1])}
    return res


WEB_HEAD = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="Atlas interactif du Léman : température de l'eau, faune, espèces menacées, pollution, plages et périodes de reproduction.">
<meta name="theme-color" content="#0c6e7d">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Léman">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon-192.png" type="image/png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,-apple-system,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
"""
WEB_FOOT = """<script>
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
</script>
</body>
</html>
"""


def build(res):
    """Écrit la page claude.ai (leman-vivant.html) et l'app web (docs/index.html)."""
    page = open(TEMPLATE).read()
    page = page.replace("/*DATA*/", json.dumps(res, ensure_ascii=False, separators=(",", ":")))
    page = page.replace("/*LAKE*/", json.dumps(json.load(open(LAKE)), separators=(",", ":")))
    open(PAGE, "w").write(page)
    print("Page reconstruite :", PAGE)

    # App web : titre, polices et styles dans <head>, le reste dans <body>
    cut = page.index("</style>") + len("</style>")
    head = page[:cut].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    os.makedirs(os.path.dirname(WEB), exist_ok=True)
    open(WEB, "w").write(WEB_HEAD + head + "\n</head>\n<body>\n" + page[cut:] + "\n" + WEB_FOOT)
    print("App web reconstruite :", WEB)


# Niveau du lac : station OFEV 2027 « Lac Léman - St-Prex »
STATION = "https://www.hydrodaten.admin.ch/fr/seen-und-fluesse/stationen-und-daten/2027"
NIVEAU_40J = "https://www.hydrodaten.admin.ch/plots/p_q_40days/2027_p_q_40days_fr.json"
# Moyennes mensuelles 1943-2025 publiées par l'OFEV (secours si la page ne répond pas)
MOYENNES_SECOURS = [372.03, 371.86, 371.68, 371.67, 371.90, 372.18, 372.27, 372.26, 372.24, 372.21, 372.19, 372.14]
# Niveaux de danger de crue OFEV pour cette station : seuils bas des degrés 2 à 5
DANGER = [(372.9, 5), (372.65, 4), (372.55, 3), (372.35, 2)]


def moyennes_mensuelles():
    """Lit les 12 moyennes mensuelles sur la page de la station (sinon valeurs de secours)."""
    try:
        req = urllib.request.Request(STATION, headers={"User-Agent": "leman-vivant-beta/0.2"})
        page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
        m = re.search(r"Moyenne mensuelle((?:\s*\d{3}\.\d{2}\s*m){12})", txt)
        periode = re.search(r"Période (\d{4}) - (\d{4})", txt)
        vals = [float(v) for v in re.findall(r"\d{3}\.\d{2}", m.group(1))]
        return vals, f"{periode.group(1)}–{periode.group(2)}" if periode else "1943–2025"
    except Exception:
        return MOYENNES_SECOURS, "1943–2025"


def normale_du_jour(moyennes, jour):
    """Interpole la moyenne du jour entre les moyennes mensuelles (placées au 15 de chaque mois)."""
    pts = []
    for annee in (jour.year - 1, jour.year, jour.year + 1):
        pts += [(datetime.date(annee, i + 1, 15), v) for i, v in enumerate(moyennes)]
    for (d1, v1), (d2, v2) in zip(pts, pts[1:]):
        if d1 <= jour <= d2:
            return v1 + (v2 - v1) * (jour - d1).days / (d2 - d1).days


def niveau():
    d = get(NIVEAU_40J)
    serie = next(t for t in d["plot"]["data"] if t.get("y"))
    pts = [(datetime.datetime.fromisoformat(x.replace(".000", "")), y) for x, y in zip(serie["x"], serie["y"]) if y is not None]
    t_last, last = pts[-1]
    veille = min(pts, key=lambda p: abs((t_last - p[0]).total_seconds() - 86400))[1]
    jours = {}
    for t, y in pts:  # une valeur par jour (moyenne)
        jours.setdefault(t.date().isoformat(), []).append(y)
    moyennes, periode = moyennes_mensuelles()
    normale = normale_du_jour(moyennes, t_last.date())
    return {
        "last": round(last, 3), "time": t_last.isoformat(timespec="minutes"),
        "veille_cm": round((last - veille) * 100, 1),
        "normale": round(normale, 3), "ecart_cm": round((last - normale) * 100, 1), "periode": periode,
        "danger": next((n for seuil, n in DANGER if last >= seuil), 1),
        "jours": [[k, round(sum(v) / len(v), 3)] for k, v in sorted(jours.items())],
    }


def main():
    old = json.load(open(DATA)) if os.path.exists(DATA) else {"zones": {}}
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    res = {"fetched": now.strftime("%Y-%m-%d %H:%M UTC"), "zones": {}}
    problems = []
    for zid, box, (lat, lon) in ZONES:
        prev = old["zones"].get(zid, {})
        z = {}
        try:
            z.update(faune(box))
        except Exception as e:
            problems.append(f"{zid} faune : {e}")
            z.update({k: prev.get(k) for k in ("total", "counts", "fish", "threatened")})
        try:
            z["temp"] = temperature(lat, lon, now)
        except Exception as e:
            problems.append(f"{zid} température : {e}")
            z["temp"] = prev.get("temp", {})
        res["zones"][zid] = z
        print(zid, "ok", {k: v.get("last") for k, v in z["temp"].items()}, flush=True)
    try:
        res["niveau"] = niveau()
        n = res["niveau"]
        print(f"niveau ok {n['last']} m, écart {n['ecart_cm']:+} cm à la normale", flush=True)
    except Exception as e:
        problems.append(f"niveau du lac : {e}")
        if old.get("niveau"):
            res["niveau"] = old["niveau"]
    if any(res["zones"][z].get("total") is None for z, *_ in ZONES):
        sys.exit("Données incomplètes et pas de version précédente : page non reconstruite.")
    y, m, d = res["fetched"][:10].split("-")
    res["fetchedFr"] = f"{int(d)} {MOIS[int(m) - 1]} {y}"
    json.dump(res, open(DATA, "w"), ensure_ascii=False)

    build(res)
    if problems:
        print("Sources en panne (anciennes données conservées) :", *problems, sep="\n- ")


if __name__ == "__main__":
    if "--build" in sys.argv:
        build(json.load(open(DATA)))
    else:
        main()
