import { FOODS } from "./foods.js";
import { FoodIndex, parseText, macrosFor, foodFromServing, SERVING_UNITS } from "./parser.js";
import { LocalStore, RemoteStore, getSyncConfig, setSyncConfig, clearSyncConfig } from "./store.js";

const $ = (s) => document.querySelector(s);
const syncConfig = getSyncConfig();
const store = syncConfig ? new RemoteStore(syncConfig.password) : new LocalStore();
const index = new FoodIndex(FOODS);
// Built-in foods first, then saved foods so they win on name clashes.
const rebuildIndex = () => index.reset([...FOODS, ...store.customFoods()]);
rebuildIndex();

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
// Run a store mutation, then re-render; any error (offline, wrong password) lands in the flash line.
async function mutate(fn, after = () => { renderDay(); renderWeek(); }) {
  try { const r = await fn(); after(); return r; }
  catch (e) { flash(e.message, "err"); renderDay(); renderWeek(); return undefined; }
}
function plural(unit, n) { return n === 1 ? unit : unit.endsWith("y") && !/[aeiou]y$/.test(unit) ? unit.slice(0, -1) + "ies" : unit + "s"; }
function fmtServings(grams, food) {
  if (!food || !food.serving_g || !grams) return "";
  const n = Math.round(grams / food.serving_g * 100) / 100;
  return `${n} ${plural(food.serving_unit || "serving", n)}`;
}

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
          <div class="meta">${e.food_name && e.food_name !== e.description.toLowerCase() ? esc(e.food_name) + " \u00b7 " : ""}${fmtServings(e.grams, store.getFood(e.food_name)) ? esc(fmtServings(e.grams, store.getFood(e.food_name))) + " \u00b7 " : ""}<span class="grams" title="Tap to change amount">${fmt(e.grams)} g</span></div>
        </div>
        <div class="macros"><span class="k"><b>${fmt(e.kcal)}</b> kcal</span><span class="p"><b>${fmt(e.protein)}</b>P</span><span class="c"><b>${fmt(e.carbs)}</b>C</span><span class="f"><b>${fmt(e.fat)}</b>F</span></div>
        <button class="icon del" title="Delete">\u00d7</button>
      </li>`).join("");
  }
  ul.querySelectorAll(".del").forEach((b) => b.onclick = () => mutate(() => store.deleteEntry(b.closest("li").dataset.id)));
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
      <div class="kc">${d.kcal ? fmt(d.kcal) : "\u2013"}</div></div>`;
  }).join("");
  $("#week").querySelectorAll(".day").forEach((el) => el.onclick = () => load(el.dataset.date));
}

