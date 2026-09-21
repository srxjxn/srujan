"""Turn free text like "2 eggs, 150g chicken breast and a banana" into food items.

Pipeline:
  1. split the text into segments ("2 eggs" | "150g chicken breast" | "a banana")
  2. for each segment pull out quantity + unit, leaving the food description
  3. match the description against the food index (exact -> phrase -> fuzzy)
  4. convert quantity+unit into grams using the food's unit table
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from .foods import Food

# --------------------------------------------------------------------------- #
# Units
# --------------------------------------------------------------------------- #

# Food-independent weight/volume units -> grams (1 ml treated as 1 g).
WEIGHT_UNITS: dict[str, float] = {
    "g": 1, "gram": 1, "grams": 1, "gm": 1, "gms": 1, "gr": 1,
    "kg": 1000, "kilo": 1000, "kilos": 1000, "kilogram": 1000, "kilograms": 1000,
    "oz": 28.35, "ounce": 28.35, "ounces": 28.35,
    "lb": 453.6, "lbs": 453.6, "pound": 453.6, "pounds": 453.6,
    "ml": 1, "milliliter": 1, "milliliters": 1, "millilitre": 1, "millilitres": 1,
    "l": 1000, "liter": 1000, "liters": 1000, "litre": 1000, "litres": 1000,
    "floz": 29.57,
}

# Food-dependent units. Value is the fallback grams when the food has no entry
# for that unit; None means "one default serving of the food".
GENERIC_UNITS: dict[str, float | None] = {
    "cup": 240, "tbsp": 15, "tsp": 5, "slice": 30, "piece": None, "scoop": 30,
    "serving": None, "portion": None, "bowl": 300, "plate": 350, "handful": 30,
    "can": 355, "bottle": 500, "glass": 250, "packet": 40, "pack": 40, "bar": 45,
    "shot": 44, "pint": 473, "container": None, "tub": None, "clove": 3,
    "patty": 113, "fillet": 170, "link": 50, "stick": 30, "wedge": 40,
    "spear": 16, "square": 10, "cone": 100, "mug": 350, "box": None,
    "pouch": 90, "tin": None, "head": 300, "ear": 90, "cob": 90, "strip": 8,
    "rasher": 8, "breast": 174, "thigh": 90, "wing": 34, "chop": 150,
    "nugget": 17, "roll": None, "wrap": None, "jar": 250, "half": None,
    "small": None, "medium": None, "large": None, "block": 350, "dollop": 30,
    "splash": 15, "drizzle": 5, "dash": 1, "pat": 5, "cube": 10, "sheet": 1,
    "floret": 11, "leaf": 10, "baby": 10, "double": 88, "espresso": 30,
    "tall": 350, "grande": 470, "venti": 590, "burger": None, "whole": None,
    "ring": 84, "sandwich": None,
}

# Multipliers applied to serving_g when the food has no explicit unit entry.
SIZE_MULTIPLIER = {"small": 0.75, "medium": 1.0, "large": 1.5, "half": 0.5, "whole": 1.0, "double": 2.0}

UNIT_ALIASES: dict[str, str] = {
    "cups": "cup", "c": "cup",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsps": "tbsp", "tbs": "tbsp", "tbl": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsps": "tsp",
    "slices": "slice", "pieces": "piece", "pc": "piece", "pcs": "piece", "pce": "piece",
    "scoops": "scoop", "servings": "serving", "portions": "portion", "bowls": "bowl",
    "plates": "plate", "handfuls": "handful", "cans": "can", "bottles": "bottle",
    "glasses": "glass", "packets": "packet", "packs": "pack", "bars": "bar",
    "shots": "shot", "pints": "pint", "containers": "container", "tubs": "tub",
    "cloves": "clove", "patties": "patty", "fillets": "fillet", "filets": "fillet",
    "filet": "fillet", "links": "link", "sticks": "stick", "wedges": "wedge",
    "spears": "spear", "squares": "square", "cones": "cone", "mugs": "mug",
    "boxes": "box", "pouches": "pouch", "tins": "tin", "heads": "head",
    "ears": "ear", "cobs": "cob", "strips": "strip", "rashers": "rasher",
    "breasts": "breast", "thighs": "thigh", "wings": "wing", "chops": "chop",
    "nuggets": "nugget", "rolls": "roll", "wraps": "wrap", "jars": "jar",
    "halves": "half", "blocks": "block", "dollops": "dollop", "sheets": "sheet",
    "florets": "floret", "leaves": "leaf", "rings": "ring", "sandwiches": "sandwich",
    "sm": "small", "med": "medium", "lg": "large", "xl": "large",
    "burgers": "burger",
}

NUMBER_WORDS: dict[str, float] = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "dozen": 12, "half": 0.5, "quarter": 0.25, "couple": 2, "few": 3, "several": 3,
    "single": 1, "double": 2, "triple": 3,
}

UNICODE_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}

# Words that never help identify a food.
FILLER = {"of", "the", "some", "my", "a", "an", "and", "with", "for", "in", "on",
          "to", "at", "from", "ate", "had", "have", "having", "eat", "eating", "i",
          "im", "i'm", "just", "about", "around", "roughly", "approx", "approximately",
          "breakfast", "lunch", "dinner", "snack", "today", "tonight", "morning",
          "this", "that", "another", "more", "extra", "bit", "little", "big", "x"}

_NUM_RE = re.compile(r"^(\d+(?:[.,]\d+)?)(?:/(\d+))?$")
_NUM_UNIT_RE = re.compile(r"^(\d+(?:[.,]\d+)?)([a-z]+)$")
_X_QTY_RE = re.compile(r"^x(\d+(?:\.\d+)?)$")
_QTY_X_RE = re.compile(r"^(\d+(?:\.\d+)?)x$")


def _to_number(tok: str) -> float | None:
    if tok in UNICODE_FRACTIONS:
        return UNICODE_FRACTIONS[tok]
    if tok and tok[-1] in UNICODE_FRACTIONS and tok[:-1].isdigit():
        return int(tok[:-1]) + UNICODE_FRACTIONS[tok[-1]]
    m = _NUM_RE.match(tok)
    if not m:
        return None
    whole = float(m.group(1).replace(",", "."))
    if m.group(2):
        denom = float(m.group(2))
        return whole / denom if denom else None
    return whole


def _norm_unit(tok: str) -> str | None:
    tok = UNIT_ALIASES.get(tok, tok)
    if tok in WEIGHT_UNITS or tok in GENERIC_UNITS:
        return tok
    return None


# --------------------------------------------------------------------------- #
# Text normalisation and segmentation
# --------------------------------------------------------------------------- #

def singularize(tok: str) -> str:
    if len(tok) <= 3:
        return tok
    if tok.endswith("ies"):
        return tok[:-3] + "y"
    if tok.endswith(("shes", "ches", "xes", "sses", "oes")):
        return tok[:-2]
    if tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def normalize_tokens(text: str) -> list[str]:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^\w\s%½¼¾⅓⅔⅛/.'-]", " ", text)
    toks = [t.strip("'-.") for t in text.split()]
    return [singularize(t) for t in toks if t and t not in FILLER]


def normalize_phrase(text: str) -> str:
    return " ".join(normalize_tokens(text))


_SPLIT_RE = re.compile(r"\s*(?:,|;|\n|\+|\band\b|\bwith\b|\bplus\b|\balong with\b|\bthen\b)\s*", re.I)


_AND_A_HALF_RE = re.compile(r"\b(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)\s+and\s+a\s+(half|quarter)\b", re.I)


def _prenormalize(text: str) -> str:
    """'two and a half cups' -> 'two half cups' so 'and' doesn't split the item."""
    return _AND_A_HALF_RE.sub(r"\1 \2", text)


