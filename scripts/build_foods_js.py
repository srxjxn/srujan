"""Generate web/foods.js from food_tracker/foods.py so the web app shares the same database.

    python scripts/build_foods_js.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from food_tracker.foods import FOODS  # noqa: E402

rows = [
    {"name": f.name, "kcal": f.kcal, "protein": f.protein, "carbs": f.carbs, "fat": f.fat,
     "serving_g": f.serving_g, "units": f.units, "aliases": f.aliases}
    for f in FOODS
]
out = ROOT / "web" / "foods.js"
out.write_text(
    "// GENERATED from food_tracker/foods.py by scripts/build_foods_js.py - do not edit by hand.\n"
    "export const FOODS = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n"
)
print(f"wrote {out.relative_to(ROOT)} ({len(rows)} foods)")
