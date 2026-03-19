"""
/no <number>     — Reject job #N. Removes from sheet, adds to never-show-again list.
/wait <number>   — Hold job #N. Keeps on sheet, bumped to next review round.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from core.state  import init_db, get_job_by_number, get_pending_jobs, set_status, set_wait

logger = logging.getLogger(__name__)


async def no_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    args = context.args or []

    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "Usage: <b>/no [number]</b>\nExample: /no 2\n\n"
            "This removes the job and ensures it never shows up again.",
            parse_mode="HTML"
        )
        return

    n   = int(args[0])
    job = get_job_by_number(n)

    if not job:
        await update.message.reply_text(
            f"❌ No pending job #{n}. Use /review to see current list."
        )
        return

    set_status(job["id"], "rejected")

    pending_remaining = len(get_pending_jobs())
    await update.message.reply_text(
        f"🗑 <b>Skipped</b> — {job['title']} @ {job['company']}\n"
        f"This listing is gone and won't appear in future searches.\n\n"
        f"<b>{pending_remaining} jobs</b> still pending review.",
        parse_mode="HTML"
    )


async def wait_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    args = context.args or []

    if not args or not args[0].isdigit():
        await update.message.reply_text(
            "Usage: <b>/wait [number]</b>\nExample: /wait 4\n\n"
            "Job stays on the list and comes up again in the next review round.",
            parse_mode="HTML"
        )
        return

    n   = int(args[0])
    job = get_job_by_number(n)

    if not job:
        await update.message.reply_text(
            f"❌ No pending job #{n}. Use /review to see current list."
        )
        return

    set_wait(job["id"])

    pending_remaining = len(get_pending_jobs())
    round_next = job.get("review_round", 1) + 1
    await update.message.reply_text(
        f"⏸ <b>Held</b> — {job['title']} @ {job['company']}\n"
        f"This job stays on the list and will show up in review round {round_next}.\n\n"
        f"<b>{pending_remaining} jobs</b> still in current round.",
        parse_mode="HTML"
    )
