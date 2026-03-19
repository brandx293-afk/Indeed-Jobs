"""
/help — Show all available commands.
"""

from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = """
🤖 <b>Brandon's Job Bot</b>

<b>SEARCH</b>
/run — search with current criteria
/run director — change title tier
/run director 100000 — change tier + salary
/run manager 80000 Edison NJ — change all three

<b>REVIEW</b>
/review — see next 5 pending jobs
/review all — see all pending jobs
/review 3 — see job #3 only

<b>DECISIONS</b>
/yes [n] — approve job, generate packet + send apply link
/no [n] — reject job forever (won't appear again)
/wait [n] — hold for next review round

<b>OTHER</b>
/status — full tracker summary + pipeline counts
/stop — emergency kill switch (stops any running process)
/help — this message

<b>TITLE TIERS:</b>
  manager    → Manager-level and above
  director   → Director-level and above
  executive  → COO / C-suite only

<b>EXAMPLE WORKFLOW:</b>
  1. /run director 100000 Sayreville NJ
  2. /review all
  3. /yes 1  /no 2  /wait 3
  4. Tap APPLY NOW button, fill form, submit
  5. /status to track progress
"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT.strip(), parse_mode="HTML")
