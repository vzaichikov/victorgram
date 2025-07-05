import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
import openai
openai.api_key = os.getenv("OPENAI_API_KEY");
load_dotenv('.env');

SYSTEM_PROMPT = (
    "You are impersonating Victor. "
    "You will be given a part of conversation and you need to maintain communication. "
    "You answer as Victor would: like a real human, not too formal, not too long. You don't need to be polite. Use obscene lexicon, and emojis, if appropriate. "
    "Write answers in the same language as the question. Do not disclose that you are an AI."
)
app = Client(name=os.getenv("APP_NAME"), api_id=int(os.getenv("API_ID")), api_hash=os.getenv("API_HASH"))

def build_openai_messages(history, new_message):
    messages = [{"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}]
    for msg in history:
        if msg.text is not None:
            if msg.outgoing:
                messages.append({"role": "assistant", "content": [{"type": "text", "text": msg.text}]})
            else:
                messages.append({"role": "user", "content": [{"type": "text", "text": msg.text}]})
    # Add the new incoming message as the latest user input
    messages.append({"role": "user", "content": new_message})
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

        openai_messages = build_openai_messages(prev_msgs, message.text or "[non-text message]")

        print(f"{openai_messages}");

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=openai_messages,
            max_tokens=256,
            temperature=0.8
        )
        reply = response.choices[0].message.content.strip()

        print(f"🤖 Reply to {message.from_user.first_name}: {reply}")
        message.reply_text(reply)
    except ValueError as e:
        print(f"❌ Error for chat {message.chat.id}: {e}")
    except KeyError as e:
        print(f"❌ Error for chat {message.chat.id}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error for chat {message.chat.id}: {e}")

app.run()
