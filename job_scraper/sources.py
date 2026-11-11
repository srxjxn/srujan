"""One fetcher per applicant-tracking system. Each returns a list of Job for one company.

All of these are the public, unauthenticated endpoints that power the companies' own careers pages.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

from .fetch import FetchError, request_json
from .models import Job


def _ms_to_date(ms) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()


def _iso_date(value) -> str:
    return value[:10] if isinstance(value, str) else ""


def greenhouse(company: str, slug: str, **_) -> list[Job]:
    data = request_json(f"https://boards-api.greenhouse.io/v1/boards/{quote(slug)}/jobs")
    jobs = []
    for j in data.get("jobs", []):
        jobs.append(Job(
            company=company, ats="greenhouse", job_id=str(j["id"]), title=j.get("title", "").strip(),
            location=(j.get("location") or {}).get("name", ""), url=j.get("absolute_url", ""),
            department=", ".join(d.get("name", "") for d in j.get("departments") or []),
            posted=_iso_date(j.get("first_published") or j.get("updated_at")),
        ))
    return jobs


def lever(company: str, slug: str, **_) -> list[Job]:
    data = request_json(f"https://api.lever.co/v0/postings/{quote(slug)}?mode=json")
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        locs = cats.get("allLocations") or [cats.get("location", "")]
        jobs.append(Job(
            company=company, ats="lever", job_id=j["id"], title=j.get("text", "").strip(),
            location=" / ".join(l for l in locs if l), url=j.get("hostedUrl", ""),
            department=cats.get("team", "") or cats.get("department", ""),
            posted=_ms_to_date(j.get("createdAt")),
            remote=(j.get("workplaceType") == "remote") if j.get("workplaceType") else None,
        ))
    return jobs


def ashby(company: str, slug: str, **_) -> list[Job]:
    data = request_json(f"https://api.ashbyhq.com/posting-api/job-board/{quote(slug)}")
    jobs = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location", "")] + [
            s.get("location", "") for s in j.get("secondaryLocations") or [] if isinstance(s, dict)
        ]
        jobs.append(Job(
            company=company, ats="ashby", job_id=j.get("id", j.get("jobUrl", "")),
            title=j.get("title", "").strip(), location=" / ".join(l for l in locs if l),
            url=j.get("jobUrl", ""), department=j.get("department", "") or j.get("team", ""),
            posted=_iso_date(j.get("publishedAt")), remote=j.get("isRemote"),
        ))
    return jobs


def smartrecruiters(company: str, slug: str, max_jobs: int = 2000, **_) -> list[Job]:
    jobs, offset = [], 0
    while offset < max_jobs:
        data = request_json(
            f"https://api.smartrecruiters.com/v1/companies/{quote(slug)}/postings?limit=100&offset={offset}"
        )
        page = data.get("content", [])
        for j in page:
            loc = j.get("location") or {}
            where = ", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country", "").upper()) if x)
            jobs.append(Job(
                company=company, ats="smartrecruiters", job_id=str(j["id"]), title=j.get("name", "").strip(),
                location=where, url=f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                department=(j.get("department") or {}).get("label", ""),
                posted=_iso_date(j.get("releasedDate")), remote=loc.get("remote"),
            ))
        offset += len(page)
        if not page or offset >= data.get("totalFound", 0):
            break
    return jobs


def parse_workday_url(url: str) -> tuple[str, str, str]:
    """https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite -> (host, tenant, site)."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.netloc
    if "myworkdayjobs.com" not in host:
        raise FetchError(f"not a Workday careers URL: {url}")
    parts = [p for p in parsed.path.split("/") if p and not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", p)]
    if not parts:
        raise FetchError(f"Workday URL is missing the site name (the part after the domain): {url}")
    return host, host.split(".")[0], parts[0]


def workday(company: str, url: str, search: list[str] | None = None, max_jobs: int = 2000, **_) -> list[Job]:
    """Workday caps pages at 20 results, so with `search` terms we ask Workday to filter server-side
    instead of paging through every posting at a large company."""
    host, tenant, site = parse_workday_url(url)
    endpoint = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    seen: dict[str, Job] = {}
    for term in search or [""]:
        offset, total = 0, None
        while offset < max_jobs:
            data = request_json(endpoint, body={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term})
            page = data.get("jobPostings", [])
            for j in page:
                path = j.get("externalPath", "")
                if not path or path in seen:
                    continue
                seen[path] = Job(
                    company=company, ats="workday", job_id=(j.get("bulletFields") or [path])[0],
                    title=j.get("title", "").strip(), location=j.get("locationsText", ""),
                    url=f"https://{host}/en-US/{site}{path}", posted=j.get("postedOn", ""),
                )
            if total is None:  # Workday only reports the total on the first page
                total = data.get("total", 0)
            offset += 20
            if len(page) < 20 or offset >= total:
                break
    return list(seen.values())


FETCHERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
}
