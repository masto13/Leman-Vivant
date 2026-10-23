# Léman Vivant (bêta)

Atlas interactif du Léman : température de l'eau, faune, espèces menacées, pollution, plages et périodes de reproduction.

## Ce que contient le dossier

| Élément | Rôle |
|---|---|
| `docs/` | L'app web installable, servie par GitHub Pages (`index.html`, icônes, mode hors ligne) |
| `leman-vivant.html` | La même page, pour la version publiée sur claude.ai |
| `outils/actualiser.py` | Récupère les données (Alplakes, GBIF) et reconstruit les deux pages |
| `outils/template.html` | Le modèle de la page : c'est ici qu'on modifie le contenu et le design |
| `logos/` | Le logo de l'association (SVG, PNG) et la page qui génère les icônes |
| `.github/workflows/actualiser.yml` | Mise à jour automatique chaque matin sur les serveurs de GitHub |

## Commandes utiles

```bash
python3 outils/actualiser.py            # données du jour + reconstruction
python3 outils/actualiser.py --build    # reconstruction seule (après une modif du modèle)
```

Après une modification de `outils/template.html`, lancez `--build`, puis envoyez les changements sur GitHub (`git add -A && git commit -m "…" && git push`).

## Sources

Température : Alplakes (Eawag), modèle Delft3D. Faune : GBIF. Statuts : Liste rouge UICN via GBIF. Contour du lac : © contributeurs OpenStreetMap.
