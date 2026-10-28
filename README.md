# Le monde des vivants · Léman Vivant (bêta)

Site de l'association Le monde des vivants (www.lemondedesvivants.org) : une page d'accueil « Nos lacs » et un atlas par lac. Premier atlas : Léman Vivant (`/leman/`), atlas interactif du Léman : température de l'eau, faune, espèces menacées, pollution, plages et périodes de reproduction.

## Ce que contient le dossier

| Élément | Rôle |
|---|---|
| `docs/index.html` | La page d'accueil de l'association (« Nos lacs »), reconstruite chaque matin avec l'encart « Cette semaine au Léman » |
| `outils/accueil.html` | Le modèle de la page d'accueil : c'est ici qu'on modifie ses textes |
| `outils/pages.py` | Fabrique l'accueil, une page par espèce (`docs/leman/especes/`) et le plan du site |
| `docs/leman/` | L'atlas Léman Vivant (`index.html`, reconstruit par le script) et son image d'aperçu |
| `docs/` | Le reste du site servi par GitHub Pages : icônes, `favicon.ico`, photos, mode hors ligne (`sw.js`), plan du site |
| `leman-vivant.html` | La même page, pour la version publiée sur claude.ai |
| `outils/actualiser.py` | Récupère les données (Alplakes, GBIF) et reconstruit l'atlas (`docs/leman/index.html` et `leman-vivant.html`) |
| `outils/template.html` | Le modèle de la page : c'est ici qu'on modifie le contenu et le design |
| `outils/especes.json` | Les fiches espèces écrites à la main (comment la reconnaître, où la voir, le saviez-vous). Chaque fiche avec un nom et « reconnaitre » obtient sa page |
| `docs/especes/` | Les photos des espèces (Wikimedia Commons, licences libres, crédits dans `outils/data/photos.json`) |
| `docs/fonts/`, `docs/lib/` | Les polices (Newsreader, Instrument Sans) et la bibliothèque de la carte (d3), hébergées avec le site : aucun service tiers n'est appelé pendant la visite |
| `logos/` | Le logo de l'association (SVG, PNG) et la page qui génère les icônes et les images d'aperçu (`docs/og.png`, `docs/leman/og.png`) |
| `.github/workflows/actualiser.yml` | Mise à jour automatique chaque matin sur les serveurs de GitHub |

## Commandes utiles

```bash
python3 outils/actualiser.py            # données du jour + reconstruction
python3 outils/actualiser.py --build    # reconstruction seule (après une modif du modèle)
python3 outils/actualiser.py --photos   # cherche les photos d'espèces manquantes, puis reconstruit
```

Après une modification de `outils/template.html`, lancez `--build`, puis envoyez les changements sur GitHub (`git add -A && git commit -m "…" && git push`).

## Sources

Température : Alplakes (Eawag), modèle Delft3D. Faune : GBIF. Photos et résumés : Wikipédia et Wikimedia Commons. Statuts : Liste rouge UICN via GBIF. Contour du lac : © contributeurs OpenStreetMap.
