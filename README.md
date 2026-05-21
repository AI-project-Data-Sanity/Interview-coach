# Interview-coach
Telegram bot to help you prepare for behavioral interviews. Upload your resume and get a personalized set of interview questions powered by AI.

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
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   DB_PATH=data/interview.db

   # LLM provider: mistral | gemini | openrouter
   LLM_PROVIDER=mistral
   LLM_MODEL=mistral-small-latest

   # Only the key for the active LLM_PROVIDER is required
   MISTRAL_KEY=your_mistral_api_key
   OPENROUTER_KEY=your_openrouter_key
   GEMINI_API_KEY=your_gemini_api_key
   ```

   - Telegram token: [@BotFather](https://t.me/BotFather)
   - Mistral key: [console.mistral.ai](https://console.mistral.ai)
   - OpenRouter key: [openrouter.ai/keys](https://openrouter.ai/keys)
   - Gemini key: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
   - `DB_PATH`: path to the SQLite database (e.g., `data/interview.db`)

3. Set up the database — use the provided `data/interview.db` or see [db_creation/](db_creation/) to rebuild from scratch.

## Run

```bash
python3 bot.py
```

Stop the bot with `Ctrl+C`.

## LLM providers

The bot and evaluator support three providers, configured via `LLM_PROVIDER` and `LLM_MODEL` in `.env`:

| Provider | Example model |
|---|---|
| `mistral` | `mistral-small-latest` |
| `gemini` | `gemini-2.0-flash-lite` |
| `openrouter` | `deepseek/deepseek-v4-flash:free` |

## Tests

No API keys or running database are required — all external dependencies are mocked.

```bash
pip3 install pytest pytest-mock
pytest tests/ -v
```

The suite covers `db_calls`, `llm_calls`, `resume_parser`, and `app`.