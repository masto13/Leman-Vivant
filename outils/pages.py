"""Pages du site fabriquées à partir des données : accueil, pages des espèces, plan du site.

Appelé par actualiser.py à chaque reconstruction. Les textes des espèces viennent de
outils/especes.json ; les zones et le calendrier sont lus dans outils/template.html.
"""
import datetime
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), "docs")
SITE = "https://www.lemondedesvivants.org"
ACCUEIL = os.path.join(HERE, "accueil.html")
IUCN = {"CR": "En danger critique", "EN": "En danger", "VU": "Vulnérable", "NT": "Quasi menacée",
        "LC": "Préoccupation mineure"}
MENACEE = ("CR", "EN", "VU", "NT")
# ordre des groupes sur la page « Les espèces du Léman »
GROUPES = ["Poisson", "Oiseau", "Amphibien", "Reptile", "Mammifère", "Chauve-souris",
           "Insecte", "Libellule", "Papillon", "Crustacé"]
PLURIEL = {"Poisson": "Poissons", "Oiseau": "Oiseaux", "Amphibien": "Amphibiens", "Reptile": "Reptiles",
           "Mammifère": "Mammifères", "Chauve-souris": "Chauves-souris", "Insecte": "Insectes",
           "Libellule": "Libellules", "Papillon": "Papillons", "Crustacé": "Crustacés"}
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]

e = lambda t: html.escape(str(t or ""), quote=True)


def slug(sci):
    return re.sub(r"[^a-z]+", "-", sci.lower()).strip("-")


def lire_modele(template):
    """Noms des zones et calendrier de la vie du lac, tels qu'écrits dans le modèle de l'atlas."""
    zones = {m[0]: {"name": m[1], "short": m[2]}
             for m in re.findall(r'^\s+(\w+):\{name:"([^"]+)",short:"([^"]+)"', template, re.M)}
    cal = [{"what": m[0], "m": [int(x) for x in m[1].split(",")]}
           for m in re.findall(r'\{what:"([^"]+)",where:"[^"]*",m:\[([\d,]+)\]', template)]
    return zones, cal


def nb(n):
    return f"{n:,}".replace(",", "\u202f")