def split_segments(text: str, protected_phrases: list[str]) -> list[str]:
    """Split on separators but keep phrases like 'mac and cheese' intact."""
    work = _prenormalize(text)
    restore: dict[str, str] = {}
    for i, phrase in enumerate(protected_phrases):
        pat = re.compile(re.escape(phrase), re.I)
        if pat.search(work):
            token = f"\x00{i}\x00"
            restore[token] = phrase
            work = pat.sub(token, work)
    parts = [p.strip(" .") for p in _SPLIT_RE.split(work)]
    out = []
    for p in parts:
        for token, phrase in restore.items():
            p = p.replace(token, phrase)
        if p:
            out.append(p)
    return out


# --------------------------------------------------------------------------- #
# Quantity extraction
# --------------------------------------------------------------------------- #

@dataclass
class Measure:
    qty: float | None = None      # None = not specified
    unit: str | None = None       # normalised unit or None
    food_text: str = ""


def _pop_quantity(tokens: list[str]) -> tuple[float | None, list[str]]:
    """Consume a leading quantity ("2", "1 1/2", "half a", "a couple of")."""
    qty: float | None = None
    from_article = False
    i = 0
    while i < len(tokens):
        t = tokens[i]
        n = _to_number(t)
        if n is not None:
            qty = n if qty is None or from_article else qty + n   # "1 1/2"
            from_article = False
            i += 1
            continue
        m = _QTY_X_RE.match(t)
        if m:
            qty = float(m.group(1))
            i += 1
            continue
        if t in NUMBER_WORDS and (qty is None or from_article or t in ("half", "quarter")):
            if t in ("half", "quarter") and qty is not None and not from_article:
                qty = qty + NUMBER_WORDS[t]          # "two and a half"
            else:
                qty = NUMBER_WORDS[t]                 # "a couple", "a dozen", "a half"
            from_article = t in ("a", "an")
            i += 1
            # swallow "of" / "a" after couple/few/half
            while i < len(tokens) and tokens[i] in ("of", "a", "an"):
                i += 1
            continue
        if t in ("a", "an", "of") and qty is not None:
            i += 1
            continue
        break
    return qty, tokens[i:]


