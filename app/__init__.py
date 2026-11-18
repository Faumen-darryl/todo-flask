"""Application Flask : to-do list de travail stockée en local dans SQLite."""

import os
import secrets

from flask import Flask


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # Sert uniquement aux messages flash ; l'app tourne en local.
        SECRET_KEY=os.environ.get("TODO_SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.path.join(app.instance_path, "todo.db"),
        # True uniquement pour générer le site GitHub Pages (figer.py) : la page
        # est rendue vide et c'est le JavaScript qui gère les tâches dans le navigateur.
        STATIC_SITE=False,
    )
    if test_config is not None:
        app.config.update(test_config)

    # Le dossier instance/ contient la base : il est ignoré par git.
    os.makedirs(app.instance_path, exist_ok=True)

    from . import db, filters, routes

    db.init_app(app)
    filters.init_app(app)
    app.register_blueprint(routes.bp)

    # Le schéma est idempotent : on le joue au démarrage pour que l'app
    # fonctionne même si `flask init-db` a été oublié.
    with app.app_context():
        db.init_db()

    return app
