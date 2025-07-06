import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from io import BytesIO
import base64
from openai_client import OpenAIClient

load_dotenv(".env")

SYSTEM_PROMPT = (
    "You are impersonating Victor. "
    "You will be given a part of conversation and you need to maintain communication. "
    "You answer as Victor would: like a real human, not too formal, not too long. You don't need to be polite. Use obscene lexicon, and emojis, if appropriate. "
    "Write answers in the same language as the question. Do not disclose that you are an AI."
)
app = Client(
    name=os.getenv("APP_NAME"),
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH")
)

ai_client = OpenAIClient()

def message_to_content(client: Client, msg: Message):
    parts = []
    text = msg.text or msg.caption
    if text:
        parts.append({"type": "text", "text": text})

    media = None
    mime_type = "image/jpeg"
    if msg.photo:
        media = client.download_media(msg, in_memory=True)
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
        media = client.download_media(msg, in_memory=True)
        mime_type = msg.document.mime_type

    if media:
        encoded = base64.b64encode(media.getvalue()).decode()
        parts.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}})

    if not parts:
        parts.append({"type": "text", "text": "[non-text message]"})

    return parts


def build_openai_messages(client: Client, history, new_message: Message):
    messages = [{"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}]
    for msg in history:
        content = message_to_content(client, msg)
        role = "assistant" if msg.outgoing else "user"
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message_to_content(client, new_message)})
    return messages

@app.on_message(filters.private & filters.incoming)
def handle_message(client: Client, message: Message):
    user_id = message.from_user.id

    username = message.from_user.username
    if username and username.lower().endswith("_bot"):
        print(f"Skipping bot user: {username}")
        return

    # Exclude groups/channels by checking chat.id
    if user_id < 0:
        print(f"Skipping group/channel: {user_id}")
        return

    if message.chat.id < 0:
        print(f"Skipping group/channel: {message.chat.id}")
        return

    try:
        # Get last 51 messages to exclude the current incoming one (the 51st is the new one)
        history = list(client.get_chat_history(user_id, limit=51))
        if history and history[0].id == message.id:
            history = history[1:]

        prev_msgs = list(reversed(history[:50]))

        openai_messages = build_openai_messages(client, prev_msgs, message)

        print(f"{openai_messages}");

        reply = ai_client.complete(openai_messages)

        print(f"🤖 Reply to {message.from_user.first_name}: {reply}")
        message.reply_text(reply)
    except ValueError as e:
        print(f"❌ Error for chat {message.chat.id}: {e}")
    except KeyError as e:
        print(f"❌ Error for chat {message.chat.id}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error for chat {message.chat.id}: {e}")

app.run()