def extract_measure(segment: str) -> Measure:
    text = _prenormalize(segment.lower().strip())
    text = re.sub(r"[()\[\]]", " ", text)
    text = re.sub(r"\bfl\.?\s*oz\b", "floz", text)
    text = re.sub(r"(\d)\s*x\s*(?=[a-z])", r"\1x ", text)      # "2x eggs"
    text = re.sub(r"(?<=[a-z])\s*x\s*(\d)", r" x\1", text)    # "eggs x2"
    raw = [t.strip("'.") for t in re.split(r"\s+", text) if t.strip("'.")]

    # Expand "150g" -> "150", "g"
    tokens: list[str] = []
    for t in raw:
        m = _NUM_UNIT_RE.match(t)
        if m and _norm_unit(m.group(2)):
            tokens.extend([m.group(1), m.group(2)])
        else:
            tokens.append(t)

    # Leading quantity
    qty, rest = _pop_quantity(tokens)
    unit: str | None = None
    if rest:
        u = _norm_unit(rest[0])
        if u and (len(rest) > 1 or qty is not None):
            unit = u
            rest = rest[1:]
            while rest and rest[0] in ("of", "a", "an"):
                rest = rest[1:]
        elif qty is not None and rest[0] in SIZE_MULTIPLIER and len(rest) > 1:
            unit = rest[0]
            rest = rest[1:]

    # Trailing quantity: "chicken breast 200 g", "protein bar x2", "rice 1 cup"
    if qty is None and unit is None and len(rest) >= 2:
        m = _X_QTY_RE.match(rest[-1])
        if m:
            qty = float(m.group(1))
            rest = rest[:-1]
        else:
            tail_unit = _norm_unit(rest[-1])
            if tail_unit and len(rest) >= 3 and _to_number(rest[-2]) is not None:
                qty, unit = _to_number(rest[-2]), tail_unit
                rest = rest[:-2]
            elif _to_number(rest[-1]) is not None:
                qty = _to_number(rest[-1])
                rest = rest[:-1]

    food_text = " ".join(rest).strip()
    return Measure(qty=qty, unit=unit, food_text=food_text)


# --------------------------------------------------------------------------- #
# Food matching
# --------------------------------------------------------------------------- #

