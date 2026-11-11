# Food Tracker

Type what you ate in plain English, get your macros. That's it.

```
2 eggs, 2 slices of toast and a banana
150g chicken breast with 1 cup rice
half an avocado, 1 tbsp peanut butter
a latte and a croissant
```

Each item is matched against a built-in database of ~260 common foods (with lots of aliases),
converted to grams using per-food serving sizes, and logged with calories, protein, carbs and fat.
Daily totals are shown against your goals, with a 7-day calorie history.

## Put it on your phone (Vercel)

The `web/` folder is a static version of the app: same parser and food database, ported to
JavaScript, with your log saved in the browser on the device. No server, no database to set up.

1. Go to https://vercel.com/new and import this repository (branch `claude/food-tracker-macros-ujfjip`,
   or `main` once merged).
2. Leave the settings as they are. `vercel.json` declares an explicit static build of the `web/` folder,
   which stops Vercel from auto-detecting the Python server (it would otherwise see `requirements.txt`
   and try to deploy FastAPI).
3. Deploy, then open the URL on your phone. In Safari or Chrome use **Share → Add to Home Screen**
   to get an app icon that opens full-screen.

Or from a terminal: `npx vercel --prod` in the repo root. If a deploy ever complains about a FastAPI
entrypoint, run it from inside the folder instead: `cd web && npx vercel --prod`.

Because the data lives in that browser only, use **Export data** in the footer for a backup and
**Import** to restore it on another device. The Claude fallback for unknown foods is server-side
only, so the static version asks you for the macros instead (and remembers them).

To pull food database changes through to the web build: `python scripts/build_foods_js.py`.
JS parser tests: `node --test web/parser.test.mjs`.

## Run the server version locally

```bash
pip install -r requirements.txt
python run.py
```

Open http://localhost:8000. Data is stored in `data/food_tracker.db` (SQLite, created on first run).

## What the input understands

| You type | It logs |
|---|---|
| `2 eggs` | 2 × one egg (50 g each) |
| `150g chicken breast`, `chicken breast 150g`, `6oz salmon` | explicit weight |
| `1 cup rice`, `2 slices of toast`, `1 tbsp peanut butter` | per-food unit sizes |
| `half an avocado`, `a couple of eggs`, `1 1/2 cups oats` | fractions and number words |
| `banana` (no amount) | one typical serving |
| `large banana`, `small apple` | size multipliers |
| `mac and cheese`, `pb&j` | multi-word dishes stay intact |

Items are separated by commas, "and", "with" or new lines.

### Foods it doesn't know

Anything unmatched shows up with a small form: enter the calories and macros for the amount you ate,
and (by default) it's remembered as a custom food so the same words are recognised next time.

**Optional Claude lookup.** If the `anthropic` package is installed and credentials are configured
(`ANTHROPIC_API_KEY`, or `ant auth login`), unknown foods are estimated by Claude automatically and
cached as custom foods, so each new food costs at most one API call. Set `FOOD_TRACKER_MODEL` to change
the model (default `claude-opus-5`) or `FOOD_TRACKER_DISABLE_CLAUDE=1` to turn it off.

## My foods (your own labels, logged by the serving)

For the things you eat every week, skip the estimates: save the food once from its nutrition label
and log it by the serving.

1. Open **My foods → + Add a food**.
2. Enter the name, what one serving is called (`scoop`, `bar`, `slice`, `cup`... or just `serving`),
   the serving size in grams or ml, and the calories, protein, carbs and fat **per serving**, straight
   off the label. Optional "also called" names (`whey, protein shake`) are matched too.
3. Log it like anything else:

```
2 scoops whey
1.5 servings of gold standard whey
half a scoop of whey
3 rx bars and 2 eggs
45g whey            <- weights still work, scaled from the label
```

Every serving comes out at exactly the label's numbers. The **+1 scoop** button on each saved food logs
one serving to the selected day. Saved foods win over the built-in database when a name clashes, so
saving `whey protein` replaces the generic entry with yours. Edit or remove a food from the same list.
Entries you already logged keep their numbers.

Foods added through the "couldn't find these" form are saved the same way (one serving = the amount you
entered) and show up in this list, so you can tidy them up later.

## Editing

