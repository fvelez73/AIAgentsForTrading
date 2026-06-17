"""
Central configuration for the SEC agent (and future agents).

Secrets come from environment variables (set these in Railway's
variable manager, or a local .env file for development).
Tickers are hardcoded here for now per the test design; later this
can be swapped for a YAML file or Postgres without touching agent code.
"""

import os

# ---------------------------------------------------------------------------
# Tracked tickers (hardcoded for the SEC test).
# CIK is optional — if omitted, the agent resolves it from the ticker via
# the SEC's company_tickers.json mapping at runtime.
# ---------------------------------------------------------------------------
TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
]

# Which filing form types the SEC agent cares about.
SEC_FORM_TYPES = ["10-K", "10-Q", "8-K"]

# Only report filings from the last N days (the daily run window + buffer).
SEC_LOOKBACK_DAYS = 2

# ---------------------------------------------------------------------------
# SEC EDGAR requires a descriptive User-Agent with contact info.
# See: https://www.sec.gov/os/webmaster-faq#developers
# ---------------------------------------------------------------------------
SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "DailyIntelBot/1.0 (contact@example.com)",  # <-- change to a real contact
)

# ---------------------------------------------------------------------------
# Anthropic (Claude) for summarization.
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# ---------------------------------------------------------------------------
# Telegram delivery.
# Create a bot via @BotFather to get the token, then get your chat/channel id.
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("8996577695:AAFgrDTiyMTjeLpHvQP00g3Ts6-_eH7sPlE", "")
TELEGRAM_CHAT_ID = os.environ.get("8615962435", "")

# Max characters Telegram allows per message.
TELEGRAM_MAX_CHARS = 4096
