// Règles métier de la version en ligne (GitHub Pages), identiques à app/queries.py :
// ordre d'entrée, aucune suppression, même calcul de la progression.
// Module pur, sans accès au DOM ni au stockage : testé avec `node --test`.

export const MAX_TITLE_LENGTH = 200;
export const STATUSES = ["todo", "done"];

export class InvalidTitle extends Error {}

export function emptyState() {
  return { version: 1, nextId: 1, tasks: [] };
}

/** Même format que SQLite strftime('%Y-%m-%dT%H:%M:%fZ') : UTC avec millisecondes. */
function isoNow(now) {
  return (now ?? new Date()).toISOString();
}

export function cleanTitle(title) {
  const cleaned = String(title ?? "").trim();
  if (!cleaned) {
    throw new InvalidTitle("Le titre de la tâche est obligatoire.");
  }
  const length = [...cleaned].length; // en caractères, comme len() en Python
  if (length > MAX_TITLE_LENGTH) {
    throw new InvalidTitle(
      `Le titre ne doit pas dépasser ${MAX_TITLE_LENGTH} caractères (${length} saisis).`,
    );
  }
  return cleaned;
}

/** Ajoute une tâche « à faire » et la renvoie. Modifie `state`. */
export function addTask(state, title, now) {
  const task = {
    id: state.nextId,
    title: cleanTitle(title),
    status: "todo",
    created_at: isoNow(now),
    completed_at: null,
  };
  state.nextId += 1;
  state.tasks.push(task);
  return task;
}

function byEntryOrder(a, b) {
  if (a.created_at !== b.created_at) return a.created_at < b.created_at ? -1 : 1;
  return a.id - b.id;
}

/** Tâches d'un statut, la plus ancienne en premier (created_at puis id). */
export function listTasks(state, status) {
  if (!STATUSES.includes(status)) throw new Error(`Statut inconnu : ${status}`);
  return state.tasks.filter((t) => t.status === status).sort(byEntryOrder);
}

/** Passe une tâche à « terminée ». Renvoie false si elle n'était pas à faire. */
export function completeTask(state, id, now) {
  const task = state.tasks.find((t) => t.id === id && t.status === "todo");
  if (!task) return false;
  task.status = "done";
  task.completed_at = isoNow(now);
  return true;
}

/** Arrondi au plus proche ; 100 % seulement si tout est fait, 0 % seulement si rien ne l'est. */
export function progressPercent(done, total) {
  if (total === 0) return 0;
  let pct = Math.floor((200 * done + total) / (2 * total));
  if (done < total) pct = Math.min(pct, 99);
  if (done > 0) pct = Math.max(pct, 1);
  return pct;
}

export function getStats(state) {
  const total = state.tasks.length;
  const done = state.tasks.filter((t) => t.status === "done").length;
  return { total, done, todo: total - done, pct: progressPercent(done, total) };
}

// --------------------------------------------------------------------------
// Dates en heure de Paris
// --------------------------------------------------------------------------

const DATE_TIME = new Intl.DateTimeFormat("fr-FR", {
  timeZone: "Europe/Paris",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const TODAY = new Intl.DateTimeFormat("fr-FR", {
  timeZone: "Europe/Paris",
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
});

/** '2026-11-18T09:30:00.000Z' -> '18 / 11 / 2026 à 10:30' (comme le filtre Jinja `paris`). */
export function formatParis(iso) {
  if (!iso) return "";
  const parts = Object.fromEntries(
    DATE_TIME.formatToParts(new Date(iso)).map((p) => [p.type, p.value]),
  );
  return `${parts.day} / ${parts.month} / ${parts.year} à ${parts.hour}:${parts.minute}`;
}

/** 'mercredi 18 novembre 2026' (comme today_paris() côté Python). */
export function todayParis(now) {
  return TODAY.format(now ?? new Date());
}

// --------------------------------------------------------------------------
// Lecture, sauvegarde et import
// --------------------------------------------------------------------------

const ISO_UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z$/;

function normalizeTask(raw) {
  if (!raw || typeof raw !== "object") return null;
  let title;
  try {
    title = cleanTitle(raw.title);
  } catch {
    return null;
  }
  const status = raw.status === "done" ? "done" : "todo";
  if (typeof raw.created_at !== "string" || !ISO_UTC.test(raw.created_at)) return null;
  const completedOk = typeof raw.completed_at === "string" && ISO_UTC.test(raw.completed_at);
  return {
    id: Number.isInteger(raw.id) && raw.id > 0 ? raw.id : null,
    title,
    status,
    created_at: raw.created_at,
    completed_at: status === "done" ? (completedOk ? raw.completed_at : raw.created_at) : null,
  };
}

/** Lit un état enregistré (JSON). Les entrées invalides sont ignorées. */
export function parseState(json) {
  const data = typeof json === "string" ? JSON.parse(json) : json;
  const rawTasks = Array.isArray(data) ? data : data?.tasks;
  if (!Array.isArray(rawTasks)) throw new Error("Fichier de tâches illisible.");

  const state = emptyState();
  const usedIds = new Set();
  const pending = [];
  for (const raw of rawTasks) {
    const task = normalizeTask(raw);
    if (!task) continue;
    if (task.id === null || usedIds.has(task.id)) {
      pending.push(task);
    } else {
      usedIds.add(task.id);
      state.tasks.push(task);
    }
  }
  let next = Math.max(0, ...usedIds, Number.isInteger(data?.nextId) ? data.nextId - 1 : 0) + 1;
  for (const task of pending) {
    task.id = next++;
    state.tasks.push(task);
  }
  state.nextId = next;
  return state;
}

export function serialize(state) {
  return JSON.stringify({ version: 1, nextId: state.nextId, tasks: state.tasks });
}

/**
 * Fusionne une sauvegarde dans l'état courant, sans jamais rien supprimer :
 * les tâches absentes sont ajoutées, et une tâche à faire que la sauvegarde
 * indique comme terminée passe dans « Terminées ». Une tâche terminée ne
 * redevient jamais « à faire ».
 */
export function mergeImport(state, imported) {
  const key = (t) => `${t.created_at}\u0000${t.title}`;
  const existing = new Map(state.tasks.map((t) => [key(t), t]));
  let added = 0;
  let completed = 0;
  for (const task of [...imported.tasks].sort(byEntryOrder)) {
    const current = existing.get(key(task));
    if (!current) {
      const copy = { ...task, id: state.nextId };
      state.nextId += 1;
      state.tasks.push(copy);
      existing.set(key(copy), copy);
      added += 1;
    } else if (current.status === "todo" && task.status === "done") {
      current.status = "done";
      current.completed_at = task.completed_at;
      completed += 1;
    }
  }
  return { added, completed };
}
