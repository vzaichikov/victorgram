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
2. Create a `.env` file with the following variables:
   - `APP_NAME` – Pyrogram session name
   - `API_ID` and `API_HASH` – values from [my.telegram.org](https://my.telegram.org)
   - `OPENAI_API_KEY` – key for OpenAI or configure OLLAMA variables
3. Run the bot:
   ```bash
   python app.py
   ```

The main entry point is `app.py` and helper functions are located in `bot_utils.py`.
