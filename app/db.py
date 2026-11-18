"""Connexion SQLite (module sqlite3 de la bibliothèque standard)."""

import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db() -> sqlite3.Connection:
    """Connexion de la requête en cours, ouverte à la demande et réutilisée."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Crée la table et l'index s'ils n'existent pas. Ne supprime jamais rien."""
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """Crée la base SQLite (sans effacer les tâches existantes)."""
    init_db()
    click.echo(f"Base prête : {current_app.config['DATABASE']}")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
