import os
import json
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from io import BytesIO
import base64
from ai_client import AIClient

load_dotenv(".env")

SYSTEM_PROMPTS_DIR = "prompts"
with open("system_prompt.txt", "r", encoding="utf-8") as f:
    GENERAL_SYSTEM_PROMPT = f.read().strip()

def get_system_prompt(user_id: int) -> str:
    path = os.path.join(SYSTEM_PROMPTS_DIR, f"{user_id}.txt")
    if os.path.exists(path):
        print(f"ℹ️ Using custom system prompt for user {user_id}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return GENERAL_SYSTEM_PROMPT
app = Client(
    name=os.getenv("APP_NAME"),
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH")
)

ai_client = AIClient()

def message_to_content(client: Client, msg: Message):
    parts = []
    text = msg.text or msg.caption

    if not text and not msg.photo and not msg.document:
        return 0

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


def keep_last_image_only(messages):
    last_index = None
    last_image = None
    for i, msg in enumerate(messages):
        for part in msg["content"]:
            if part.get("type") == "image_url":
                last_index = i
                last_image = part
    if last_index is None:
        return messages
    for msg in messages:
        msg["content"] = [p for p in msg["content"] if p.get("type") != "image_url"]
    messages[last_index]["content"].append(last_image)
    return messages


def build_openai_messages(client: Client, history, new_message: Message, system_prompt: str):
    messages = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]
    for msg in history:
        prepared = message_to_content(client, msg)

        if prepared != 0:
            role = "assistant" if msg.outgoing else "user"
            if messages[-1]["role"] == role:
                messages[-1]["content"].extend(prepared)
            else:
                messages.append({"role": role, "content": prepared})

    prepared_new = message_to_content(client, new_message)
    if prepared_new != 0:
        if messages[-1]["role"] == "user":
            messages[-1]["content"].extend(prepared_new)
        else:
            messages.append({"role": "user", "content": prepared_new})
    messages = keep_last_image_only(messages)
    return messages

@app.on_message(filters.private & filters.incoming)
def handle_message(client: Client, message: Message):
    user_id = message.from_user.id
    system_prompt = get_system_prompt(user_id)

    username = message.from_user.username
    if username and username.lower().endswith("_bot"):
        print(f"Skipping bot user: {username}")
        return

    if int(user_id) < 0:
        print(f"Skipping group/channel: {user_id}")
        return

    if int(message.chat.id) < 0:
        print(f"Skipping group/channel: {message.chat.id}")
        return

    print(f"🤖 Got message from {message.from_user.first_name} ({user_id}): {message.text or 'Non-text message'}")

    try:
        history = list(client.get_chat_history(user_id, limit=int(os.getenv("HISTORY_LIMIT"))))
        if history and history[0].id == message.id:
            history = history[1:]

        limit = int(os.getenv("HISTORY_LIMIT")) - 1
        prev_msgs = list(reversed(history[:limit]))

        openai_messages = build_openai_messages(client, prev_msgs, message, system_prompt)

        print(f"🤖 Sending message to AI api")
        # print(json.dumps(openai_messages, ensure_ascii=False, indent=4))

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
