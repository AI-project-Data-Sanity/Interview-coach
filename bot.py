import os
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes,
)

load_dotenv()

from resume_parser import parse_resume_pdf
from db_calls import get_all_questions
# from app import get_questions_from_llm  # uncomment when ready

DB_PATH = "data/interview.db"

AFTER_START, WAITING_FOR_PDF, AFTER_RESUME, IN_INTERVIEW = range(4)


# --- API stubs (replace with real HTTP calls) ---

def api_register_user(user_id: int):
    # POST /users  body: {user_id}
    pass

def api_save_resume(user_id: int, text: str):
    # POST /resumes  body: {user_id, text}
    pass

def api_finish_session(user_id: int):
    # POST /sessions/finish  body: {user_id}
    pass

def api_get_feedback(user_id: int, question_id: int, answer: str) -> str:
    # POST /feedback  body: {user_id, question_id, answer}
    # Returns feedback string
    known_answers = get_answers_by_id(DB_PATH, question_id)
    return f"Known good answers for reference:\n" + "\n".join(
        f"- [{a['mark']}] {a['answer']} ({a['reason']})" for a in known_answers
    )


# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    api_register_user(user_id)
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


async def send_resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send your resume as a PDF file.")
    return WAITING_FOR_PDF


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.mime_type != "application/pdf":
        await update.message.reply_text("That doesn't look like a PDF. Please send a PDF file.")
        return WAITING_FOR_PDF

    await update.message.reply_text("Received your resume, processing...")

    user_id = update.message.from_user.id
    file = await doc.get_file()
    pdf_path = Path(f"/tmp/{doc.file_id}.pdf")
    await file.download_to_drive(pdf_path)

    resume_text = parse_resume_pdf(pdf_path)
    context.user_data["resume_text"] = resume_text
    api_save_resume(user_id, resume_text)

    await update.message.reply_text(
        "Resume saved!\n"
        "Use /start_interview to begin, or /finish to end the session."
    )
    return AFTER_RESUME


async def start_interview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    resume_text = context.user_data.get("resume_text", "")

    await update.message.reply_text("Preparing your questions...")

    all_questions = get_all_questions(DB_PATH)
    question_ids = get_questions_from_llm(resume_text, all_questions)
    questions = [q for q in all_questions if q["question_id"] in question_ids]

    if not questions:
        await update.message.reply_text(
            "Could not generate questions. Please try uploading your resume again with /send_resume."
        )
        return AFTER_RESUME

    context.user_data["questions"] = questions
    context.user_data["current_index"] = 0

    first = questions[0]
    await update.message.reply_text(
        f"Question 1/{len(questions)}:\n\n{first['question']}"
    )
    return IN_INTERVIEW


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    questions = context.user_data["questions"]
    index = context.user_data["current_index"]
    current_question = questions[index]

    answer = update.message.text
    feedback = api_get_feedback(user_id, current_question["question_id"], answer)
    await update.message.reply_text(f"Feedback:\n{feedback}")

    next_index = index + 1
    if next_index >= len(questions):
        api_finish_session(user_id)
        context.user_data.clear()
        await update.message.reply_text(
            "Interview complete! Well done.\nUse /start to begin a new session."
        )
        return ConversationHandler.END

    context.user_data["current_index"] = next_index
    next_q = questions[next_index]
    await update.message.reply_text(
        f"Question {next_index + 1}/{len(questions)}:\n\n{next_q['question']}"
    )
    return IN_INTERVIEW


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    api_finish_session(user_id)
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
