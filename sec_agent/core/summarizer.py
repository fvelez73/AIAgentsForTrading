"""
Claude summarization for SEC filings.

Each filing is summarized independently and kept short so that the
downstream Report agent can aggregate many filings without blowing up
the context window or cost.
"""

from __future__ import annotations

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from core.document import Document

_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

_SYSTEM = (
    "You are a financial analyst summarizing SEC filings for a daily "
    "intelligence briefing. Be precise, factual, and concise. Never "
    "speculate beyond the filing. Output plain text, no markdown headers."
)

_PROMPT = """Summarize the following SEC {form_type} filing for {ticker}.

Produce:
1. One-sentence headline of what this filing is.
2. 2-4 bullet points of the most material facts (numbers, events, changes).
3. One line flagging anything an investor should pay attention to, or "No material flags."

Keep the whole thing under 120 words.

FILING TEXT (may be truncated):
\"\"\"
{text}
\"\"\""""


def summarize_filing(doc: Document, filing_text: str) -> str:
    if _client is None:
        return "[Summarization skipped: ANTHROPIC_API_KEY not set]"
    if not filing_text.strip():
        return "[No extractable text from filing; see source link.]"

    msg = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": _PROMPT.format(
                    form_type=doc.form_type or "",
                    ticker=doc.ticker or "",
                    text=filing_text,
                ),
            }
        ],
    )
    return "".join(block.text for block in msg.content if block.type == "text").strip()
