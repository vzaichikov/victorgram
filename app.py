import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

log_handlers = [logging.StreamHandler()]
log_file = os.getenv("LOG_FILE")
if log_file:
    log_handlers.append(logging.FileHandler(log_file))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=log_handlers,
)
logger = logging.getLogger(__name__)

if len(sys.argv) != 2:
    print("Usage: python app.py <instance>")
    logger.error("Usage: python app.py <instance>")
    sys.exit(1)

instance = sys.argv[1]
env_file = f".env.{instance}"
print(f"\u2139\ufe0f Loading instance: {instance}")
logger.info("\u2139\ufe0f Loading instance: %s", instance)
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
        logger.info("Skipping bot user: %s", username)
        return

    if int(user_id) < 0:
        print(f"Skipping group/channel: {user_id}")
        logger.info("Skipping group/channel: %s", user_id)
        return

    if int(message.chat.id) < 0:
        print(f"Skipping group/channel: {message.chat.id}")
        logger.info("Skipping group/channel: %s", message.chat.id)
        return

    print(
        f"\U0001F916 Got message from {message.from_user.first_name} ({user_id}): {message.text or 'Non-text message'}"
    )
    logger.info(
        "\U0001F916 Got message from %s (%s): %s",
        message.from_user.first_name,
        user_id,
        message.text or "Non-text message",
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