def dec(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")


# ---------- styles communs aux pages générées ----------
CSS = """
:root{
  --bg:#f3f5ef; --surface:#fbfcf8; --ink:#1e302c; --muted:#5b6d67; --line:#dbe1d5;
  --sky:#e3ece9; --ridge1:#c3d3d4; --water:#c5dcd8; --accent:#2e7a7b; --accent-soft:#dcebe8; --accent-ink:#fff;
  --reed:#6f8a45; --warn:#b2623f; --warn-soft:#f3e2d8;
  --cr:#b0414a; --en:#c46a44; --vu:#c99a3b; --nt:#8a9a4a;
  --display:"Newsreader", "Iowan Old Style", Georgia, serif;
  --body:"Instrument Sans", "Avenir Next", system-ui, sans-serif; color-scheme:light}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f1a19; --surface:#152321; --ink:#e3ebe5; --muted:#9aaea6; --line:#273836;
  --sky:#142422; --ridge1:#1e3533; --water:#21403f; --accent:#7cc3bf; --accent-soft:#1d3634; --accent-ink:#0b1f1e;
  --reed:#a9c27a; --warn:#e2916b; --warn-soft:#3a2620;
  --cr:#f07f86; --en:#ee9a72; --vu:#e6c066; --nt:#b9c97a; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f1a19; --surface:#152321; --ink:#e3ebe5; --muted:#9aaea6; --line:#273836;
  --sky:#142422; --ridge1:#1e3533; --water:#21403f; --accent:#7cc3bf; --accent-soft:#1d3634; --accent-ink:#0b1f1e;
  --reed:#a9c27a; --warn:#e2916b; --warn-soft:#3a2620;
  --cr:#f07f86; --en:#ee9a72; --vu:#e6c066; --nt:#b9c97a; color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-size:15.5px;line-height:1.55}
h1,h2,h3{font-family:var(--display);font-weight:400;margin:0;text-wrap:balance}
h1{font-size:clamp(36px,6.5vw,60px);line-height:1;letter-spacing:-.015em}
h2{font-size:clamp(24px,3.4vw,30px);line-height:1.12}
h3{font-size:19px;line-height:1.2}
p{margin:0}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.eyebrow{font:italic 400 16px/1.2 var(--display);color:var(--muted)}
.inner{max-width:1080px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.topnav{position:sticky;top:0;z-index:10;padding-top:env(safe-area-inset-top,0px);background:color-mix(in srgb,var(--sky) 88%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border-bottom:1px solid color-mix(in srgb,var(--ridge1) 60%,transparent)}
.topnav .inner{padding-block:10px;display:flex;align-items:center;justify-content:space-between;gap:8px 20px;flex-wrap:wrap}
.brand{font:italic 400 19px/1 var(--display);color:var(--ink);text-decoration:none;white-space:nowrap;display:inline-flex;align-items:center;gap:9px}
.mark{width:26px;height:26px;flex:none;display:block}
.navtabs{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;max-width:100%}
.navtabs::-webkit-scrollbar{display:none}
.navtabs a{font:500 14px/1 var(--body);color:var(--muted);text-decoration:none;padding:9px 12px;border-radius:999px;white-space:nowrap}
.navtabs a:hover{color:var(--ink)}
.navtabs a[aria-current="page"]{color:var(--ink);background:var(--surface)}
main{padding-block:28px 56px;display:grid;gap:36px}
.crumbs{font-size:13.5px;color:var(--muted)}
.crumbs a{color:var(--muted)}
.iucn{display:inline-block;font:600 11px/1 var(--body);padding:4px 6px;border-radius:5px;color:#fff;background:var(--muted);vertical-align:1px}
.iucn.CR{background:var(--cr)} .iucn.EN{background:var(--en)} .iucn.VU{background:var(--vu)} .iucn.NT{background:var(--nt)} .iucn.LC{background:var(--reed)}
.sci{font-style:italic}
.site-foot{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px 24px;border-top:1px solid var(--line);padding-top:20px;font-size:13.5px;color:var(--muted)}
.site-foot b{font:italic 400 16px var(--display);color:var(--ink)}
.site-foot a{color:var(--muted)}
@media (max-width:520px){.navtabs a{padding:8px 10px;font-size:13.5px}}
"""

CSS_ESPECE = """
.sp{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:32px;align-items:start}
.sp > div:first-child{position:sticky;top:76px}
.sp-photo{margin:0}
.sp-photo img{display:block;width:100%;height:auto;aspect-ratio:3/2;object-fit:cover;border-radius:20px;background:var(--water)}
.sp-photo figcaption{font-size:12px;color:var(--muted);padding:8px 2px 0}
.sp-photo figcaption a{color:var(--muted)}
.sp-head{display:grid;gap:10px}
.sp-meta{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;font-size:14px;color:var(--muted)}
.sp-body{display:grid;gap:22px}
.sec{display:grid;gap:8px}
.sec p{color:var(--ink)}
ul.traits{margin:0;padding:0;list-style:none;display:grid;gap:8px}
ul.traits li{display:grid;grid-template-columns:22px 1fr;gap:8px;line-height:1.45}
ul.traits li::before{content:"";width:8px;height:8px;margin:7px 0 0 6px;border-radius:50%;background:var(--reed)}
.menace{background:var(--warn-soft);border-radius:14px;padding:14px 16px}
.menace h2{color:var(--warn)}
.savoir{background:var(--accent-soft);border-radius:14px;padding:14px 16px}
.savoir p{font:italic 18px/1.45 var(--display)}
.zones{display:flex;flex-wrap:wrap;gap:6px}
.zones a{font:500 13.5px/1 var(--body);padding:9px 12px;border-radius:999px;border:1px solid var(--line);color:var(--ink);text-decoration:none}
.zones a:hover{background:var(--accent-soft)}
.zones a span{color:var(--muted);font-weight:400}
.links{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:14px}
.sec h2{font-size:21px}
.more{display:grid;gap:12px}
.mini{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
@media (max-width:820px){.sp{grid-template-columns:1fr;gap:22px}.sp > div:first-child{position:static}}
"""

CSS_LISTE = """
.intro{display:grid;gap:10px;max-width:66ch}
.intro p{color:var(--muted)}
.groups{display:grid;gap:36px}
.group{display:grid;gap:14px}
.group h2 small{font:400 15px var(--body);color:var(--muted);margin-left:6px}
.mini{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}
"""

CSS_CARTE = """
.card{display:grid;align-content:start;border-radius:16px;overflow:hidden;background:var(--surface);box-shadow:0 1px 0 var(--line);text-decoration:none;color:var(--ink)}
.card:hover{box-shadow:0 1px 0 var(--line),0 12px 28px -20px rgba(30,60,55,.45)}
.card img,.card .noimg{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;background:var(--water)}
.card div{padding:10px 12px 12px;display:grid;gap:2px}
.card b{font:400 18px/1.15 var(--display)}
.card span{font-size:12.5px;color:var(--muted)}
"""

SYMBOLE = """<svg width="0" height="0" style="position:absolute" aria-hidden="true"><symbol id="mdv" viewBox="0 0 120 120"><clipPath id="mdv-disc"><circle cx="60" cy="60" r="60"/></clipPath><g clip-path="url(#mdv-disc)"><rect width="120" height="120" style="fill:var(--accent)"/><path d="M0 66 L22 44 L32 52 L52 26 L66 42 L74 36 L96 58 L106 52 L120 64 V66 Z" style="fill:var(--bg)"/><path d="M0 66 L22 88 L32 80 L52 106 L66 90 L74 96 L96 74 L106 80 L120 68 V66 Z" style="fill:var(--bg)" fill-opacity=".38"/><path d="M10 80 q8 -3 16 0 M70 86 q10 -3 20 0 M36 98 q7 -2.5 14 0" style="stroke:var(--accent)" stroke-width="3.4" stroke-linecap="round" fill="none"/></g></symbol></svg>"""


def polices():
    """Polices hébergées avec le site : les deux plus utilisées préchargées, les @font-face en ligne."""
    css = open(os.path.join(DOCS, "fonts", "fonts.css")).read().split("\n", 1)[1].strip()
    return ('<link rel="preload" href="/fonts/newsreader-normal-latin.woff2" as="font" type="font/woff2" crossorigin>\n'
            '<link rel="preload" href="/fonts/instrument-sans-normal-latin.woff2" as="font" type="font/woff2" crossorigin>\n'
            f"<style>{css}</style>")


def page(titre, description, chemin, corps, css, image=None, jsonld=None, actif=None):
    """Squelette commun : en-tête pour Google et les aperçus de liens, navigation, pied de page."""
    url = SITE + chemin
    image = image or SITE + "/leman/og.png"
    nav = [("/leman/", "Léman Vivant", "atlas"), ("/leman/especes/", "Espèces", "especes"),
           ("/#association", "L'association", None), ("/#contact", "Contact", None)]
    cur = ' aria-current="page"'
    liens = "".join(f'<a href="{h}"{cur if k and k == actif else ""}>{t}</a>' for h, t, k in nav)
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>\n' if jsonld else ""
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(titre)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Le monde des vivants">
<meta property="og:locale" content="fr_CH">
<meta property="og:title" content="{e(titre)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{e(image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#2e7a7b">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/icons/symbole.svg" type="image/svg+xml">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png?v=2">
{ld}{polices()}
<style>{CSS}{css}</style>
</head>
<body>
{SYMBOLE}
<nav class="topnav" aria-label="Navigation principale">
  <div class="inner">
    <a class="brand" href="/"><svg class="mark" aria-hidden="true"><use href="#mdv"/></svg>Le monde des vivants</a>
    <div class="navtabs">{liens}</div>
  </div>
</nav>
<main class="inner">
{corps}
  <footer class="site-foot">
    <span><b>Le monde des vivants</b> · association en cours de création</span>
    <span><a href="mailto:contact@lemondedesvivants.org">contact@lemondedesvivants.org</a> · <a href="/leman/#association">Sources, confidentialité et mentions légales</a></span>
  </footer>
</main>
<script>if ("serviceWorker" in navigator) addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {{}}));</script>
</body>
</html>
"""


def observations(res):
    """Pour chaque espèce : statut UICN, nom GBIF et nombre d'observations par zone."""
    obs = {}
    for zid, z in res["zones"].items():
        for o in (z.get("fish") or []) + (z.get("threatened") or []):
            d = obs.setdefault(o["sci"], {"iucn": o.get("iucn"), "fr": o.get("fr"), "zones": {}})
            d["zones"][zid] = max(d["zones"].get(zid, 0), o.get("n", 0))
    return obs


