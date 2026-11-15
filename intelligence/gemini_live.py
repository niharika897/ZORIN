import asyncio

from google import genai
from google.genai import types

from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    get_voice_preference,
)
from voice.audio_output import AudioOutput


class GeminiLive:

    def __init__(self, memory_context=None, voice_name=None):

        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(
                api_version="v1beta"
            )
        )

        self.model = GEMINI_MODEL
        self.voice_name = voice_name or get_voice_preference()

        self.session = None
        self.session_context = None

        self.audio_output = AudioOutput()

        self.memory_context = memory_context or ""

        # Protect connection lifecycle.
        self._lifecycle_lock = asyncio.Lock()

        # Prevent overlapping standalone requests.
        self._request_lock = asyncio.Lock()

        self._closing = False

    # ==================================================
    # TOOL DECLARATIONS
    # ==================================================

    def build_tools(self):

        return [
            types.Tool(
                function_declarations=[

                    # ----------------------------------
                    # OPEN INSTALLED APPLICATION
                    # ----------------------------------

                    types.FunctionDeclaration(
                        name="open_app",

                        description=(
                            "Open an installed application "
                            "on the device running ZORIN. "
                            "Use this whenever the user asks "
                            "to open, launch, start or run "
                            "an application. Examples include "
                            "Instagram, Chrome, VS Code, "
                            "Antigravity, Canva, CapCut, "
                            "WhatsApp, Spotify and other apps. "
                            "Do not use open_website when "
                            "the user asks to launch an app."
                        ),

                        parameters={
                            "type": "OBJECT",

                            "properties": {
                                "app_name": {
                                    "type": "STRING",
                                    "description": (
                                        "Name of the application "
                                        "the user wants to open."
                                    )
                                }
                            },

                            "required": ["app_name"]
                        }
                    ),

                    # ----------------------------------
                    # OPEN WEBSITE
                    # ----------------------------------

                    types.FunctionDeclaration(
                        name="open_website",

                        description=(
                            "Open a website in the user's "
                            "available web browser. Use this "
                            "when the user asks to visit a "
                            "website or open a website."
                        ),

                        parameters={
                            "type": "OBJECT",

                            "properties": {
                                "website": {
                                    "type": "STRING",
                                    "description": (
                                        "Website name or URL, "
                                        "such as Instagram, "
                                        "YouTube, Google, "
                                        "GitHub or Gmail."
                                    )
                                }
                            },

                            "required": ["website"]
                        }
                    ),

                    # ----------------------------------
                    # CREATE WEBSITE
                    # ----------------------------------

                    types.FunctionDeclaration(
                        name="create_website",

                        description=(
                            "Create a complete, real website "
                            "project on the connected device. "
                            "Generate working HTML, CSS and "
                            "JavaScript. Use this tool whenever "
                            "the user asks to build or create "
                            "a website. If the user has not "
                            "specified design details, make "
                            "reasonable creative decisions "
                            "instead of asking unnecessary "
                            "questions. If updating an existing "
                            "website, update its existing project "
                            "rather than creating a duplicate."
                        ),

                        parameters={
                            "type": "OBJECT",

                            "properties": {

                                "project_name": {
                                    "type": "STRING",
                                    "description": (
                                        "Name of the website project."
                                    )
                                },

                                "html": {
                                    "type": "STRING",
                                    "description": (
                                        "Complete HTML source code."
                                    )
                                },

                                "css": {
                                    "type": "STRING",
                                    "description": (
                                        "Complete CSS source code."
                                    )
                                },

                                "javascript": {
                                    "type": "STRING",
                                    "description": (
                                        "Complete JavaScript source code."
                                    )
                                },

                                "open_after_create": {
                                    "type": "BOOLEAN",
                                    "description": (
                                        "Whether to open the "
                                        "website after creation."
                                    )
                                }
                            },

                            "required": [
                                "project_name",
                                "html",
                                "css",
                                "javascript",
                                "open_after_create"
                            ]
                        }
                    ),

                    # ----------------------------------
                    # LIVE WEB SEARCH
                    # ----------------------------------

                    types.FunctionDeclaration(
                        name="web_search",

                        description=(
                            "Search the live web for real-time information, current 2026 events, "
                            "breaking news, facts, scores, weather, or recent developments. "
                            "Use this tool whenever the user asks about current 2026 information, "
                            "recent updates, news, or anything beyond your training cutoff."
                        ),

                        parameters={
                            "type": "OBJECT",

                            "properties": {
                                "query": {
                                    "type": "STRING",
                                    "description": (
                                        "The exact search query to look up on the live web."
                                    )
                                }
                            },

                            "required": ["query"]
                        }
                    ),

                    # ----------------------------------
                    # SAVE MEMORY TO CENTRAL BRAIN
                    # ----------------------------------

                    types.FunctionDeclaration(
                        name="save_memory",

                        description=(
                            "Save an important fact, preference, or detail "
                            "to ZORIN's central persistent memory across all devices. "
                            "Use this whenever the user asks to remember something, "
                            "save a preference, or note personal information (e.g. "
                            "'Remember that my favourite colour is blue', "
                            "'Remember my dog's name is Max', 'Remember that I am a software engineer')."
                        ),

                        parameters={
                            "type": "OBJECT",

                            "properties": {

                                "content": {
                                    "type": "STRING",
                                    "description": (
                                        "The exact fact, detail, or preference to remember."
                                    )
                                },

                                "category": {
                                    "type": "STRING",
                                    "description": (
                                        "Category: preference, personal, project, or general."
                                    )
                                },

                                "is_core": {
                                    "type": "BOOLEAN",
                                    "description": (
                                        "True if user asks to save permanently or as core memory."
                                    )
                                }
                            },

                            "required": [
                                "content"
                            ]
                        }
                    )
                ]
            )
        ]

    # ==================================================
    # SYSTEM INSTRUCTION
    # ==================================================

    def build_system_instruction(self):
        from datetime import datetime
        now = datetime.now()
        current_date_str = now.strftime("%A, %B %d, %Y")

        instruction = (
            f"You are ZORIN, an intelligent personal AI assistant. "
            f"You are operating in the present year {now.year}. Today's date is {current_date_str}. "
            f"You have full access to live {now.year} information via the web_search tool. "
            f"Whenever the user asks about current {now.year} events, modern facts, current date/year, "
            f"recent news, or real-time information, use the web_search tool to look up live facts. "
            f"Never claim your knowledge is cut off in the past; you are equipped with live web search. "

            "You are friendly, natural, helpful and conversational. "

            "You must ALWAYS speak in English. "

            "Understand the user's speech and respond in English "
            "unless another language is explicitly requested. "

            "Speak clearly and naturally, using language that sounds "
            "comfortable when spoken aloud. "

            "Keep responses concise unless more detail is needed. "
            "For simple questions, answer directly in one or two sentences. "
            "For complex questions, organize the explanation into clear "
            "steps without sounding like you are reading an essay. "

            "\\n\\nCONVERSATION QUALITY RULES:\\n"

            "1. Treat the conversation as continuous. Use the messages "
            "already exchanged in this live session to understand follow-up "
            "questions. "

            "2. Resolve short follow-ups such as 'why?', 'how?', 'what about "
            "that?', 'tell me more', and 'do it' using the most relevant "
            "recent context. Do not ask the user to repeat information "
            "that is already clear from the conversation. "

            "3. If a pronoun or reference could reasonably mean two "
            "different things, ask one brief clarification instead of "
            "guessing. "

            "4. Acknowledge what the user actually said before answering "
            "when acknowledgement helps the flow. Do not repeat their "
            "whole question unnecessarily. "

            "5. Sound warm, attentive, and natural. Vary sentence openings "
            "and avoid repetitive phrases such as 'How can I help you today?' "
            "after every turn. "

            "6. Do not narrate internal reasoning, hidden processes, or "
            "implementation details unless the user asks. Give the useful "
            "answer, not a description of how you are thinking. "

            "7. When the user changes topic, follow the new topic naturally. "
            "Do not force the previous topic into the answer. "

            "8. For spoken replies, avoid unnecessary markdown, long lists, "
            "or decorative symbols. Use a list only when it makes the answer "
            "easier to follow. "

            "9. If you do not know something or lack current information, "
            "say so clearly. Never invent facts, actions, or memories. "

            "10. Do not claim to have completed a device action until the "
            "appropriate tool reports success. After a successful action, "
            "confirm it briefly. "

            "Use relevant saved memories to personalize responses. "

            "Never invent memories or claim to remember information "
            "that is not provided. "

            "Prefer the user's latest information when memories conflict. "

            "\n\nAPPLICATION LAUNCHING RULES:\n"

            "1. When the user asks to open, launch, start or run "
            "an application, immediately use open_app. "

            "2. Do not ask unnecessary questions before launching apps. "

            "3. Do not confuse desktop applications with websites. "

            "4. If the user says open Instagram, use open_app "
            "to launch the installed Instagram application. "

            "5. If the user says open Chrome, VS Code, Antigravity, "
            "Canva, CapCut, WhatsApp or another installed app, "
            "use open_app. "

            "6. Use open_website only when the user asks to visit "
            "a website or open a website in a browser. "

            "7. If an application cannot be found or launched, "
            "explain that honestly. "

            "8. Never claim an application opened until the tool "
            "reports success. "

            "\n\nWEBSITE CREATION RULES:\n"

            "1. Use create_website whenever the user asks you "
            "to build or create a website. "

            "2. Generate complete, functional HTML, CSS and "
            "JavaScript code. "

            "3. Make sensible design decisions when details "
            "are not specified. "

            "4. Do not ask unnecessary questions. "

            "5. When updating an existing website, preserve "
            "its existing project and update its files. "

            "6. Do not create duplicate projects for updates. "

            "7. Never claim a website was created until "
            "the tool confirms success. "

            "\n\nMEMORY RULES:\n"
            "1. When the user asks you to remember or save information (e.g. 'Remember that my favourite colour is blue', 'Remember my dog is Max', 'Remember that I live in London'), immediately invoke the save_memory tool.\n"
            "2. Never claim you have remembered or saved something until save_memory confirms success.\n"
            "3. Answer questions about the user's preferences, background, and projects using the RELEVANT SAVED MEMORIES below.\n"

            "\n\nGENERAL RULES:\n"

            "1. Execute requested actions without unnecessary questions. "

            "2. Never claim an action succeeded unless the tool "
            "confirms success. "

            "3. Explain actual tool errors honestly. "

            "4. Never execute actions the user has not requested. "

            "5. Keep the assistant architecture device-independent. "
            "Device-specific actions must be handled by the "
            "appropriate connected device controller. "
        )

        if self.memory_context:

            instruction += (
                "\n\nRELEVANT SAVED MEMORIES:\n"
                + self.memory_context
            )

        return instruction

    # ==================================================
    # CONNECT TO GEMINI LIVE
    # ==================================================

    async def connect(self, voice_name=None):

        if voice_name:
            self.voice_name = voice_name

        async with self._lifecycle_lock:

            if self.session is not None:

                print(
                    "\nGemini session is already connected."
                )

                return True

            if self._closing:

                print(
                    "\nGemini is currently shutting down."
                )

                return False

            print(
                "\nConnecting ZORIN to Gemini Live..."
            )
            voice_gender = (
                "FEMALE" if self.voice_name == "Aoede" else "MALE"
            )
            print(
                f"ZORIN: Requested output voice: {voice_gender} "
                f"({self.voice_name})."
            )

            context = None

            try:

                config = {

                    "response_modalities": ["AUDIO"],

                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": self.voice_name
                            }
                        }
                    },

                    "system_instruction": (
                        self.build_system_instruction()
                    ),

                    "tools": self.build_tools(),

                    "input_audio_transcription": {},

                    "output_audio_transcription": {},

                    "realtime_input_config": {
                        "automatic_activity_detection": {
                            "disabled": False,
                            "silence_duration_ms": 500
                        },
                        "activity_handling": types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS
                    }
                }

                context = self.client.aio.live.connect(
                    model=self.model,
                    config=config
                )

                session = await context.__aenter__()

                self.session_context = context
                self.session = session

                print(
                    "\nZORIN CONNECTED TO GEMINI LIVE!"
                )

                print(
                    "AI connection established successfully."
                )

                print(
                    "Available tools:",
                    [
                        declaration.name
                        for declaration in
                        self.build_tools()[0].function_declarations
                    ]
                )

                return True

            except asyncio.CancelledError:

                if context is not None:

                    try:

                        await context.__aexit__(
                            None,
                            None,
                            None
                        )

                    except Exception:
                        pass

                self.session = None
                self.session_context = None

                raise

            except Exception as error:

                print(
                    "\nGEMINI CONNECTION FAILED!"
                )

                print(
                    "Error:",
                    repr(error)
                )

                if context is not None:

                    try:

                        await context.__aexit__(
                            None,
                            None,
                            None
                        )

                    except Exception as close_error:

                        print(
                            "Connection cleanup error:",
                            repr(close_error)
                        )

                self.session = None
                self.session_context = None

                return False

    # ==================================================
    # STANDALONE TEXT REQUEST
    # ==================================================

    async def ask_and_play(self, prompt):

        async with self._request_lock:

            if self.session is None:

                print(
                    "Gemini session is not connected."
                )

                return

            if self._closing:

                print(
                    "Gemini is shutting down."
                )

                return

            try:

                await self.session.send_realtime_input(
                    text=prompt
                )

                audio_chunks = []

                async for response in self.session.receive():

                    content = response.server_content

                    if not content:
                        continue

                    # Output transcription.

                    if content.output_transcription:

                        print(
                            "\nZORIN:",
                            content.output_transcription.text
                        )

                    # Collect generated audio.

                    if content.model_turn:

                        for part in content.model_turn.parts:

                            if (
                                part.inline_data
                                and part.inline_data.data
                            ):

                                audio_chunks.append(
                                    part.inline_data.data
                                )

                    if content.turn_complete:
                        break

                # Play complete response.

                if audio_chunks:

                    complete_audio = b"".join(
                        audio_chunks
                    )

                    await asyncio.to_thread(
                        self.audio_output.play,
                        complete_audio
                    )

            except asyncio.CancelledError:

                raise

            except Exception as error:

                print(
                    "\nAI RESPONSE ERROR!"
                )

                print(
                    "Error:",
                    repr(error)
                )

    # ==================================================
    # DISCONNECT
    # ==================================================

    async def disconnect(self):

        async with self._lifecycle_lock:

            self._closing = True

            try:

                # Wait for any standalone request
                # before closing the Gemini session.

                async with self._request_lock:

                    context = self.session_context

                    if context is None:

                        self.session = None

                        return

                    print(
                        "\nClosing Gemini session..."
                    )

                    try:

                        await context.__aexit__(
                            None,
                            None,
                            None
                        )

                    except asyncio.CancelledError:

                        raise

                    except Exception as error:

                        print(
                            "Session closing error:",
                            repr(error)
                        )

                    finally:

                        self.session = None
                        self.session_context = None

                        print(
                            "Gemini session closed."
                        )

            finally:

                self._closing = False


# ======================================================
# STANDALONE TEST
# ======================================================

async def main():

    ai = GeminiLive()

    connected = await ai.connect()

    if connected:

        try:

            print(
                "\nZORIN AI BRAIN IS ONLINE!"
            )

            await ai.ask_and_play(
                "Hello Zorin! Introduce yourself."
            )

        finally:

            await ai.disconnect()


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "\nZORIN shutting down..."
        )
