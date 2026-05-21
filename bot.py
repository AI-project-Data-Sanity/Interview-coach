import logging
import os
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes,
)

load_dotenv()

from app import register_user
from app import save_resume
from app import get_question_list
from app import get_question_text_by_id
from app import get_llm_feedback


AFTER_START, WAITING_FOR_PDF, AFTER_RESUME, IN_INTERVIEW = range(4)

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.username

    try:
        register_user(user_id, user_name)
    except Exception as e:
        await update.message.reply_text(f"Registration failed. Please try again later.\n{e}")
        return ConversationHandler.END
    # allow_reentry=True lets users call /start mid-session; clear stale resume/questions from previous run
    context.user_data.clear()

    await update.message.reply_text(
        "Welcome to Interview Coach!\n"
        "Use /send_resume to upload your resume PDF.\n"
        "Use /finish to end the session."
    )

    return AFTER_START


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — Register and start\n"
        "/send_resume — Upload your resume PDF\n"
        "/start_interview — Begin the interview\n"
        "/finish — End the session"
    )


async def send_resume_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your resume as a PDF file.")
    return WAITING_FOR_PDF


async def handle_document(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document

    if doc.mime_type != "application/pdf":
        await update.message.reply_text("That doesn't look like a PDF. Please send a PDF file.")
        return WAITING_FOR_PDF

    user_id = update.message.from_user.id
    file = await doc.get_file()
    pdf_path = Path(f"data/{doc.file_id}.pdf")
    await file.download_to_drive(pdf_path)

    await update.message.reply_text("Received your resume, processing...")

    try:
        save_resume(user_id, pdf_path)
    except Exception as e:
        await update.message.reply_text(f"Failed to save resume. Please try again.\n{e}")
        return WAITING_FOR_PDF

    await update.message.reply_text(
        "Resume saved!\n"
        "Use /start_interview to begin, or /finish to end the session."
    )
    return AFTER_RESUME


async def start_interview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    await update.message.reply_text("Preparing your questions...")

    try:
        question_ids = get_question_list(user_id)
    except Exception as e:
        await update.message.reply_text(f"Failed to generate questions. Please try again.\n{e}")
        return AFTER_RESUME

    if not question_ids:
        await update.message.reply_text(
            "Could not generate questions. Please try uploading your resume again with /send_resume."
        )
        return AFTER_RESUME

    context.user_data["question_ids"] = question_ids
    context.user_data["current_index"] = 0

    try:
        first_text = get_question_text_by_id(question_ids[0])
    except Exception as e:
        await update.message.reply_text(f"Failed to load question. Please try again.\n{e}")
        return AFTER_RESUME
    await update.message.reply_text(
        f"Question 1/{len(question_ids)}:\n\n{first_text}"
    )
    return IN_INTERVIEW


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    questions_ids = context.user_data["question_ids"]
    index = context.user_data["current_index"]
    current_question_id = questions_ids[index]

    answer = update.message.text
    if len(answer) > 3000:
        await update.message.reply_text("Your answer is too long. Please send a shorter one (up to 3000 characters).")
        return IN_INTERVIEW

    try:
        feedback = get_llm_feedback(user_id, current_question_id, answer)
    except Exception as e:
        await update.message.reply_text(f"Failed to get feedback. Please try again.\n{e}")
        return IN_INTERVIEW

    await update.message.reply_text(f"Feedback:\n{feedback}")

    next_index = index + 1
    if next_index >= len(questions_ids):
        await update.message.reply_text("Interview complete! Well done.")
        return await finish(update, context)

    context.user_data["current_index"] = next_index
    try:
        next_q_text = get_question_text_by_id(questions_ids[next_index])
    except Exception as e:
        await update.message.reply_text(f"Failed to load next question. Please try again.\n{e}")
        return IN_INTERVIEW
    await update.message.reply_text(
        f"Question {next_index + 1}/{len(questions_ids)}:\n\n{next_q_text}"
    )
    return IN_INTERVIEW


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Session ended. Use /start to begin again.")
    return ConversationHandler.END


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AFTER_START: [
                CommandHandler("send_resume", send_resume_command),
                CommandHandler("finish", finish),
            ],
            WAITING_FOR_PDF: [
                MessageHandler(filters.Document.ALL, handle_document),
                CommandHandler("finish", finish),
            ],
            AFTER_RESUME: [
                CommandHandler("start_interview", start_interview),
                CommandHandler("send_resume", send_resume_command),
                CommandHandler("finish", finish),
            ],
            IN_INTERVIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CommandHandler("send_resume", send_resume_command),
                CommandHandler("finish", finish),
            ],
        },
        fallbacks=[CommandHandler("finish", finish)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    app.run_polling()


if __name__ == "__main__":
    main()