def carte(sci, f, iucn):
    img = f'<img src="/especes/{e(f["img"])}" alt="" loading="lazy">' if f.get("img") else '<span class="noimg"></span>'
    statut = f'<span><span class="iucn {iucn}">{iucn}</span> {IUCN[iucn]}</span>' if iucn in MENACEE else f'<span class="sci">{e(sci)}</span>'
    return f'<a class="card" href="/leman/especes/{slug(sci)}/">{img}<div><b>{e(f["nom"])}</b>{statut}</div></a>'


def page_espece(sci, f, o, zones, voisines):
    nom, iucn = f["nom"], (o.get("iucn") or "LC")
    menacee = iucn in MENACEE
    chemin = f"/leman/especes/{slug(sci)}/"
    groupe = f.get("groupe", "Espèce")
    desc = f"{nom} ({sci}) dans le Léman : comment la reconnaître, où et quand la voir"
    desc += f", et pourquoi elle est menacée ({IUCN[iucn].lower()})." if menacee else "."
    photo = ""
    if f.get("img"):
        credit = f'<a href="{e(f["source"])}" target="_blank" rel="noopener">{e(f.get("auteur"))}</a>' if f.get("source") else e(f.get("auteur"))
        photo = (f'<figure class="sp-photo"><img src="/especes/{e(f["img"])}" alt="{e(nom)}" width="520" height="347">'
                 f'<figcaption>Photo : {credit}{" · " + e(f["licence"]) if f.get("licence") else ""}</figcaption></figure>')
    zl = sorted(o.get("zones", {}).items(), key=lambda kv: -kv[1])
    zhtml = "".join(f'<a href="/leman/#carte" data-zone="{z}">{e(zones.get(z, {}).get("short", z))} <span>· {nb(n)} obs.</span></a>'
                    for z, n in zl if z in zones)
    secs = []
    if f.get("reconnaitre"):
        secs.append('<section class="sec"><h2>Comment la reconnaître</h2><ul class="traits">'
                    + "".join(f"<li>{e(t)}</li>" for t in f["reconnaitre"]) + "</ul></section>")
    if f.get("ou"):
        secs.append(f'<section class="sec"><h2>Où et quand la voir</h2><p>{e(f["ou"])}</p></section>')
    if f.get("menace"):
        secs.append(f'<section class="sec{" menace" if menacee else ""}"><h2>{"Pourquoi elle est menacée" if menacee else "À savoir"}</h2><p>{e(f["menace"])}</p></section>')
    if f.get("savoir"):
        secs.append(f'<section class="sec savoir"><div class="eyebrow">Le saviez-vous ?</div><p>{e(f["savoir"])}</p></section>')
    if zhtml:
        secs.append(f'<section class="sec"><h2>Observée dans le Léman</h2><div class="zones">{zhtml}</div>'
                    '<p class="crumbs">Observations publiées sur le GBIF (iNaturalist, ornitho.ch, musées…), rives comprises.</p></section>')
    liens = []
    if f.get("wiki"):
        liens.append(f'<a href="{e(f["wiki"])}" target="_blank" rel="noopener">En savoir plus sur Wikipédia</a>')
    liens.append(f'<a href="https://www.gbif.org/species/search?q={e(sci)}" target="_blank" rel="noopener">Toutes les observations (GBIF)</a>')
    secs.append(f'<div class="links">{"".join(liens)}</div>')
    autres = "".join(carte(s, ff, oo.get("iucn") or "LC") for s, ff, oo in voisines)
    corps = f"""  <div class="crumbs"><a href="/leman/">Léman Vivant</a> › <a href="/leman/especes/">Espèces</a> › {e(nom)}</div>
  <article class="sp">
    <div>{photo}</div>
    <div class="sp-body">
      <header class="sp-head">
        <div class="eyebrow">{e(groupe)} · vu au bord du Léman</div>
        <h1>{e(nom)}</h1>
        <div class="sp-meta"><span class="sci">{e(sci)}</span><span><span class="iucn {iucn}">{iucn}</span> {IUCN[iucn]}</span>{f'<span>Taille : {e(f["taille"])}</span>' if f.get("taille") else ""}</div>
      </header>
      {"".join(secs)}
    </div>
  </article>
  {f'<section class="more"><h2>Autres {e(PLURIEL.get(groupe, "espèces")).lower()} du Léman</h2><div class="mini">{autres}</div></section>' if autres else ""}
  <script>
  // « Observée dans le Léman » : ouvre l'atlas sur la zone choisie
  document.querySelectorAll("[data-zone]").forEach(a => a.addEventListener("click", () => {{ try {{ localStorage.setItem("leman-zone", a.dataset.zone); }} catch (e) {{}} }}));
  </script>"""
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Léman Vivant", "item": SITE + "/leman/"},
        {"@type": "ListItem", "position": 2, "name": "Espèces", "item": SITE + "/leman/especes/"},
        {"@type": "ListItem", "position": 3, "name": nom, "item": SITE + chemin}]}
    image = SITE + "/especes/" + f["img"] if f.get("img") else None
    return chemin, page(f"{nom} dans le Léman · Léman Vivant", desc, chemin, corps, CSS_ESPECE + CSS_CARTE, image, ld, "especes")


