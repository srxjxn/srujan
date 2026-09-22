// Port of food_tracker/parser.py. Turns "2 eggs, 150g chicken breast and a banana"
// into [{food, qty, unit, grams, macros}, ...].

export const WEIGHT_UNITS = {
  g: 1, gram: 1, grams: 1, gm: 1, gms: 1, gr: 1,
  kg: 1000, kilo: 1000, kilos: 1000, kilogram: 1000, kilograms: 1000,
  oz: 28.35, ounce: 28.35, ounces: 28.35,
  lb: 453.6, lbs: 453.6, pound: 453.6, pounds: 453.6,
  ml: 1, milliliter: 1, milliliters: 1, millilitre: 1, millilitres: 1,
  l: 1000, liter: 1000, liters: 1000, litre: 1000, litres: 1000,
  floz: 29.57,
};

// null = one default serving of the food
export const GENERIC_UNITS = {
  cup: 240, tbsp: 15, tsp: 5, slice: 30, piece: null, scoop: 30, serving: null, portion: null,
  bowl: 300, plate: 350, handful: 30, can: 355, bottle: 500, glass: 250, packet: 40, pack: 40,
  bar: 45, shot: 44, pint: 473, container: null, tub: null, clove: 3, patty: 113, fillet: 170,
  link: 50, stick: 30, wedge: 40, spear: 16, square: 10, cone: 100, mug: 350, box: null,
  pouch: 90, tin: null, head: 300, ear: 90, cob: 90, strip: 8, rasher: 8, breast: 174,
  thigh: 90, wing: 34, chop: 150, nugget: 17, roll: null, wrap: null, jar: 250, half: null,
  small: null, medium: null, large: null, block: 350, dollop: 30, splash: 15, drizzle: 5,
  dash: 1, pat: 5, cube: 10, sheet: 1, floret: 11, leaf: 10, baby: 10, double: 88,
  espresso: 30, tall: 350, grande: 470, venti: 590, burger: null, whole: null, ring: 84,
  sandwich: null,
};

// Serving words offered when saving a food from its label. Any GENERIC_UNITS key works;
// an unknown word still logs fine, it just falls back to "N servings".
export const SERVING_UNITS = ["serving", "scoop", "bar", "piece", "slice", "cup", "tbsp", "tsp", "packet", "pouch",
  "container", "bottle", "can", "glass", "bowl", "patty", "square", "stick", "wrap", "roll", "sandwich", "burger",
  "cone", "jar", "shot", "handful", "link", "nugget"];

const SIZE_MULTIPLIER = { small: 0.75, medium: 1, large: 1.5, half: 0.5, whole: 1, double: 2 };

const UNIT_ALIASES = {
  cups: "cup", c: "cup",
  tablespoon: "tbsp", tablespoons: "tbsp", tbsps: "tbsp", tbs: "tbsp", tbl: "tbsp",
  teaspoon: "tsp", teaspoons: "tsp", tsps: "tsp",
  slices: "slice", pieces: "piece", pc: "piece", pcs: "piece", pce: "piece",
  scoops: "scoop", servings: "serving", portions: "portion", bowls: "bowl", plates: "plate",
  handfuls: "handful", cans: "can", bottles: "bottle", glasses: "glass", packets: "packet",
  packs: "pack", bars: "bar", shots: "shot", pints: "pint", containers: "container",
  tubs: "tub", cloves: "clove", patties: "patty", fillets: "fillet", filets: "fillet",
  filet: "fillet", links: "link", sticks: "stick", wedges: "wedge", spears: "spear",
  squares: "square", cones: "cone", mugs: "mug", boxes: "box", pouches: "pouch", tins: "tin",
  heads: "head", ears: "ear", cobs: "cob", strips: "strip", rashers: "rasher",
  breasts: "breast", thighs: "thigh", wings: "wing", chops: "chop", nuggets: "nugget",
  rolls: "roll", wraps: "wrap", jars: "jar", halves: "half", blocks: "block",
  dollops: "dollop", sheets: "sheet", florets: "floret", leaves: "leaf", rings: "ring",
  sandwiches: "sandwich", sm: "small", med: "medium", lg: "large", xl: "large", burgers: "burger",
};

const NUMBER_WORDS = {
  a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8,
  nine: 9, ten: 10, eleven: 11, twelve: 12, dozen: 12, half: 0.5, quarter: 0.25,
  couple: 2, few: 3, several: 3, single: 1, double: 2, triple: 3,
};

