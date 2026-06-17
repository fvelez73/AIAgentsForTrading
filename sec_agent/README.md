# SEC Agent — Daily Intelligence Bot (Test #1)

First node of the LangGraph multi-agent reporting system. Pulls recent SEC
EDGAR filings (10-K, 10-Q, 8-K) for tracked tickers, summarizes each with
Claude, and posts a digest to Telegram.

## Graph
collect → summarize → format → deliver
(each node fails soft — one bad ticker/filing won't kill the daily report)

## Run locally
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`, fill in values, then `export $(cat .env | xargs)`
3. Dry run (no Telegram needed): `python main.py --dry-run`
4. Full run: `python main.py`

## Deploy on Railway
1. Push this repo to GitHub, create a Railway project from it.
2. Add the env vars from `.env.example` in Railway → Variables.
3. Railway auto-detects Python (Nixpacks) and installs requirements.txt.
4. Add a **Cron Schedule** (Settings → Cron) e.g. `0 11 * * *` for 11:00 UTC daily.
   `restartPolicyType: NEVER` (in railway.json) makes it run once and exit.

## Config
Edit `config.py`: TICKERS, SEC_FORM_TYPES, SEC_LOOKBACK_DAYS.

## Extending to other agents
Social / Market / Earnings agents reuse the same collect→summarize→format→deliver
shape. Build each as a new module in `agents/`, emit `core.document.Document`
objects from its collector, and a future top-level graph can fan out to all of
them in parallel before a single Report agent merges the Documents.

## Note on testing
Logic verified with mocked EDGAR responses (filtering, graph, formatting,
Telegram splitting all pass). Live sec.gov calls require network egress to
sec.gov / data.sec.gov, which works on your machine and on Railway.