def page_liste(fiches, obs):
    par_groupe = {}
    for sci, f in fiches.items():
        par_groupe.setdefault(f.get("groupe", "Autres"), []).append(sci)
    blocs = []
    for g in sorted(par_groupe, key=lambda g: GROUPES.index(g) if g in GROUPES else 99):
        lst = sorted(par_groupe[g], key=lambda s: fiches[s]["nom"].lower())
        cartes = "".join(carte(s, fiches[s], obs.get(s, {}).get("iucn") or "LC") for s in lst)
        blocs.append(f'<section class="group" id="{slug(g)}"><h2>{e(PLURIEL.get(g, g))}<small>{len(lst)}</small></h2><div class="mini">{cartes}</div></section>')
    n_men = sum(1 for s in fiches if (obs.get(s, {}).get("iucn") or "LC") in MENACEE)
    corps = f"""  <div class="crumbs"><a href="/leman/">Léman Vivant</a> › Espèces</div>
  <header class="intro">
    <div class="eyebrow">Léman Vivant</div>
    <h1>Les espèces du Léman</h1>
    <p>{len(fiches)} espèces observées dans le lac et sur ses rives, dont {n_men} menacées à l'échelle mondiale. Pour chacune : comment la reconnaître, où et quand la voir, et ce qu'il faut savoir pour la protéger.</p>
  </header>
  <div class="groups">{"".join(blocs)}</div>"""
    desc = f"Poissons, oiseaux, amphibiens, insectes : {len(fiches)} espèces du Léman, comment les reconnaître, où et quand les voir, et lesquelles sont menacées."
    return page("Les espèces du Léman · Léman Vivant", desc, "/leman/especes/", corps, CSS_LISTE + CSS_CARTE, actif="especes")


