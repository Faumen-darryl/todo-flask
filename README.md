# todo-flask

Petite to-do list de travail : on note les tâches au fil de l'eau, on les valide une par une et on suit sa progression.

**Version en ligne : <https://faumen-darryl.github.io/todo-flask/>**, rien à installer.

- Les tâches s'affichent **par ordre d'entrée** : la plus ancienne en haut.
- Une tâche validée **n'est jamais supprimée** : elle passe dans « Terminées », avec sa date de validation.
- La **progression** (terminées / total et pourcentage) est affichée en permanence.
- Les tâches ne sont **jamais publiées** : elles restent sur votre poste (voir ci-dessous).

Le design reprend l'identité visuelle du site [test-institut-etudes.com](https://www.test-institut-etudes.com/) : orange `#FF5E14`, fond pêche, texte bleu marine, titres en majuscules, cartes blanches, polices Barlow et Rajdhani.

## Deux versions, mêmes règles

| | Version en ligne (GitHub Pages) | Version locale (Flask) |
|---|---|---|
| Accès | <https://faumen-darryl.github.io/todo-flask/> | `flask --app app run`, puis <http://127.0.0.1:5000> |
| Tâches enregistrées | dans le navigateur (`localStorage`) | dans `instance/todo.db` (SQLite) |
| Fonctionnement | JavaScript (`app/static/js/`) | formulaires POST, sans JavaScript |

Les deux listes sont indépendantes. Les règles (ordre, validation sans suppression, calcul du pourcentage, format des dates) sont codées deux fois, en Python (`app/queries.py`) et en JavaScript (`app/static/js/taches.js`), et testées des deux côtés avec les mêmes cas.

### Version en ligne : où sont mes tâches ?

Dans le navigateur, sur l'ordinateur où vous les avez saisies. La page publiée est la même pour tout le monde, mais personne d'autre ne voit vos tâches.

- Elles ne passent pas d'un navigateur à l'autre, ni d'un poste à l'autre.
- Vider les données du navigateur pour ce site, ou naviguer en privé, les efface.
- Le bouton **Exporter** télécharge une sauvegarde (`taches-AAAA-MM-JJ.json`). **Importer** la recharge, par exemple sur un autre poste. L'import ajoute les tâches manquantes et ne supprime jamais rien.

## Version locale

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

Installer les dépendances et lancer :

```bash
pip install -r requirements.txt
flask --app app run --debug
```

La base `instance/todo.db` est créée au premier lancement (ou avec `flask --app app init-db`, qui ne supprime jamais de données). Pour la sauvegarder, copiez ce fichier, application arrêtée. `instance/` et `*.db` sont dans `.gitignore` : les tâches ne partent jamais sur GitHub.

## Déploiement

Chaque push lance le workflow **Tests et déploiement** (`.github/workflows/tests-et-deploiement.yml`) :

1. tests Python (`pytest`, sous Python 3.11 et 3.13) et JavaScript (`node --test`) ;
2. sur `main` uniquement : `python figer.py` génère le site statique dans `build/` (Frozen-Flask) ;
3. publication sur GitHub Pages.

Le site figé n'embarque aucune tâche : `figer.py` utilise une base temporaire vide et rend la page en mode `STATIC_SITE`.

Réglage à faire une fois dans le dépôt : **Settings → Pages → Build and deployment → Source : GitHub Actions**.

Aperçu local du site figé :

```bash
python figer.py
python -m http.server --directory build 8000
```

## Tests

```bash
pytest
node --test tests/js/*.test.js
```

## Structure

```
app/
├── __init__.py      create_app() : configuration, chemin de la base, routes
├── db.py            connexion SQLite, init_db(), commande `flask init-db`
├── queries.py       add_task, list_tasks, complete_task, get_stats (SQL paramétré)
├── routes.py        GET /, POST /tasks, POST /tasks/<id>/done
├── filters.py       filtre Jinja `paris` (UTC -> heure de Paris), date du jour
├── schema.sql       table tasks
├── templates/       base.html, index.html (macros des cartes, partagées par les deux versions)
└── static/
    ├── style.css    thème orange / pêche / bleu marine
    ├── js/          taches.js (règles métier), app.js (page en ligne)
    └── fonts/       Barlow et Rajdhani (woff2, licence SIL OFL 1.1)
figer.py             génération du site GitHub Pages
tests/               test_tasks.py, test_site_statique.py, js/taches.test.js
```

Routes de la version locale :

| Méthode | URL                | Action                                       |
|---------|--------------------|----------------------------------------------|
| GET     | `/`                | Formulaire, progression, listes              |
| POST    | `/tasks`           | Ajouter une tâche, puis redirection vers `/` |
| POST    | `/tasks/<id>/done` | Valider une tâche, puis redirection vers `/` |

Chaque action se termine par une redirection (Post/Redirect/Get) : rafraîchir la page ne ré-ajoute rien. La page ne charge aucune ressource externe : les polices sont servies depuis `app/static/fonts/`.
