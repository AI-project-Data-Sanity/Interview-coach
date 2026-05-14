import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

from resume_parser import parse_resume_pdf
from db_calls import get_all_questions
# from app import get_questions_from_llm  # uncomment when ready


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Interview Coach!\n"
        "Use /send_resume to upload your resume PDF and get interview questions.\n"
        "Use /help for more info."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start the bot\n"
        "/send_resume - Upload your resume PDF\n"
        "/finish - End the session\n"
        "/help - Show this message"
    )


async def send_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your resume as a PDF file.")


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Session ended. Use /start to begin again.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.mime_type != "application/pdf":
        await update.message.reply_text("Please send a PDF file.")
        return

    await update.message.reply_text("Received your resume, processing...")

    file = await doc.get_file()
    pdf_path = Path(f"/tmp/{doc.file_id}.pdf")
    await file.download_to_drive(pdf_path)

    # Your existing logic:
    # parsed_text = parse_resume_pdf(pdf_path)
    # questions = get_all_questions("data/interview.db")
    # question_ids = get_questions_from_llm(parsed_text, questions)
    # await update.message.reply_text(str(question_ids))

    await update.message.reply_text("Resume parsed! (wire up your logic here)")


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("send_resume", send_resume))
    app.add_handler(CommandHandler("finish", finish))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.run_polling()


if __name__ == "__main__":
    main()