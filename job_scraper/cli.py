from __future__ import annotations

import argparse
import json
import re
import sys
import time
import tomllib
from pathlib import Path

from . import output
from .fetch import FetchError
from .filters import JobFilter
from .models import Job
from .sources import FETCHERS

DEFAULT_CONFIG = "companies.toml"
DEFAULT_OUT = "jobs_output"


def load_config(path: Path) -> dict:
    with path.open("rb") as f:
        cfg = tomllib.load(f)
    companies = cfg.get("companies", [])
    problems = []
    for i, c in enumerate(companies, 1):
        name = c.get("name") or f"company #{i}"
        ats = c.get("ats")
        if ats not in FETCHERS:
            problems.append(f"{name}: ats must be one of {', '.join(FETCHERS)} (got {ats!r})")
        elif ats == "workday" and not c.get("url"):
            problems.append(f"{name}: workday companies need url = \"https://<x>.wd<N>.myworkdayjobs.com/<site>\"")
        elif ats != "workday" and not c.get("slug"):
            problems.append(f"{name}: needs slug (the company's id on {ats}; try `python -m job_scraper find \"{name}\"`)")
    if problems:
        raise SystemExit("Config problems in " + str(path) + ":\n  " + "\n  ".join(problems))
    return cfg


def scrape(cfg: dict, only: list[str] | None = None, delay: float = 0.5, log=None) -> tuple[list[Job], dict[str, str]]:
    log = log or print
    base_filter = cfg.get("filters", {})
    wanted = {o.lower() for o in only or []}
    jobs: list[Job] = []
    errors: dict[str, str] = {}
    for c in cfg.get("companies", []):
        name = c["name"]
        if wanted and name.lower() not in wanted:
            continue
        flt = JobFilter.from_config(base_filter, c)
        search = c.get("search") or base_filter.get("workday_search") or base_filter.get("title_include")
        try:
            found = FETCHERS[c["ats"]](company=name, slug=c.get("slug", ""), url=c.get("url", ""), search=search)
        except FetchError as e:
            errors[name] = str(e)
            log(f"  ✗ {name}: {e}")
            continue
        kept = [j for j in found if flt.matches(j)]
        jobs.extend(kept)
        log(f"  ✓ {name}: {len(kept)} matching of {len(found)} open roles")
        time.sleep(delay)
    return jobs, errors


def cmd_run(args) -> int:
    cfg = load_config(Path(args.config))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Scraping {len(cfg.get('companies', []))} companies...")
    jobs, errors = scrape(cfg, only=args.only)

    seen_path = out / "seen.json"
    seen = output.load_seen(seen_path)
    rows, updated = output.mark_new(jobs, seen)
    # A filtered (--only) run still records what it saw, but never forgets other companies' history.
    seen_path.write_text(json.dumps(updated, indent=0, sort_keys=True))
    output.write_csv(out / "jobs.csv", rows)
    output.write_csv(out / "new_jobs.csv", [r for r in rows if r["new"]])
    (out / "jobs.json").write_text(json.dumps(rows, indent=2))
    output.write_html(out / "report.html", rows, errors)

    new = [r for r in rows if r["new"]]
    print(f"\n{len(rows)} matching roles, {len(new)} new. Report: {out / 'report.html'}")
    for r in new[:50]:
        print(f"  NEW  {r['company']:<18} {r['title']}  ({r['location']})\n       {r['url']}")
    if errors:
        print(f"\n{len(errors)} companies failed; check their slug/url in {args.config}.")
    return 1 if errors and not jobs else 0


def _slug_candidates(name: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", name.lower())
    cands = ["".join(words), "-".join(words), words[0] if words else ""]
    return list(dict.fromkeys(c for c in cands if c))


def cmd_find(args) -> int:
    """Try the company name against each ATS that has a slug-based public API."""
    slugs = [args.slug] if args.slug else _slug_candidates(args.name)
    hits = 0
    for ats in ("greenhouse", "lever", "ashby", "smartrecruiters"):
        for slug in slugs:
            try:
                jobs = FETCHERS[ats](company=args.name, slug=slug)
            except FetchError:
                continue
            if ats == "smartrecruiters" and not jobs:
                continue  # SmartRecruiters answers for any slug, so an empty list means "not here"
            hits += 1
            print(f'  {ats:<16} slug = "{slug}"   ({len(jobs)} open roles)')
            print(f'    [[companies]]\n    name = "{args.name}"\n    ats = "{ats}"\n    slug = "{slug}"\n')
    if not hits:
        print(
            f"No Greenhouse/Lever/Ashby/SmartRecruiters board found for {args.name!r} (tried: {', '.join(slugs)}).\n"
            "Open the company's careers page and click a job; the address usually gives it away:\n"
            "  boards.greenhouse.io/<slug>  or  job-boards.greenhouse.io/<slug>  -> ats = \"greenhouse\"\n"
            "  jobs.lever.co/<slug>                                         -> ats = \"lever\"\n"
            "  jobs.ashbyhq.com/<slug>                                      -> ats = \"ashby\"\n"
            "  jobs.smartrecruiters.com/<slug>                              -> ats = \"smartrecruiters\"\n"
            "  <x>.wd5.myworkdayjobs.com/<site>                             -> ats = \"workday\", url = that address\n"
            "Retry with --slug if you spot one."
        )
    return 0 if hits else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m job_scraper", description="Scrape open roles at your target companies.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="scrape every company in the config and write the report")
    r.add_argument("--config", default=DEFAULT_CONFIG)
    r.add_argument("--out", default=DEFAULT_OUT)
    r.add_argument("--only", nargs="+", metavar="COMPANY", help="scrape just these companies (by name)")
    r.set_defaults(func=cmd_run)
    f = sub.add_parser("find", help="discover which job board a company uses")
    f.add_argument("name")
    f.add_argument("--slug", help="a specific slug to try")
    f.set_defaults(func=cmd_find)
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f"Not found: {e.filename}", file=sys.stderr)
        return 2
