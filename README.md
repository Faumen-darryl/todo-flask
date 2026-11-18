# todo-flask

Petite to-do list de travail, en local : on note les tâches au fil de l'eau, on les valide une par une et on suit sa progression.

- Les tâches s'affichent **par ordre d'entrée** : la plus ancienne en haut.
- Une tâche validée **n'est jamais supprimée** : elle passe dans « Terminées », avec sa date de validation.
- La **progression** (terminées / total et pourcentage) est affichée en permanence.
- Les données restent **en local**, dans un fichier SQLite (`instance/todo.db`) qui n'est pas versionné.

Stack : Python 3.11+, Flask, SQLite (module `sqlite3` de la bibliothèque standard), templates Jinja2, CSS maison, pytest.

## Installation

```bash
git clone https://github.com/Faumen-darryl/todo-flask.git
cd todo-flask
python -m venv .venv
```

Activer l'environnement virtuel :

```bash
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows (cmd)
.venv\Scripts\Activate.ps1       # Windows (PowerShell)
```

Installer les dépendances et créer la base :

```bash
pip install -r requirements.txt
flask --app app init-db          # crée instance/todo.db
```

`init-db` ne supprime jamais de données : on peut la relancer sans risque. L'application crée aussi la base toute seule au démarrage si elle n'existe pas.

## Lancement

```bash
flask --app app run --debug
```

Puis ouvrir <http://127.0.0.1:5000>. Le serveur n'écoute que sur la machine locale.

## Tests

```bash
pytest
```

Les tests couvrent l'ordre d'affichage, la validation sans suppression, la progression (0 % sans tâche), le refus d'un titre vide, la persistance après redémarrage, l'affichage des dates en heure de Paris et le fait que `.venv/` et la base sont ignorés par git. Ils tournent aussi sur GitHub Actions à chaque push.

## Où sont mes données ?

Dans le fichier `instance/todo.db`, à côté du code. L'environnement virtuel `.venv/` ne contient que les paquets Python.

- **Sauvegarder** : copier `instance/todo.db` (application arrêtée).
- **Repartir de zéro** : supprimer ce fichier, puis relancer `flask --app app init-db`.
- **Confidentialité** : `instance/` et `*.db` sont dans `.gitignore`, les tâches ne partent jamais sur GitHub.

Les dates sont stockées en UTC (`created_at`, `completed_at`) et affichées en heure de Paris.

## Structure

```
app/
├── __init__.py      create_app() : configuration, chemin de la base, routes
├── db.py            connexion SQLite, init_db(), commande `flask init-db`
├── queries.py       add_task, list_tasks, complete_task, get_stats (SQL paramétré)
├── routes.py        GET /, POST /tasks, POST /tasks/<id>/done
├── filters.py       filtre Jinja `paris` (UTC -> heure de Paris)
├── schema.sql       table tasks
├── templates/       base.html, index.html
└── static/          style.css (thème blanc et bleu)
tests/test_tasks.py
```

| Méthode | URL                | Action                                      |
|---------|--------------------|---------------------------------------------|
| GET     | `/`                | Formulaire, progression, listes             |
| POST    | `/tasks`           | Ajouter une tâche, puis redirection vers `/`|
| POST    | `/tasks/<id>/done` | Valider une tâche, puis redirection vers `/`|

Chaque action se termine par une redirection (Post/Redirect/Get) : rafraîchir la page ne ré-ajoute rien. Aucun JavaScript n'est nécessaire.

## Hébergement

GitHub stocke le code mais n'exécute pas d'application Flask (GitHub Pages ne sert que des sites statiques). L'application tourne en local avec `flask run`. Pour une mise en ligne plus tard (PythonAnywhere, Render…), il faudra un disque persistant pour le fichier SQLite ou une autre base.
