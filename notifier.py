"""
core/notifier.py — Telegram outbound message sender.

Sends job packets, inline buttons, and cheat sheets to Brandon's bot.
"""

import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID      = os.environ.get("ALLOWED_CHAT_ID", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_text(text: str, parse_mode: str = "HTML") -> bool:
    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id":                  CHAT_ID,
            "text":                     text,
            "parse_mode":               parse_mode,
            "disable_web_page_preview": True,
        }, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"send_text error: {e}")
        return False


def send_with_button(text: str, button_label: str, button_url: str) -> bool:
    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id":                  CHAT_ID,
            "text":                     text,
            "parse_mode":               "HTML",
            "disable_web_page_preview": True,
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": button_label, "url": button_url}]]
            }),
        }, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"send_with_button error: {e}")
        return False


def send_document(file_path: str, caption: str = "") -> bool:
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(f"{TELEGRAM_API}/sendDocument", data={
                "chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML",
            }, files={"document": (os.path.basename(file_path), f)}, timeout=30)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"send_document error: {e}")
        return False


def notify_application_ready(job: dict, packet: dict, doc_path: str = None):
    """
    Fire the 3-message application notification sequence:
    1. .docx file (if path provided)
    2. Job summary card + [APPLY NOW] inline button
    3. Pre-filled field cheat sheet
    """
    level_emoji = {"Manager": "🔵", "Director": "🟣", "VP": "🟠", "COO": "🔴"}.get(
        job.get("level", ""), "🎯"
    )
    title   = job.get("title", "")
    company = job.get("company", "")
    num     = job.get("_display_number", "")

    # 1 — doc
    if doc_path and os.path.exists(doc_path):
        send_document(doc_path, caption=f"📋 {title} @ {company} — Application Packet")

    # 2 — job card + button
    card = (
        f"{level_emoji} <b>APPLICATION READY — {company.upper()}</b>\n\n"
        f"<b>Role:</b>      {title}\n"
        f"<b>Salary:</b>    {job.get('salary', 'Not Listed')}\n"
        f"<b>Level:</b>     {job.get('level', '')}\n"
        f"<b>Location:</b>  {job.get('location', '')}\n\n"
        f"📄 Packet above — cover letter + tailored bullets + cheat sheet\n\n"
        f"Tap below to open the application, then reply:\n"
        f"<b>/yes {num}</b> to approve  |  <b>/no {num}</b> to skip  |  <b>/wait {num}</b> to hold"
    )
    send_with_button(card, "🚀  APPLY NOW  →", job.get("apply_url", "https://indeed.com"))

    # 3 — cheat sheet
    lines = ["📋 <b>PRE-FILLED FIELDS</b>\n"]
    for k, v in packet.get("prefill", {}).items():
        lines.append(f"<b>{k}:</b>  {v}")
    lines += ["", "💰 Salary field → <b>100000</b>", "🔑 Work auth → <b>US Citizen, no sponsorship</b>"]
    send_text("\n".join(lines))
