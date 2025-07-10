# VictorGram

VictorGram is a Telegram bot powered by [Pyrogram](https://docs.pyrogram.org/).  It forwards user messages to an LLM (OpenAI or Ollama) and sends the reply back to the chat.

## Features

* Works only in private chats.
* Supports text, images, PDF and DOCX documents and voice messages. Audio is transcribed with Whisper and text files are also read. PDF files are converted to images and DOCX files are converted to text.
* Adds current date, time and optional weather information to the system prompt.
* Messages from the same user are queued before being sent to the LLM.
* System prompts can be customised per user by placing a file in `prompts/<instance>/<user_id>.txt`.
* Can use OpenAI or local Ollama models and unloads models after a period of inactivity.
* A Streamlit UI (`ui.py`) allows starting and stopping instances.
* `prompt_generator.py` can create personal system prompts from chat history.

## Setup

1. Install the requirements and ensure `ffmpeg` is available (required for `openai-whisper`):
   ```bash
   pip install -r requirements.txt
   ```
2. Create an environment file for each instance (for example `.env.example`) and set the variables below.
3. Put a system prompt for that instance into `system/<instance>.txt` (an example file `system/example.txt` is provided).
4. Run the bot (for example to start the `example` instance):
   ```bash
   python app.py example
   ```

## Environment variables

| Variable | Description                                           |
| --- |-------------------------------------------------------|
| `APP_NAME` | Pyrogram session name                                 |
| `API_ID` | Telegram API ID                                       |
| `API_HASH` | Telegram API hash                                     |
| `HISTORY_LIMIT` | Number of previous messages to include in the request |
| `OPENAI_API_KEY` | Key for the OpenAI API                                |
| `OPENAI_API_BASE_URL` | Base URL for OpenAI API                               |
| `OPENAI_MODEL` | OpenAI model name                                     |
| `OLLAMA_API_KEY` | Key for Ollama server (optional)                      |
| `OLLAMA_API_BASE_URL` | Base URL for Ollama server                            |
| `OLLAMA_API_MODEL` | Ollama model name                                     |
| `USE_OLLAMA` | Set to `true` to use Ollama instead of OpenAI         |
| `OPENWEATHER_API_KEY` | Key for OpenWeather                                   |
| `WEATHER_LAT` / `WEATHER_LON` | Coordinates for weather updates                       |
| `AI_MAX_TOKENS` | Maximum tokens for the model response                 |
| `AI_TEMPERATURE` | Temperature parameter for the model                   |
| `AI_TOP_P` | Top_p parameter for the model                         |
| `NEXT_MESSAGE_WAIT_TIME` | Seconds to wait for more messages before replying     |
| `MY_USER_NAME` | Your name used by `prompt_generator.py`               |
| `WHISPER_DEVICE` | Device for Whisper (`cpu` or `cuda`)                  |
| `WHISPER_MODEL` | Whisper model name                                    |
| `MODEL_UNLOAD_TIMEOUT` | Seconds of inactivity before models are unloaded      |

Logs are saved in the `logs/` directory with one file per instance.  The main entry point is `app.py` and helper functions are located in `bot_utils.py`.
