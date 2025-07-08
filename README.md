# VictorGram

VictorGram is a small Telegram bot that uses [Pyrogram](https://docs.pyrogram.org/) and OpenAI's API.  Messages from users are forwarded to the language model and the reply is sent back to the chat.

## Features

* Private chat only.
* Supports text and image messages.
* System prompts can be customised per user by placing a file in the `prompts/` directory with the user id as filename.

## Setup

1. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file with the following variables (use `.env.<name>` to run multiple instances):
   - `APP_NAME` – Pyrogram session name
   - `API_ID` and `API_HASH` – values from [my.telegram.org](https://my.telegram.org)
   - `OPENAI_API_KEY` – key for OpenAI or configure OLLAMA variables
   - `MAIN_SYSTEM_PROMPT_FILE` – name of the prompt file located in the `system/` directory
3. Run the bot:
   ```bash
   python app.py [name]
   ```

The main entry point is `app.py` and helper functions are located in `bot_utils.py`.
