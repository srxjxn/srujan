"""FastAPI server: JSON API + static front end."""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import claude_lookup
from .db import Database
from .foods import FOODS, Food
from .parser import FoodIndex, grams_for, parse_text

log = logging.getLogger("food_tracker")

DB_PATH = os.environ.get("FOOD_TRACKER_DB", str(Path(__file__).resolve().parent.parent / "data" / "food_tracker.db"))
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Food Tracker", version="1.0.0")
db = Database(DB_PATH)
index = FoodIndex(FOODS)
for _f in db.custom_foods():
    index.add(_f)


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #

class LogRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    date: str | None = None
    use_claude: bool = True


class ManualEntry(BaseModel):
    date: str | None = None
    name: str = Field(min_length=1, max_length=200)
    grams: float | None = Field(default=None, gt=0)
    kcal: float = Field(ge=0)
    protein: float = Field(default=0, ge=0)
    carbs: float = Field(default=0, ge=0)
    fat: float = Field(default=0, ge=0)
    remember: bool = True


class GramsUpdate(BaseModel):
    grams: float = Field(gt=0)


class Goals(BaseModel):
    kcal: float | None = Field(default=None, ge=0)
    protein: float | None = Field(default=None, ge=0)
    carbs: float | None = Field(default=None, ge=0)
    fat: float | None = Field(default=None, ge=0)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _date(d: str | None) -> str:
    if not d:
        return date.today().isoformat()
    try:
        return date.fromisoformat(d).isoformat()
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")


def _totals(entries: list[dict]) -> dict:
    t = {k: 0.0 for k in ("kcal", "protein", "carbs", "fat")}
    for e in entries:
        for k in t:
            t[k] += e[k] or 0
    return {k: round(v, 1) for k, v in t.items()}


def _day_payload(d: str) -> dict:
    entries = db.entries_for(d)
    return {"date": d, "entries": entries, "totals": _totals(entries), "goals": db.get_goals()}


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status():
    return {"claude_lookup": claude_lookup.available(), "foods": len(index.keys), "model": claude_lookup.MODEL}


@app.get("/api/day")
def get_day(date: str | None = None):
    return _day_payload(_date(date))


@app.get("/api/history")
def history(days: int = 7, end: str | None = None):
    days = max(1, min(days, 90))
    last = date.fromisoformat(_date(end))
    dates = [(last - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    totals = db.daily_totals(dates)
    return {"days": [{"date": d, **totals.get(d, {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "n": 0})} for d in dates],
            "goals": db.get_goals()}


@app.post("/api/log")
def log_food(req: LogRequest):
    d = _date(req.date)
    added, unmatched = [], []
    for item in parse_text(req.text, index):
        food = item.food
        grams = item.grams
        if food is None and req.use_claude and claude_lookup.available():
            result = claude_lookup.estimate(item.input)
            if result:
                food, grams = result
                # Cache so next time it's a local match, then re-apply any explicit amount.
                db.save_food(food)
                index.add(food)
                if item.qty is not None or item.unit is not None:
                    grams = grams_for(food, item.qty, item.unit)
        if food is None:
            unmatched.append(item.to_dict())
            continue
        macros = food.macros_for(grams)
        entry = db.add_entry(d, item.input, food.name, grams, macros, food.source)
        entry["confidence"] = item.confidence
        added.append(entry)
    return {"added": added, "unmatched": unmatched, **_day_payload(d)}


@app.post("/api/entries/manual")
def manual_entry(req: ManualEntry):
    d = _date(req.date)
    grams = req.grams or 100.0
    macros = {"kcal": req.kcal, "protein": req.protein, "carbs": req.carbs, "fat": req.fat}
    if req.remember:
        k = 100.0 / grams
        food = Food(req.name.strip().lower(), round(req.kcal * k, 2), round(req.protein * k, 2),
                    round(req.carbs * k, 2), round(req.fat * k, 2), serving_g=grams, source="custom")
        db.save_food(food)
        index.add(food)
    entry = db.add_entry(d, req.name, req.name.strip().lower(), grams, macros, "manual")
    return {"added": [entry], "unmatched": [], **_day_payload(d)}


@app.patch("/api/entries/{entry_id}")
def update_entry(entry_id: int, req: GramsUpdate):
    entry = db.update_entry_grams(entry_id, req.grams)
    if not entry:
        raise HTTPException(404, "entry not found")
    return {"entry": entry, **_day_payload(entry["date"])}


@app.delete("/api/entries/{entry_id}")
def delete_entry(entry_id: int):
    entry = db.get_entry(entry_id)
    if not entry or not db.delete_entry(entry_id):
        raise HTTPException(404, "entry not found")
    return _day_payload(entry["date"])


@app.get("/api/goals")
def get_goals():
    return db.get_goals()


@app.put("/api/goals")
def put_goals(req: Goals):
    return db.set_goals({k: v for k, v in req.model_dump().items() if v is not None})


@app.get("/api/foods")
def search_foods(q: str = "", limit: int = 12):
    q = q.strip().lower()
    seen: dict[str, Food] = {}
    for key, food in index.keys.items():
        if not q or q in key or q in food.name:
            seen.setdefault(food.name, food)
    results = sorted(seen.values(), key=lambda f: (not f.name.startswith(q), len(f.name)))[:max(1, min(limit, 50))]
    return [{"name": f.name, "serving_g": f.serving_g, "source": f.source, **f.macros_for(f.serving_g)} for f in results]


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
