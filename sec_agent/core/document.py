"""
Shared data contract for all collection agents.

Every agent (SEC, Social, Market, Earnings, ...) normalizes whatever it
gathers into a list of `Document` objects. The Report agent and the
synthesis steps only ever see `Document`s, so adding a new source never
changes downstream code.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class Document:
    """A single normalized unit of collected information."""

    source: str                 # e.g. "SEC EDGAR"
    title: str                  # human-readable headline
    url: str                    # link to the original
    published: datetime         # when the source item was published
    ticker: str | None = None   # associated ticker if any
    form_type: str | None = None  # e.g. "8-K" (SEC-specific, optional)
    raw_text: str = ""          # extracted body text (may be truncated)
    summary: str = ""           # filled in by the LLM step
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["published"] = self.published.isoformat()
        return d
