"""Actualise les données de Léman Vivant et reconstruit la page.

Usage : python3 outils/actualiser.py            (récupère les données et reconstruit tout)
        python3 outils/actualiser.py --build    (reconstruit seulement, avec les données existantes)
        python3 outils/actualiser.py --photos   (cherche les photos d'espèces manquantes, puis reconstruit)
- Récupère la température (Alplakes / Eawag) et la faune (GBIF) pour chaque zone.
- Si une source ne répond pas, garde les données précédentes de cette zone.
- Écrit outils/data/zones.json puis reconstruit leman-vivant.html à côté du dossier outils.
"""
import datetime, json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request
import pages  # outils/pages.py

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "zones.json")
LAKE = os.path.join(HERE, "data", "lake_pts.json")
TEMPLATE = os.path.join(HERE, "template.html")
PAGE = os.path.join(os.path.dirname(HERE), "leman-vivant.html")
WEB = os.path.join(os.path.dirname(HERE), "docs", "leman", "index.html")

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


# Fiches espèces : textes écrits à la main (outils/especes.json) + photo et résumé tirés de Wikipédia.
# Les photos sont téléchargées une seule fois dans docs/especes/ (servies par le site, disponibles hors ligne).
FICHES = os.path.join(HERE, "especes.json")
PHOTOS = os.path.join(HERE, "data", "photos.json")
PHOTO_DIR = os.path.join(os.path.dirname(HERE), "docs", "especes")
WIKI_UA = "leman-vivant/0.3 (https://www.lemondedesvivants.org; contact@lemondedesvivants.org)"


def wiki(url):
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        time.sleep(0.3)
        return json.loads(r.read())


def slug(sci):
    return re.sub(r"[^a-z]+", "-", sci.lower()).strip("-")


