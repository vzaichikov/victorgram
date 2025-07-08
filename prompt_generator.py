import os
import sys
import asyncio
from dotenv import load_dotenv
from pyrogram import Client
from ai_client import AIClient

PROMPTS_DIR = os.path.join("prompts", os.getenv("INSTANCE_NAME", ""))
NAMES_FILE = os.path.join(PROMPTS_DIR, "names.txt")


def _load_name_pairs():
    pairs = {}
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(" - ", 1)
                if len(parts) == 2 and parts[0].isdigit():
                    pairs[int(parts[0])] = parts[1]
    return pairs


async def update_names_file(client: Client, user_ids):
    pairs = _load_name_pairs()
    for uid in user_ids:
        user = await client.get_users(int(uid))
        name = user.first_name or user.username or str(uid)
        pairs[int(uid)] = name

    os.makedirs(PROMPTS_DIR, exist_ok=True)
    with open(NAMES_FILE, "w", encoding="utf-8") as f:
        for uid, name in sorted(pairs.items()):
            f.write(f"{uid} - {name}\n")
    print(f"✅ Names saved to {NAMES_FILE}")


async def generate_prompt(client: Client, user_id: int, api_type: str):
    history = []
    user = await client.get_users(user_id)
    user_name = user.first_name or user.username or str(user_id)
    async for m in client.get_chat_history(user_id, limit=200):
        if m.text or m.caption:
            history.append(m)

    history.reverse()
    lines = []
    for m in history:
        role = os.getenv("MY_USER_NAME") if m.outgoing else user_name
        text = m.text or m.caption or ""
        lines.append(f"{role}: {text}")
    conversation = "\n".join(lines)

    prompt_text = (
        "Analyze the following message history and write a extended system prompt in Ukrainian language for LLM "
        f"impersonating real man with real emotions (and not even suggest being artificial or a bot - it's important) {os.getenv('MY_USER_NAME')} conversation with {user_name}:\n\n" + conversation
    )

    print(f"ℹ️ Sending request to AI: {prompt_text}")

    messages = [{"role": "user", "content": prompt_text}]
    ai = AIClient(api_type=api_type)
    result = ai.complete(messages)
    return result.strip(), user_name


async def main():
    if len(sys.argv) < 2:
        print("Usage: python prompt_generator.py <prompt|names> [user_id] [openai|ollama]")
        return

    mode = sys.argv[1].lower()
    if mode not in {"prompt", "names"}:
        print("Mode must be 'prompt' or 'names'")
        return

    load_dotenv(".env")
    client = Client(
        name=os.getenv("APP_NAME"),
        api_id=int(os.getenv("API_ID")),
        api_hash=os.getenv("API_HASH"),
    )

    async with client:
        if mode == "prompt":
            if len(sys.argv) != 4:
                print("Usage: python prompt_generator.py prompt <user_id> <openai|ollama>")
                return
            user_id = int(sys.argv[2])
            api_type = sys.argv[3].lower()
            if api_type not in {"openai", "ollama"}:
                print("API type must be 'openai' or 'ollama'")
                return

            result, user_name = await generate_prompt(client, user_id, api_type)

            os.makedirs(PROMPTS_DIR, exist_ok=True)
            out_path = os.path.join(PROMPTS_DIR, f"{user_id}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(result)

            print(f"ℹ️ AI returned prompt: {result}")
            print(f"✅ Prompt saved to {out_path}")

            await update_names_file(client, [user_id])
        else:  # names
            os.makedirs(PROMPTS_DIR, exist_ok=True)
            prompt_files = [f for f in os.listdir(PROMPTS_DIR) if f.endswith(".txt") and f != "names.txt"]
            ids = [int(os.path.splitext(f)[0]) for f in prompt_files if os.path.splitext(f)[0].isdigit()]
            await update_names_file(client, ids)


if __name__ == "__main__":
    asyncio.run(main())
