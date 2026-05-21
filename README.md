# Interview-coach
Telegram bot to help you prepare for behavioral interviews. Upload your resume and get a personalized set of interview questions powered by AI.

**[@job_it_interview_coach_bot](https://t.me/job_it_interview_coach_bot)**

## Commands

| Command | Description |
|---|---|
| `/start` | Start the bot |
| `/send_resume` | Upload your resume as a PDF to get interview questions |
| `/help` | Show available commands |
| `/finish` | End the current session |

## Setup

1. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

2. Create a `.env` file in the project root (use `.env copy` as a template):
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   DB_PATH=path-to-your-database.db
   GOLDEN_RESUMES_PATH=path-to-golden-resumes-folder-only-for-evaluation

   # Each task can use a different provider and model
   LLM_ASSESSMENT_PROVIDER=mistral
   LLM_ASSESSMENT_MODEL=mistral-small-latest

   LLM_PLAN_BUILDER_PROVIDER=gemini
   LLM_PLAN_BUILDER_MODEL=gemini-2.0-flash-lite

   LLM_PREPARSER_PROVIDER=mistral
   LLM_PREPARSER_MODEL=mistral-small-latest

   LLM_PARSER_PROVIDER=openrouter
   LLM_PARSER_MODEL=nvidia/nemotron-3-super-120b-a12b:free

   # Only keys for active providers are required
   MISTRAL_KEY=your_mistral_key_here
   OPENROUTER_KEY=your_openrouter_key_here
   GEMINI_API_KEY=your_gemini_key_here
   ```

   - Telegram token: [@BotFather](https://t.me/BotFather)
   - Mistral key: [console.mistral.ai](https://console.mistral.ai)
   - OpenRouter key: [openrouter.ai/keys](https://openrouter.ai/keys)
   - Gemini key: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - `DB_PATH`: path to the SQLite database (e.g., `data/interview.db`)
   - `GOLDEN_RESUMES_PATH`: only needed when running `evaluation.py`

3. Set up the database — use the provided `data/interview.db` or see [db_creation/](db_creation/) to rebuild from scratch.

## Run

```bash
python3 bot.py
```

Stop the bot with `Ctrl+C`.

## LLM providers

Each task has its own provider and model configured independently in `.env`. Supported providers: `mistral`, `gemini`, `openrouter`.

| Task | Variable prefix | Default provider | Default model |
|---|---|---|---|
| Assess answer | `LLM_ASSESSMENT_` | `mistral` | `mistral-small-latest` |
| Build interview plan | `LLM_PLAN_BUILDER_` | `gemini` | `gemini-2.0-flash-lite` |
| Check resume validity | `LLM_PREPARSER_` | `mistral` | `mistral-small-latest` |
| Extract resume text | `LLM_PARSER_` | `openrouter` | `nvidia/nemotron-3-super-120b-a12b:free` |

## Tests

No API keys or running database are required — all external dependencies are mocked.

```bash
pip3 install pytest pytest-mock
pytest tests/ -v
```

The suite covers `db_calls`, `llm_calls`, `llm_resume_parser`, and `app` (unit tests + app/DB integration tests).