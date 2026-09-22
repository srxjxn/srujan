// Local storage for the static build: the log lives in this browser only.
const KEY = "food-tracker:v1";
export const DEFAULT_GOALS = { kcal: 2200, protein: 150, carbs: 220, fat: 70 };

function loadState() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { entries: [], customFoods: [], goals: {}, nextId: 1, ...JSON.parse(raw) };
  } catch {}
  return { entries: [], customFoods: [], goals: {}, nextId: 1 };
}

export class Store {
  constructor() { this.data = loadState(); }
  save() { try { localStorage.setItem(KEY, JSON.stringify(this.data)); } catch {} }

  entriesFor(date) { return this.data.entries.filter((e) => e.date === date); }
  addEntry(date, description, foodName, grams, macros, source) {
    const e = { id: this.data.nextId++, date, created_at: new Date().toISOString(), description,
      food_name: foodName, grams, kcal: macros.kcal || 0, protein: macros.protein || 0,
      carbs: macros.carbs || 0, fat: macros.fat || 0, source };
    this.data.entries.push(e); this.save(); return e;
  }
  updateGrams(id, grams) {
    const e = this.data.entries.find((x) => x.id === id);
    if (!e) return null;
    const k = e.grams ? grams / e.grams : 0;
    for (const m of ["kcal", "protein", "carbs", "fat"]) e[m] = Math.round(e[m] * k * 10) / 10;
    e.grams = grams; this.save(); return e;
  }
  deleteEntry(id) {
    const n = this.data.entries.length;
    this.data.entries = this.data.entries.filter((e) => e.id !== id);
    this.save(); return this.data.entries.length < n;
  }
  totalsFor(date) {
    const t = { kcal: 0, protein: 0, carbs: 0, fat: 0 };
    for (const e of this.entriesFor(date)) for (const k in t) t[k] += e[k] || 0;
    for (const k in t) t[k] = Math.round(t[k] * 10) / 10;
    return t;
  }
  history(dates) { return dates.map((date) => ({ date, ...this.totalsFor(date), n: this.entriesFor(date).length })); }

  saveFood(food) {
    const i = this.data.customFoods.findIndex((f) => f.name === food.name);
    if (i >= 0) this.data.customFoods[i] = food; else this.data.customFoods.push(food);
    this.save();
  }
  customFoods() { return this.data.customFoods; }
  getFood(name) { return this.data.customFoods.find((f) => f.name === name) || null; }
  deleteFood(name) {
    const n = this.data.customFoods.length;
    this.data.customFoods = this.data.customFoods.filter((f) => f.name !== name);
    this.save(); return this.data.customFoods.length < n;
  }

  goals() { return { ...DEFAULT_GOALS, ...this.data.goals }; }
  setGoals(g) {
    for (const k in DEFAULT_GOALS) if (g[k] !== undefined && g[k] !== null && !Number.isNaN(+g[k])) this.data.goals[k] = +g[k];
    this.save(); return this.goals();
  }

  exportJSON() { return JSON.stringify(this.data, null, 2); }
  importJSON(text) {
    const d = JSON.parse(text);
    if (!d || !Array.isArray(d.entries)) throw new Error("Not a food tracker export");
    this.data = { entries: [], customFoods: [], goals: {}, nextId: 1, ...d };
    this.data.nextId = Math.max(this.data.nextId, ...this.data.entries.map((e) => e.id + 1), 1);
    this.save();
  }
}
