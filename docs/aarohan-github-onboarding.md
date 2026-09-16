# Kova on GitHub: Aarohan's Onboarding

**Who this is for:** Aarohan Sharma, cofounder, owner of discovery calls, negotiation, and closing.
**What it covers:** what Kova is building, where all of it lives on GitHub, how to get Claude Code running, and how to work in the repos without breaking anything.
**Written:** 2026-09-16.

This is the technical companion to `Operations/aarohan-onboarding-2026-09-04.md` in the `kova-systems-brain` repo. That packet tells you what to read and which deals are yours. This one tells you how the machinery works and how to drive it.

Budget about 30 minutes to read this, and 20 to 30 minutes for the one-time setup in Part 3.

---

## Part 0: Read this first (the blocker)

**As of 2026-09-16, you are still not a collaborator on any Kova repo.** The `kova-systems-brain` repo has exactly one person on it: `srxjxn`. That is tracker row 37, it is Srujan's, it was due 2026-09-11, and it is now overdue.

Until that is done:

- You cannot clone anything.
- The setup in Part 3 will fail at the clone step with a "repository not found" error. That error is misleading. It does not mean you typed it wrong, it means GitHub will not admit a private repo exists to someone who cannot see it.
- The 09-05 weekend and the 09-12 weekend both died on this exact step.

**What to do:** text Srujan and ask him to add `aarohansharm` (or whatever your GitHub username is, send it to him) as a collaborator on `srxjxn/kova-systems-brain`. It takes him 30 seconds: repo page, Settings, Collaborators, Add people. You will get an email invite. Accept it.

Everything below assumes that is done. You can read the whole document before it happens, and you should, so that when access lands you are not starting from zero.

---

## Part 1: What Kova actually is, in two minutes

**Kova Systems** is an AI consulting and build shop for small businesses. Founded 2024. Three founders: Srujan (65%, CEO), Ben Uziel (20%), you (15%).

**What we sell, as of the 2026-07-01 model:** the website is **free** at every tier. Money comes from a monthly membership.

| Tier | Founding rate | Standard | What it includes |
|---|---|---|---|
| Base | $250/mo | $350/mo | Hosting, maintenance, security, SEO and Google Business Profile, missed-call text-back |
| Growth | $400/mo | $600/mo | Base plus lead follow-up, review funnel, monthly performance touch point, quarterly roadmap, build-menu access |
| Priority | $1,000/mo | $1,500/mo | Growth plus one build credit a month and front-of-queue delivery |

Ten founding slots total across all tiers, locked for life. Annual prepay is two months free. Apps are quoted separately at $2,000 to $5,000. The source of truth is `Marketing-Sales/Sales/kova-membership-tier-sheet.md`, not this table. If this table and the tier sheet ever disagree, the tier sheet wins and this file is the one that is wrong.

**Do not quote the old model.** The $900 build fee plus $150/mo structure is dead as of 2026-06-29. It still appears in older documents in the vault, marked superseded. If a document does not carry a date after 2026-07-01, check the tier sheet before you say a number out loud on a call.

**Who does what, confirmed 2026-09-04:**

- **Srujan** does sales engineering: finding leads, verifying them, researching businesses, building mockups, writing scripts, pricing, proposals, tooling.
- **You** do discovery calls, the conversation, negotiation, and the close.
- **Srujan attends calls as a stakeholder.** He is not running his own dials against you.

**The honest state of the board:** one paying client (Modern Tennis, $400/mo, terms still unsigned), around 173 verified leads sitting uncontacted, and zero outbound sent since 2026-07-08. The raw material exists and the sending stopped. Closing that gap is the job.

---

## Part 2: The GitHub map

### 2.1 What GitHub is, if nobody has explained it properly

GitHub is where the company's files and code live, with a full history of every change.

Four ideas and you have enough to work:

- **Repository (repo).** One project, one folder, one history. Kova has nine of them. Think of a repo as a filing cabinet that remembers every version of every document that has ever been in it.
- **Commit.** A saved checkpoint with a message explaining what changed. Nothing is ever really lost, you can always go back to an earlier commit.
- **Branch.** A parallel copy where you work without touching the live version. `main` is the real one. A branch is a sandbox. You make a branch, mess around, and only merge it back into `main` when it is good.
- **Pull request (PR).** A proposal to merge your branch into `main`, with a place to discuss it first. On a solo-founder repo this is often skipped, but it is how you ask "does this look right?" without committing to it.

**Clone** means downloading a copy of a repo to your laptop. **Push** means sending your commits back up to GitHub. **Pull** means fetching everyone else's changes down. That is the whole loop: pull, work, commit, push.

