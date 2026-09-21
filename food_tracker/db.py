"""SQLite persistence: log entries, custom foods, goals."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .foods import Food

DEFAULT_GOALS = {"kcal": 2200, "protein": 150, "carbs": 220, "fat": 70}

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    description TEXT NOT NULL,
    food_name TEXT,
    grams REAL,
    kcal REAL NOT NULL DEFAULT 0,
    protein REAL NOT NULL DEFAULT 0,
    carbs REAL NOT NULL DEFAULT 0,
    fat REAL NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual'
);
CREATE INDEX IF NOT EXISTS entries_date ON entries(date);
CREATE TABLE IF NOT EXISTS custom_foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kcal REAL NOT NULL, protein REAL NOT NULL, carbs REAL NOT NULL, fat REAL NOT NULL,
    serving_g REAL NOT NULL,
    aliases TEXT NOT NULL DEFAULT '[]',
    units TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'custom',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    # ---- entries -----------------------------------------------------------
    def add_entry(self, date: str, description: str, food_name: str | None, grams: float | None,
                  macros: dict, source: str) -> dict:
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO entries(date, created_at, description, food_name, grams, kcal, protein, carbs, fat, source)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (date, _now(), description, food_name, grams,
                 macros.get("kcal", 0), macros.get("protein", 0), macros.get("carbs", 0), macros.get("fat", 0), source),
            )
            return self.get_entry(cur.lastrowid, c)

    def get_entry(self, entry_id: int, c=None) -> dict | None:
        q = "SELECT * FROM entries WHERE id=?"
        if c is not None:
            row = c.execute(q, (entry_id,)).fetchone()
        else:
            with self.conn() as c2:
                row = c2.execute(q, (entry_id,)).fetchone()
        return dict(row) if row else None

    def entries_for(self, date: str) -> list[dict]:
        with self.conn() as c:
            rows = c.execute("SELECT * FROM entries WHERE date=? ORDER BY id", (date,)).fetchall()
        return [dict(r) for r in rows]

    def update_entry_grams(self, entry_id: int, grams: float) -> dict | None:
        with self.conn() as c:
            row = c.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
            if not row:
                return None
            old = row["grams"] or 0
            k = grams / old if old else 0
            c.execute(
                "UPDATE entries SET grams=?, kcal=?, protein=?, carbs=?, fat=? WHERE id=?",
                (grams, round(row["kcal"] * k, 1), round(row["protein"] * k, 1),
                 round(row["carbs"] * k, 1), round(row["fat"] * k, 1), entry_id),
            )
            return self.get_entry(entry_id, c)

    def delete_entry(self, entry_id: int) -> bool:
        with self.conn() as c:
            return c.execute("DELETE FROM entries WHERE id=?", (entry_id,)).rowcount > 0

    def daily_totals(self, dates: list[str]) -> dict[str, dict]:
        if not dates:
            return {}
        qmarks = ",".join("?" * len(dates))
        with self.conn() as c:
            rows = c.execute(
                f"SELECT date, SUM(kcal) kcal, SUM(protein) protein, SUM(carbs) carbs, SUM(fat) fat, COUNT(*) n"
                f" FROM entries WHERE date IN ({qmarks}) GROUP BY date", dates).fetchall()
        return {r["date"]: {k: round(r[k] or 0, 1) for k in ("kcal", "protein", "carbs", "fat")} | {"n": r["n"]}
                for r in rows}

    # ---- custom foods ------------------------------------------------------
    def save_food(self, food: Food) -> None:
        with self.conn() as c:
            c.execute(
                "INSERT INTO custom_foods(name, kcal, protein, carbs, fat, serving_g, aliases, units, source, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(name) DO UPDATE SET kcal=excluded.kcal, protein=excluded.protein, carbs=excluded.carbs,"
                " fat=excluded.fat, serving_g=excluded.serving_g, aliases=excluded.aliases, units=excluded.units,"
                " source=excluded.source",
                (food.name.strip().lower(), food.kcal, food.protein, food.carbs, food.fat, food.serving_g,
                 json.dumps(food.aliases), json.dumps(food.units), food.source, _now()),
            )

    def custom_foods(self) -> list[Food]:
        with self.conn() as c:
            rows = c.execute("SELECT * FROM custom_foods ORDER BY id").fetchall()
        return [Food(r["name"], r["kcal"], r["protein"], r["carbs"], r["fat"], r["serving_g"],
                     json.loads(r["units"]), json.loads(r["aliases"]), r["source"]) for r in rows]

    # ---- goals -------------------------------------------------------------
    def get_goals(self) -> dict:
        with self.conn() as c:
            row = c.execute("SELECT value FROM settings WHERE key='goals'").fetchone()
        return {**DEFAULT_GOALS, **(json.loads(row["value"]) if row else {})}

    def set_goals(self, goals: dict) -> dict:
        clean = {k: float(goals[k]) for k in DEFAULT_GOALS if k in goals}
        merged = {**self.get_goals(), **clean}
        with self.conn() as c:
            c.execute("INSERT INTO settings(key, value) VALUES('goals', ?)"
                      " ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(merged),))
        return merged
