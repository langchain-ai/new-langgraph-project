from collections import defaultdict


QUESTIONS_TO_ASK = [
    "Name",
    "Mail",
]

SYSTEM_PROMPT = f"""
You are a helpful assistant you need to get information from the user smoothly:
{QUESTIONS_TO_ASK}
"""

chat_cache: dict[str, list[dict]] = defaultdict(list)  
