// Sync backend: one JSON document per deployment, stored in Upstash Redis
// (attach it via Vercel Marketplace) and protected by FOOD_TRACKER_PASSWORD.
//
//   GET  /api/log            -> { state }
//   POST /api/log { op, … }  -> { state, result }
//
// The client does all the parsing; this only stores entries, saved foods and goals.

import { createHash, randomUUID, timingSafeEqual } from "node:crypto";

const KEY = "food-tracker:state:v1";
const MAX_ENTRIES = 50000, MAX_FOODS = 2000, MAX_STR = 300, MAX_ALIASES = 20;
const MACROS = ["kcal", "protein", "carbs", "fat"];

export class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

export const emptyState = () => ({ entries: [], customFoods: [], goals: {}, updated_at: null });

export function normalize(raw) {
  let d = raw;
  if (typeof d === "string") { try { d = JSON.parse(d); } catch { d = null; } }
  if (!d || typeof d !== "object") return emptyState();
  return {
    entries: Array.isArray(d.entries) ? d.entries : [],
    customFoods: Array.isArray(d.customFoods) ? d.customFoods : [],
    goals: d.goals && typeof d.goals === "object" ? d.goals : {},
    updated_at: typeof d.updated_at === "string" ? d.updated_at : null,
  };
}

// ---- validation -------------------------------------------------------------
const r2 = (x) => Math.round(x * 100) / 100;
function num(v, name, { min = 0, allowNull = false } = {}) {
  if (v === null || v === undefined) { if (allowNull) return null; v = 0; }
  const n = Number(v);
  if (!Number.isFinite(n) || n < min) throw new HttpError(400, `${name} must be a number ≥ ${min}`);
  return r2(n);
}
function str(v, name, { required = true, lower = false } = {}) {
  if (v === null || v === undefined || v === "") { if (required) throw new HttpError(400, `${name} is required`); return ""; }
  if (typeof v !== "string") throw new HttpError(400, `${name} must be text`);
  v = v.trim().slice(0, MAX_STR);
  return lower ? v.toLowerCase() : v;
}

export function cleanEntry(e) {
  if (!e || typeof e !== "object") throw new HttpError(400, "entry is required");
  const date = str(e.date, "date");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new HttpError(400, "date must be YYYY-MM-DD");
  const out = {
    id: typeof e.id === "string" && e.id ? e.id.slice(0, 64) : randomUUID(),
    date,
    created_at: typeof e.created_at === "string" && e.created_at ? e.created_at.slice(0, 40) : new Date().toISOString(),
    description: str(e.description, "description"),
    food_name: str(e.food_name, "food_name", { required: false, lower: true }) || null,
    grams: num(e.grams, "grams", { allowNull: true }),
    source: str(e.source, "source", { required: false }) || "manual",
  };
  for (const m of MACROS) out[m] = num(e[m], m);
  return out;
}

export function cleanFood(f) {
  if (!f || typeof f !== "object") throw new HttpError(400, "food is required");
  const out = {
    name: str(f.name, "name", { lower: true }),
    serving_g: num(f.serving_g, "serving_g", { min: 0.01 }),
    serving_unit: str(f.serving_unit, "serving_unit", { required: false, lower: true }) || "serving",
    aliases: (Array.isArray(f.aliases) ? f.aliases : []).slice(0, MAX_ALIASES).map((a) => str(a, "alias", { required: false, lower: true })).filter(Boolean),
    units: {},
    source: str(f.source, "source", { required: false }) || "custom",
  };
  for (const m of MACROS) out[m] = Number(f[m]); // per 100 g, may have 4 decimals
  for (const m of MACROS) if (!Number.isFinite(out[m]) || out[m] < 0) throw new HttpError(400, `${m} must be a number ≥ 0`);
  if (f.units && typeof f.units === "object") {
    for (const [k, v] of Object.entries(f.units).slice(0, 20)) if (typeof k === "string" && Number.isFinite(Number(v)) && Number(v) > 0) out.units[k.slice(0, 40)] = Number(v);
  }
  return out;
}

function cleanGoals(g) {
  if (!g || typeof g !== "object") throw new HttpError(400, "goals is required");
  const out = {};
  for (const m of MACROS) if (g[m] !== undefined && g[m] !== null) out[m] = num(g[m], m);
  return out;
}

const fingerprint = (e) => `${e.date}|${e.description}|${e.created_at}`;

