"""
/status — Sends a full summary of the job tracker.

Shows counts by status, current search criteria, and top pending jobs.
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from core.state   import init_db, get_all_stats, get_criteria, get_pending_jobs, get_jobs_by_status

logger = logging.getLogger(__name__)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    stats    = get_all_stats()
    criteria = get_criteria()
    pending  = get_pending_jobs()
    approved = get_jobs_by_status("approved")

    total_tracked = sum(v for k, v in stats.items() if k != "never_show_again")

    summary = (
        f"📊 <b>JOB TRACKER STATUS</b>\n"
        f"<i>{datetime.now().strftime('%b %d, %Y — %I:%M %p')}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>PIPELINE</b>\n"
        f"⏳  Pending review:    {stats.get('pending', 0)}\n"
        f"✅  Approved:          {stats.get('approved', 0)}\n"
        f"🚀  Applied:           {stats.get('applied', 0)}\n"
        f"⏸   On hold (wait):   {stats.get('waiting', 0)}\n"
        f"🗑   Rejected:         {stats.get('rejected', 0)}\n"
        f"🚫  Never show again:  {stats.get('never_show_again', 0)}\n"
        f"<b>Total tracked:</b>       {total_tracked}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>CURRENT SEARCH CRITERIA</b>\n"
        f"🎯  Title Tier:    {criteria.get('title_tier', 'director').title()}\n"
        f"💰  Salary Floor:  ${int(criteria.get('salary_floor', 80000)):,}\n"
        f"📍  Location:      {criteria.get('base_location', 'Sayreville, NJ')} (25 mi)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>COMMANDS</b>\n"
        f"/run — search for new jobs\n"
        f"/review — see pending jobs\n"
        f"/yes [n] — approve job\n"
        f"/no [n]  — reject job\n"
        f"/wait [n] — hold for next round\n"
        f"/stop — emergency stop"
    )

    await update.message.reply_text(summary, parse_mode="HTML")

    # If there are approved jobs awaiting submission, remind
    if approved:
        links = "\n".join(
            f"  • <a href=\"{j['apply_url']}\">{j['title']} @ {j['company']}</a>"
            for j in approved[:5]
        )
        await update.message.reply_text(
            f"🚀 <b>{len(approved)} approved job(s) awaiting your submission:</b>\n{links}\n\n"
            f"Tap a link to open the pre-filled application.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
