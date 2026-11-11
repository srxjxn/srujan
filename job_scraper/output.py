"""Writes results and remembers which postings were already seen, so each run can flag what's new."""
from __future__ import annotations

import csv
import html
import json
from datetime import date
from pathlib import Path

from .models import Job

CSV_FIELDS = ["new", "company", "title", "location", "department", "posted", "url", "ats", "job_id", "first_seen"]


def load_seen(path: Path) -> dict[str, str]:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def mark_new(jobs: list[Job], seen: dict[str, str], today: str | None = None) -> tuple[list[dict], dict[str, str]]:
    """Returns rows (each job + new/first_seen) and the updated seen map.

    The first time a company is scraped nothing of its is marked new, since everything would be."""
    today = today or date.today().isoformat()
    known_companies = {key.split(":", 2)[1] for key in seen}
    updated = dict(seen)
    rows = []
    for job in jobs:
        is_new = job.key not in seen and job.company in known_companies
        updated.setdefault(job.key, today)
        rows.append({**job.to_dict(), "new": "NEW" if is_new else "", "first_seen": updated[job.key]})
    rows.sort(key=lambda r: (r["new"] != "NEW", r["company"].lower(), r["title"].lower()))
    return rows, updated


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_html(path: Path, rows: list[dict], errors: dict[str, str]) -> None:
    esc = html.escape
    new_count = sum(r["new"] == "NEW" for r in rows)
    body = "".join(
        f'<tr class="{"new" if r["new"] else ""}"><td>{esc(r["new"])}</td><td>{esc(r["company"])}</td>'
        f'<td><a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["title"])}</a></td>'
        f'<td>{esc(r["location"])}</td><td>{esc(r["department"])}</td><td>{esc(r["posted"])}</td>'
        f'<td>{esc(r["first_seen"])}</td></tr>'
        for r in rows
    )
    err = "".join(f"<li><b>{esc(c)}</b>: {esc(m)}</li>" for c, m in errors.items())
    path.write_text(f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Target company jobs</title>
<style>
body{{font:14px/1.4 system-ui,sans-serif;margin:16px;color:#1a1a1a;background:#fff}}
table{{border-collapse:collapse;width:100%}}th,td{{padding:6px 8px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}
th{{position:sticky;top:0;background:#f4f4f4;cursor:pointer}}tr.new{{background:#eef8ee}}a{{color:#0b57d0}}
input{{padding:6px;width:100%;max-width:360px;margin:8px 0}}.err{{color:#a00}}
</style>
<h1>Target company jobs</h1>
<p>{len(rows)} matching roles, {new_count} new since the last run. Generated {date.today().isoformat()}.</p>
{f'<ul class="err">{err}</ul>' if err else ''}
<input id="q" placeholder="Filter by company, title, location..." oninput="f()">
<div style="overflow-x:auto"><table id="t"><thead><tr><th></th><th>Company</th><th>Title</th><th>Location</th><th>Team</th><th>Posted</th><th>First seen</th></tr></thead>
<tbody>{body}</tbody></table></div>
<script>
function f(){{const q=document.getElementById('q').value.toLowerCase();for(const r of document.querySelectorAll('#t tbody tr'))r.style.display=r.textContent.toLowerCase().includes(q)?'':'none'}}
document.querySelectorAll('th').forEach((th,i)=>th.onclick=()=>{{const b=th.closest('table').tBodies[0];const rs=[...b.rows];const d=th.dataset.d=th.dataset.d==='1'?'0':'1';rs.sort((a,c)=>a.cells[i].textContent.localeCompare(c.cells[i].textContent)*(d==='1'?1:-1));rs.forEach(r=>b.appendChild(r))}});
</script>
""", encoding="utf-8")