// ---- operations --------------------------------------------------------------
export function apply(state, body) {
  if (!body || typeof body !== "object") throw new HttpError(400, "JSON body required");
  const s = { ...state, entries: [...state.entries], customFoods: [...state.customFoods], goals: { ...state.goals } };
  let result = null;
  switch (body.op) {
    case "add": {
      const entry = cleanEntry({ ...body.entry, id: undefined });
      if (s.entries.length >= MAX_ENTRIES) throw new HttpError(413, "log is full");
      s.entries.push(entry); result = entry; break;
    }
    case "update": {
      const id = str(body.id, "id"), grams = num(body.grams, "grams", { min: 0.01 });
      const i = s.entries.findIndex((e) => e.id === id);
      if (i < 0) throw new HttpError(404, "entry not found");
      const e = { ...s.entries[i] }, k = e.grams ? grams / e.grams : 0;
      for (const m of MACROS) e[m] = r2(e[m] * k);
      e.grams = grams; s.entries[i] = e; result = e; break;
    }
    case "delete": {
      const id = str(body.id, "id");
      const n = s.entries.length;
      s.entries = s.entries.filter((e) => e.id !== id);
      result = { deleted: s.entries.length < n }; break;
    }
    case "goals": {
      Object.assign(s.goals, cleanGoals(body.goals)); result = s.goals; break;
    }
    case "food": {
      const food = cleanFood(body.food);
      const replaces = str(body.replaces, "replaces", { required: false, lower: true });
      if (replaces && replaces !== food.name) s.customFoods = s.customFoods.filter((f) => f.name !== replaces);
      const i = s.customFoods.findIndex((f) => f.name === food.name);
      if (i >= 0) s.customFoods[i] = food; else { if (s.customFoods.length >= MAX_FOODS) throw new HttpError(413, "too many saved foods"); s.customFoods.push(food); }
      result = food; break;
    }
    case "deleteFood": {
      const name = str(body.name, "name", { lower: true });
      const n = s.customFoods.length;
      s.customFoods = s.customFoods.filter((f) => f.name !== name);
      result = { deleted: s.customFoods.length < n }; break;
    }
    case "merge": {
      // Bring another device's local log in without creating duplicates. The server copy wins on clashes.
      const incoming = normalize(body.state);
      const seen = new Set(s.entries.map(fingerprint));
      let entries = 0, foods = 0;
      for (const raw of incoming.entries.slice(0, MAX_ENTRIES)) {
        const e = cleanEntry({ ...raw, id: undefined });
        if (seen.has(fingerprint(e))) continue;
        seen.add(fingerprint(e)); s.entries.push(e); entries++;
      }
      const have = new Set(s.customFoods.map((f) => f.name));
      for (const raw of incoming.customFoods.slice(0, MAX_FOODS)) {
        const f = cleanFood(raw);
        if (have.has(f.name)) continue;
        have.add(f.name); s.customFoods.push(f); foods++;
      }
      for (const [k, v] of Object.entries(cleanGoals(incoming.goals))) if (s.goals[k] === undefined) s.goals[k] = v;
      result = { entries, foods }; break;
    }
    default:
      throw new HttpError(400, `unknown op "${body.op}"`);
  }
  s.entries.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : a.created_at < b.created_at ? -1 : 1));
  s.updated_at = new Date().toISOString();
  return { state: s, result };
}

// ---- storage ---------------------------------------------------------------------
let memory;
export async function getBackend(env = process.env) {
  if (env.FOOD_TRACKER_MEMORY) {
    memory ??= new Map();
    return { async get(k) { return memory.get(k) ?? null; }, async set(k, v) { memory.set(k, v); } };
  }
  const url = env.UPSTASH_REDIS_REST_URL || env.KV_REST_API_URL;
  const token = env.UPSTASH_REDIS_REST_TOKEN || env.KV_REST_API_TOKEN;
  if (!url || !token) return null;
  const { Redis } = await import("@upstash/redis");
  const redis = new Redis({ url, token });
  return { get: (k) => redis.get(k), set: (k, v) => redis.set(k, v) };
}

// ---- http ----------------------------------------------------------------------------
const sha = (s) => createHash("sha256").update(String(s)).digest();
const passwordOk = (given, expected) => Boolean(given) && timingSafeEqual(sha(given), sha(expected));

async function readJson(req) {
  if (req.body !== undefined && req.body !== null) {
    if (typeof req.body === "string") { try { return JSON.parse(req.body); } catch { throw new HttpError(400, "invalid JSON"); } }
    return req.body;
  }
  const chunks = [];
  for await (const c of req) chunks.push(c);
  if (!chunks.length) return null;
  try { return JSON.parse(Buffer.concat(chunks).toString("utf8")); } catch { throw new HttpError(400, "invalid JSON"); }
}

function send(res, status, obj) {
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("cache-control", "no-store");
  res.end(JSON.stringify(obj));
}

export default async function handler(req, res, env = process.env) {
  try {
    const backend = await getBackend(env);
    if (!backend) throw new HttpError(503, "Sync isn't set up yet: no Redis database is connected to this deployment.");
    if (!env.FOOD_TRACKER_PASSWORD) throw new HttpError(503, "Sync isn't set up yet: FOOD_TRACKER_PASSWORD isn't configured on the deployment.");
    const given = String(req.headers?.authorization || "").replace(/^Bearer\s+/i, "");
    if (!passwordOk(given, env.FOOD_TRACKER_PASSWORD)) throw new HttpError(401, "Wrong sync password.");

    const state = normalize(await backend.get(KEY));
    if (req.method === "GET") return send(res, 200, { state });
    if (req.method !== "POST") throw new HttpError(405, "method not allowed");
    const { state: next, result } = apply(state, await readJson(req));
    await backend.set(KEY, next);
    return send(res, 200, { state: next, result });
  } catch (e) {
    if (e instanceof HttpError) return send(res, e.status, { error: e.message });
    console.error(e);
    return send(res, 500, { error: "Sync failed on the server. Try again in a moment." });
  }
}
