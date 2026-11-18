"""Accès aux données. Toutes les requêtes sont paramétrées (?), aucun DELETE."""

import sqlite3

from .db import get_db

MAX_TITLE_LENGTH = 200
STATUSES = ("todo", "done")


class InvalidTitle(ValueError):
    """Titre refusé (vide ou trop long). Le message est affiché à l'utilisateur."""


def add_task(title: str | None) -> int:
    """Ajoute une tâche « à faire » et renvoie son id."""
    cleaned = (title or "").strip()
    if not cleaned:
        raise InvalidTitle("Le titre de la tâche est obligatoire.")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise InvalidTitle(
            f"Le titre ne doit pas dépasser {MAX_TITLE_LENGTH} caractères "
            f"({len(cleaned)} saisis)."
        )
    db = get_db()
    cur = db.execute("INSERT INTO tasks (title) VALUES (?)", (cleaned,))
    db.commit()
    return cur.lastrowid


def get_task(task_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT id, title, status, created_at, completed_at FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()


def list_tasks(status: str) -> list[sqlite3.Row]:
    """Tâches d'un statut, par ordre d'entrée : la plus ancienne en premier."""
    if status not in STATUSES:
        raise ValueError(f"Statut inconnu : {status!r}")
    return get_db().execute(
        "SELECT id, title, status, created_at, completed_at FROM tasks "
        "WHERE status = ? ORDER BY created_at ASC, id ASC",
        (status,),
    ).fetchall()


def complete_task(task_id: int) -> bool:
    """Passe une tâche à « terminée ». Renvoie False si elle n'était pas à faire."""
    db = get_db()
    # completed_at au même format que created_at : UTC avec millisecondes.
    cur = db.execute(
        "UPDATE tasks SET status = 'done', "
        "completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
        "WHERE id = ? AND status = 'todo'",
        (task_id,),
    )
    db.commit()
    return cur.rowcount == 1


def progress_percent(done: int, total: int) -> int:
    """Pourcentage entier arrondi au plus proche (0,5 vers le haut).

    100 % n'est affiché que si tout est terminé, et 0 % seulement si rien ne l'est :
    avec 199 tâches sur 200, on lit 99 % et non 100 %.
    """
    if total == 0:
        return 0
    pct = (200 * done + total) // (2 * total)
    if done < total:
        pct = min(pct, 99)
    if done > 0:
        pct = max(pct, 1)
    return pct


def get_stats() -> dict[str, int]:
    row = get_db().execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(status = 'done'), 0) AS done FROM tasks"
    ).fetchone()
    total, done = row["total"], row["done"]
    return {
        "total": total,
        "done": done,
        "todo": total - done,
        "pct": progress_percent(done, total),
    }
