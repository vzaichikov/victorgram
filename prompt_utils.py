from datetime import datetime


def enhance_system_prompt(prompt: str) -> str:
    """Append current date and time information to the system prompt."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    hour = now.hour
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "day"
    elif 17 <= hour < 22:
        period = "evening"
    else:
        period = "night"
    return f"{prompt}\nIf your answer is related to daytime, use this info Current date: {date_str}. Current time: {time_str}. It's {period}."

