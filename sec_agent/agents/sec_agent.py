"""
SEC Agent as a LangGraph state machine.

Graph:
    collect -> summarize -> format -> deliver

Each node is resilient: a failure in one ticker's fetch or one filing's
summary is logged into state.errors rather than crashing the run, so the
daily report still goes out with whatever was gathered.

This same shape (collect -> summarize -> format -> deliver) is what the
Social / Market / Earnings agents will reuse; only the `collect` and
`summarize` internals change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from config import SEC_FORM_TYPES, SEC_LOOKBACK_DAYS, TICKERS
from core import sec_client, summarizer, telegram
from core.document import Document


class SECState(TypedDict):
    documents: list[Document]
    report_text: str
    errors: list[str]
    delivery: dict


# --- Nodes -----------------------------------------------------------------

def collect(state: SECState) -> SECState:
    docs: list[Document] = []
    errors = list(state.get("errors", []))
    for ticker in TICKERS:
        try:
            found = sec_client.fetch_recent_filings(
                ticker, SEC_FORM_TYPES, SEC_LOOKBACK_DAYS
            )
            docs.extend(found)
        except Exception as e:  # noqa: BLE001 - keep run alive
            errors.append(f"collect[{ticker}]: {type(e).__name__}: {e}")
    return {**state, "documents": docs, "errors": errors}


def summarize(state: SECState) -> SECState:
    errors = list(state.get("errors", []))
    for doc in state["documents"]:
        try:
            text = sec_client.fetch_filing_text(doc)
            doc.summary = summarizer.summarize_filing(doc, text)
        except Exception as e:  # noqa: BLE001
            doc.summary = "[Summary unavailable]"
            errors.append(f"summarize[{doc.ticker} {doc.form_type}]: {e}")
    return {**state, "errors": errors}


def format_report(state: SECState) -> SECState:
    docs = state["documents"]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"<b>📑 SEC Filings Brief — {today}</b>", ""]

    if not docs:
        lines.append("No new filings in the lookback window.")
    else:
        # group by ticker
        by_ticker: dict[str, list[Document]] = {}
        for d in docs:
            by_ticker.setdefault(d.ticker or "—", []).append(d)
        for ticker, items in sorted(by_ticker.items()):
            lines.append(f"<b>{ticker}</b>")
            for d in items:
                lines.append(f"• <b>{d.form_type}</b> — {d.published.date()}")
                if d.summary:
                    lines.append(d.summary)
                lines.append(f'<a href="{d.url}">source</a>')
                lines.append("")

    if state.get("errors"):
        lines.append("")
        lines.append(f"<i>{len(state['errors'])} non-fatal issue(s) during run.</i>")

    return {**state, "report_text": "\n".join(lines).strip()}


def deliver(state: SECState) -> SECState:
    result = telegram.send_report(state["report_text"])
    return {**state, "delivery": result}


# --- Graph assembly --------------------------------------------------------

def build_graph():
    g = StateGraph(SECState)
    g.add_node("collect", collect)
    g.add_node("summarize", summarize)
    g.add_node("format", format_report)
    g.add_node("deliver", deliver)

    g.add_edge(START, "collect")
    g.add_edge("collect", "summarize")
    g.add_edge("summarize", "format")
    g.add_edge("format", "deliver")
    g.add_edge("deliver", END)
    return g.compile()


def run() -> SECState:
    graph = build_graph()
    initial: SECState = {
        "documents": [],
        "report_text": "",
        "errors": [],
        "delivery": {},
    }
    return graph.invoke(initial)
