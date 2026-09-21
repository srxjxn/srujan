import { FOODS } from "./foods.js";
import { FoodIndex, parseText, macrosFor } from "./parser.js";
import { Store } from "./store.js";

const $ = (s) => document.querySelector(s);
const store = new Store();
const index = new FoodIndex(FOODS);
for (const f of store.customFoods()) index.add(f);

const state = { date: localISO(new Date()) };
const MACROS = [
  ["kcal", "Calories", "", "var(--kcal)"],
  ["protein", "Protein", "g", "var(--protein)"],
  ["carbs", "Carbs", "g", "var(--carbs)"],
  ["fat", "Fat", "g", "var(--fat)"],
];

function localISO(d) { return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); }
function shiftDate(days) { const d = new Date(state.date + "T12:00:00"); d.setDate(d.getDate() + days); return localISO(d); }
function fmt(n, dp = 0) { return Number(n || 0).toFixed(dp); }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function flash(msg, cls = "ok") { const f = $("#flash"); f.textContent = msg; f.className = "flash " + cls; }

// ---- rendering -----------------------------------------------------------
function renderDay() {
  const date = state.date, entries = store.entriesFor(date), totals = store.totalsFor(date), goals = store.goals();
  $("#date").value = date;
  $("#totals-title").textContent = date === localISO(new Date()) ? "Today's totals" : `Totals for ${date}`;

  $("#totals").innerHTML = MACROS.map(([k, label, unit, color]) => {
    const v = totals[k], g = goals[k] || 0, pct = g ? Math.min(100, v / g * 100) : 0;
    return `<div class="stat ${g && v > g ? "over" : ""}">
      <div class="label">${label}</div>
      <div class="value">${fmt(v)}<small>${unit}</small></div>
      <div class="bar"><i style="width:${pct}%;background:${color}"></i></div>
      <div class="goal">${g ? `${fmt(Math.max(0, g - v))}${unit} left of ${fmt(g)}` : "no goal"}</div>
    </div>`;
  }).join("");

  const ul = $("#entries");
  if (!entries.length) {
    ul.innerHTML = `<li class="empty">Nothing logged yet. Type what you ate above.</li>`;
  } else {
    ul.innerHTML = entries.map((e) => `
      <li data-id="${e.id}">
        <div>
          <div class="desc">${esc(e.description)}${e.source && e.source !== "database" ? `<span class="badge ${e.source}">${e.source}</span>` : ""}</div>
          <div class="meta">${e.food_name && e.food_name !== e.description.toLowerCase() ? esc(e.food_name) + " · " : ""}<span class="grams" title="Tap to change amount">${fmt(e.grams)} g</span></div>
        </div>
        <div class="macros"><span class="k"><b>${fmt(e.kcal)}</b> kcal</span><span class="p"><b>${fmt(e.protein)}</b>P</span><span class="c"><b>${fmt(e.carbs)}</b>C</span><span class="f"><b>${fmt(e.fat)}</b>F</span></div>
        <button class="icon del" title="Delete">×</button>
      </li>`).join("");
  }
  ul.querySelectorAll(".del").forEach((b) => b.onclick = () => { store.deleteEntry(+b.closest("li").dataset.id); renderDay(); renderWeek(); });
  ul.querySelectorAll(".grams").forEach((s) => s.onclick = () => editGrams(s));
}

function renderWeek() {
  const last = new Date(state.date + "T12:00:00");
  const dates = [];
  for (let i = 6; i >= 0; i--) { const d = new Date(last); d.setDate(d.getDate() - i); dates.push(localISO(d)); }
  const days = store.history(dates), goals = store.goals();
  const max = Math.max(goals.kcal || 0, ...days.map((d) => d.kcal), 1);
  $("#week").innerHTML = days.map((d) => {
    const dt = new Date(d.date + "T12:00:00");
    return `<div class="day ${d.date === state.date ? "today" : ""}" data-date="${d.date}">
      <div class="col"><i style="height:${Math.round(d.kcal / max * 100)}%"></i></div>
      <div>${dt.toLocaleDateString(undefined, { weekday: "short" })}</div>
      <div class="kc">${d.kcal ? fmt(d.kcal) : "–"}</div></div>`;
  }).join("");
  $("#week").querySelectorAll(".day").forEach((el) => el.onclick = () => load(el.dataset.date));
}

function renderUnmatched(items) {
  const box = $("#unmatched"), list = $("#unmatched-list");
  if (!items.length) { box.hidden = true; list.innerHTML = ""; return; }
  box.hidden = false;
  list.innerHTML = items.map((u, i) => `
    <div class="item">
      <div><b>${esc(u.input)}</b> <span class="meta">— enter the nutrition for the amount you ate</span></div>
      <form class="manual-form" data-i="${i}">
        <div class="name"><label>Name</label><input name="name" value="${esc(u.foodText || u.input)}" required></div>
        <div><label>Grams</label><input name="grams" type="number" inputmode="decimal" min="1" step="1" placeholder="100"></div>
        <div><label>kcal</label><input name="kcal" type="number" inputmode="decimal" min="0" step="1" required></div>
        <div><label>Protein</label><input name="protein" type="number" inputmode="decimal" min="0" step="0.1" value="0"></div>
        <div><label>Carbs</label><input name="carbs" type="number" inputmode="decimal" min="0" step="0.1" value="0"></div>
        <div><label>Fat</label><input name="fat" type="number" inputmode="decimal" min="0" step="0.1" value="0"></div>
        <div><button class="primary" type="submit">Add</button></div>
        <label class="remember"><input type="checkbox" name="remember" checked> Remember this food so it's recognised next time</label>
      </form>
    </div>`).join("");
  list.querySelectorAll("form.manual-form").forEach((f) => f.onsubmit = (ev) => {
    ev.preventDefault();
    const fd = new FormData(f);
    const name = String(fd.get("name")).trim();
    const grams = Number(fd.get("grams")) || 100;
    const macros = { kcal: +fd.get("kcal") || 0, protein: +fd.get("protein") || 0, carbs: +fd.get("carbs") || 0, fat: +fd.get("fat") || 0 };
    if (fd.get("remember") === "on") {
      const k = 100 / grams;
      const food = { name: name.toLowerCase(), kcal: +(macros.kcal * k).toFixed(2), protein: +(macros.protein * k).toFixed(2),
        carbs: +(macros.carbs * k).toFixed(2), fat: +(macros.fat * k).toFixed(2), serving_g: grams, units: {}, aliases: [], source: "custom" };
      store.saveFood(food); index.add(food);
    }
    store.addEntry(state.date, name, name.toLowerCase(), grams, macros, "manual");
    renderDay(); renderWeek();
    f.closest(".item").remove();
    if (!list.children.length) box.hidden = true;
    flash(`Added ${name}.`);
  });
}

