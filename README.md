# Halal Market Ledger

A daily Shariah-screened equity review. 112 securities — 50 US stocks, 50 TSX
listings and 12 halal ETFs and funds — scored each trading day on a single
105-point value-and-quality model, published as a static site.

**Live site:** https://khanyousefzai.github.io/halal-market-ledger/

---

## One-time setup

The code already lives in `khanyousefzai/stock`. Four settings switches remain,
and the site will not work until all four are done.

1. **Make the repo public** — Settings → General → *Danger Zone* → **Change
   visibility** → Public. GitHub Pages does not serve private repos on a free
   account. This is why the URL currently 404s.

2. **Turn on Pages** — Settings → **Pages** → *Build and deployment* → set
   **Source** to **GitHub Actions** (not "Deploy from a branch").

3. **Let Actions push** — Settings → **Actions** → **General** → *Workflow
   permissions* → **Read and write permissions**. Without this the daily commit
   fails with a 403 and no report is ever saved.

4. **Check the branch name.** The workflow's cron does not care about branches,
   but the push in the commit step targets whatever branch is checked out. If
   your default branch is `master` rather than `main`, nothing needs changing —
   just confirm the first manual run succeeds.

Then run it once by hand: **Actions** → *Daily report* → **Run workflow**. A
green run means the whole chain works. Tick *dry run* first if you want to test
the data fetch without committing anything.

---

## Layout

```
generate_report.py       Daily entry point — fetch, score, write, archive
  fetch_data.py            Yahoo Finance layer; normalises units, never guesses
  scoring.py               105-point model, guardrails, colour bands, commentary
  render_report.py         Renders one day's report page
  report_css.py            Report stylesheet
  universe.py              The 112 tickers + Shariah screen membership
  investor_tweets.py       Optional: watched-account cashtag mentions (needs X_BEARER_TOKEN)
  thirteen_f.py            Free: watched investors' latest SEC 13F holdings, no key needed
build_site.py            Rebuilds index.html from data/history.json
index.html               Landing page (generated; do not hand-edit)
data/history.json        Machine-readable archive: one entry per run
reports/YYYY-MM-DD.html  One self-contained report page per trading day
assets/style.css         Landing-page styling (light + dark themes)
requirements.txt         Python dependencies
.github/workflows/daily.yml   Cron -> generate -> commit -> deploy
```

`index.html` is derived. The two things that actually carry data are
`data/history.json` and the files in `reports/`.

---

## How the daily run works

Nothing manual. `.github/workflows/daily.yml` runs on a cron schedule and does
the whole job inside GitHub Actions:

1. Fetches all 112 securities from Yahoo Finance (`generate_report.py`)
2. Scores the 100 stocks and applies the guardrails
3. Writes `reports/YYYY-MM-DD.html`
4. Appends the run to `data/history.json`
5. Rebuilds `index.html`
6. **Commits and pushes the result**, then deploys to Pages

The schedule is `10 13 * * 1-5` — 13:10 UTC on weekdays, which is 09:10 ET while
US daylight time is in effect. GitHub cron is always UTC and does not follow DST,
so in winter this lands at 08:10 ET; add a second cron line if you want it pinned.

GitHub's scheduled runs are best-effort and can be delayed by several minutes
during busy periods. That is normal and does not affect the report.

### Running it by hand

Actions tab → **Daily report** → **Run workflow**. Tick **dry run** to fetch and
score without writing or committing anything — useful for checking the data
source still works without touching the archive.

### If a run fails

The job aborts and writes nothing if fewer than 80% of the 100 stocks fetch
successfully, so a bad upstream day leaves the site untouched rather than
publishing a half-empty report. Individual failures are listed in the report's
Data Quality box and in the Actions log.

Re-running for a date that already exists replaces that entry rather than
duplicating it.

## Adding a report by hand

Rarely needed, but if you want to backfill a day:

1. Write the page to `reports/YYYY-MM-DD.html`
2. Append one object to the array in `data/history.json`
3. Run `python3 build_site.py`, then commit and push

Or just run `python3 generate_report.py --date YYYY-MM-DD` locally, which does
all three. Note that Yahoo returns *current* fundamentals, not historical ones,
so backfilled entries carry today's ratios with an older label.

### `history.json` entry shape

```jsonc
{
  "date":    "2026-08-24",              // sort key; matches the reports/ filename
  "label":   "Mon 24 Aug 2026",
  "session": "24 Aug 2026, 13:44 UTC",
  "us_avg":  -0.83,
  "counts":  {"Strong Buy":3,"Buy":14,"Hold":20,"Wait":8,"Skip":3},
  "top_us":  [{"t":"MU","n":"Micron Technology, Inc.","p":906.0,"c":-6.29,"s":95.8,"u":67.2}],
  "best_ca": {"t":"STN","n":"Stantec Inc.","p":101.55,"c":-0.33,"s":73.7,"u":38.2},
  "top_etf": {"t":"SPUS","n":"SP Funds S&P 500 Sharia ETF","p":58.21,"c":-0.70},
  "note":    "Auto-generated one-line session summary.",
  "us":      [{"t":"MU","p":906.0,"c":-6.29,"s":95.8,"v":"Strong Buy"}],  // all 50
  "ca":      [{"t":"STN","p":101.55,"c":-0.33,"s":73.7,"v":"Buy"}]        // all 50
}
```

