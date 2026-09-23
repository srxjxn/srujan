// Two stores with the same surface. LocalStore keeps the log in this browser;
// RemoteStore keeps it on the sync backend (api/log.js) so every device sees the
// same data. Reads are synchronous over an in-memory copy; mutations return promises.
const KEY = "food-tracker:v1";
const SYNC_KEY = "food-tracker:sync";
export const DEFAULT_GOALS = { kcal: 2200, protein: 150, carbs: 220, fat: 70 };

const emptyState = () => ({ entries: [], customFoods: [], goals: {}, nextId: 1 });
const r1 = (x) => Math.round(x * 10) / 10;

export function getSyncConfig() {
  try { const raw = localStorage.getItem(SYNC_KEY); if (raw) { const c = JSON.parse(raw); if (c && c.password) return c; } } catch {}
  return null;
}
export function setSyncConfig(cfg) { try { localStorage.setItem(SYNC_KEY, JSON.stringify(cfg)); } catch {} }
export function clearSyncConfig() { try { localStorage.removeItem(SYNC_KEY); } catch {} }

class BaseStore {
  constructor() { this.data = emptyState(); }
  entriesFor(date) { return this.data.entries.filter((e) => e.date === date); }
  totalsFor(date) {
    const t = { kcal: 0, protein: 0, carbs: 0, fat: 0 };
    for (const e of this.entriesFor(date)) for (const k in t) t[k] += e[k] || 0;
    for (const k in t) t[k] = r1(t[k]);
    return t;
  }
  history(dates) { return dates.map((date) => ({ date, ...this.totalsFor(date), n: this.entriesFor(date).length })); }
  customFoods() { return this.data.customFoods; }
  getFood(name) { return this.data.customFoods.find((f) => f.name === name) || null; }
  goals() { return { ...DEFAULT_GOALS, ...this.data.goals }; }
  exportJSON() { return JSON.stringify(this.data, null, 2); }
}

export class LocalStore extends BaseStore {
  get remote() { return false; }
  async load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) this.data = { ...emptyState(), ...JSON.parse(raw) };
    } catch {}
  }
  save() { try { localStorage.setItem(KEY, JSON.stringify(this.data)); } catch {} }

  async addEntry(date, description, foodName, grams, macros, source) {
    const e = { id: String(this.data.nextId++), date, created_at: new Date().toISOString(), description,
      food_name: foodName, grams, kcal: macros.kcal || 0, protein: macros.protein || 0,
      carbs: macros.carbs || 0, fat: macros.fat || 0, source };
    this.data.entries.push(e); this.save(); return e;
  }
  async updateGrams(id, grams) {
    const e = this.data.entries.find((x) => String(x.id) === String(id));
    if (!e) return null;
    const k = e.grams ? grams / e.grams : 0;
    for (const m of ["kcal", "protein", "carbs", "fat"]) e[m] = r1(e[m] * k);
    e.grams = grams; this.save(); return e;
  }
  async deleteEntry(id) {
    const n = this.data.entries.length;
    this.data.entries = this.data.entries.filter((e) => String(e.id) !== String(id));
    this.save(); return this.data.entries.length < n;
  }
  async saveFood(food, replaces) {
    if (replaces && replaces !== food.name) this.data.customFoods = this.data.customFoods.filter((f) => f.name !== replaces);
    const i = this.data.customFoods.findIndex((f) => f.name === food.name);
    if (i >= 0) this.data.customFoods[i] = food; else this.data.customFoods.push(food);
    this.save(); return food;
  }
  async deleteFood(name) {
    const n = this.data.customFoods.length;
    this.data.customFoods = this.data.customFoods.filter((f) => f.name !== name);
    this.save(); return this.data.customFoods.length < n;
  }
  async setGoals(g) {
    for (const k in DEFAULT_GOALS) if (g[k] !== undefined && g[k] !== null && !Number.isNaN(+g[k])) this.data.goals[k] = +g[k];
    this.save(); return this.goals();
  }
  async importJSON(text) {
    const d = parseBackup(text);
    this.data = { ...emptyState(), ...d };
    this.data.nextId = Math.max(Number(this.data.nextId) || 1, ...this.data.entries.map((e) => (Number(e.id) || 0) + 1), 1);
    this.save();
    return { entries: d.entries.length, foods: d.customFoods.length };
  }
}

export function parseBackup(text) {
  const d = JSON.parse(text);
  if (!d || !Array.isArray(d.entries)) throw new Error("That doesn't look like a food tracker backup.");
  return { entries: d.entries, customFoods: Array.isArray(d.customFoods) ? d.customFoods : [], goals: d.goals && typeof d.goals === "object" ? d.goals : {} };
}

export class RemoteStore extends BaseStore {
  constructor(password, url = "/api/log") { super(); this.password = password; this.url = url; }
  get remote() { return true; }
  async request(method, body) {
    let res;
    try {
      res = await fetch(this.url, {
        method, headers: { "content-type": "application/json", authorization: `Bearer ${this.password}` },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch { throw new Error("Couldn't reach the sync server. Check your connection and try again."); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { const err = new Error(data.error || `Sync failed (${res.status}).`); err.status = res.status; throw err; }
    return data;
  }
  async load() { this.data = { ...emptyState(), ...(await this.request("GET")).state }; }
  async op(body) { const r = await this.request("POST", body); this.data = { ...emptyState(), ...r.state }; return r.result; }

  addEntry(date, description, foodName, grams, macros, source) {
    return this.op({ op: "add", entry: { date, description, food_name: foodName, grams, source, kcal: macros.kcal || 0, protein: macros.protein || 0, carbs: macros.carbs || 0, fat: macros.fat || 0 } });
  }
  updateGrams(id, grams) { return this.op({ op: "update", id: String(id), grams }); }
  async deleteEntry(id) { return (await this.op({ op: "delete", id: String(id) })).deleted; }
  saveFood(food, replaces) { return this.op({ op: "food", food, replaces }); }
  async deleteFood(name) { return (await this.op({ op: "deleteFood", name })).deleted; }
  async setGoals(g) { await this.op({ op: "goals", goals: g }); return this.goals(); }
  merge(state) { return this.op({ op: "merge", state }); }
  importJSON(text) { return this.merge(parseBackup(text)); }
}
