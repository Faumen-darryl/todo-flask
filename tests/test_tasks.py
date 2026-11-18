"""Tests de la to-do list : ordre, validation sans suppression, progression."""

import shutil
import sqlite3
import subprocess
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path

import pytest

from app import create_app, queries
from app.filters import paris_datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Outils
# --------------------------------------------------------------------------- #


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "todo.db"


@pytest.fixture
def app(db_path):
    return create_app({"TESTING": True, "DATABASE": str(db_path), "SECRET_KEY": "test"})


@pytest.fixture
def client(app):
    return app.test_client()


def sql(db_path, query, params=()):
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute(query, params).fetchall()
        conn.commit()
        return rows


def row_count(db_path):
    return sql(db_path, "SELECT COUNT(*) FROM tasks")[0][0]


def add(client, title):
    return client.post("/tasks", data={"title": title})


class TaskListParser(HTMLParser):
    """Récupère les titres affichés dans les listes « À faire » et « Terminées »."""

    def __init__(self):
        super().__init__()
        self.lists = {"todo-list": [], "done-list": []}
        self._list = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "ol" and attrs.get("id") in self.lists:
            self._list = attrs["id"]
        elif tag == "span" and self._list and "task-title" in (attrs.get("class") or "").split():
            self._in_title = True
            self.lists[self._list].append("")

    def handle_endtag(self, tag):
        if tag == "ol":
            self._list = None
        elif tag == "span":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.lists[self._list][-1] += data


def displayed(client):
    """(titres à faire, titres terminés) tels qu'affichés sur la page, dans l'ordre."""
    parser = TaskListParser()
    parser.feed(client.get("/").get_data(as_text=True))
    return parser.lists["todo-list"], parser.lists["done-list"]


# --------------------------------------------------------------------------- #
# Ordre d'affichage
# --------------------------------------------------------------------------- #


def test_first_added_task_is_displayed_above_the_second(client):
    add(client, "Première")
    add(client, "Seconde")

    todo, done = displayed(client)
    assert todo == ["Première", "Seconde"]
    assert done == []


def test_order_is_created_at_then_id(app, client, db_path):
    sql(
        db_path,
        "INSERT INTO tasks (title, created_at) VALUES (?, ?), (?, ?), (?, ?)",
        (
            "Saisie à 10 h 30", "2026-11-18T09:30:00.000Z",
            "Saisie à 10 h (a)", "2026-11-18T09:00:00.000Z",
            "Saisie à 10 h (b)", "2026-11-18T09:00:00.000Z",
        ),
    )
    expected = ["Saisie à 10 h (a)", "Saisie à 10 h (b)", "Saisie à 10 h 30"]

    with app.app_context():
        assert [t["title"] for t in queries.list_tasks("todo")] == expected
    assert displayed(client)[0] == expected


def test_done_tasks_keep_entry_order(client):
    add(client, "A")
    add(client, "B")
    client.post("/tasks/2/done")
    client.post("/tasks/1/done")

    assert displayed(client)[1] == ["A", "B"]


# --------------------------------------------------------------------------- #
# Validation : jamais de suppression
# --------------------------------------------------------------------------- #


def test_completing_moves_task_to_done_without_deleting(client, db_path):
    add(client, "Envoyer le rapport")
    add(client, "Appeler le fournisseur")
    assert row_count(db_path) == 2

    response = client.post("/tasks/1/done")

    assert response.status_code == 302
    assert row_count(db_path) == 2
    assert displayed(client) == (["Appeler le fournisseur"], ["Envoyer le rapport"])
    status, completed_at = sql(db_path, "SELECT status, completed_at FROM tasks WHERE id = 1")[0]
    assert status == "done"
    assert completed_at is not None


def test_completing_twice_is_harmless(client, db_path):
    add(client, "Tâche")
    client.post("/tasks/1/done")
    first_completed_at = sql(db_path, "SELECT completed_at FROM tasks WHERE id = 1")[0][0]

    response = client.post("/tasks/1/done")

    assert response.status_code == 302
    assert sql(db_path, "SELECT completed_at FROM tasks WHERE id = 1")[0][0] == first_completed_at


def test_completing_unknown_task_returns_404(client):
    assert client.post("/tasks/42/done").status_code == 404


def test_there_is_no_delete_route(client, db_path):
    add(client, "Tâche")

    assert client.post("/tasks/1/delete").status_code == 404
    assert client.get("/tasks/1/done").status_code == 405
    assert row_count(db_path) == 1


# --------------------------------------------------------------------------- #
# Progression
# --------------------------------------------------------------------------- #


def test_progress_is_zero_when_there_are_no_tasks(app, client):
    with app.app_context():
        assert queries.get_stats() == {"total": 0, "done": 0, "todo": 0, "pct": 0}

    html = client.get("/").get_data(as_text=True)
    assert "0 / 0" in html
    assert "(0&nbsp;%)" in html
    assert 'style="width: 0%"' in html