Keys are short because they repeat 100 times per run: `t` ticker, `n` name,
`p` price, `c` day change %, `s` score, `u` upside %, `v` verdict.
The `us`/`ca` arrays drive the score-trend sparklines.

## Investor chatter (optional)

`investor_tweets.py` pulls recent posts from a short list of watched X/Twitter
accounts (`WATCHED` in that file — currently Bill Ackman, Michael Burry, Chamath
Palihapitiya) and keeps only the ones that cashtag a ticker in the 112-security
universe. It renders as section I on the report page when there's a match.

This needs an X API v2 **developer account on a paid plan** — the free tier
cannot read timelines. Without a token the pipeline runs exactly as before;
the section is silently omitted and nothing fails.

To enable it:

1. Get a Bearer Token from [developer.x.com](https://developer.x.com).
2. **Settings → Secrets and variables → Actions → New repository secret** —
   name it `X_BEARER_TOKEN`, paste the token.
3. Next run picks it up automatically; no code changes needed.

Treat every match as chatter to read, not a trade signal — these accounts
comment publicly far more than they disclose actual positions.

## 13F holdings (free, on by default)

`thirteen_f.py` is the no-key alternative to investor chatter: it pulls each
watched investor's most recent Form 13F-HR — the quarterly holdings
disclosure the SEC requires from every institutional manager over $100M —
straight from SEC EDGAR, and flags any position that overlaps the universe.
No signup, no token, nothing to configure. Renders as section J when there's
a match.

`WATCHED` currently covers 15 well-known investors: Bill Ackman, Michael
Burry, Chamath Palihapitiya, Warren Buffett, Carl Icahn, Ray Dalio, Seth
Klarman, David Tepper, Stanley Druckenmiller, Ken Griffin, Cathie Wood, David
Einhorn, Daniel Loeb, Nelson Peltz and George Soros. Each entry is `(display
name, firm, SEC CIK)` — add another by resolving their CIK at
[sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany)
(search by firm name, filter to 13F-HR) rather than guessing; a couple of
filers route their real 13F-HR through a differently-named related entity
(see the comment above `WATCHED` for the two cases already worked out).
Multi-strategy managers in the list (Citadel especially) report the same
position split across many lots — `fetch()` aggregates those to one row per
(filer, ticker) before the report caps the table at the 30 largest.

It's a quarterly snapshot, not a live signal — 13F filings can lag up to 45
days after quarter end, so a position shown here may already have changed by
the time you read it. SEC EDGAR asks every requester to identify themselves
with a User-Agent header (name + contact); the default in `thirteen_f.py`
works as-is, or set `SEC_EDGAR_USER_AGENT` to use your own. One thing found
the hard way: SEC's edge filter 403s any User-Agent containing the literal
string "github.com" — not documented anywhere, just tested and worked around.

## Keeping the Shariah screens current

`universe.py` holds `SCREENS` — which index actually holds each US name — plus
`SCREENS_ASOF`. This is **not** fetched automatically, because the issuers publish
holdings as files rather than an API, and a wrong screen is worse than a stale one.

Re-check it periodically against sp-funds.com (SPUS) and wahedinvest.com (HLAL),
update the dict and the date. As of 2026-08-25: SPUS holds 49 of the 50 US names
(only ASML isn't, being NL-domiciled — both funds track US-only universes). HLAL
is confirmed for 36 of them; the other 11 (added alongside SPUS on 2026-08-25)
default to `hlal: False` in `SCREENS` not because they're excluded but because
wahedinvest.com blocks automated fetches and their status hasn't been checked yet
— re-verify by hand and flip the flag once confirmed either way.

The 50 Canadian names have no index-fund Shariah screen at all — SPUS and HLAL
are both US-domiciled and structurally can't hold TSX listings. They're screened
by hand for permissible business lines only (see the comment above `CA_STOCKS`
in `universe.py` for the exclusion categories); the financial-ratio and
purification screens still need checking individually, same as before.

## Scoring

Each of the 100 stocks is scored out of 105:

| Component        | Points |
|------------------|--------|
| Analyst upside   | 26     |
| P/E valuation    | 20     |
| Debt / equity    | 20     |
| Return on equity | 20     |
| Current ratio    | 15     |
| Day momentum     | 5      |

Bands: **80+** Strong Buy · **65–79** Buy · **48–64** Hold · **36–47** Wait ·
**under 36** Skip.

Guardrails override the score — a high total cannot buy past them:

- D/E above 3.0 → capped at Wait
- P/E above 150 → capped at Wait
- Analyst target below price → capped at Hold
- Upside under 3% → capped at Hold
- No analyst target published → capped at Hold

The weighting puts more on the balance sheet (D/E + current ratio = 35 points)
than on the analyst target (26), because forecasts are opinions and the balance
sheet is a fact.

---

## Not investment advice

An automated screen, not a recommendation to buy or sell. The scores are a fixed
formula applied to publicly reported ratios; they encode no view on business
quality, management, or anything not visible in those numbers. Shariah
compliance is a personal religious obligation — index screens disagree with one
another, and none of this substitutes for your own scholarship or a qualified
advisor.
