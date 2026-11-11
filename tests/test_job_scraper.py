import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from job_scraper import cli, output, sources
from job_scraper.filters import JobFilter
from job_scraper.models import Job


def job(title="Software Engineer", location="San Francisco, CA", company="Acme", job_id="1", **kw):
    return Job(company=company, ats="greenhouse", job_id=job_id, title=title, location=location, url="u", **kw)


class FilterTests(unittest.TestCase):
    def test_include_exclude_are_whole_word(self):
        f = JobFilter(title_include=["software engineer", "ML"], title_exclude=["intern"])
        self.assertTrue(f.matches(job("Senior Software Engineer, Payments")))
        self.assertTrue(f.matches(job("ML Platform Engineer")))
        self.assertFalse(f.matches(job("HTML Email Designer")))  # "ML" inside "HTML"
        self.assertFalse(f.matches(job("Software Engineer Intern")))
        self.assertTrue(f.matches(job("Software Engineer, Internal Tools")))  # "intern" inside "Internal"

    def test_empty_include_keeps_everything(self):
        self.assertTrue(JobFilter().matches(job("Chef")))

    def test_locations_and_remote(self):
        f = JobFilter(locations=["New York"], include_remote=True)
        self.assertTrue(f.matches(job(location="New York, NY")))
        self.assertFalse(f.matches(job(location="London")))
        self.assertTrue(f.matches(job(location="Remote - US")))
        self.assertTrue(f.matches(job(location="London", remote=True)))
        self.assertTrue(f.matches(job(location="3 Locations")))  # Workday hides these; keep
        self.assertFalse(JobFilter(locations=["New York"], include_remote=False).matches(job(location="Remote")))

    def test_company_override(self):
        f = JobFilter.from_config({"title_include": ["engineer"]}, {"title_include": ["designer"], "name": "X"})
        self.assertTrue(f.matches(job("Product Designer")))
        self.assertFalse(f.matches(job("Engineer")))


class SourceTests(unittest.TestCase):
    def test_greenhouse(self):
        data = {"jobs": [{"id": 7, "title": " SWE ", "absolute_url": "https://x/7", "location": {"name": "NYC"},
                          "departments": [{"name": "Eng"}], "first_published": "2026-10-01T00:00:00-04:00"}]}
        with mock.patch.object(sources, "request_json", return_value=data):
            [j] = sources.greenhouse("Acme", "acme")
        self.assertEqual((j.job_id, j.title, j.location, j.department, j.posted), ("7", "SWE", "NYC", "Eng", "2026-10-01"))

    def test_lever(self):
        data = [{"id": "abc", "text": "Backend Engineer", "hostedUrl": "https://jobs.lever.co/a/abc",
                 "categories": {"location": "Austin", "allLocations": ["Austin", "Remote"], "team": "Platform"},
                 "createdAt": 1767225600000, "workplaceType": "hybrid"}]
        with mock.patch.object(sources, "request_json", return_value=data):
            [j] = sources.lever("Acme", "acme")
        self.assertEqual((j.location, j.department, j.posted, j.remote), ("Austin / Remote", "Platform", "2026-01-01", False))

    def test_ashby_skips_unlisted(self):
        data = {"jobs": [
            {"id": "1", "title": "A", "location": "SF", "jobUrl": "u1", "isRemote": True, "publishedAt": "2026-09-09T1"},
            {"id": "2", "title": "B", "location": "SF", "jobUrl": "u2", "isListed": False},
        ]}
        with mock.patch.object(sources, "request_json", return_value=data):
            jobs = sources.ashby("Acme", "acme")
        self.assertEqual([j.title for j in jobs], ["A"])
        self.assertTrue(jobs[0].remote)

    def test_smartrecruiters_pages(self):
        def fake(url, **_):
            offset = int(url.rsplit("=", 1)[1])
            n = 100 if offset == 0 else 30
            return {"totalFound": 130, "content": [
                {"id": f"{offset + i}", "name": "Eng", "location": {"city": "Paris", "country": "fr"}} for i in range(n)]}
        with mock.patch.object(sources, "request_json", side_effect=fake) as m:
            jobs = sources.smartrecruiters("Acme", "Acme")
        self.assertEqual((len(jobs), m.call_count, jobs[0].location), (130, 2, "Paris, FR"))

    def test_workday_url_parsing(self):
        self.assertEqual(sources.parse_workday_url("https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"),
                         ("nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"))
        with self.assertRaises(sources.FetchError):
            sources.parse_workday_url("https://careers.example.com/jobs")

    def test_workday_pages_with_total_only_on_first_page_and_dedupes_terms(self):
        def fake(url, body, **_):
            off = body["offset"]
            page = [{"title": f"Job {off + i}", "externalPath": f"/job/{off + i}", "locationsText": "Remote",
                     "bulletFields": [f"R{off + i}"]} for i in range(20 if off < 40 else 5)]
            return {"total": 45 if off == 0 else 0, "jobPostings": page}
        with mock.patch.object(sources, "request_json", side_effect=fake):
            jobs = sources.workday("NV", url="https://nv.wd1.myworkdayjobs.com/Site", search=["a", "b"])
        self.assertEqual(len(jobs), 45)
        self.assertEqual(jobs[0].url, "https://nv.wd1.myworkdayjobs.com/en-US/Site/job/0")


