"""Tests de la version en ligne (site figé pour GitHub Pages)."""

import sqlite3
from contextlib import closing

import pytest

from app import create_app
from figer import figer

URL_PAGES = "https://faumen-darryl.github.io/todo-flask/"


@pytest.fixture
def static_client(tmp_path):
    db_path = tmp_path / "todo.db"
    app = create_app({"TESTING": True, "STATIC_SITE": True, "DATABASE": str(db_path)})
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("INSERT INTO tasks (title) VALUES (?)", ("Tâche confidentielle",))
        conn.commit()
    return app.test_client()


@pytest.fixture(scope="module")
def build(tmp_path_factory):
    destination = tmp_path_factory.mktemp("site") / "build"
    figer(str(destination), url_de_base=URL_PAGES)
    return destination


def test_static_page_never_contains_database_tasks(static_client):
    html = static_client.get("/").get_data(as_text=True)

    assert "Tâche confidentielle" not in html
    assert "0 / 0" in html
    assert "(0&nbsp;%)" in html


def test_static_page_loads_the_script_and_card_templates(static_client):
    html = static_client.get("/").get_data(as_text=True)

    assert '<script type="module" src="/static/js/app.js"></script>' in html
    assert '<template id="tpl-todo">' in html
    assert '<template id="tpl-done">' in html
    assert 'id="export"' in html and 'id="import-file"' in html
    assert 'action="/tasks' not in html  # les formulaires sont gérés en JavaScript


def test_local_page_uses_no_javascript(tmp_path):
    client = create_app({"TESTING": True, "DATABASE": str(tmp_path / "t.db")}).test_client()
    html = client.get("/").get_data(as_text=True)

    assert "<script" not in html
    assert "<template" not in html
    assert 'action="/tasks"' in html


def test_freeze_generates_the_site(build):
    files = sorted(p.relative_to(build).as_posix() for p in build.rglob("*") if p.is_file())

    assert "index.html" in files
    for expected in (
        "static/style.css",
        "static/js/app.js",
        "static/js/taches.js",
        "static/fonts/barlow-latin-400-normal.woff2",
        "static/fonts/rajdhani-latin-700-normal.woff2",
        "static/fonts/OFL-Barlow.txt",
    ):
        assert expected in files
    assert not any(f.startswith("tasks") for f in files)
    assert not any(f.endswith(".db") for f in files)


def test_frozen_links_point_to_the_pages_subfolder(build):
    html = (build / "index.html").read_text(encoding="utf-8")

    assert 'href="/todo-flask/static/style.css"' in html
    assert 'src="/todo-flask/static/js/app.js"' in html
    assert "Version en ligne" in html


def test_frozen_card_templates_match_server_cards(build, tmp_path):
    """Les cartes du site en ligne sont celles du rendu Flask (mêmes macros)."""
    frozen = (build / "index.html").read_text(encoding="utf-8")
    template = frozen.split('<template id="tpl-todo">')[1].split("</template>")[0]

    client = create_app({"TESTING": True, "DATABASE": str(tmp_path / "t.db")}).test_client()
    client.post("/tasks", data={"title": "Exemple"})
    server = client.get("/").get_data(as_text=True)

    for marker in ('class="card task"', 'class="task-title"', "js-created", "btn--check"):
        assert marker in template
        assert marker in server
