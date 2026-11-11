from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Job:
    company: str
    ats: str
    job_id: str
    title: str
    location: str
    url: str
    department: str = ""
    posted: str = ""
    remote: bool | None = None

    @property
    def key(self) -> str:
        """Stable identity across runs, used to tell new postings from ones already seen."""
        return f"{self.ats}:{self.company}:{self.job_id}"

    def to_dict(self) -> dict:
        return asdict(self)
