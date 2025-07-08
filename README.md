# VictorGram

VictorGram is a small Telegram bot that uses [Pyrogram](https://docs.pyrogram.org/) and OpenAI's API.  Messages from users are forwarded to the language model and the reply is sent back to the chat.

## Features

* Private chat only.
* Supports text and image messages.
* System prompts can be customised per user by placing a file in `prompts/<instance>/<user_id>.txt`.

## Setup

1. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Create an environment file for each instance (for example `.env.example`) with the following variables:
   - `APP_NAME` – Pyrogram session name
   - `API_ID` and `API_HASH` – values from [my.telegram.org](https://my.telegram.org)
   - `OPENAI_API_KEY` – key for OpenAI or configure OLLAMA variables
3. Put a system prompt for that instance into `system/<instance>.txt` (an example file `system/example.txt` is provided).
4. Run the bot (for example to start the `example` instance):
  ```bash
  python app.py example
  ```

The main entry point is `app.py` and helper functions are located in `bot_utils.py`.
