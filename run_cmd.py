"""
/run [tier] [salary] [location]
  
Scrapes Indeed for new jobs matching current (or updated) criteria.
Arguments are optional — any provided will update the stored criteria.

Examples:
  /run                              — use current saved criteria
  /run director                     — change tier to director
  /run executive 120000             — change tier + salary floor
  /run manager 80000 Newark NJ      — change all three
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from state   import init_db, get_criteria, set_criteria, upsert_job, is_rejected, get_pending_jobs
from scraper import run_full_search
from notifier import send_text

logger = logging.getLogger(__name__)
_running = False   # simple lock to prevent double-runs


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _running
    if _running:
        await update.message.reply_text("⚠️ A search is already running. Use /stop to cancel it first.")
        return

    init_db()
    args = context.args or []

    # Parse optional overrides from args
    criteria = get_criteria()
    tier_opts = {"manager", "director", "executive"}

    if args:
        i = 0
        # Tier
        if args[i].lower() in tier_opts:
            set_criteria("title_tier", args[i].lower())
            criteria["title_tier"] = args[i].lower()
            i += 1
        # Salary
        if i < len(args) and args[i].isdigit():
            set_criteria("salary_floor", args[i])
            criteria["salary_floor"] = args[i]
            i += 1
        # Location (rest of args)
        if i < len(args):
            loc = " ".join(args[i:])
            set_criteria("base_location", loc)
            criteria["base_location"] = loc

    # Confirm criteria before running
    await update.message.reply_text(
        f"🔍 <b>Starting job search...</b>\n\n"
        f"<b>Title Tier:</b>    {criteria.get('title_tier', 'director').title()}\n"
        f"<b>Salary Floor:</b>  ${int(criteria.get('salary_floor', 80000)):,}\n"
        f"<b>Location:</b>      {criteria.get('base_location', 'Sayreville, NJ')} (25-mile radius)\n\n"
        f"This may take a minute — I'll report back when done.",
        parse_mode="HTML"
    )

    _running = True
    try:
        jobs = run_full_search(criteria)

        new_count = 0
        skipped   = 0
        for job in jobs:
            if is_rejected(job["id"]):
                skipped += 1
                continue
            upsert_job(job)
            new_count += 1

        pending = get_pending_jobs()
        await update.message.reply_text(
            f"✅ <b>Search complete!</b>\n\n"
            f"<b>New jobs added:</b>  {new_count}\n"
            f"<b>Already rejected:</b> {skipped} (filtered out)\n"
            f"<b>Pending review:</b>  {len(pending)}\n\n"
            f"Use <b>/review</b> or <b>/review all</b> to see them.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"/run error: {e}")
        await update.message.reply_text(f"❌ Search failed: {e}")
    finally:
        _running = False