- Click the grams on any entry to change the amount; macros rescale.
- The × removes an entry.
- "Edit goals" sets daily targets for calories, protein, carbs and fat.
- Use the date picker or arrows to log against past days.

## API

All JSON, served by FastAPI (interactive docs at `/docs`).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/log` | `{text, date?}` → parse, log, return the day |
| `GET` | `/api/day?date=` | entries, totals and goals for a day |
| `POST` | `/api/entries/manual` | log a food with explicit macros, optionally remembering it |
| `PATCH` | `/api/entries/{id}` | `{grams}` rescale an entry |
| `DELETE` | `/api/entries/{id}` | remove an entry |
| `GET/PUT` | `/api/goals` | daily targets |
| `GET` | `/api/my-foods` | saved foods with per-serving macros |
| `POST` | `/api/my-foods` | `{name, serving_unit, serving_g, kcal, protein, carbs, fat, aliases?, replaces?}` save or update a food from its label |
| `DELETE` | `/api/my-foods/{name}` | remove a saved food |
| `GET` | `/api/history?days=7` | daily totals |
| `GET` | `/api/foods?q=` | search the food database |

## Configuration

| Variable | Default | |
|---|---|---|
| `PORT` / `HOST` | `8000` / `127.0.0.1` | where the server listens |
| `FOOD_TRACKER_DB` | `data/food_tracker.db` | SQLite path |
| `FOOD_TRACKER_MODEL` | `claude-opus-5` | model for unknown-food lookup |
| `FOOD_TRACKER_DISABLE_CLAUDE` | unset | set to disable the Claude fallback |

## Tests

```bash
python -m unittest
```

## Layout

```
food_tracker/
  foods.py          built-in food database (per-100 g macros, serving sizes, unit weights, aliases)
                    and food_from_serving(), which turns a nutrition label into a Food
  parser.py         free-text → (food, grams) items
  db.py             SQLite: entries, custom foods, goals
  claude_lookup.py  optional Claude fallback for unknown foods
  app.py            FastAPI routes
  static/index.html the front end (no build step)
run.py              starts the server
tests/              parser tests
web/                static build for Vercel (parser.js, store.js, app.js, generated foods.js)
scripts/build_foods_js.py  regenerates web/foods.js from foods.py
vercel.json         serves web/ as a static site
```

---

# Job scraper: open roles at your target companies

`job_scraper/` pulls every open role from a fixed list of companies, filters them by title and location,
and flags what's new since the last run. It reads the public job-board APIs that the companies' own
careers pages use (Greenhouse, Lever, Ashby, SmartRecruiters, Workday), so it needs no logins, browser,
or extra packages. It uses only the Python 3.11+ standard library.

```bash
python -m job_scraper find "Company Name"   # which job board does it use? prints a config entry
python -m job_scraper run                   # scrape everything in companies.toml
python -m job_scraper run --only Stripe     # just one or a few companies
```

1. Put your companies in `companies.toml` (the examples there show each board type). If `find` can't
   identify a company, click any job on its careers page and look at the address. `jobs.lever.co/<slug>`,
   `job-boards.greenhouse.io/<slug>`, `jobs.ashbyhq.com/<slug>`, `jobs.smartrecruiters.com/<slug>` and
   `<x>.wd5.myworkdayjobs.com/<site>` each tell you the board.
2. Set the `[filters]`: title words to include and exclude, and optional locations. Terms match whole
   words, so `intern` won't drop "Internal Tools". Any company can override the filters.
3. Run it. Results go to `jobs_output/` (git-ignored):
   - `report.html`: every matching role, newest first, with clickable links, search and sortable columns
   - `jobs.csv` / `jobs.json`: the same data, for a spreadsheet
   - `new_jobs.csv`: only roles that appeared since the last run
   - `seen.json`: the memory behind "new"; delete it to start over

The first run for a company records its current roles without marking them new. After that, each
run flags only roles that weren't there before, so running it daily gives you a short list of fresh postings.

Not covered: companies on their own in-house careers sites (Google, Amazon, Apple, Meta, Microsoft)
or on Taleo, iCIMS and similar systems. They need per-site scraping. Tests: `python -m unittest tests.test_job_scraper`.