def semaine(res, cal):
    """Encart « Cette semaine au Léman » de la page d'accueil."""
    tuiles = []
    t = (res["zones"].get("lausanne", {}).get("temp") or {}).get("1") or {}
    if t.get("last") is not None:
        vals = [v for v in t.get("val", []) if v is not None]
        tend = ""
        if len(vals) > 1:
            d = vals[-1] - vals[0]
            tend = "stable sur la semaine" if abs(d) < 0.5 else f"{'+' if d > 0 else '−'}{dec(abs(d))} °C en une semaine"
        tuiles.append(("Eau en surface à Lausanne", f"{dec(t['last'])} °C", tend))
    n = res.get("niveau")
    if n:
        ec = n["ecart_cm"]
        txt = "proche de la normale" if abs(ec) < 3 else f"{dec(abs(ec), 0)} cm {'au-dessus' if ec > 0 else 'au-dessous'} de la normale"
        if n.get("danger", 1) >= 2:
            txt = f"danger de crue {n['danger']}/5"
        tuiles.append(("Niveau du lac", f"{dec(n['last'], 2)} m", txt))
    mois = int(res["fetched"][5:7]) - 1
    pic = [c["what"] for c in cal if c["m"][mois] == 2] or [c["what"] for c in cal if c["m"][mois] == 1]
    if pic:
        tuiles.append(("En ce moment", pic[0], " · ".join(pic[1:3])))
    if not tuiles:
        return ""
    html_t = "".join(f'<div class="wk"><span>{e(a)}</span><b>{e(b)}</b><em>{e(c)}</em></div>' for a, b, c in tuiles)
    return f"""<section class="week" aria-label="Cette semaine au Léman">
    <div class="week-head"><h2>Cette semaine au Léman</h2><span>Données du {e(res.get("fetchedFr", ""))}</span></div>
    <div class="wks">{html_t}</div>
    <a href="/leman/">Voir tout l'atlas →</a>
  </section>"""


