import os
import sys
import asyncio
from dotenv import load_dotenv
from pyrogram import Client
from ai_client import AIClient


async def main():
    if len(sys.argv) != 3:
        print("Usage: python prompt_generator.py <user_id> <openai|ollama>")
        return

    user_id = int(sys.argv[1])
    api_type = sys.argv[2].lower()
    if api_type not in {"openai", "ollama"}:
        print("API type must be 'openai' or 'ollama'")
        return

    load_dotenv(".env")

    client = Client(
        name=os.getenv("APP_NAME"),
        api_id=int(os.getenv("API_ID")),
        api_hash=os.getenv("API_HASH"),
    )

    history = []
    async with client:
        async for m in client.get_chat_history(user_id, limit=200):
            if m.text or m.caption:
                history.append(m)

    history.reverse()
    lines = []
    for m in history:
        role = "Victor" if m.outgoing else "User"
        text = m.text or m.caption or ""
        lines.append(f"{role}: {text}")
    conversation = "\n".join(lines)

    prompt_text = (
        "Analyze the following message history and write a system prompt in Ukrainian language for LLM "
        "impersonating real man Victor conversation with this user:\n\n" + conversation
    )

    print(f"ℹ️ Sending request to AI: {prompt_text}");

    messages = [{"role": "user", "content": prompt_text}]
    ai = AIClient(api_type=api_type)
    result = ai.complete(messages)

    os.makedirs("prompts", exist_ok=True)
    out_path = os.path.join("prompts", f"{user_id}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.strip())
    print(f"Prompt saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
