// Version en ligne (GitHub Pages) : les tâches sont enregistrées dans le
// navigateur (localStorage). Ce script n'est chargé que dans le site figé ;
// en local, Flask et SQLite font le travail et la page n'utilise pas de JavaScript.

import * as T from "./taches.js";

const KEY = "todo-flask:taches";
const $ = (id) => document.getElementById(id);

let state = T.emptyState();

// --------------------------------------------------------------------------
// Stockage
// --------------------------------------------------------------------------

function load() {
  let raw;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    state = T.emptyState();
    flash("error", "Ce navigateur bloque l'enregistrement des données : les tâches seront perdues en fermant la page.");
    return;
  }
  if (!raw) {
    state = T.emptyState();
    return;
  }
  try {
    state = T.parseState(raw);
  } catch {
    // Données illisibles : on les met de côté au lieu de les écraser.
    try {
      localStorage.setItem(`${KEY}:illisible:${Date.now()}`, raw);
    } catch {
      /* rien de plus à faire */
    }
    state = T.emptyState();
    flash("error", "Les tâches enregistrées étaient illisibles. Elles ont été mises de côté et la liste repart à zéro.");
  }
}

function save() {
  try {
    localStorage.setItem(KEY, T.serialize(state));
    return true;
  } catch {
    flash("error", "Impossible d'enregistrer dans ce navigateur (navigation privée ou stockage plein). Exportez vos tâches pour ne pas les perdre.");
    return false;
  }
}

// --------------------------------------------------------------------------
// Affichage
// --------------------------------------------------------------------------

function flash(category, message) {
  const p = document.createElement("p");
  p.className = `flash flash--${category}`;
  p.setAttribute("role", category === "error" ? "alert" : "status");
  p.textContent = message;
  $("flash-zone").replaceChildren(p);
}

function clearFlash() {
  $("flash-zone").replaceChildren();
}

function setTime(node, selector, iso) {
  const time = node.querySelector(selector);
  time.dateTime = iso;
  time.textContent = T.formatParis(iso);
}

function fillTodo(node, task) {
  node.querySelector(".task-title").textContent = task.title;
  setTime(node, ".js-created", task.created_at);
  node.querySelector("form").dataset.id = String(task.id);
  node.querySelector("button").setAttribute("aria-label", `Valider « ${task.title} »`);
}

function fillDone(node, task) {
  node.querySelector(".task-title").textContent = task.title;
  setTime(node, ".js-created", task.created_at);
  setTime(node, ".js-completed", task.completed_at);
}

function fillList(listId, emptyId, templateId, tasks, fill) {
  const template = $(templateId).content.firstElementChild;
  const items = tasks.map((task) => {
    const node = template.cloneNode(true);
    fill(node, task);
    return node;
  });
  $(listId).replaceChildren(...items);
  $(emptyId).hidden = tasks.length > 0;
}

function render() {
  const todo = T.listTasks(state, "todo");
  const done = T.listTasks(state, "done");
  const stats = T.getStats(state);

  fillList("todo-list", "todo-empty", "tpl-todo", todo, fillTodo);
  fillList("done-list", "done-empty", "tpl-done", done, fillDone);
  $("todo-count").textContent = String(todo.length);
  $("done-count").textContent = String(done.length);

  const strong = document.createElement("strong");
  strong.textContent = `${stats.done} / ${stats.total}`;
  $("progress-text").replaceChildren(
    strong,
    ` terminée${stats.done > 1 ? "s" : ""} (${stats.pct} %)`,
  );
  $("progress-bar").style.width = `${stats.pct}%`;
  $("progress").setAttribute("aria-valuenow", String(stats.pct));
  document.title = `Tâches de travail (${stats.pct} %)`;
}

// --------------------------------------------------------------------------
// Actions
// --------------------------------------------------------------------------

function onAdd(event) {
  event.preventDefault();
  const input = $("title");
  try {
    T.addTask(state, input.value);
  } catch (err) {
    if (err instanceof T.InvalidTitle) {
      flash("error", err.message);
      return;
    }
    throw err;
  }
  clearFlash();
  save();
  render();
  input.value = "";
  input.focus();
}

function onComplete(event) {
  const form = event.target.closest("form[data-id]");
  if (!form) return;
  event.preventDefault();
  const buttons = [...$("todo-list").querySelectorAll("button")];
  const index = buttons.indexOf(form.querySelector("button"));

  if (T.completeTask(state, Number(form.dataset.id))) {
    save();
    render();
  }
  // Garde le focus clavier sur la tâche suivante (ou le champ de saisie).
  const next = $("todo-list").querySelectorAll("button")[index];
  (next ?? $("title")).focus();
}

function onExport() {
  const blob = new Blob([JSON.stringify(JSON.parse(T.serialize(state)), null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `taches-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function onImport(event) {
  const input = event.target;
  const [file] = input.files;
  input.value = "";
  if (!file) return;
  let imported;
  try {
    imported = T.parseState(await file.text());
  } catch {
    flash("error", "Ce fichier n'est pas une sauvegarde de tâches valide.");
    return;
  }
  const { added, completed } = T.mergeImport(state, imported);
  save();
  render();
  const s = (n) => (n > 1 ? "s" : "");
  flash(
    "info",
    `Import terminé : ${added} tâche${s(added)} ajoutée${s(added)}, ${completed} passée${s(completed)} en « Terminées ».`,
  );
}

// --------------------------------------------------------------------------
// Démarrage
// --------------------------------------------------------------------------

$("today").textContent = T.todayParis();
load();
render();

$("add-form").addEventListener("submit", onAdd);
$("todo-list").addEventListener("submit", onComplete);
$("export").addEventListener("click", onExport);
$("import-file").addEventListener("change", onImport);

// Plusieurs onglets ouverts : chacun se met à jour quand un autre enregistre.
window.addEventListener("storage", (event) => {
  if (event.key === KEY) {
    load();
    render();
  }
});
