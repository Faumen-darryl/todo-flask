"""Routes HTTP. Chaque POST se termine par une redirection (Post/Redirect/Get)."""

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from . import queries

bp = Blueprint("tasks", __name__)


@bp.get("/")
def index():
    if current_app.config["STATIC_SITE"]:
        # Site public figé : jamais de tâches de la base locale dans le HTML.
        todo, done = [], []
        stats = {"total": 0, "done": 0, "todo": 0, "pct": 0}
    else:
        todo = queries.list_tasks("todo")
        done = queries.list_tasks("done")
        stats = queries.get_stats()
    return render_template(
        "index.html",
        todo=todo,
        done=done,
        stats=stats,
        max_title_length=queries.MAX_TITLE_LENGTH,
    )


@bp.post("/tasks")
def create_task():
    try:
        queries.add_task(request.form.get("title"))
    except queries.InvalidTitle as exc:
        flash(str(exc), "error")
    return redirect(url_for("tasks.index"))


@bp.post("/tasks/<int:task_id>/done")
def complete_task(task_id: int):
    if not queries.complete_task(task_id) and queries.get_task(task_id) is None:
        abort(404)
    # Une tâche déjà terminée (double clic, onglet périmé) : rien à faire.
    return redirect(url_for("tasks.index"))
