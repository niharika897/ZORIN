import asyncio
import json

from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY


class MemoryExtractor:

    def __init__(self, memory_manager):

        self.memory = memory_manager

        self.client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        self.models = [
            "gemini-3.1-flash-lite",
            "gemini-3.8-flash"
        ]
        self.model = self.models[0]

    # --------------------------------------------------
    # EXTRACT MEMORIES
    # --------------------------------------------------

    async def extract(self, conversation):

        if (
            not conversation
            or not isinstance(conversation, str)
            or len(conversation.strip()) < 30
        ):
            return []

        prompt = f"""
You are ZORIN's long-term memory extraction system.

Extract only:

1. Stable personal preferences.
2. Long-term goals.
3. Ongoing projects.
4. Learning interests and progress.
5. Communication preferences.
6. Important non-sensitive personal facts.

Never extract sensitive information, passwords,
temporary activities, or casual questions.

Never create protected Core Memories.
Only create ordinary long-term memories.

Return valid JSON:

{{
    "memories": [
        {{
            "category": "preference",
            "content": "The user prefers...",
            "importance": 3
        }}
    ]
}}

Importance must be between 1 and 5.

If nothing is worth remembering, return
{{"memories": []}}.

CONVERSATION:
{conversation}
"""

        for attempt in range(len(self.models)):
            current_model = self.models[attempt]

            try:

                response = await asyncio.wait_for(

                    self.client.aio.models.generate_content(

                        model=current_model,

                        contents=prompt,

                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2
                        )

                    ),

                    timeout=15
                )

                if not response.text:

                    raise ValueError(
                        "Memory extraction returned an empty response."
                    )

                result = json.loads(response.text)

                if not isinstance(result, dict):

                    raise ValueError(
                        "Invalid memory response format."
                    )

                memories = result.get("memories", [])

                if not isinstance(memories, list):

                    raise ValueError(
                        "Invalid memories list."
                    )

                saved = []

                for item in memories:

                    if not isinstance(item, dict):
                        continue

                    content = item.get("content", "")

                    if not isinstance(content, str):
                        continue

                    content = content.strip()

                    if not content:
                        continue

                    category = item.get(
                        "category",
                        "general"
                    )

                    if not isinstance(category, str):
                        category = "general"

                    category = category.strip() or "general"

                    importance = item.get(
                        "importance",
                        2
                    )

                    if (
                        isinstance(importance, bool)
                        or not isinstance(importance, int)
                    ):
                        importance = 2

                    importance = max(
                        1,
                        min(5, importance)
                    )

                    # Save ordinary long-term memory only.
                    success = self.memory.remember(
                        content=content,
                        category=category,
                        importance=importance
                    )

                    if success:
                        saved.append(content)

                print(
                    f"\nZORIN MEMORY: Saved {len(saved)} memories."
                )

                # [] means extraction succeeded,
                # but nothing useful was found.

                return saved

            except asyncio.CancelledError:

                raise

            except Exception as error:

                temporary_error = any(

                    code in str(error).lower()

                    for code in [
                        "503",
                        "429",
                        "500",
                        "unavailable",
                        "overloaded",
                        "timeout"
                    ]

                ) or isinstance(
                    error,
                    asyncio.TimeoutError
                )

                if temporary_error and attempt < 2:

                    delay = 2 ** (attempt + 1)

                    print(
                        f"\nZORIN MEMORY: Temporary failure. "
                        f"Retrying in {delay} seconds..."
                    )

                    await asyncio.sleep(delay)

                else:

                    print(
                        "\nMEMORY EXTRACTION ERROR:",
                        repr(error)
                    )

                    # None means extraction failed.
                    # The queue worker can retry later.

                    return None

        # Safe fallback if all attempts finish.
        return None