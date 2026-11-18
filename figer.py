"""Génère la version en ligne (GitHub Pages) dans `build/`.

Usage :
    python figer.py

La variable d'environnement URL_DE_BASE donne l'adresse du site publié
(par exemple https://faumen-darryl.github.io/todo-flask/), afin que les
fichiers statiques pointent vers le bon sous-dossier. Sans elle, le site est
généré pour être servi à la racine (aperçu local).

Le site figé n'embarque aucune tâche : il utilise une base temporaire vide,
et la page est rendue en mode STATIC_SITE (les tâches vivent dans le navigateur).
"""

import os
import tempfile

from flask_frozen import Freezer

from app import create_app


def figer(destination="build", url_de_base=None):
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(
            {
                "STATIC_SITE": True,
                "DATABASE": os.path.join(tmp, "vide.db"),
                "SECRET_KEY": "site-statique",
                "FREEZER_DESTINATION": os.path.abspath(destination),
                "FREEZER_BASE_URL": url_de_base or os.environ.get("URL_DE_BASE") or None,
                "FREEZER_REMOVE_EXTRA_FILES": True,
                "FREEZER_IGNORE_MIMETYPE_WARNINGS": True,
            }
        )
        # log_url_for=False : les formulaires POST (/tasks…) n'ont pas de page à figer.
        freezer = Freezer(app, log_url_for=False)
        return list(freezer.freeze())


if __name__ == "__main__":
    pages = figer()
    print(f"{len(pages)} fichiers générés dans build/")
