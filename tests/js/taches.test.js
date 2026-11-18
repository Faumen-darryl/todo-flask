// Tests des règles métier de la version en ligne : node --test tests/js/*.test.js
import assert from "node:assert/strict";
import { test } from "node:test";

import * as T from "../../app/static/js/taches.js";

const at = (iso) => new Date(iso);

function stateWith(...titles) {
  const state = T.emptyState();
  titles.forEach((title, i) => T.addTask(state, title, at(`2026-11-18T09:0${i}:00.000Z`)));
  return state;
}

const titles = (tasks) => tasks.map((t) => t.title);

// --- Ordre d'entrée ---------------------------------------------------------

test("la première tâche ajoutée est au-dessus de la seconde", () => {
  const state = T.emptyState();
  T.addTask(state, "Première");
  T.addTask(state, "Seconde");
  assert.deepEqual(titles(T.listTasks(state, "todo")), ["Première", "Seconde"]);
});

test("l'ordre suit created_at puis id", () => {
  const state = T.emptyState();
  T.addTask(state, "Saisie à 10 h 30", at("2026-11-18T09:30:00.000Z"));
  T.addTask(state, "Saisie à 10 h (a)", at("2026-11-18T09:00:00.000Z"));
  T.addTask(state, "Saisie à 10 h (b)", at("2026-11-18T09:00:00.000Z"));
  assert.deepEqual(titles(T.listTasks(state, "todo")), [
    "Saisie à 10 h (a)",
    "Saisie à 10 h (b)",
    "Saisie à 10 h 30",
  ]);
});

test("les terminées gardent l'ordre d'entrée", () => {
  const state = stateWith("A", "B");
  T.completeTask(state, 2);
  T.completeTask(state, 1);
  assert.deepEqual(titles(T.listTasks(state, "done")), ["A", "B"]);
});

// --- Validation sans suppression -------------------------------------------

test("valider déplace la tâche sans rien supprimer", () => {
  const state = stateWith("Envoyer le rapport", "Appeler le fournisseur");
  const now = at("2026-11-18T15:00:00.000Z");

  assert.equal(T.completeTask(state, 1, now), true);

  assert.equal(state.tasks.length, 2);
  assert.deepEqual(titles(T.listTasks(state, "todo")), ["Appeler le fournisseur"]);
  assert.deepEqual(titles(T.listTasks(state, "done")), ["Envoyer le rapport"]);
  assert.equal(state.tasks[0].completed_at, "2026-11-18T15:00:00.000Z");
});

test("valider deux fois ne change rien", () => {
  const state = stateWith("Tâche");
  T.completeTask(state, 1, at("2026-11-18T15:00:00.000Z"));
  assert.equal(T.completeTask(state, 1, at("2026-11-18T16:00:00.000Z")), false);
  assert.equal(state.tasks[0].completed_at, "2026-11-18T15:00:00.000Z");
});

test("valider une tâche inconnue renvoie false", () => {
  assert.equal(T.completeTask(stateWith("Tâche"), 42), false);
});

test("le module n'expose aucune fonction de suppression", () => {
  const names = Object.keys(T).map((n) => n.toLowerCase());
  assert.ok(!names.some((n) => n.includes("delete") || n.includes("remove")));
});

// --- Progression -----------------------------------------------------------

test("0 % quand il n'y a aucune tâche", () => {
  assert.deepEqual(T.getStats(T.emptyState()), { total: 0, done: 0, todo: 0, pct: 0 });
});

test("la progression suit les validations", () => {
  const state = stateWith("Un", "Deux", "Trois");
  T.completeTask(state, 1);
  assert.deepEqual(T.getStats(state), { total: 3, done: 1, todo: 2, pct: 33 });
  T.completeTask(state, 2);
  assert.equal(T.getStats(state).pct, 67);
  T.completeTask(state, 3);
  assert.equal(T.getStats(state).pct, 100);
});

test("même arrondi que la version Python", () => {
  const cases = [
    [0, 0, 0], [0, 5, 0], [1, 3, 33], [2, 3, 67], [7, 12, 58],
    [1, 8, 13], [5, 8, 63], [3, 3, 100], [199, 200, 99], [1, 300, 1],
  ];
  for (const [done, total, expected] of cases) {
    assert.equal(T.progressPercent(done, total), expected, `${done} / ${total}`);
  }
});

