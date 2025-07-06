import os
import json
import asyncio
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

waiting_users = {}
waiting_lock = asyncio.Lock()

async def message_to_content(client: Client, msg: Message):
    parts = []
    text = msg.text or msg.caption

    if not text and not msg.photo and not msg.document:
        return 0

    if text:
        parts.append({"type": "text", "text": text})

    media = None
    mime_type = "image/jpeg"
    if msg.photo:
        media = await client.download_media(msg, in_memory=True)
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
        media = await client.download_media(msg, in_memory=True)
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

def merge_text_parts(messages):
    for msg in messages:
        new_content = []
        buffer = []
        for part in msg["content"]:
            if part.get("type") == "text":
                buffer.append(part["text"])
            else:
                if buffer:
                    new_content.append({"type": "text", "text": "\n".join(buffer)})
                    buffer = []
                new_content.append(part)
        if buffer:
            new_content.append({"type": "text", "text": "\n".join(buffer)})
        msg["content"] = new_content
    return messages


async def build_openai_messages(client: Client, history, new_messages, system_prompt: str):
    messages = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]

    for msg in history:
        prepared = await message_to_content(client, msg)
        if prepared != 0:
            role = "assistant" if msg.outgoing else "user"
            if messages[-1]["role"] == role:
                messages[-1]["content"].extend(prepared)
            else:
                messages.append({"role": role, "content": prepared})

    if not isinstance(new_messages, list):
        new_messages = [new_messages]

    combined_new = []
    for msg in new_messages:
        prepared = await message_to_content(client, msg)
        if prepared != 0:
            combined_new.extend(prepared)

    if combined_new:
        if messages[-1]["role"] == "user":
            messages[-1]["content"].extend(combined_new)
        else:
            messages.append({"role": "user", "content": combined_new})

    messages = keep_last_image_only(messages)
    messages = merge_text_parts(messages)
    return messages

async def process_waiting_messages(client: Client, user_id: int):
    print(f"🤖 Processing waiting messages for {user_id}")
    await asyncio.sleep(int(os.getenv("NEXT_MESSAGE_WAIT_TIME", 10)))
    async with waiting_lock:
        msgs = waiting_users.pop(user_id, [])
    if not msgs:
        return
    system_prompt = get_system_prompt(user_id)
    print(f"🤖 Processing {len(msgs)} messages from {user_id}")
    try:
        history = []
        limit = int(os.getenv("HISTORY_LIMIT")) + len(msgs)
        async for m in client.get_chat_history(user_id, limit=limit):
            history.append(m)

        history = []
        limit = int(os.getenv("HISTORY_LIMIT")) + len(msgs)
        async for m in client.get_chat_history(user_id, limit=limit):
            history.append(m)

        for m in reversed(msgs):
            if history and history[0].id == m.id:
                history = history[1:]
        limit = int(os.getenv("HISTORY_LIMIT")) - 1
        prev_msgs = list(reversed(history[:limit]))
        openai_messages = await build_openai_messages(client, prev_msgs, msgs, system_prompt)
        print("🤖 Sending message to AI api")
        print(json.dumps(openai_messages, ensure_ascii=False, indent=4))
        reply = ai_client.complete(openai_messages)
        print(f"🤖 Reply to {msgs[-1].from_user.first_name}: {reply}")

        await msgs[-1].reply_text(reply)
    except ValueError as e:
        print(f"❌ Error for chat {user_id}: {e}")
    except KeyError as e:
        print(f"❌ Error for chat {user_id}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error for chat {user_id}: {e}")


@app.on_message(filters.private & filters.incoming)
async def handle_message(client: Client, message: Message):
    user_id = message.from_user.id

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

    async with waiting_lock:
        if user_id in waiting_users:
            waiting_users[user_id].append(message)
            return
        waiting_users[user_id] = [message]
        asyncio.create_task(process_waiting_messages(client, user_id))

app.run()
