# Interview-coach
Telegram bot to help you prepare for behavioral interviews. Upload your resume and get a personalized set of interview questions powered by Mistral AI.

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

2. Create a `.env` file in the project root:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   MISTRAL_KEY=your_mistral_api_key
   DB_PATH=path_to_your_database.db
   ```

   - Get a Telegram bot token from [@BotFather](https://t.me/BotFather)
   - Get a Mistral API key from [console.mistral.ai](https://console.mistral.ai)
   - Set `DB_PATH` to the desired location for the SQLite database (e.g., `data/interview.db`)
   
   See db_creation folder to fully reproduce the database building process or just use the provided `interview.db` file.

## Run

```bash
python3 bot.py
```

Stop the bot with `Ctrl+C`.