// --- Titre -------------------------------------------------------------------

test("un titre vide est refusé", () => {
  for (const title of ["", "   ", "\t\n", null, undefined]) {
    const state = T.emptyState();
    assert.throws(() => T.addTask(state, title), T.InvalidTitle);
    assert.equal(state.tasks.length, 0);
  }
});

test("le titre est nettoyé et limité à 200 caractères", () => {
  const state = T.emptyState();
  assert.equal(T.addTask(state, "   Préparer la réunion   ").title, "Préparer la réunion");
  T.addTask(state, "é".repeat(200));
  assert.throws(() => T.addTask(state, "x".repeat(201)), /ne doit pas dépasser 200 caractères/);
  assert.equal(state.tasks.length, 2);
});

// --- Dates -----------------------------------------------------------------

test("dates affichées en heure de Paris", () => {
  assert.equal(T.formatParis("2026-01-15T09:00:00.000Z"), "15 / 01 / 2026 à 10:00"); // hiver
  assert.equal(T.formatParis("2026-07-15T08:00:00.000Z"), "15 / 07 / 2026 à 10:00"); // été
  assert.equal(T.formatParis("2026-12-31T23:30:00.000Z"), "01 / 01 / 2027 à 00:30");
  assert.equal(T.formatParis(null), "");
});

test("date du jour en toutes lettres", () => {
  assert.equal(T.todayParis(at("2026-11-18T12:00:00Z")), "mercredi 18 novembre 2026");
  assert.equal(T.todayParis(at("2026-08-02T23:30:00Z")), "lundi 3 août 2026");
});

test("created_at a le même format que SQLite", () => {
  const task = T.addTask(T.emptyState(), "Tâche");
  assert.match(task.created_at, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
});

// --- Sauvegarde et import ----------------------------------------------------

test("un état sauvegardé se relit à l'identique", () => {
  const state = stateWith("A", "B");
  T.completeTask(state, 1);
  const again = T.parseState(T.serialize(state));
  assert.deepEqual(again, state);
  assert.equal(T.addTask(again, "C").id, 3);
});

test("la lecture ignore les entrées invalides et répare les id", () => {
  const state = T.parseState({
    tasks: [
      { id: 1, title: "Bonne", status: "todo", created_at: "2026-11-18T09:00:00.000Z" },
      { id: 1, title: "Doublon d'id", status: "done", created_at: "2026-11-18T09:01:00.000Z" },
      { id: 2, title: "   ", status: "todo", created_at: "2026-11-18T09:02:00.000Z" },
      { id: 3, title: "Date invalide", status: "todo", created_at: "hier" },
      "pas un objet",
    ],
  });
  assert.deepEqual(titles(state.tasks), ["Bonne", "Doublon d'id"]);
  assert.deepEqual(state.tasks.map((t) => t.id), [1, 2]);
  assert.equal(state.tasks[1].completed_at, "2026-11-18T09:01:00.000Z");
  assert.equal(state.nextId, 3);
});

test("un fichier qui n'est pas une sauvegarde est refusé", () => {
  assert.throws(() => T.parseState('{"pas":"bon"}'));
  assert.throws(() => T.parseState("pas du JSON"));
});

test("l'import ajoute ce qui manque et ne supprime jamais rien", () => {
  const local = stateWith("A", "B");
  const backup = stateWith("A", "B", "C");
  T.completeTask(backup, 2, at("2026-11-18T15:00:00.000Z"));

  assert.deepEqual(T.mergeImport(local, backup), { added: 1, completed: 1 });
  assert.deepEqual(titles(T.listTasks(local, "todo")), ["A", "C"]);
  assert.deepEqual(titles(T.listTasks(local, "done")), ["B"]);

  // Réimporter le même fichier ne change rien.
  assert.deepEqual(T.mergeImport(local, backup), { added: 0, completed: 0 });
  assert.equal(local.tasks.length, 3);
});

test("l'import ne remet jamais une tâche terminée à faire", () => {
  const local = stateWith("A");
  T.completeTask(local, 1);
  const backup = stateWith("A");
  T.mergeImport(local, backup);
  assert.equal(local.tasks[0].status, "done");
});
