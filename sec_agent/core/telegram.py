"""
Telegram delivery.

Sends the assembled report to a chat/channel. Telegram limits messages
to 4096 chars, so long reports are split on paragraph boundaries.
"""

from __future__ import annotations

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_MAX_CHARS

_API = "https://api.telegram.org/bot{token}/sendMessage"


def _split(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for para in text.split("\n\n"):
        candidate = (current + "\n\n" + para) if current else para
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # paragraph itself too long -> hard split
            while len(para) > limit:
                chunks.append(para[:limit])
                para = para[limit:]
            current = para
    if current:
        chunks.append(current)
    return chunks


def send_report(text: str) -> dict:
    """Send report to Telegram. Returns a status dict (does not raise on send)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"sent": False, "reason": "Telegram credentials not set", "chunks": 0}

    url = _API.format(token=TELEGRAM_BOT_TOKEN)
    chunks = _split(text, TELEGRAM_MAX_CHARS)
    sent = 0
    for chunk in chunks:
        resp = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if resp.ok:
            sent += 1
        else:
            return {
                "sent": False,
                "reason": f"Telegram API error: {resp.status_code} {resp.text[:200]}",
                "chunks": sent,
            }
    return {"sent": True, "reason": "ok", "chunks": sent}
