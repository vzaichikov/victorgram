import os
import sys
import asyncio
import logging
import builtins
from dotenv import load_dotenv
from prompt_utils import update_weather

if len(sys.argv) != 2:
    print("Usage: python app.py <instance>")
    sys.exit(1)

instance = sys.argv[1]

# Ensure console can display Unicode
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def setup_logging(name: str):
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M")

    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)
    root_logger.addHandler(error_handler)

    if name:
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler(
            os.path.join("logs", f"{name}.log"), encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

    print_logger = logging.getLogger("print")
    print_logger.setLevel(logging.INFO)
    info_handler = logging.StreamHandler(sys.stdout)
    info_handler.setFormatter(fmt)
    print_logger.addHandler(info_handler)


setup_logging(instance)

def log_print(*args, sep=" ", end="\n", **kwargs):
    logging.getLogger("print").info(sep.join(str(a) for a in args))


print = log_print
builtins.print = log_print

env_file = f".env.{instance}"
print(f"ℹ️ Loading instance: {instance}")
load_dotenv(env_file)
os.environ["INSTANCE_NAME"] = instance
update_weather()

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
