"""Title and location filters. Terms match whole words, case-insensitively,
so "intern" does not match "internal" and "ML" does not match "HTML"."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Job

# Workday shows "3 Locations" instead of naming them; we can't judge those, so we keep them.
_UNKNOWN_LOCATION = re.compile(r"^\s*\d+\s+locations?\s*$", re.I)


def _pattern(terms: list[str]) -> re.Pattern | None:
    terms = [t.strip() for t in terms if t and t.strip()]
    if not terms:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(t) for t in terms) + r")(?!\w)", re.I)


@dataclass
class JobFilter:
    title_include: list[str] = field(default_factory=list)
    title_exclude: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    include_remote: bool = True

    def __post_init__(self):
        self._inc = _pattern(self.title_include)
        self._exc = _pattern(self.title_exclude)
        self._loc = _pattern(self.locations)

    def matches(self, job: Job) -> bool:
        if self._inc and not self._inc.search(job.title):
            return False
        if self._exc and self._exc.search(job.title):
            return False
        return self._location_ok(job)

    def _location_ok(self, job: Job) -> bool:
        if not self._loc:
            return True
        if not job.location.strip() or _UNKNOWN_LOCATION.match(job.location):
            return True
        if self._loc.search(job.location):
            return True
        if self.include_remote and (job.remote or re.search(r"\bremote\b", job.location, re.I)):
            return True
        return False

    @classmethod
    def from_config(cls, base: dict, override: dict | None = None) -> "JobFilter":
        merged = {**base, **{k: v for k, v in (override or {}).items() if k in cls.__dataclass_fields__}}
        return cls(**{k: v for k, v in merged.items() if k in cls.__dataclass_fields__})