### 2.2 The one rule that can actually cost money

**Pushing to `main` on three specific repos deploys to the live internet immediately.** There is no staging step, no confirm dialog, no undo button.

Those three are `kova-systems-website`, `moderntennis-website`, and `ModernTennis-BackOffice`. The Vercel GitHub App is connected to all three. A push to `main` is a production release, full stop. One of those is a paying client's live site.

None of these repos have branch protection, because the GitHub account is on the free plan and branch protection is not available for private repos there. Nothing will stop you. The guard rail is knowing this.

Practical rule: **you have no reason to push to `main` on any code repo.** If you ever find yourself about to, stop and text Srujan.

### 2.3 Every Kova repo and what it is

All of it lives under the personal GitHub account `srxjxn`. There is no Kova GitHub organization yet.

| Repo | What it is | Does it matter to you? |
|---|---|---|
| **`kova-systems-brain`** | The knowledge layer. The business context file, the wiki, the pipeline, client pages, lead lists, scripts, weekly tracker. This is the Obsidian vault at `~/Desktop/KovaLabs`. | **Yes. This is your repo.** Ninety percent of your time is here. |
| `kova-skills` | The master copy of the 15 custom Claude skills Kova runs on. | Eventually. Note: as of the last check this repo was **staged but never actually created**. Until `bootstrap.sh` is run, the skills still live inside `kova-systems-brain` under `Skills/`. |
| `kova-systems-website` | The agency site, Next.js, live at https://www.kovasystems.com | Read only. Push to main deploys. |
| `moderntennis-website` | Modern Tennis client site. A redesign sits unmerged on `feat/marked-court-redesign`, waiting on Ben. | Read only. Push to main deploys. Paying client. |
| `ModernTennis-BackOffice` | Modern Tennis admin tool, live since 2026-07-01. | Read only. Push to main deploys. Paying client. |
| `MT_APP` | The Modern Tennis iOS app, shipped to the App Store. Our flagship case study, and your strongest proof on a call. | Worth knowing it exists. It is the thing you point at. |
| `kova-dashboard` | Internal stats dashboard on Vercel, behind Basic Auth. | Not really. |
| `kova-mockup-factory` | Internal tool that generates outbound mockups. | Indirectly. This is what produces the mockups you take into calls. |
| `kova-systems` | An empty monorepo scaffold from 2026-08-22. No app, no code, fate undecided. | No. Ignore it. Do not confuse it with `kova-systems-brain`. |

