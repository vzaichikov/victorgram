import os
import json
import asyncio
import base64
import random
from io import BytesIO
from pyrogram import Client
from pyrogram.types import Message
from ai_client import AIClient
from pyrogram.enums import ChatAction
from pyrogram.raw import functions as raw_functions, types as raw_types
from prompt_utils import enhance_system_prompt
from docx import Document
import fitz

SYSTEM_PROMPTS_DIR = "prompts"
GROUP_PROMPTS_SUBDIR = "groups"
SYSTEM_DIR = "system"
INSTANCE_NAME = os.getenv("INSTANCE_NAME")
if not INSTANCE_NAME:
    raise ValueError("INSTANCE_NAME not set")
with open(os.path.join(SYSTEM_DIR, f"{INSTANCE_NAME}.txt"), "r", encoding="utf-8") as f:
    GENERAL_SYSTEM_PROMPT = f.read().strip()

CACHE_DIR = os.path.join("data", INSTANCE_NAME, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_system_prompt(chat_id: int, name: str) -> str:
    if chat_id < 0:
        path = os.path.join(
            SYSTEM_PROMPTS_DIR, INSTANCE_NAME, GROUP_PROMPTS_SUBDIR, f"{chat_id}.txt"
        )
    else:
        path = os.path.join(SYSTEM_PROMPTS_DIR, INSTANCE_NAME, f"{chat_id}.txt")

    if os.path.exists(path):
        print(f"ℹ️ Using custom system prompt for chat {chat_id}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    if chat_id < 0:
        return GENERAL_SYSTEM_PROMPT + f"\nThe group's name is {name}."

    return GENERAL_SYSTEM_PROMPT + f"\nThe other person's name is {name}."

async def message_to_content(client: Client, msg: Message, ai_client: AIClient):
    parts = []
    text = msg.text or msg.caption

    if not text and not msg.photo and not msg.document and not msg.voice and not msg.audio and not msg.video_note:
        return 0

    if msg.voice or msg.audio or msg.video_note:
        try:
            print("ℹ️ Got audio message, trying to transcript with Whisper")
            media = await client.download_media(msg, in_memory=True)
            transcript = ai_client.transcribe(media.getvalue())
            if transcript:
                print(f"ℹ️ Got transcription: {transcript}")
                text = (text + "\n" if text else "") + transcript
        except Exception as e:
            print(f"⛔ Whisper error: {e}")

    if text:
        parts.append({"type": "text", "text": text})

    media = None
    mime_type = "image/jpeg"
    if msg.photo:
        media = await client.download_media(msg, in_memory=True)
    elif msg.document and msg.document.mime_type:
        mime_type = msg.document.mime_type
        print(f"ℹ️ Got document with mime type {mime_type}")
        fname = msg.document.file_name or ""
        if mime_type.startswith("image/") and fname.lower().endswith(("jpg", "jpeg", "gif", "png", "webp", "avif")):
            media = await client.download_media(msg, in_memory=True)
        elif mime_type == "application/pdf" or fname.lower().endswith(".pdf"):
            uid = msg.document.file_unique_id or msg.document.file_id
            doc_dir = os.path.join(CACHE_DIR, uid)
            os.makedirs(doc_dir, exist_ok=True)
            image_files = sorted([f for f in os.listdir(doc_dir) if f.endswith(".jpg")])
            if not image_files:
                print("ℹ️ Converting PDF to images with PyMuPDF")
                pdf_bytes = await client.download_media(msg, in_memory=True)
                pdf_bytes = pdf_bytes.getvalue()
                with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                    for i, page in enumerate(doc):
                        pix = page.get_pixmap()
                        out_path = os.path.join(doc_dir, f"page_{i+1}.jpg")
                        with open(out_path, "wb") as f:
                            f.write(pix.tobytes("jpg"))
                        print(f"✅ Saved PDF page {i+1} to {out_path}")
                        image_files.append(f"page_{i+1}.jpg")
            for img in image_files:
                with open(os.path.join(doc_dir, img), "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}, "document": True})
        elif mime_type.startswith("application/vnd.openxmlformats") or fname.lower().endswith(".docx"):
            uid = msg.document.file_unique_id or msg.document.file_id
            out_path = os.path.join(CACHE_DIR, f"{uid}.txt")
            if not os.path.exists(out_path):
                print("ℹ️ Extracting text from DOCX file")
                doc_bytes = await client.download_media(msg, in_memory=True)
                doc = Document(BytesIO(doc_bytes.getvalue()))
                text_content = "\n".join(p.text for p in doc.paragraphs)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                print(f"✅ Saved DOCX text to {out_path}")
            else:
                print(f"ℹ️ Loading cached DOCX text from {out_path}")
                with open(out_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            if text_content:
                parts.append({"type": "text", "text": text_content, "document": True})
        elif mime_type.startswith("text/") or fname.lower().endswith((".txt", ".md", ".log")):
            text_bytes = await client.download_media(msg, in_memory=True)
            try:
                text_content = text_bytes.getvalue().decode("utf-8")
            except UnicodeDecodeError:
                text_content = text_bytes.getvalue().decode("latin-1")
            parts.append({"type": "text", "text": text_content})
    if media:
        encoded = base64.b64encode(media.getvalue()).decode()
        parts.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}})

    if not parts:
        parts.append({"type": "text", "text": "[non-text message]"})

    return parts

def keep_last_image_only(messages):
    last_index = None
    for i, msg in enumerate(messages):
        for part in msg["content"]:
            if part.get("type") == "image_url" or part.get("document"):
                last_index = i
    if last_index is None:
        return messages

    doc_parts = []
    for i, msg in enumerate(messages):
        new_content = []
        for part in msg["content"]:
            is_doc = part.get("type") == "image_url" or part.get("document")
            if is_doc:
                if i == last_index:
                    doc_parts.append(part)
            else:
                new_content.append(part)
        msg["content"] = new_content

    messages[last_index]["content"].extend(doc_parts)
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

async def build_openai_messages(client: Client, history, new_messages, system_prompt: str, ai_client: AIClient):
    messages = [{"role": "system", "content": [{"type": "text", "text": system_prompt}]}]

    for msg in history:
        prepared = await message_to_content(client, msg, ai_client)
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
        prepared = await message_to_content(client, msg, ai_client)
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


async def send_topic_message(client: Client, chat_id: int, topic_id: int, text: str):
    await client.invoke(
        raw_functions.messages.SendMessage(
            peer=await client.resolve_peer(chat_id),
            message=text,
            random_id=client.rnd_id(),
            reply_to=raw_types.InputReplyToMessage(
                top_msg_id=topic_id,
                reply_to_msg_id=0,
            ),
        )
    )


async def send_typing_loop(
    client: Client,
    chat_id: int,
    stop_event: asyncio.Event,
    thread_id: int | None = None,
):
    while not stop_event.is_set():
        try:
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception as e:
            print(f"⛔ Typing notification error for {chat_id}: {e}")
        await asyncio.sleep(random.uniform(2, 3))

async def process_waiting_messages(
    client: Client,
    chat_id: int,
    waiting_dict,
    waiting_lock,
    ai_client,
    delay: int | None = None,
    reply_targets: dict | None = None,
    *,
    key=None,
    thread_id: int | None = None,
):
    if key is None:
        key = chat_id
    print(f"🤖 Processing waiting messages for {chat_id}")
    if delay is None:
        delay = int(os.getenv("NEXT_MESSAGE_WAIT_TIME", 10))
    await asyncio.sleep(delay)
    async with waiting_lock:
        msgs = waiting_dict.pop(key, [])
        reply_to = None
        if reply_targets is not None:
            reply_to = reply_targets.pop(key, None)
    if not msgs:
        return
    if chat_id < 0:
        user_name = msgs[-1].chat.title or str(chat_id)
    else:
        user_name = (
            msgs[-1].from_user.first_name
            or msgs[-1].from_user.username
            or str(chat_id)
        )
    system_prompt = enhance_system_prompt(get_system_prompt(chat_id, user_name))
    print(f"🤖 Processing {len(msgs)} messages from {chat_id}")
    try:
        history = []
        limit = int(os.getenv("HISTORY_LIMIT")) + len(msgs)
        async for m in client.get_chat_history(chat_id, limit=limit):
            history.append(m)

        for m in reversed(msgs):
            if history and history[0].id == m.id:
                history = history[1:]
        limit = int(os.getenv("HISTORY_LIMIT")) - 1
        prev_msgs = list(reversed(history[:limit]))
        openai_messages = await build_openai_messages(client, prev_msgs, msgs, system_prompt, ai_client)
        print("🤖 Sending message to AI, with typing notification")
        await client.send_chat_action(chat_id, ChatAction.TYPING)
        stop_event = asyncio.Event()
        typing_task = asyncio.create_task(
            send_typing_loop(client, chat_id, stop_event, thread_id=thread_id)
        )
        reply = await asyncio.to_thread(ai_client.complete, openai_messages)
        stop_event.set()
        await typing_task
        print(f"🤖 Reply to {msgs[-1].from_user.first_name}: {reply}")

        if reply_to is not None:
            await reply_to.reply_text(reply)
        else:
            if thread_id:
                await send_topic_message(client, chat_id, thread_id, reply)
            else:
                await client.send_message(chat_id, reply)
    except ValueError as e:
        print(f"⛔ Error for chat {chat_id}: {e}")
    except KeyError as e:
        print(f"⛔ Error for chat {chat_id}: {e}")
    except Exception as e:
        print(f"⛔ Unexpected error for chat {chat_id}: {e}")
    finally:
        await client.send_chat_action(chat_id, ChatAction.CANCEL)

