import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

if len(sys.argv) != 2:
    print("Usage: python app.py <instance>")
    sys.exit(1)

instance = sys.argv[1]


def setup_logging(name: str):
    logger = logging.getLogger()
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    logger.addHandler(stream)
    if name:
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler(
            os.path.join("logs", f"{name}.log"), encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)


setup_logging(instance)


def log_print(*args, sep=" ", end="\n", **kwargs):
    logging.getLogger().info(sep.join(str(a) for a in args))


print = log_print

env_file = f".env.{instance}"
print(f"ℹ️ Loading instance: {instance}")
load_dotenv(env_file)
os.environ["INSTANCE_NAME"] = instance

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from ai_client import AIClient
from bot_utils import process_waiting_messages

app = Client(
    name=os.getenv("APP_NAME"),
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH")
)

ai_client = AIClient()

waiting_users = {}
waiting_lock = asyncio.Lock()


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

    print(
        f"🤖 Got message from {message.from_user.first_name} ({user_id}): {message.text or 'Non-text message'}"
    )

    async with waiting_lock:
        if user_id in waiting_users:
            waiting_users[user_id].append(message)
            return
        waiting_users[user_id] = [message]
        await client.send_chat_action(user_id, ChatAction.TYPING)
        asyncio.create_task(
            process_waiting_messages(client, user_id, waiting_users, waiting_lock, ai_client)
        )

app.run()