class FoodIndex:
    def __init__(self, foods: list[Food]):
        self.keys: dict[str, Food] = {}
        self.protected: list[str] = []
        for food in foods:
            self.add(food)

    def add(self, food: Food) -> None:
        for name in [food.name, *food.aliases]:
            key = normalize_phrase(name)
            if key:
                self.keys[key] = food
            if re.search(r"\b(and|with|plus)\b", name, re.I):
                self.protected.append(name.lower())
        self._keys_by_len = sorted(self.keys, key=lambda k: (-len(k.split()), -len(k)))

    def match(self, text: str) -> tuple[Food | None, float]:
        query = normalize_phrase(text)
        if not query:
            return None, 0.0
        if query in self.keys:
            return self.keys[query], 1.0
        qtoks = query.split()
        # longest key that appears as a contiguous phrase in the query
        for key in self._keys_by_len:
            ktoks = key.split()
            n = len(ktoks)
            if n > len(qtoks):
                continue
            for i in range(len(qtoks) - n + 1):
                if qtoks[i:i + n] == ktoks:
                    conf = 0.9 if n == len(qtoks) else max(0.5, 0.85 * n / len(qtoks))
                    return self.keys[key], round(conf, 2)
        # fuzzy full-string (typos)
        close = difflib.get_close_matches(query, list(self.keys), n=1, cutoff=0.8)
        if close:
            return self.keys[close[0]], 0.7
        # fuzzy per-token (e.g. "chiken")
        fixed = []
        for t in qtoks:
            c = difflib.get_close_matches(t, self._vocab(), n=1, cutoff=0.85)
            fixed.append(c[0] if c else t)
        if fixed != qtoks:
            f, conf = self.match(" ".join(fixed))
            if f:
                return f, min(conf, 0.7)
        return None, 0.0

    def _vocab(self) -> list[str]:
        if not hasattr(self, "_vocab_cache"):
            v: set[str] = set()
            for k in self.keys:
                v.update(k.split())
            self._vocab_cache = sorted(v)
        return self._vocab_cache


# --------------------------------------------------------------------------- #
# Putting it together
# --------------------------------------------------------------------------- #

@dataclass
class ParsedItem:
    input: str
    food: Food | None
    qty: float | None
    unit: str | None
    grams: float | None
    confidence: float
    macros: dict[str, float] = field(default_factory=dict)
    food_text: str = ""

    def to_dict(self) -> dict:
        return {
            "input": self.input,
            "food_name": self.food.name if self.food else None,
            "food_text": self.food_text,
            "qty": self.qty,
            "unit": self.unit,
            "grams": self.grams,
            "confidence": self.confidence,
            "source": self.food.source if self.food else None,
            **self.macros,
        }


def grams_for(food: Food, qty: float | None, unit: str | None) -> float:
    if unit in WEIGHT_UNITS:
        return round((qty or 1) * WEIGHT_UNITS[unit], 1)
    q = qty if qty is not None else 1
    if unit is None:
        return round(q * food.serving_g, 1)
    if unit in food.units:
        return round(q * food.units[unit], 1)
    if unit in SIZE_MULTIPLIER:
        return round(q * food.serving_g * SIZE_MULTIPLIER[unit], 1)
    fallback = GENERIC_UNITS.get(unit)
    return round(q * (fallback if fallback is not None else food.serving_g), 1)


MAX_GRAMS = 10_000  # anything heavier than 10 kg in one item is a parsing mistake


def parse_text(text: str, index: FoodIndex) -> list[ParsedItem]:
    items: list[ParsedItem] = []
    for seg in split_segments(text, index.protected):
        m = extract_measure(seg)
        if not m.food_text:
            continue
        food, conf = index.match(m.food_text)
        if food is None:
            items.append(ParsedItem(seg, None, m.qty, m.unit, None, 0.0, {}, m.food_text))
            continue
        grams = grams_for(food, m.qty, m.unit)
        if grams <= 0 or grams > MAX_GRAMS:
            # "banana 20250921" or similar nonsense - don't log a 20-tonne banana.
            items.append(ParsedItem(seg, None, m.qty, m.unit, None, 0.0, {}, m.food_text))
            continue
        items.append(ParsedItem(seg, food, m.qty, m.unit, grams, conf, food.macros_for(grams), m.food_text))
    return items
