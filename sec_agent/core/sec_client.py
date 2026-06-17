"""
SEC EDGAR client.

Uses only official, free SEC endpoints (no scraping):
  - company_tickers.json    -> ticker -> CIK mapping
  - data.sec.gov submissions -> recent filings per company

SEC asks for:
  - a descriptive User-Agent with contact info
  - <= 10 requests/second
We stay well under that with a small sleep between calls.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import requests

from config import SEC_USER_AGENT
from core.document import Document

_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_FILING_INDEX_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"  # not used directly; kept for ref
)

# SEC is strict about headers. Send a full, browser-like header set with a
# descriptive User-Agent containing real contact info (set via SEC_USER_AGENT).
_HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json, text/html",
    "Host": "www.sec.gov",
}

# Simple in-process cache for the ticker->CIK map (refreshed per run).
_ticker_map_cache: dict[str, int] | None = None


def _get(url: str, max_retries: int = 4) -> requests.Response:
    """GET with exponential backoff on 429/403/5xx (SEC rate limiting)."""
    # Host header must match the URL's host (www.sec.gov vs data.sec.gov).
    headers = dict(_HEADERS)
    if "data.sec.gov" in url:
        headers["Host"] = "data.sec.gov"

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                time.sleep(0.2)  # stay well under 10 req/sec
                return resp
            if resp.status_code in (429, 403) or resp.status_code >= 500:
                # Back off: 2s, 4s, 8s, 16s
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                last_exc = requests.HTTPError(
                    f"{resp.status_code} from SEC (attempt {attempt + 1})"
                )
                continue
            resp.raise_for_status()  # other 4xx: don't retry
        except requests.RequestException as e:
            last_exc = e
            time.sleep(2 ** (attempt + 1))
    # Exhausted retries
    raise last_exc or requests.HTTPError("SEC request failed")


def _load_ticker_map() -> dict[str, int]:
    global _ticker_map_cache
    if _ticker_map_cache is not None:
        return _ticker_map_cache
    data = _get(_TICKER_MAP_URL).json()
    # data is keyed by arbitrary index; each value has ticker + cik_str
    mapping = {
        row["ticker"].upper(): int(row["cik_str"]) for row in data.values()
    }
    _ticker_map_cache = mapping
    return mapping


def resolve_cik(ticker: str) -> int | None:
    return _load_ticker_map().get(ticker.upper())


def fetch_recent_filings(
    ticker: str,
    form_types: list[str],
    lookback_days: int,
) -> list[Document]:
    """Return recent filings for one ticker as normalized Documents."""
    cik = resolve_cik(ticker)
    if cik is None:
        return []

    data = _get(_SUBMISSIONS_URL.format(cik=cik)).json()
    company_name = data.get("name", ticker)
    recent = data.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession = recent.get("accessionNumber", [])
    primary_doc = recent.get("primaryDocument", [])
    primary_desc = recent.get("primaryDocDescription", [])

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=lookback_days)
    wanted = {f.upper() for f in form_types}

    docs: list[Document] = []
    for i, form in enumerate(forms):
        if form.upper() not in wanted:
            continue
        try:
            filed = datetime.strptime(dates[i], "%Y-%m-%d").date()
        except (ValueError, IndexError):
            continue
        if filed < cutoff:
            continue

        acc_no = accession[i].replace("-", "")
        doc_name = primary_doc[i] if i < len(primary_doc) else ""
        url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no}/{doc_name}"
            if doc_name
            else f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"
        )
        desc = primary_desc[i] if i < len(primary_desc) else ""

        docs.append(
            Document(
                source="SEC EDGAR",
                title=f"{company_name} — {form} filed {dates[i]}"
                + (f" ({desc})" if desc else ""),
                url=url,
                published=datetime.combine(
                    filed, datetime.min.time(), tzinfo=timezone.utc
                ),
                ticker=ticker.upper(),
                form_type=form.upper(),
                metadata={"cik": cik, "accession": accession[i]},
            )
        )
    return docs


def fetch_filing_text(doc: Document, max_chars: int = 40_000) -> str:
    """Fetch and lightly clean the primary filing document's text."""
    try:
        resp = _get(doc.url)
    except requests.RequestException:
        return ""
    text = resp.text
    # Strip HTML crudely; good enough for LLM summarization input.
    import re

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