function renderUnmatched(items) {
  const box = $("#unmatched"), list = $("#unmatched-list");
  if (!items.length) { box.hidden = true; list.innerHTML = ""; return; }
  box.hidden = false;
  list.innerHTML = items.map((u, i) => `
    <div class="item">
      <div><b>${esc(u.input)}</b> <span class="meta">\u2014 enter the nutrition for the amount you ate</span></div>
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
  list.querySelectorAll("form.manual-form").forEach((f) => f.onsubmit = async (ev) => {
    ev.preventDefault();
    const fd = new FormData(f);
    const name = String(fd.get("name")).trim();
    const grams = Number(fd.get("grams")) || 100;
    const macros = { kcal: +fd.get("kcal") || 0, protein: +fd.get("protein") || 0, carbs: +fd.get("carbs") || 0, fat: +fd.get("fat") || 0 };
    const ok = await mutate(async () => {
      if (fd.get("remember") === "on") {
        const food = foodFromServing({ name, servingG: grams, ...macros });
        await store.saveFood(food); index.add(food); renderMyFoods();
      }
      await store.addEntry(state.date, name, name.toLowerCase(), grams, macros, "manual");
      return true;
    });
    if (!ok) return;
    f.closest(".item").remove();
    if (!list.children.length) box.hidden = true;
    flash(`Added ${name}.`);
  });
}

// ---- actions -------------------------------------------------------------
function load(date) { state.date = date; renderDay(); renderWeek(); }

$("#logform").onsubmit = async (ev) => {
  ev.preventDefault();
  const text = $("#text").value.trim();
  if (!text) return;
  const added = [], unmatched = [];
  const btn = $("#add"); btn.disabled = true;
  const ok = await mutate(async () => {
    for (const item of parseText(text, index)) {
      if (!item.food) { unmatched.push(item); continue; }
      added.push(await store.addEntry(state.date, item.input, item.food.name, item.grams, item.macros, item.food.source || "database"));
    }
    return true;
  });
  btn.disabled = false;
  if (!ok) return;
  renderUnmatched(unmatched);
  $("#text").value = "";
  if (added.length) {
    const kcal = added.reduce((s, e) => s + e.kcal, 0);
    flash(`Added ${added.map((e) => `${e.food_name} (${fmt(e.grams)}g)`).join(", ")} \u00b7 ${fmt(kcal)} kcal`);
  } else if (!unmatched.length) flash("Nothing recognised in that text.", "err");
  else flash("");
  if (unmatched.length) $("#unmatched").scrollIntoView({ behavior: "smooth", block: "nearest" });
};

function editGrams(span) {
  const id = span.closest("li").dataset.id, cur = parseFloat(span.textContent);
  const input = document.createElement("input");
  input.type = "number"; input.inputMode = "decimal"; input.min = "1"; input.step = "1"; input.value = cur;
  span.replaceWith(input); input.focus(); input.select();
  let done = false;
  const commit = () => {
    if (done) return; done = true;
    const g = parseFloat(input.value);
    if (g && g !== cur) mutate(() => store.updateGrams(id, g)); else renderDay();
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
$("#goalsform").onsubmit = async (ev) => {
  ev.preventDefault();
  const body = {};
  for (const [k] of MACROS) body[k] = Number(ev.target.elements[k].value);
  if (await mutate(() => store.setGoals(body))) ev.target.classList.remove("open");
};

// ---- my foods: saved from the label, logged by the serving ----------------
function foodView(f) { return { ...f, serving_unit: f.serving_unit || "serving", aliases: f.aliases || [], ...macrosFor(f, f.serving_g) }; }

function renderMyFoods() {
  const foods = store.customFoods().map(foodView);
  const ul = $("#foodlist-mine");
  if (!foods.length) { ul.innerHTML = `<li class="empty">No saved foods yet. Add the ones you eat every week.</li>`; return; }
  ul.innerHTML = foods.map((f) => `
    <li data-name="${esc(f.name)}">
      <div>
        <div class="desc">${esc(f.name)}</div>
        <div class="meta">1 ${esc(f.serving_unit)} = ${fmt(f.serving_g, f.serving_g % 1 ? 1 : 0)} g${f.aliases.length ? " \u00b7 also " + esc(f.aliases.join(", ")) : ""}</div>
      </div>
      <div class="macros"><span class="k"><b>${fmt(f.kcal)}</b> kcal</span><span class="p"><b>${fmt(f.protein, 1)}</b>P</span><span class="c"><b>${fmt(f.carbs, 1)}</b>C</span><span class="f"><b>${fmt(f.fat, 1)}</b>F</span></div>
      <div class="actions">
        <button class="small log" title="Log one serving to this day">+1 ${esc(f.serving_unit)}</button>
        <button class="small edit">Edit</button>
        <button class="icon del" title="Remove saved food">\u00d7</button>
      </div>
    </li>`).join("");
  ul.querySelectorAll(".log").forEach((b) => b.onclick = () => logSaved(store.getFood(b.closest("li").dataset.name)));
  ul.querySelectorAll(".edit").forEach((b) => b.onclick = () => openFoodForm(store.getFood(b.closest("li").dataset.name)));
  ul.querySelectorAll(".del").forEach((b) => b.onclick = () => deleteSaved(b.closest("li").dataset.name));
}

function openFoodForm(food) {
  const f = $("#foodform");
  f.reset();
  f.elements.replaces.value = food ? food.name : "";
  if (food) {
    const v = foodView(food);
    f.elements.name.value = v.name;
    f.elements.aliases.value = v.aliases.join(", ");
    f.elements.serving_unit.value = v.serving_unit;
    f.elements.serving_g.value = v.serving_g;
    for (const [k] of MACROS) f.elements[k].value = v[k];
  }
  f.classList.add("open");
  updateFoodPreview();
  f.elements.name.focus();
}

function updateFoodPreview() {
  const f = $("#foodform"), g = Number(f.elements.serving_g.value), kcal = Number(f.elements.kcal.value);
  $("#foodpreview").textContent = g > 0 && f.elements.kcal.value !== "" ? `= ${fmt(kcal / g * 100)} kcal per 100 g` : "";
}

$("#servingunits").innerHTML = SERVING_UNITS.map((u) => `<option value="${u}">`).join("");
$("#addfood").onclick = () => $("#foodform").classList.contains("open") && !$("#foodform").elements.replaces.value ? $("#foodform").classList.remove("open") : openFoodForm(null);
$("#cancelfood").onclick = () => $("#foodform").classList.remove("open");
$("#foodform").oninput = updateFoodPreview;
$("#foodform").onsubmit = async (ev) => {
  ev.preventDefault();
  const el = ev.target.elements;
  const name = el.name.value.trim().toLowerCase();
  try {
    const food = foodFromServing({
      name, servingG: Number(el.serving_g.value), servingUnit: el.serving_unit.value,
      aliases: el.aliases.value.split(",").map((a) => a.trim()).filter(Boolean),
      kcal: Number(el.kcal.value || 0), protein: Number(el.protein.value || 0), carbs: Number(el.carbs.value || 0), fat: Number(el.fat.value || 0),
    });
    if (!(await mutate(() => store.saveFood(food, el.replaces.value || undefined), () => { rebuildIndex(); renderMyFoods(); renderDay(); }))) return;
    ev.target.classList.remove("open");
    flash(`Saved ${food.name}. Type "2 ${plural(food.serving_unit, 2)} ${food.name}" to log it.`);
  } catch (e) { flash(e.message, "err"); }
};

function logSaved(food) {
  if (!food) return;
  const unit = food.serving_unit || "serving";
  const text = `1 ${unit} ${food.name}`;
  const item = parseText(text, index).find((i) => i.food);
  if (!item) { flash(`Could not log "${text}".`, "err"); return; }
  mutate(() => store.addEntry(state.date, text, item.food.name, item.grams, item.macros, item.food.source || "custom"))
    .then((e) => e && flash(`Added ${text} \u00b7 ${fmt(e.kcal)} kcal`));
}

function deleteSaved(name) {
  if (!confirm(`Remove "${name}" from your saved foods? Entries already logged stay as they are.`)) return;
  mutate(() => store.deleteFood(name), () => { rebuildIndex(); renderMyFoods(); renderDay(); });
}

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
    $("#foodlist").innerHTML = foods.map((f) => `<option value="${esc(prefix + f.name)}">${f.source === "custom" ? `1 ${esc(f.serving_unit || "serving")} = ` : ""}${fmt(f.serving_g)}g \u00b7 ${fmt(macrosFor(f, f.serving_g).kcal)} kcal</option>`).join("");
  }, 150);
};

// backup / restore (data lives only in this browser)
$("#export").onclick = async (e) => {
  e.preventDefault();
  const json = store.exportJSON();
  try {
    await navigator.clipboard.writeText(json);
    flash("Backup copied to the clipboard. Paste it somewhere safe (Notes, email) to keep it.");
  } catch {
    const ta = document.createElement("textarea");
    ta.value = json; ta.readOnly = true; ta.style.cssText = "width:100%;height:160px;margin-top:8px;font:12px monospace";
    $("#status").after(ta); ta.select();
    flash("Copy the text below to keep a backup.");
  }
};
$("#import").onclick = async (e) => {
  e.preventDefault();
  const pasted = prompt(store.remote ? "Paste a backup to merge it into your synced log:" : "Paste a backup here to restore it (this replaces the log on this device):");
  if (!pasted) return;
  await mutate(() => store.importJSON(pasted), () => { rebuildIndex(); renderMyFoods(); load(state.date); flash("Backup restored."); });
};

// ---- sync across devices ----------------------------------------------------
function renderSyncStatus(error) {
  const s = $("#syncstatus"), a = $("#synclink");
  if (store.remote) {
    s.textContent = error ? `Sync problem: ${error}` : "Synced across your devices";
    s.className = error ? "err" : "";
    a.textContent = "Turn off sync";
  } else {
    s.textContent = "Your log is saved on this device only";
    s.className = "";
    a.textContent = "Sync across devices";
  }
}

async function connectSync() {
  const password = prompt("Enter your sync password. Use the same one on every device.\n(It's the FOOD_TRACKER_PASSWORD you set on Vercel.)");
  if (!password) return;
  const remote = new RemoteStore(password);
  try { await remote.load(); } catch (e) { flash(e.message, "err"); return; }
  const local = store.remote ? null : store.data;
  if (local && (local.entries.length || local.customFoods.length)) {
    if (confirm(`Copy the ${local.entries.length} entries and ${local.customFoods.length} saved foods on this device into your synced log? (Nothing is duplicated.)`)) {
      try { await remote.merge(local); } catch (e) { flash(e.message, "err"); return; }
    }
  }
  setSyncConfig({ password });
  location.reload();
}

$("#synclink").onclick = (e) => {
  e.preventDefault();
  if (!store.remote) return connectSync();
  if (confirm("Turn off sync on this device? Your synced log stays on the server; this device goes back to its own local log.")) { clearSyncConfig(); location.reload(); }
};

// ---- boot ---------------------------------------------------------------------
(async () => {
  let loadError = null;
  try { await store.load(); } catch (e) { loadError = e.message; flash(e.message, "err"); }
  rebuildIndex();
  renderMyFoods();
  load(state.date);
  renderSyncStatus(loadError);
  $("#status").textContent = `${index.keys.size} foods in the database`;
  $("#text").focus();
})();
