from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

from app import app
from models import db, TelegramUser

import subprocess
import os

TOKEN = "8889190021:AAH190hTUy4GwP2p_MbYNYDnscxW5JUmQ34"


# ---------------- START ---------------- #

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    telegram_id = str(
        update.effective_user.id
    )

    username = update.effective_user.username

    with app.app_context():

        existing = TelegramUser.query.filter_by(
            telegram_id=telegram_id
        ).first()

        if not existing:

            user = TelegramUser(
                telegram_id=telegram_id,
                username=username,
                plan='free',
                searches_left=3
            )

            db.session.add(user)

            db.session.commit()

    await update.message.reply_text(
        """
Welcome to Summitlink Intelligence Bot

FREE PLAN:
3 searches only

Use:
/search username
        """
    )


# ---------------- SEARCH ---------------- #

async def search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if len(context.args) == 0:

        await update.message.reply_text(
            "Usage: /search username"
        )

        return

    username = context.args[0]

    telegram_id = str(
        update.effective_user.id
    )

    with app.app_context():

        user = TelegramUser.query.filter_by(
            telegram_id=telegram_id
        ).first()

        if not user:

            await update.message.reply_text(
                "Access denied"
            )

            return

        # FREE PLAN LIMIT

        if user.plan == 'free':

            if user.searches_left <= 0:

                await update.message.reply_text(
                    """
Free plan exhausted.

Upgrade to PRO:
Unlimited intelligence searches.
                    """
                )

                return

            user.searches_left -= 1

            db.session.commit()

    await update.message.reply_text(
        f"Investigating {username}..."
    )

    command = [
        "python",
        "/data/data/com.termux/files/home/sherlock/sherlock_project/sherlock.py",
        username
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    os.makedirs(
        "reports",
        exist_ok=True
    )

    report_path = f"reports/{username}.txt"

    with open(report_path, "w") as file:

        file.write(output)

    await update.message.reply_document(
        document=open(report_path, "rb")
    )


# ---------------- PLAN ---------------- #

async def plan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    telegram_id = str(
        update.effective_user.id
    )

    with app.app_context():

        user = TelegramUser.query.filter_by(
            telegram_id=telegram_id
        ).first()

        if user:

            await update.message.reply_text(
                f"""
Plan: {user.plan}

Searches Left:
{user.searches_left}
                """
            )


# ---------------- APP ---------------- #

bot = ApplicationBuilder().token(
    TOKEN
).build()

bot.add_handler(
    CommandHandler("start", start)
)

bot.add_handler(
    CommandHandler("search", search)
)

bot.add_handler(
    CommandHandler("plan", plan)
)

print(
    "Summitlink Premium Intelligence Bot Running..."
)

bot.run_polling()
