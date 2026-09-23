// node --test api/log.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { PassThrough } from "node:stream";
import handler, { apply, emptyState, cleanEntry } from "./log.js";

const ENV = { FOOD_TRACKER_MEMORY: "1", FOOD_TRACKER_PASSWORD: "hunter2" };

function call(method, body, password = "hunter2", env = ENV) {
  const req = new PassThrough();
  req.method = method;
  req.headers = password ? { authorization: `Bearer ${password}` } : {};
  if (body !== undefined) req.end(JSON.stringify(body)); else req.end();
  return new Promise((resolve) => {
    const res = { statusCode: 200, headers: {}, setHeader(k, v) { this.headers[k] = v; }, end(s) { resolve({ status: this.statusCode, body: JSON.parse(s) }); } };
    handler(req, res, env);
  });
}

test("apply: add, update, delete", () => {
  let { state, result: e } = apply(emptyState(), { op: "add", entry: { date: "2026-09-23", description: "2 eggs", food_name: "egg", grams: 100, kcal: 143, protein: 12.6, carbs: 0.7, fat: 9.5, source: "database" } });
  assert.equal(state.entries.length, 1);
  assert.match(e.id, /^[0-9a-f-]{36}$/);
  ({ state } = apply(state, { op: "update", id: e.id, grams: 200 }));
  assert.equal(state.entries[0].kcal, 286);
  assert.throws(() => apply(state, { op: "update", id: "nope", grams: 5 }), /not found/);
  ({ state } = apply(state, { op: "delete", id: e.id }));
  assert.equal(state.entries.length, 0);
});

test("apply: validation", () => {
  assert.throws(() => apply(emptyState(), { op: "add", entry: { date: "yesterday", description: "x" } }), /YYYY-MM-DD/);
  assert.throws(() => apply(emptyState(), { op: "add", entry: { date: "2026-09-23", description: "x", kcal: -1 } }), /kcal/);
  assert.throws(() => apply(emptyState(), { op: "nope" }), /unknown op/);
  assert.throws(() => apply(emptyState(), { op: "food", food: { name: "x", serving_g: 0, kcal: 1 } }), /serving_g/);
});

test("apply: foods and goals", () => {
  let { state } = apply(emptyState(), { op: "food", food: { name: "Whey", serving_g: 31, serving_unit: "scoop", kcal: 387, protein: 77, carbs: 10, fat: 3, aliases: ["protein shake"], units: { scoop: 31 } } });
  assert.equal(state.customFoods[0].name, "whey");
  ({ state } = apply(state, { op: "food", replaces: "whey", food: { name: "gold whey", serving_g: 31, kcal: 387, protein: 77, carbs: 10, fat: 3 } }));
  assert.deepEqual(state.customFoods.map((f) => f.name), ["gold whey"]);
  ({ state } = apply(state, { op: "deleteFood", name: "gold whey" }));
  assert.equal(state.customFoods.length, 0);
  ({ state } = apply(state, { op: "goals", goals: { kcal: 2500, protein: "180" } }));
  assert.deepEqual(state.goals, { kcal: 2500, protein: 180 });
});

test("apply: merge dedupes and keeps server copy", () => {
  const local = { entries: [
    { id: 1, date: "2026-09-22", created_at: "2026-09-22T10:00:00Z", description: "a banana", food_name: "banana", grams: 118, kcal: 105, protein: 1.3, carbs: 26.9, fat: 0.4, source: "database" },
    { id: 2, date: "2026-09-22", created_at: "2026-09-22T11:00:00Z", description: "coffee", food_name: "coffee", grams: 240, kcal: 2, protein: 0, carbs: 0, fat: 0, source: "database" },
  ], customFoods: [{ name: "whey", serving_g: 31, kcal: 387, protein: 77, carbs: 10, fat: 3 }], goals: { kcal: 1800 }, nextId: 3 };
  let { state, result } = apply(emptyState(), { op: "merge", state: local });
  assert.deepEqual(result, { entries: 2, foods: 1 });
  assert.equal(state.goals.kcal, 1800);
  ({ state, result } = apply(state, { op: "merge", state: local }));
  assert.deepEqual(result, { entries: 0, foods: 0 });
  assert.equal(state.entries.length, 2);
  assert.ok(state.entries.every((e) => typeof e.id === "string" && e.id.length === 36));
});

test("handler: auth and setup errors", async () => {
  assert.equal((await call("GET", undefined, "wrong")).status, 401);
  assert.equal((await call("GET", undefined, null)).status, 401);
  const noPw = await call("GET", undefined, "hunter2", { FOOD_TRACKER_MEMORY: "1" });
  assert.equal(noPw.status, 503);
  assert.match(noPw.body.error, /FOOD_TRACKER_PASSWORD/);
  const noDb = await call("GET", undefined, "hunter2", { FOOD_TRACKER_PASSWORD: "hunter2" });
  assert.equal(noDb.status, 503);
  assert.match(noDb.body.error, /Redis/);
  assert.equal((await call("PUT", {})).status, 405);
});

test("handler: round trip persists between calls", async () => {
  const before = await call("GET");
  assert.equal(before.status, 200);
  const n = before.body.state.entries.length;
  const add = await call("POST", { op: "add", entry: { date: "2026-09-23", description: "a latte", food_name: "latte", grams: 350, kcal: 175, protein: 11.6, carbs: 17.5, fat: 7 } });
  assert.equal(add.status, 200);
  assert.equal(add.body.result.description, "a latte");
  const after = await call("GET");
  assert.equal(after.body.state.entries.length, n + 1);
  const bad = await call("POST", { op: "add", entry: { description: "no date" } });
  assert.equal(bad.status, 400);
});

test("cleanEntry assigns ids and rounds", () => {
  const e = cleanEntry({ date: "2026-09-23", description: "x", kcal: 1.006 });
  assert.equal(e.kcal, 1.01);
  assert.equal(e.grams, null);
});