// ---- actions -------------------------------------------------------------
function load(date) { state.date = date; renderDay(); renderWeek(); }

$("#logform").onsubmit = (ev) => {
  ev.preventDefault();
  const text = $("#text").value.trim();
  if (!text) return;
  const added = [], unmatched = [];
  for (const item of parseText(text, index)) {
    if (!item.food) { unmatched.push(item); continue; }
    added.push(store.addEntry(state.date, item.input, item.food.name, item.grams, item.macros, item.food.source || "database"));
  }
  renderDay(); renderWeek(); renderUnmatched(unmatched);
  $("#text").value = "";
  if (added.length) {
    const kcal = added.reduce((s, e) => s + e.kcal, 0);
    flash(`Added ${added.map((e) => `${e.food_name} (${fmt(e.grams)}g)`).join(", ")} · ${fmt(kcal)} kcal`);
  } else if (!unmatched.length) flash("Nothing recognised in that text.", "err");
  else flash("");
  if (unmatched.length) $("#unmatched").scrollIntoView({ behavior: "smooth", block: "nearest" });
};

function editGrams(span) {
  const id = +span.closest("li").dataset.id, cur = parseFloat(span.textContent);
  const input = document.createElement("input");
  input.type = "number"; input.inputMode = "decimal"; input.min = "1"; input.step = "1"; input.value = cur;
  span.replaceWith(input); input.focus(); input.select();
  let done = false;
  const commit = () => {
    if (done) return; done = true;
    const g = parseFloat(input.value);
    if (g && g !== cur) store.updateGrams(id, g);
    renderDay(); renderWeek();
  };
  input.onblur = commit;
  input.onkeydown = (e) => { if (e.key === "Enter") input.blur(); if (e.key === "Escape") { done = true; renderDay(); } };
}

$("#prev").onclick = () => load(shiftDate(-1));
$("#next").onclick = () => load(shiftDate(1));
$("#today").onclick = () => load(localISO(new Date()));
$("#date").onchange = (e) => e.target.value && load(e.target.value);

$("#editgoals").onclick = () => {
  const f = $("#goalsform"), goals = store.goals();
  for (const [k] of MACROS) f.elements[k].value = goals[k];
  f.classList.toggle("open");
};
$("#cancelgoals").onclick = () => $("#goalsform").classList.remove("open");
$("#goalsform").onsubmit = (ev) => {
  ev.preventDefault();
  const body = {};
  for (const [k] of MACROS) body[k] = Number(ev.target.elements[k].value);
  store.setGoals(body); renderDay(); renderWeek();
  ev.target.classList.remove("open");
};

// suggestions for the item currently being typed
let suggestTimer;
$("#text").oninput = () => {
  clearTimeout(suggestTimer);
  suggestTimer = setTimeout(() => {
    const value = $("#text").value;
    const raw = value.split(/,|\band\b|\bwith\b/i).pop().replace(/^[\s\d./½¼¾]+(g|oz|cups?|tbsp|tsp|slices?|pieces?)?\s*(of)?\s*/i, "").trim().toLowerCase();
    if (raw.length < 2) return;
    const prefix = value.slice(0, value.length - raw.length);
    const seen = new Map();
    for (const [key, food] of index.keys) if (key.includes(raw) || food.name.includes(raw)) seen.set(food.name, food);
    const foods = [...seen.values()].sort((a, b) => (a.name.startsWith(raw) ? 0 : 1) - (b.name.startsWith(raw) ? 0 : 1) || a.name.length - b.name.length).slice(0, 8);
    $("#foodlist").innerHTML = foods.map((f) => `<option value="${esc(prefix + f.name)}">${fmt(f.serving_g)}g · ${fmt(macrosFor(f, f.serving_g).kcal)} kcal</option>`).join("");
  }, 150);
};

// backup / restore (data lives only in this browser)
$("#export").onclick = (e) => {
  e.preventDefault();
  const blob = new Blob([store.exportJSON()], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = `food-tracker-${localISO(new Date())}.json`; a.click();
  URL.revokeObjectURL(a.href);
};
$("#import").onclick = (e) => { e.preventDefault(); $("#importfile").click(); };
$("#importfile").onchange = async (e) => {
  const file = e.target.files[0]; if (!file) return;
  try {
    store.importJSON(await file.text());
    for (const f of store.customFoods()) index.add(f);
    load(state.date); flash("Data imported.");
  } catch (err) { flash(err.message, "err"); }
  e.target.value = "";
};

load(state.date);
$("#status").textContent = `${index.keys.size} foods in the database · your log is saved on this device`;
$("#text").focus();
