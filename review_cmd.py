"""
/review          — show next 5 pending jobs
/review all      — show all pending jobs
/review 3        — show job #3 only

Sends short summary cards for pending jobs.
Each card shows the job number to use with /yes, /no, /wait.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from core.state   import init_db, get_pending_jobs, get_job_by_number
from core.notifier import send_text

logger = logging.getLogger(__name__)

BATCH_SIZE = 5


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    args = context.args or []
    pending = get_pending_jobs()

    if not pending:
        await update.message.reply_text(
            "📭 <b>No pending jobs to review.</b>\n\n"
            "Use /run to search for new listings.",
            parse_mode="HTML"
        )
        return

    # Determine which jobs to show
    if args and args[0].lower() == "all":
        jobs_to_show = pending
        header = f"📋 <b>All {len(pending)} pending jobs:</b>\n"
    elif args and args[0].isdigit():
        n = int(args[0])
        job = get_job_by_number(n)
        if not job:
            await update.message.reply_text(f"❌ No job #{n} in the pending list.")
            return
        jobs_to_show = [job]
        header = f"📋 <b>Job #{n}:</b>\n"
    else:
        jobs_to_show = pending[:BATCH_SIZE]
        remaining    = len(pending) - BATCH_SIZE
        header = (
            f"📋 <b>Showing {len(jobs_to_show)} of {len(pending)} pending jobs</b>"
            + (f" ({remaining} more — use /review all)" if remaining > 0 else "")
            + ":\n"
        )

    await update.message.reply_text(header, parse_mode="HTML")

    # Send one card per job
    for i, job in enumerate(jobs_to_show, 1):
        # Display number is position in full pending list
        display_num = pending.index(job) + 1 if job in pending else i

        level_emoji = {"Manager": "🔵", "Director": "🟣", "VP": "🟠", "COO": "🔴"}.get(
            job.get("level", ""), "🎯"
        )
        salary = job.get("salary", "Not Listed")
        round_tag = f"  _(review round {job['review_round']})_" if job.get("review_round", 1) > 1 else ""

        card = (
            f"{level_emoji} <b>#{display_num} — {job['title']}</b>{round_tag}\n"
            f"🏢  {job['company']}\n"
            f"📍  {job['location']}\n"
            f"💰  {salary}\n"
            f"🔗  <a href=\"{job['apply_url']}\">View listing</a>\n\n"
            f"Reply: <b>/yes {display_num}</b>  |  <b>/no {display_num}</b>  |  <b>/wait {display_num}</b>"
        )
        await update.message.reply_text(card, parse_mode="HTML", disable_web_page_preview=True)

    # Footer if more jobs remain
    if not args and len(pending) > BATCH_SIZE:
        await update.message.reply_text(
            f"⬆️ That's the first {BATCH_SIZE}. Use /review all to see everything at once.",
            parse_mode="HTML"
        )
