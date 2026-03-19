"""
/stop — Emergency kill switch.

Immediately halts any running search or generation process
and sends confirmation.
"""

import logging
import run_cmd as run_module
from telegram import Update
from telegram.ext import ContextTypes
from notifier import send_text

logger = logging.getLogger(__name__)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    was_running = run_module._running
    run_module._running = False   # Force-release the lock

    if was_running:
        await update.message.reply_text(
            "🛑 <b>STOPPED.</b>\n\nAll running processes have been halted.\n"
            "Your data is safe — nothing was lost.\n\n"
            "Use /status to see current job counts, or /run to start a new search.",
            parse_mode="HTML"
        )
        logger.warning("Emergency stop triggered by user.")
    else:
        await update.message.reply_text(
            "✅ Nothing was running. Bot is idle.\n\n"
            "Use /run to start a job search, or /status to check the tracker.",
            parse_mode="HTML"
        )