const UNICODE_FRACTIONS = { "½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125 };

const FILLER = new Set(["of", "the", "some", "my", "a", "an", "and", "with", "for", "in", "on",
  "to", "at", "from", "ate", "had", "have", "having", "eat", "eating", "i", "im", "i'm", "just",
  "about", "around", "roughly", "approx", "approximately", "breakfast", "lunch", "dinner",
  "snack", "today", "tonight", "morning", "this", "that", "another", "more", "extra", "bit",
  "little", "big", "x"]);

export const MAX_GRAMS = 10000;

const NUM_RE = /^(\d+(?:[.,]\d+)?)(?:\/(\d+))?$/;
const NUM_UNIT_RE = /^(\d+(?:[.,]\d+)?)([a-z]+)$/;
const X_QTY_RE = /^x(\d+(?:\.\d+)?)$/;
const QTY_X_RE = /^(\d+(?:\.\d+)?)x$/;

function toNumber(tok) {
  if (tok in UNICODE_FRACTIONS) return UNICODE_FRACTIONS[tok];
  const last = tok.slice(-1);
  if (last in UNICODE_FRACTIONS && /^\d+$/.test(tok.slice(0, -1))) return parseInt(tok.slice(0, -1), 10) + UNICODE_FRACTIONS[last];
  const m = NUM_RE.exec(tok);
  if (!m) return null;
  const whole = parseFloat(m[1].replace(",", "."));
  if (m[2]) { const d = parseFloat(m[2]); return d ? whole / d : null; }
  return whole;
}

function normUnit(tok) {
  tok = UNIT_ALIASES[tok] ?? tok;
  return tok in WEIGHT_UNITS || tok in GENERIC_UNITS ? tok : null;
}

// "Scoops" -> "scoop", "tablespoon" -> "tbsp", "" -> "serving". Unknown words are kept, singular.
export function normalizeUnitWord(word) {
  const w = String(word || "").toLowerCase().replace(/[^a-z]/g, "");
  if (!w) return "serving";
  for (let cand of [w, singularize(w)]) {
    cand = UNIT_ALIASES[cand] ?? cand;
    if (cand in GENERIC_UNITS) return cand;
    if (cand in WEIGHT_UNITS) return "serving";
  }
  return singularize(w);
}

// Build a food straight off a nutrition label: macros for ONE serving of servingG grams.
// Stored per 100 g so "2 scoops" and "45g" both come out exact.
export function foodFromServing({ name, servingG, kcal, protein = 0, carbs = 0, fat = 0, servingUnit = "serving", aliases = [], source = "custom" }) {
  if (!(servingG > 0)) throw new Error("Serving size must be positive");
  const k = 100 / servingG, r4 = (x) => Math.round(x * 1e4) / 1e4;
  const unit = normalizeUnitWord(servingUnit);
  const clean = String(name).trim().toLowerCase();
  const seen = new Set([clean]);
  const cleanAliases = aliases.map((a) => String(a).trim().toLowerCase()).filter((a) => a && !seen.has(a) && seen.add(a));
  return { name: clean, kcal: r4(kcal * k), protein: r4(protein * k), carbs: r4(carbs * k), fat: r4(fat * k),
    serving_g: servingG, units: { serving: servingG, [unit]: servingG }, aliases: cleanAliases, source, serving_unit: unit };
}

export function singularize(tok) {
  if (tok.length <= 3) return tok;
  if (tok.endsWith("ies")) return tok.slice(0, -3) + "y";
  if (/(shes|ches|xes|sses|oes)$/.test(tok)) return tok.slice(0, -2);
  if (tok.endsWith("s") && !tok.endsWith("ss")) return tok.slice(0, -1);
  return tok;
}

const stripEdges = (t) => t.replace(/^['\-.]+|['\-.]+$/g, "");

export function normalizeTokens(text) {
  text = text.toLowerCase().replace(/&/g, " and ");
  text = text.replace(/[^\p{L}\p{N}_\s%½¼¾⅓⅔⅛/.'-]/gu, " ");
  return text.split(/\s+/).map(stripEdges).filter((t) => t && !FILLER.has(t)).map(singularize);
}

export const normalizePhrase = (text) => normalizeTokens(text).join(" ");

const SPLIT_RE = /\s*(?:,|;|\n|\+|\band\b|\bwith\b|\bplus\b|\balong with\b|\bthen\b)\s*/i;
const AND_A_HALF_RE = /\b(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)\s+and\s+a\s+(half|quarter)\b/gi;
const prenormalize = (text) => text.replace(AND_A_HALF_RE, "$1 $2");
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export function splitSegments(text, protectedPhrases) {
  let work = prenormalize(text);
  const restore = [];
  protectedPhrases.forEach((phrase, i) => {
    const re = new RegExp(escapeRe(phrase), "gi");
    if (re.test(work)) {
      const token = `\u0000${i}\u0000`;
      restore.push([token, phrase]);
      work = work.replace(re, token);
    }
  });
  return work.split(SPLIT_RE).map((p) => {
    p = p.replace(/^[\s.]+|[\s.]+$/g, "");
    for (const [token, phrase] of restore) p = p.split(token).join(phrase);
    return p;
  }).filter(Boolean);
}

function popQuantity(tokens) {
  let qty = null, fromArticle = false, i = 0;
  while (i < tokens.length) {
    const t = tokens[i];
    const n = toNumber(t);
    if (n !== null) { qty = qty === null || fromArticle ? n : qty + n; fromArticle = false; i++; continue; }
    const m = QTY_X_RE.exec(t);
    if (m) { qty = parseFloat(m[1]); i++; continue; }
    if (t in NUMBER_WORDS && (qty === null || fromArticle || t === "half" || t === "quarter")) {
      if ((t === "half" || t === "quarter") && qty !== null && !fromArticle) qty += NUMBER_WORDS[t];
      else qty = NUMBER_WORDS[t];
      fromArticle = t === "a" || t === "an";
      i++;
      while (i < tokens.length && ["of", "a", "an"].includes(tokens[i])) i++;
      continue;
    }
    if (["a", "an", "of"].includes(t) && qty !== null) { i++; continue; }
    break;
  }
  return [qty, tokens.slice(i)];
}

export function extractMeasure(segment) {
  let text = prenormalize(segment.toLowerCase().trim());
  text = text.replace(/[()[\]]/g, " ");
  text = text.replace(/\bfl\.?\s*oz\b/g, "floz");
  text = text.replace(/(\d)\s*x\s*(?=[a-z])/g, "$1x ");
  text = text.replace(/(?<=[a-z])\s*x\s*(\d)/g, " x$1");
  const raw = text.split(/\s+/).map((t) => t.replace(/^['.]+|['.]+$/g, "")).filter(Boolean);

  const tokens = [];
  for (const t of raw) {
    const m = NUM_UNIT_RE.exec(t);
    if (m && normUnit(m[2])) tokens.push(m[1], m[2]); else tokens.push(t);
  }

  let [qty, rest] = popQuantity(tokens);
  let unit = null;
  if (rest.length) {
    const u = normUnit(rest[0]);
    if (u && (rest.length > 1 || qty !== null)) {
      unit = u; rest = rest.slice(1);
      while (rest.length && ["of", "a", "an"].includes(rest[0])) rest = rest.slice(1);
    } else if (qty !== null && rest[0] in SIZE_MULTIPLIER && rest.length > 1) {
      unit = rest[0]; rest = rest.slice(1);
    }
  }

  if (qty === null && unit === null && rest.length >= 2) {
    const m = X_QTY_RE.exec(rest[rest.length - 1]);
    if (m) { qty = parseFloat(m[1]); rest = rest.slice(0, -1); }
    else {
      const tailUnit = normUnit(rest[rest.length - 1]);
      if (tailUnit && rest.length >= 3 && toNumber(rest[rest.length - 2]) !== null) {
        qty = toNumber(rest[rest.length - 2]); unit = tailUnit; rest = rest.slice(0, -2);
      } else if (toNumber(rest[rest.length - 1]) !== null) {
        qty = toNumber(rest[rest.length - 1]); rest = rest.slice(0, -1);
      }
    }
  }
  return { qty, unit, foodText: rest.join(" ").trim() };
}

// ---- similarity (stand-in for difflib) --------------------------------------
function levenshtein(a, b) {
  if (a === b) return 0;
  const m = a.length, n = b.length;
  if (!m) return n; if (!n) return m;
  let prev = Array.from({ length: n + 1 }, (_, j) => j);
  for (let i = 1; i <= m; i++) {
    const cur = [i];
    for (let j = 1; j <= n; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    }
    prev = cur;
  }
  return prev[n];
}
const ratio = (a, b) => 1 - levenshtein(a, b) / Math.max(a.length, b.length, 1);
function closest(word, candidates, cutoff) {
  let best = null, bestScore = cutoff;
  for (const c of candidates) {
    if (Math.abs(c.length - word.length) > word.length * (1 - cutoff) + 1) continue;
    const s = ratio(word, c);
    if (s >= bestScore) { best = c; bestScore = s; }
  }
  return best;
}

// ---- index --------------------------------------------------------------------
export class FoodIndex {
  constructor(foods = []) { this.reset(foods); }
  // Rebuild from scratch. Later foods win on name clashes, so add custom foods last.
  reset(foods) {
    this.keys = new Map();
    this.protected = [];
    for (const f of foods) this._index(f);
    this._finalize();
  }
  add(food) { this._index(food); this._finalize(); }
  _index(food) {
    for (const name of [food.name, ...(food.aliases || [])]) {
      const key = normalizePhrase(name);
      if (key) this.keys.set(key, food);
      if (/\b(and|with|plus)\b/i.test(name) && !this.protected.includes(name.toLowerCase())) this.protected.push(name.toLowerCase());
    }
  }
  _finalize() {
    this._sorted = [...this.keys.keys()].sort((a, b) => (b.split(" ").length - a.split(" ").length) || (b.length - a.length));
    this._vocab = null;
  }
  vocab() {
    if (!this._vocab) { const v = new Set(); for (const k of this.keys.keys()) k.split(" ").forEach((t) => v.add(t)); this._vocab = [...v]; }
    return this._vocab;
  }
  match(text, depth = 0) {
    const query = normalizePhrase(text);
    if (!query) return [null, 0];
    if (this.keys.has(query)) return [this.keys.get(query), 1];
    const q = query.split(" ");
    for (const key of this._sorted) {
      const k = key.split(" "), n = k.length;
      if (n > q.length) continue;
      for (let i = 0; i + n <= q.length; i++) {
        let ok = true;
        for (let j = 0; j < n; j++) if (q[i + j] !== k[j]) { ok = false; break; }
        if (ok) return [this.keys.get(key), n === q.length ? 0.9 : Math.round(Math.max(0.5, 0.85 * n / q.length) * 100) / 100];
      }
    }
    const close = closest(query, this.keys.keys(), 0.8);
    if (close) return [this.keys.get(close), 0.7];
    if (depth === 0) {
      const fixed = q.map((t) => closest(t, this.vocab(), 0.85) ?? t);
      if (fixed.join(" ") !== query) {
        const [f, conf] = this.match(fixed.join(" "), 1);
        if (f) return [f, Math.min(conf, 0.7)];
      }
    }
    return [null, 0];
  }
}

const r1 = (x) => Math.round(x * 10) / 10;

export function gramsFor(food, qty, unit) {
  if (unit in WEIGHT_UNITS) return r1((qty ?? 1) * WEIGHT_UNITS[unit]);
  const q = qty ?? 1;
  if (unit === null || unit === undefined) return r1(q * food.serving_g);
  if (food.units && unit in food.units) return r1(q * food.units[unit]);
  if (unit in SIZE_MULTIPLIER) return r1(q * food.serving_g * SIZE_MULTIPLIER[unit]);
  const fb = GENERIC_UNITS[unit];
  return r1(q * (fb ?? food.serving_g));
}

export function macrosFor(food, grams) {
  const k = grams / 100;
  return { kcal: r1(food.kcal * k), protein: r1(food.protein * k), carbs: r1(food.carbs * k), fat: r1(food.fat * k) };
}

export function parseText(text, index) {
  const items = [];
  for (const seg of splitSegments(text, index.protected)) {
    const m = extractMeasure(seg);
    if (!m.foodText) continue;
    const [food, confidence] = index.match(m.foodText);
    if (!food) { items.push({ input: seg, food: null, qty: m.qty, unit: m.unit, grams: null, confidence: 0, macros: {}, foodText: m.foodText }); continue; }
    const grams = gramsFor(food, m.qty, m.unit);
    if (grams <= 0 || grams > MAX_GRAMS) { items.push({ input: seg, food: null, qty: m.qty, unit: m.unit, grams: null, confidence: 0, macros: {}, foodText: m.foodText }); continue; }
    items.push({ input: seg, food, qty: m.qty, unit: m.unit, grams, confidence, macros: macrosFor(food, grams), foodText: m.foodText });
  }
  return items;
}