Repos on the same account that are **not** Kova: `srujan`, `jpmc-task-3`, `Job_board`, `v0-sports-market-tracker`, `Miggles`, and `personal-brain` (Srujan's private personal vault, nothing to do with the agency).

The canonical, maintained version of this table is `Knowledge-Base/KovaLabs-Wiki/wiki/tools/repos.md` inside the brain repo. It also lists deploy targets, Supabase projects, and where each repo's secrets live. Read it once you have access.

### 2.4 Inside `kova-systems-brain`, where things are

| You want | It is at |
|---|---|
| The whole business in one file | `kova-labs-business-context.md` |
| The standing rules every Claude session follows | `CLAUDE.md` |
| Live deals and prospects | `Knowledge-Base/KovaLabs-Wiki/wiki/pipeline/pipeline.md` |
| This week's action items | `Operations/weekly-tracker/week-2026-08-31.md` |
| Your lead lists and the scripts written in your name | `Clients/Leads/` |
| Per-client history | `Knowledge-Base/KovaLabs-Wiki/wiki/clients/` |
| Who owns what, equity, how decisions get made | `Knowledge-Base/KovaLabs-Wiki/wiki/team/founders.md` |
| The outreach operating rules and compliance | `Knowledge-Base/KovaLabs-Wiki/wiki/processes/outreach-team-ops.md` |
| What happened when | `Knowledge-Base/KovaLabs-Wiki/log.md` |
| Your orientation packet | `Operations/aarohan-onboarding-2026-09-04.md` |

**Nothing sensitive is in this repo.** Contracts, invoices, legal documents, and every API key are deliberately gitignored out of it. That is why it is safe to hand you access to the whole thing. Keep it that way: never commit a password, an API key, or a signed contract here.

---

## Part 3: Getting Claude Code running

You have two paths. Pick one.

### Path A: The browser (fastest, nothing to install)

Go to **https://claude.ai/code**, connect your GitHub account, pick `srxjxn/kova-systems-brain`, and start asking questions. No Terminal, no install, works from any machine including an iPad.

This is the right path for reading and asking. Start here if the terminal is not somewhere you are comfortable yet.

### Path B: The terminal (what you will end up using)

More capable, and it is what the skills expect. About 20 minutes, once.

**Step 1. Get your own Claude Pro subscription.** $20/month, on your own account. Do not use Srujan's login. Reading the vault will not come close to the usage limit.

**Step 2. Install Claude Code.** Open Terminal (Cmd+Space, type `Terminal`, Enter) and paste:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Check it:

```bash
claude --version
```

If you get `command not found`, fully quit Terminal (Cmd+Q) and reopen it. The installer adds Claude to your PATH, and each Terminal window reads that only at startup.

**Step 3. Connect to GitHub.** The GitHub CLI is the least painful route and avoids SSH keys entirely:

```bash
brew install gh
gh auth login
```

At the prompts choose `GitHub.com`, then **HTTPS**, then let it open your browser and authorize. If `brew` is not found, install Homebrew from brew.sh first, or download `gh` directly from cli.github.com.

**Step 4. Clone the brain repo.** Put it where the automations expect it, which is `~/Desktop/KovaLabs`:

```bash
cd ~/Desktop
gh repo clone srxjxn/kova-systems-brain KovaLabs
cd KovaLabs
```

The path matters. Skills and scheduled tasks have `~/Desktop/KovaLabs` hard coded in places, so cloning it somewhere else will silently break things later.

**Step 5. Start it.**

```bash
claude
```

First run opens your browser to sign in. Sign in, come back to Terminal, press Enter. It will not ask again on this Mac.

**Step 6. Optional, and worth it: Obsidian.** The brain repo is also an Obsidian vault, which makes the wiki much nicer to read with working links between pages. Install Obsidian, then "Open folder as vault" and pick `~/Desktop/KovaLabs`. **The vault root is `KovaLabs`, not the `KovaLabs-Wiki` subfolder.** Picking the subfolder is the common mistake and it breaks every link.

### If something breaks

```bash
claude doctor
```

That runs diagnostics and usually names the problem. If it does not, text Srujan instead of burning an hour. The reading is the point, not the tooling.

These commands were checked against `code.claude.com/docs` on 2026-09-06 and re-confirmed for this document. Anthropic changes them from time to time. If something behaves differently when you run it, **the docs win, not this file.**

---

## Part 4: Actually using it

### 4.1 Just ask

Claude has read the entire repo. You do not need to know where a file is, or use the right vocabulary. Open a session in the repo folder and ask in plain English:

- "What is the state of the pipeline?"
- "What do we know about Modern Tennis, and why is it our best case study?"
- "Show me my assigned leads and the scripts written for them."
- "What has actually been sent to a prospect in the last 60 days?"
- "Explain our pricing like I have to say it on a call tomorrow."
- "What objections should I expect from a lawn care owner with no website?"

### 4.2 Four habits that make you good at this fast

1. **Ask it to explain itself.** "Why did you do it that way?" and "what else did you consider?" teaches you more than any documentation.
2. **Type `/help` in a session once** to see what slash commands exist. Skim it, move on.
3. **Plain English is correct.** "Find me everything we know about how we price websites" works perfectly.
4. **Read `CLAUDE.md` in the repo root.** That file is the standing instruction set every Claude session at Kova follows. Knowing what it tells Claude tells you a great deal about how Kova operates.

### 4.3 The skills

Kova runs on 15 custom Claude skills. Four of them become yours:

| Skill | What it does | When you reach for it |
|---|---|---|
| `kova-research` | Website analysis, social audit, and an AI opportunity matrix for one prospect. Writes a research brief. | Before a discovery call, so you walk in knowing their gaps |
| `kova-leads` | Finds and qualifies prospects by industry and location, scores them, writes a ranked list with outreach angles | When the pipeline runs thin |
| `kova-followup` | Scans the pipeline for quiet and ghosted deals, drafts follow-ups. **Drafts only, never sends.** | After a call goes quiet |
| `kova-proposal` | Produces the branded client proposal as a Word document | Once a deal is real |

Trigger them by name in a session: "research this business" or `/kova-research`. "Who's gone quiet" or `/kova-followup`.

**Do not run them solo the first time.** Several write to the pipeline and to client pages. Run your first one with Srujan on the call.

These are shared tools, not anyone's personal ones. They used to assume Srujan was at the keyboard, which broke the moment a second person joined. That was fixed on 2026-09-06: `kova-followup` now works out who owns a deal from the pipeline and drafts in that person's voice, and `kova-research` writes its brief for whoever is taking the call. If you hit a spot where a skill still assumes it is Srujan, that is a bug worth flagging.

---

## Part 5: Working in the repo without breaking anything

### Phase 1: Read only (start here)

For your first few sessions, read and ask. If Claude offers to change a file, say no. Anything you want changed, text Srujan. You cannot break anything by reading.

### Phase 2: Making changes

Once you are comfortable, you will want to edit things: your own scripts so they sound like you, notes from a call, a client page after a conversation. That is real work and it belongs in the repo.

The safe loop, every time:

```bash
# 1. Start every session by getting current
git pull

# 2. Make a branch so main stays clean
git checkout -b aarohan/call-notes-kirilloffs

# 3. Do the work (edit files, or let Claude do it)

# 4. Save a checkpoint
git add -A
git commit -m "Add call notes from Kirilloff's discovery call"

# 5. Send it up
git push -u origin aarohan/call-notes-kirilloffs
```

Then open a pull request on GitHub so Srujan can look before it merges into `main`.

**You do not have to memorize any of this.** Say "commit this and push it to a new branch" and Claude will run the commands. But read what it is about to do before you approve it. Understanding the loop is what keeps you from being scared of it.

**Branch naming:** `aarohan/what-it-is`. Your name up front makes it obvious whose branch it is.

**Commit messages:** say what changed and why, not "update". Future you reading `git log` will be grateful.

### Phase 3: End of every session

From the repo root:

```bash
git add -A && git commit -m "<short summary of session>" && git push
```

This is in `CLAUDE.md` and it is how other devices and other Claude sessions get current context. The vault auto-commits through Obsidian Git but **never auto-pushes**, so if you skip this your work exists only on your laptop and nobody else sees it.

---

## Part 6: The rules that are not optional

**1. The Content Accuracy Rule.** Never invent, estimate, or assume client content. Not pricing, not staff names, not schedules, not locations, not testimonials, not contact info. Only what is on the client's own website, their intake form, or what they told you directly. Missing information becomes `[TBD — confirm with client]`. Use exact numbers from client sources, no rounding and no derived figures.

This is the single most important rule at Kova. A made-up price on a mockup is the kind of thing that loses a deal and a reputation at the same time.

**2. No em dashes.** Not in any writing, especially anything a client sees. They read as AI written. Use commas, periods, or colons. En dashes in number ranges like $1,000–$2,000 are fine.

**3. Never commit a secret.** No passwords, no API keys, no signed contracts, no `.env` files. The brain repo has never held a secret and must not start. This is not theoretical: `MT_APP` was public with live production credentials sitting in a docs file, and cleaning that up is still an open item.

**4. Outreach compliance, before you dial anyone.** From `outreach-team-ops.md`:

- List scrubbed against federal DNC and the Texas No-Call list first.
- Quiet hours: 9am to 9pm Mon-Sat, noon to 9pm Sunday, Central.
- Manual SMS from a real SIM line, and live calls. **No automated cold SMS.** Texas SB 140 makes cold texts actionable with per-text recoveries, and TCPA runs $500 to $1,500 per text.
- Opt-outs honored the same day.
- 30 to 50 touches per day, maximum.

**5. Brand voice.** Confident, clear, jargon free. Always think about how it reads to a small business owner who does not know what an LLM is. Not "LLM-powered semantic routing." Say "an AI assistant that answers customer questions on your website at 2am."

---

## Part 7: When things go wrong

| What you see | What it means | What to do |
|---|---|---|
| `repository not found` on clone | You do not have access, or you are not logged in | Check Part 0. Run `gh auth status` |
| `command not found: claude` | PATH not picked up yet | Quit Terminal fully (Cmd+Q) and reopen |
| `command not found: brew` | Homebrew is not installed | Install from brew.sh, or get `gh` from cli.github.com |
| `Permission denied (publickey)` | Git is trying SSH | You cloned with an SSH URL. Re-clone using `gh repo clone`, which uses HTTPS |
| Merge conflict | You and someone else changed the same lines | Do not guess. Ask Claude to explain the conflict, then text Srujan if it touches anything you did not write |
| Claude seems to have no idea what Kova is | You started it outside the repo folder | `cd ~/Desktop/KovaLabs` first, then run `claude` |
| Obsidian links all broken | You opened the wrong folder as the vault | Vault root is `KovaLabs`, not `KovaLabs-Wiki` |
| Anything else | | `claude doctor`, then text Srujan |

---

## Part 8: Glossary

| Term | Plain English |
|---|---|
| Repo | One project folder, with its full history |
| Clone | Download a copy of a repo to your laptop |
| Commit | A saved checkpoint with a message |
| Branch | A parallel workspace. `main` is the real one |
| `main` | The live, official version |
| Push / Pull | Send your commits up / fetch others' changes down |
| PR (pull request) | A proposal to merge a branch, with a place to discuss first |
| Merge conflict | Two people changed the same lines and git needs a human to choose |
| The vault / the brain | `kova-systems-brain`, our knowledge repo. Same thing, two names |
| The wiki | `Knowledge-Base/KovaLabs-Wiki/` inside the vault |
| Vercel | The host. Push to main on a site repo and it goes live |
| Supabase | The database behind the sites and the app |
| Skill | A custom Claude workflow, triggered like `/kova-research` |
| Obsidian | The app that makes the wiki nice to read |
| CLAUDE.md | The standing instructions every Claude session at Kova follows |

---

## Part 9: Your first week

**Before anything (Srujan):**
- [ ] Add Aarohan as a collaborator on `srxjxn/kova-systems-brain`. Tracker row 37, overdue since 2026-09-11.

**Setup (20 to 30 min, once):**
- [ ] Accept the GitHub invite
- [ ] Claude Pro subscription on your own account
- [ ] Install Claude Code, or just use claude.ai/code
- [ ] `gh auth login`, then clone to `~/Desktop/KovaLabs`
- [ ] Run `claude` from inside that folder and ask it one question
- [ ] Optional: open the folder as an Obsidian vault

**Reading (about 90 min, in this order):**
- [ ] `kova-labs-business-context.md` (30 min, the foundation)
- [ ] `wiki/overview.md` (5 min, the map)
- [ ] `wiki/team/founders.md` (5 min)
- [ ] `wiki/pipeline/pipeline.md` (20 min, your four deals are in here)
- [ ] `wiki/processes/outreach-team-ops.md` (10 min)
- [ ] `wiki/concepts/outbound-copywriting-framework.md` (15 min)
- [ ] `Clients/Leads/SportsAcademies-DFW-2026-07-06.md` and `Clients/Leads/TreeService-DFW-2026-07-08.md` (10 min)

If you only have time for two, read the business context file and the pipeline.

**Then answer Srujan's five questions.** They were due 2026-09-13 and that date has passed because access never arrived. They are still the right five:

1. Is sports academies and coaching the right vertical for you? It was assigned on 7/06 off the Modern Tennis case study and has been marked PROVISIONAL ever since.
2. Which `@kovasystems.com` address do you want? Your Google Workspace seat has been blocked on this since May. `aarohan@` is the obvious one.
3. What do you need from Srujan before your first real dial? Mockups, a one-pager, pricing you can quote without checking, call recording, something else.
4. Anything in the scripts that does not sound like you? They go out signed "this is Aarohan with Kova Systems," so they have to survive you saying them on a live call.
5. What 20-minute weekly slot works, recurring, same time every week?

**Also still open and worth knowing:** hold the calls until Srujan answers whether we are targeting DFW or Chicago. All four of your prospects are DFW. That is tracker row 2 and it is his.

**Your four assigned deals**, all already in the pipeline file:

| Prospect | Channel | Contact | The angle |
|---|---|---|---|
| Kirilloff's Baseball School | Text | (412) 287-6689 | Lessons booked by text, Modern Tennis app as the case study |
| Hitters Row Baseball Academy | Email | bustos@hittersrow.com | Three separate domains, no pricing anywhere |
| Sealy Soccer Factory | Email | info@sealysoccerfactory.com | EZFacility bolt-on plus an empty reviews page |
| Lindgren's Lawn and Landscape | Call | (405) 838-9592 | No website at all, social only. 20+ years, 18 reviews |

Lindgren's needs a mockup built before the call. That is Srujan's, and it has been owed since 7/08.

---

## A last thing

Getting good at Claude Code is not overhead on your role. It is most of the leverage in it. Srujan builds the supply, you close, and the tool is what lets two people run a pipeline that would normally take six. The weekend of reading is not a formality, it is the part where you stop needing to ask what we sell.

---

## Change Log

- 2026-09-16: Written. Covers the repo landscape, GitHub fundamentals, Claude Code setup for both browser and terminal, the commit workflow, the non-negotiable rules, troubleshooting, and a first-week checklist. Verified against GitHub that no collaborator has been added yet, so Part 0 leads with that blocker. Repo inventory taken from `wiki/tools/repos.md` and confirmed against the live GitHub account. Pricing taken from `kova-labs-business-context.md`, with the tier sheet named as source of truth over this file.
