"""Routes HTTP. Chaque POST se termine par une redirection (Post/Redirect/Get)."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from . import queries

bp = Blueprint("tasks", __name__)


@bp.get("/")
def index():
    return render_template(
        "index.html",
        todo=queries.list_tasks("todo"),
        done=queries.list_tasks("done"),
        stats=queries.get_stats(),
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