class OutputTests(unittest.TestCase):
    def test_new_only_for_companies_seen_before(self):
        rows, seen = output.mark_new([job(job_id="1")], {}, today="2026-11-01")
        self.assertEqual(rows[0]["new"], "")  # first run of a company: nothing is "new"
        jobs = [job(job_id="1"), job(job_id="2"), job(company="Newco", job_id="9")]
        rows, seen = output.mark_new(jobs, seen, today="2026-11-02")
        by_id = {r["job_id"]: r for r in rows}
        self.assertEqual((by_id["1"]["new"], by_id["2"]["new"], by_id["9"]["new"]), ("", "NEW", ""))
        self.assertEqual((by_id["1"]["first_seen"], by_id["2"]["first_seen"]), ("2026-11-01", "2026-11-02"))
        self.assertEqual(rows[0]["job_id"], "2")  # new ones sort first


class CliTests(unittest.TestCase):
    def test_example_config_is_valid(self):
        cfg = cli.load_config(Path(__file__).resolve().parent.parent / "companies.toml")
        self.assertGreater(len(cfg["companies"]), 0)

    def test_bad_config_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.toml"
            p.write_text('[[companies]]\nname="A"\nats="greenhouse"\n[[companies]]\nname="B"\nats="taleo"\nslug="b"\n')
            with self.assertRaises(SystemExit) as e:
                cli.load_config(p)
        self.assertIn("A: needs slug", str(e.exception))
        self.assertIn("B: ats must be one of", str(e.exception))

    def test_run_end_to_end_with_a_failing_company(self):
        def fake_gh(company, slug, **_):
            if slug == "broken":
                raise sources.FetchError("HTTP 404")
            return [job("Software Engineer", company=company, job_id="1"), job("Recruiter", company=company, job_id="2")]
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(cli.FETCHERS, {"greenhouse": fake_gh}), \
                mock.patch.object(cli.time, "sleep"), mock.patch("builtins.print"):
            cfgp = Path(d) / "c.toml"
            cfgp.write_text('[filters]\ntitle_include=["engineer"]\n'
                            '[[companies]]\nname="Acme"\nats="greenhouse"\nslug="acme"\n'
                            '[[companies]]\nname="Gone"\nats="greenhouse"\nslug="broken"\n')
            code = cli.main(["run", "--config", str(cfgp), "--out", str(Path(d) / "out")])
            rows = json.loads((Path(d) / "out" / "jobs.json").read_text())
            report = (Path(d) / "out" / "report.html").read_text()
        self.assertEqual(code, 0)
        self.assertEqual([r["title"] for r in rows], ["Software Engineer"])
        self.assertIn("HTTP 404", report)


if __name__ == "__main__":
    unittest.main()
