"""Optional fallback: ask Claude for macros when a food isn't in the local database.

Only active when the Anthropic SDK is installed and credentials are configured
(ANTHROPIC_API_KEY, or an `ant auth login` profile). Results are cached as custom
foods so each new food costs at most one API call.
"""

from __future__ import annotations

import logging
import os

from pydantic import BaseModel, Field

from .foods import Food

log = logging.getLogger(__name__)

MODEL = os.environ.get("FOOD_TRACKER_MODEL", "claude-opus-5")

SYSTEM = (
    "You are a nutrition database. Given a short description of something someone ate, "
    "estimate its nutrition. Give macros PER 100 GRAMS of the food as prepared/eaten, "
    "a typical single-serving weight in grams, and the total grams the description implies "
    "(use the typical serving if no amount is stated). Use USDA-style values; for branded "
    "or restaurant items use the closest generic equivalent. Keep the name short and generic "
    "(e.g. 'chicken tinga' not 'my mom's chicken tinga')."
)


class FoodEstimate(BaseModel):
    name: str = Field(description="Short generic food name, lowercase")
    kcal_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    serving_g: float = Field(description="Typical single serving weight in grams")
    total_grams: float = Field(description="Grams implied by the description")
    is_food: bool = Field(description="False if the text does not describe something edible")


def available() -> bool:
    if os.environ.get("FOOD_TRACKER_DISABLE_CLAUDE"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    # `ant auth login` stores a profile the SDK picks up automatically.
    cfg = os.path.expanduser("~/.config/anthropic")
    return os.path.isdir(cfg) and any(os.scandir(cfg))


def estimate(description: str) -> tuple[Food, float] | None:
    """Return (Food with per-100g macros, total grams) or None if unavailable/inedible."""
    if not available():
        return None
    import anthropic

    client = anthropic.Anthropic()
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": description}],
            output_format=FoodEstimate,
        )
    except anthropic.APIError as e:
        log.warning("Claude lookup failed: %s", e)
        return None
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return None
    est: FoodEstimate = response.parsed_output
    if not est.is_food or est.total_grams <= 0:
        return None
    food = Food(
        name=est.name.strip().lower(),
        kcal=est.kcal_per_100g, protein=est.protein_per_100g,
        carbs=est.carbs_per_100g, fat=est.fat_per_100g,
        serving_g=est.serving_g or est.total_grams,
        source="claude",
    )
    return food, est.total_grams