def construire(res, especes, template):
    """Écrit l'accueil, les pages des espèces et le plan du site."""
    zones, cal = lire_modele(template)
    obs = observations(res)
    fiches = {s: f for s, f in especes.items() if f.get("reconnaitre") and f.get("nom")}

    # pages des espèces (et suppression de celles qui n'ont plus de fiche)
    racine = os.path.join(DOCS, "leman", "especes")
    os.makedirs(racine, exist_ok=True)
    chemins = []
    for sci, f in fiches.items():
        g = f.get("groupe")
        voisines = [(s, fiches[s], obs.get(s, {})) for s in sorted(fiches, key=lambda s: -sum(obs.get(s, {}).get("zones", {}).values()))
                    if s != sci and fiches[s].get("groupe") == g][:4]
        chemin, contenu = page_espece(sci, f, obs.get(sci, {}), zones, voisines)
        os.makedirs(os.path.join(DOCS, chemin.strip("/")), exist_ok=True)
        open(os.path.join(DOCS, chemin.strip("/"), "index.html"), "w").write(contenu)
        chemins.append(chemin)
    garder = {slug(s) for s in fiches}
    for d in os.listdir(racine):
        if os.path.isdir(os.path.join(racine, d)) and d not in garder:
            for x in os.listdir(os.path.join(racine, d)):
                os.remove(os.path.join(racine, d, x))
            os.rmdir(os.path.join(racine, d))
    open(os.path.join(racine, "index.html"), "w").write(page_liste(fiches, obs))

    # accueil
    acc = open(ACCUEIL).read().replace("<!--SEMAINE-->", semaine(res, cal)).replace("<!--POLICES-->", polices())
    open(os.path.join(DOCS, "index.html"), "w").write(acc)

    # plan du site
    urls = [("/", "weekly"), ("/leman/", "daily"), ("/leman/especes/", "weekly")] + [(c, "monthly") for c in sorted(chemins)]
    open(os.path.join(DOCS, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{u}</loc><changefreq>{c}</changefreq></url>\n" for u, c in urls) + "</urlset>\n")
    print(f"Accueil, {len(chemins)} pages d'espèces et plan du site reconstruits")
