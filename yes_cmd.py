"""
/yes <number>    — Approve job #N for application.

Triggers:
  1. Generate cover letter + tailored bullets via Anthropic API
  2. Send 3-message Telegram notification (packet + apply button + cheat sheet)
  3. Mark job as 'approved' in DB
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from state     import init_db, get_pending_jobs, get_job_by_number, set_status
from generator import generate_application_packet
from notifier  import notify_application_ready, send_text

logger = logging.getLogger(__name__)


async def yes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    args = context.args or []

    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "Usage: <b>/yes [number]</b>\nExample: /yes 3\n\n"
            "Use /review to see pending job numbers.",
            parse_mode="HTML"
        )
        return

    n = int(args[0])
    pending = get_pending_jobs()
    job = get_job_by_number(n)

    if not job:
        await update.message.reply_text(
            f"❌ No pending job #{n}. Use /review to see current list."
        )
        return

    job["_display_number"] = n
    await update.message.reply_text(
        f"✅ <b>Approved!</b> Generating application packet for:\n"
        f"<b>{job['title']}</b> @ {job['company']}\n\n"
        f"⏳ Give me ~30 seconds to write your cover letter and bullet swaps...",
        parse_mode="HTML"
    )

    try:
        packet = generate_application_packet(job)
        notify_application_ready(job, packet)
        set_status(job["id"], "approved")

        remaining = len(pending) - 1
        await update.message.reply_text(
            f"🚀 <b>Packet sent!</b> Check the messages above — your cover letter, "
            f"tailored bullets, and the <b>APPLY NOW</b> button are all there.\n\n"
            f"Fill in the form, hit submit, then come back and confirm.\n"
            f"<b>{remaining} jobs</b> still pending review.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"/yes error: {e}")
        await update.message.reply_text(f"❌ Packet generation failed: {e}")