def sans_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def photo(sci, commons=None):
    """Cherche la page Wikipédia de l'espèce, son image principale (libre) et son crédit.
    `commons` : nom d'un fichier Wikimedia Commons à utiliser à la place (champ "commons" de especes.json)."""
    q = urllib.parse.quote(sci)
    p = wiki("https://fr.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=pageimages|extracts|info"
             f"&piprop=name&exintro=1&explaintext=1&exsentences=3&inprop=url&titles={q}")
    page = next(iter(p["query"]["pages"].values()))
    out = {} if "missing" in page else {"wiki": page.get("fullurl"), "resume": (page.get("extract") or "").strip()}
    name = commons or page.get("pageimage")
    if not name:
        return out
    c = wiki("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo"
             f"&iiprop=url|extmetadata&iiurlwidth=480&titles=File:{urllib.parse.quote(name)}")
    info = next(iter(c["query"]["pages"].values())).get("imageinfo", [{}])[0]
    meta = info.get("extmetadata", {})
    lic = meta.get("LicenseShortName", {}).get("value", "")
    if not info.get("thumburl") or not re.search(r"CC|domain|GFDL|Public", lic, re.I):
        return out
    ext = ".png" if info["thumburl"].split("?")[0].lower().endswith(".png") else ".jpg"
    fichier = slug(sci) + ext
    os.makedirs(PHOTO_DIR, exist_ok=True)
    req = urllib.request.Request(info["thumburl"], headers={"User-Agent": WIKI_UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(os.path.join(PHOTO_DIR, fichier), "wb") as f:
        f.write(r.read())
    out.update({"img": fichier, "auteur": sans_html(meta.get("Artist", {}).get("value"))[:80] or "Wikimedia Commons",
                "licence": lic, "source": info.get("descriptionurl")})
    return out


def photos(res, tout=False):
    """Complète outils/data/photos.json pour les espèces affichées qui n'ont pas encore de photo."""
    cache = json.load(open(PHOTOS)) if os.path.exists(PHOTOS) else {}
    fiches = json.load(open(FICHES)) if os.path.exists(FICHES) else {}
    noms = {s["sci"] for z in res["zones"].values() for k in ("fish", "threatened") for s in (z.get(k) or [])}
    for sci in sorted(noms):
        choix = fiches.get(sci, {}).get("commons")
        deja = sci in cache and (not choix or cache[sci].get("commons") == choix)
        if deja and not (tout and not cache[sci].get("img")):
            continue
        try:
            cache[sci] = photo(sci, choix)
            if choix:
                cache[sci]["commons"] = choix
            print("photo", sci, "ok" if cache[sci].get("img") else "absente", flush=True)
        except Exception as e:
            print("photo", sci, "erreur :", e, flush=True)
    json.dump(cache, open(PHOTOS, "w"), ensure_ascii=False, indent=1, sort_keys=True)


def especes():
    """Fusionne les textes écrits à la main et les infos Wikipédia pour la page."""
    fiches = json.load(open(FICHES)) if os.path.exists(FICHES) else {}
    cache = json.load(open(PHOTOS)) if os.path.exists(PHOTOS) else {}
    fiches.pop("_aide", None)
    garder = ("nom", "groupe", "taille", "reconnaitre", "ou", "menace", "savoir", "img", "auteur", "licence", "source", "wiki", "resume")
    return {sci: {k: v for k, v in {**cache.get(sci, {}), **fiches.get(sci, {})}.items() if k in garder}
            for sci in sorted(set(fiches) | set(cache))}  # ordre fixe : pas de faux changements


WEB_HEAD = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="L'atlas du Léman : température de l'eau, niveau du lac, faune, espèces menacées, plages et zones de reproduction, zone par zone et mis à jour chaque matin.">
<link rel="canonical" href="https://www.lemondedesvivants.org/leman/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Le monde des vivants">
<meta property="og:locale" content="fr_CH">
<meta property="og:title" content="Léman Vivant · l'atlas vivant du lac Léman">
<meta property="og:description" content="Température de l'eau, niveau du lac, faune, espèces menacées et zones à respecter, zone par zone et chaque jour.">
<meta property="og:url" content="https://www.lemondedesvivants.org/leman/">
<meta property="og:image" content="https://www.lemondedesvivants.org/leman/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#2e7a7b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Léman">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/icons/symbole.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,-apple-system,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
"""
WEB_FOOT = """<script>
if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
</script>
</body>
</html>
"""


def build(res):
    """Écrit la page claude.ai (leman-vivant.html), l'atlas du site (docs/leman/index.html) et les pages générées (pages.py)."""
    page = open(TEMPLATE).read()
    page = page.replace("/*DATA*/", json.dumps(res, ensure_ascii=False, separators=(",", ":")))
    page = page.replace("/*LAKE*/", json.dumps(json.load(open(LAKE)), separators=(",", ":")))
    page = page.replace("/*SPECIES*/", json.dumps(especes(), ensure_ascii=False, separators=(",", ":")))
    open(PAGE, "w").write(page)
    print("Page reconstruite :", PAGE)

    # App web : titre, polices et styles dans <head>, le reste dans <body>
    cut = page.index("</style>") + len("</style>")
    head = page[:cut].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    head = head.replace("<title>Léman Vivant</title>", "<title>Léman Vivant · Le monde des vivants</title>")
    os.makedirs(os.path.dirname(WEB), exist_ok=True)
    body = page[cut:].replace('PHOTO_BASE = "https://www.lemondedesvivants.org/especes/"', 'PHOTO_BASE = "/especes/"')
    body = body.replace('<a class="brand" href="#carte">', '<a class="brand" href="/">')
    body = body.replace("https://www.lemondedesvivants.org/", "/")  # liens internes du site
    open(WEB, "w").write(WEB_HEAD + head + "\n</head>\n<body>\n" + body + "\n" + WEB_FOOT)
    print("App web reconstruite :", WEB)
    pages.construire(res, especes(), open(TEMPLATE).read())  # accueil, pages des espèces, plan du site


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


# Qualité des eaux de baignade : classement officiel publié chaque année par l'Agence européenne
# de l'environnement (données des cantons suisses et des agences régionales de santé françaises)
EEA = "https://marine.discomap.eea.europa.eu/arcgis/rest/services/BathingWater/BathingWater_Dyna_WM_{}/MapServer/3/query"
QUALITE = {"Excellent": "excellente", "Good": "bonne", "Sufficient": "suffisante", "Poor": "insuffisante",
           "Not classified": "non classée"}
PETITS_MOTS = {"de", "du", "des", "la", "le", "les", "sur", "à", "aux", "et", "en"}


def joli_nom(s):
    """« PLAGE DE LA POINTE-À-LA-BISE » → « Plage de la Pointe-à-la-Bise »."""
    def mot(m, premier):
        if "'" in m:  # d'hermance → d'Hermance
            a, b = m.split("'", 1)
            return a + "'" + mot(b, False).capitalize() if a in ("d", "l") else m.capitalize()
        if "-" in m:
            return "-".join(mot(p, premier and i == 0) for i, p in enumerate(m.split("-")))
        return m if (m in PETITS_MOTS and not premier) else m.capitalize()
    return " ".join(mot(m, i == 0) for i, m in enumerate(s.lower().split()))


def pres_du_lac(lon, lat, km=1.0):
    """Vrai si le point est à moins de `km` du contour du Léman."""
    kx = math.cos(math.radians(46.37)) * 111.32
    lake = json.load(open(LAKE))
    px, py = lon * kx, lat * 111.32
    best = 1e9
    for (x1, y1), (x2, y2) in zip(lake, lake[1:] + lake[:1]):
        ax, ay, bx, by = x1 * kx, y1 * 111.32, x2 * kx, y2 * 111.32
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, math.hypot(px - ax - t * dx, py - ay - t * dy))
    return best <= km


def baignade(now):
    params = ("where=1%3D1&geometry=6.10,46.18,6.98,46.56&geometryType=esriGeometryEnvelope&inSR=4326"
              "&spatialRel=esriSpatialRelIntersects&returnGeometry=false&f=json&outFields=bathingWaterName,"
              "countryCode,bwWaterCategory,longitude,latitude,qualityStatus,bathingWaterIdentifier,bwProfileLink")
    for saison in range(now.year, now.year - 4, -1):  # le classement d'une saison paraît l'année suivante
        try:
            feats = get(EEA.format(saison) + "?" + params).get("features", [])
        except Exception:
            continue
        sites = []
        for f in feats:
            a = f["attributes"]
            if a["bwWaterCategory"] != "Lake" or not pres_du_lac(a["longitude"], a["latitude"]):
                continue
            sites.append({"nom": joli_nom(a["bathingWaterName"]), "pays": a["countryCode"],
                          "lon": round(a["longitude"], 5), "lat": round(a["latitude"], 5),
                          "qualite": QUALITE.get(a["qualityStatus"], "non classée"),
                          "lien": (a["bwProfileLink"] or "").replace("http://", "https://")})
        if sites:
            return {"saison": saison, "sites": sorted(sites, key=lambda s: s["nom"])}
    raise RuntimeError("aucun classement de baignade trouvé")


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
    try:
        res["baignade"] = baignade(now)
        print(f"baignade ok : {len(res['baignade']['sites'])} sites, saison {res['baignade']['saison']}", flush=True)
    except Exception as e:
        problems.append(f"baignade : {e}")
        if old.get("baignade"):
            res["baignade"] = old["baignade"]
    if any(res["zones"][z].get("total") is None for z, *_ in ZONES):
        sys.exit("Données incomplètes et pas de version précédente : page non reconstruite.")
    y, m, d = res["fetched"][:10].split("-")
    res["fetchedFr"] = f"{int(d)} {MOIS[int(m) - 1]} {y}"
    json.dump(res, open(DATA, "w"), ensure_ascii=False)
    try:
        photos(res)
    except Exception as e:
        problems.append(f"photos des espèces : {e}")

    build(res)
    if problems:
        print("Sources en panne (anciennes données conservées) :", *problems, sep="\n- ")


if __name__ == "__main__":
    if "--photos" in sys.argv:  # cherche les photos manquantes, puis reconstruit
        photos(json.load(open(DATA)), tout=True)
        build(json.load(open(DATA)))
    elif "--build" in sys.argv:
        build(json.load(open(DATA)))
    else:
        main()