def test_progress_updates_after_each_completion(client):
    for title in ("Un", "Deux", "Trois"):
        add(client, title)

    client.post("/tasks/1/done")
    html = client.get("/").get_data(as_text=True)
    assert "1 / 3" in html and "(33&nbsp;%)" in html

    client.post("/tasks/2/done")
    html = client.get("/").get_data(as_text=True)
    assert "2 / 3" in html and "(67&nbsp;%)" in html

    client.post("/tasks/3/done")
    html = client.get("/").get_data(as_text=True)
    assert "3 / 3" in html and "(100&nbsp;%)" in html


@pytest.mark.parametrize(
    ("done", "total", "expected"),
    [
        (0, 0, 0),
        (0, 5, 0),
        (1, 3, 33),
        (2, 3, 67),
        (7, 12, 58),
        (1, 8, 13),    # 12,5 -> 13 (arrondi au plus proche, pas « bancaire »)
        (5, 8, 63),    # 62,5 -> 63
        (3, 3, 100),
        (199, 200, 99),  # jamais 100 % tant qu'une tâche reste à faire
        (1, 300, 1),     # jamais 0 % dès qu'une tâche est terminée
    ],
)
def test_progress_percent(done, total, expected):
    assert queries.progress_percent(done, total) == expected


# --------------------------------------------------------------------------- #
# Ajout et contrôle du titre
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("title", ["", "   ", "\t\n", None])
def test_empty_title_is_refused(client, db_path, title):
    data = {} if title is None else {"title": title}

    response = client.post("/tasks", data=data, follow_redirects=True)

    assert response.status_code == 200
    assert "Le titre de la tâche est obligatoire." in response.get_data(as_text=True)
    assert row_count(db_path) == 0


def test_title_is_stripped(client):
    add(client, "   Préparer la réunion   ")
    assert displayed(client)[0] == ["Préparer la réunion"]


def test_title_length_is_limited(client, db_path):
    add(client, "x" * queries.MAX_TITLE_LENGTH)
    response = client.post(
        "/tasks", data={"title": "x" * (queries.MAX_TITLE_LENGTH + 1)}, follow_redirects=True
    )

    assert "ne doit pas dépasser 200 caractères" in response.get_data(as_text=True)
    assert row_count(db_path) == 1


def test_database_rejects_blank_titles_too(db_path, app):
    with pytest.raises(sqlite3.IntegrityError):
        sql(db_path, "INSERT INTO tasks (title) VALUES (?)", ("   ",))


def test_titles_are_stored_and_shown_literally(client, db_path):
    add(client, "'); DROP TABLE tasks; --")
    add(client, "<script>alert(1)</script>")

    assert row_count(db_path) == 2
    html = client.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert displayed(client)[0] == ["'); DROP TABLE tasks; --", "<script>alert(1)</script>"]


def test_post_redirect_get(client, db_path):
    response = add(client, "Tâche")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    client.get("/")  # un rafraîchissement de la page ne ré-ajoute rien
    client.get("/")
    assert row_count(db_path) == 1


# --------------------------------------------------------------------------- #
# Persistance et base de données
# --------------------------------------------------------------------------- #


def test_tasks_survive_an_application_restart(db_path):
    first = create_app({"TESTING": True, "DATABASE": str(db_path)}).test_client()
    add(first, "Avant redémarrage")
    first.post("/tasks/1/done")
    add(first, "Encore à faire")

    restarted = create_app({"TESTING": True, "DATABASE": str(db_path)}).test_client()
    assert displayed(restarted) == (["Encore à faire"], ["Avant redémarrage"])


def test_init_db_command_keeps_existing_tasks(app, client, db_path):
    add(client, "Ne pas perdre")

    result = app.test_cli_runner().invoke(args=["init-db"])

    assert result.exit_code == 0
    assert "Base prête" in result.output
    assert displayed(client)[0] == ["Ne pas perdre"]


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("utc", "paris"),
    [
        ("2026-01-15T09:00:00.000Z", "15/01/2026 à 10:00"),  # heure d'hiver (UTC+1)
        ("2026-07-15T08:00:00.000Z", "15/07/2026 à 10:00"),  # heure d'été (UTC+2)
        ("2026-12-31T23:30:00.000Z", "01/01/2027 à 00:30"),  # changement de jour
        (None, ""),
    ],
)
def test_paris_datetime(utc, paris):
    assert paris_datetime(utc) == paris


def test_page_shows_creation_and_completion_dates_in_paris_time(client, db_path):
    sql(
        db_path,
        "INSERT INTO tasks (title, status, created_at, completed_at) VALUES (?, 'done', ?, ?)",
        ("Faite", "2026-03-02T08:15:00.000Z", "2026-03-02T16:45:00.000Z"),
    )
    html = client.get("/").get_data(as_text=True)
    assert "02/03/2026 à 09:15" in html
    assert "02/03/2026 à 17:45" in html


# --------------------------------------------------------------------------- #
# Données locales : rien de sensible dans git
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(shutil.which("git") is None, reason="git non installé")
@pytest.mark.parametrize("path", [".venv/", "instance/todo.db", "autre.db"])
def test_local_data_is_ignored_by_git(path):
    in_repo = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    if in_repo.returncode != 0:
        pytest.skip("pas un dépôt git")
    ignored = subprocess.run(["git", "check-ignore", "-q", path], cwd=PROJECT_ROOT)
    assert ignored.returncode == 0, f"{path} n'est pas ignoré par git"
