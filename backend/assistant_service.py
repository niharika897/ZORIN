import asyncio
import json
import os
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY
from backend.database import get_connection, current_timestamp
from backend.device_registry import get_user_devices, get_default_device
from backend.device_hub import device_hub

# Models in order of priority
MODEL_CANDIDATES = [
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-2.5-flash"
]


class MultiDeviceAssistantService:
    """
    Central AI service powering ZORIN across all devices.
    Performs multi-turn conversation with user memory injection and
    routes physical tool executions (app launching, web opening, site generation)
    to the appropriate target device node across the network.
    """

    def __init__(self):
        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(api_version="v1beta")
        )

    def _get_tools(self) -> list:
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="open_app",
                        description=(
                            "Open an installed application (Chrome, VS Code, Spotify, Notepad, Calculator, WhatsApp, etc.) "
                            "on a registered target device (e.g., the user's laptop or PC)."
                        ),
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "app_name": {
                                    "type": "STRING",
                                    "description": "Name of the application to open."
                                },
                                "target_device": {
                                    "type": "STRING",
                                    "description": "Optional name or ID of the device where the app should open. Leave blank for default laptop/desktop."
                                }
                            },
                            "required": ["app_name"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="open_website",
                        description="Open a website URL in the browser on the user's target device.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "website": {
                                    "type": "STRING",
                                    "description": "The URL or name of the website (e.g., 'https://github.com' or 'YouTube')."
                                },
                                "target_device": {
                                    "type": "STRING",
                                    "description": "Optional name or ID of the device. Leave blank for default."
                                }
                            },
                            "required": ["website"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="create_website",
                        description="Create a real HTML/CSS/JS website project and open it on the user's target PC.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "project_name": {
                                    "type": "STRING",
                                    "description": "Name for the project directory."
                                },
                                "html": {
                                    "type": "STRING",
                                    "description": "Complete HTML code."
                                },
                                "css": {
                                    "type": "STRING",
                                    "description": "Optional CSS styling."
                                },
                                "javascript": {
                                    "type": "STRING",
                                    "description": "Optional JavaScript logic."
                                },
                                "target_device": {
                                    "type": "STRING",
                                    "description": "Optional target device name."
                                }
                            },
                            "required": ["project_name", "html"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="list_user_devices",
                        description="List all devices currently paired with the user's account and their online status.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {}
                        }
                    ),
                    types.FunctionDeclaration(
                        name="save_memory",
                        description="Save an important fact, preference, or detail to the user's central persistent memory across all devices.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "content": {
                                    "type": "STRING",
                                    "description": "The exact fact or detail to remember permanently."
                                },
                                "category": {
                                    "type": "STRING",
                                    "description": "Category (preference, personal, project, general)."
                                },
                                "is_core": {
                                    "type": "BOOLEAN",
                                    "description": "Set to true if user explicitly asks to save as core or permanently."
                                }
                            },
                            "required": ["content"]
                        }
                    )
                ]
            )
        ]

    def _resolve_target_device_id(self, user_id: str, requested_device_name: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
        """
        Resolves a user-friendly device name (or default) to (device_id, device_name).
        """
        devices = get_user_devices(user_id)
        if not devices:
            return None, None

        if requested_device_name and requested_device_name.strip():
            query = requested_device_name.strip().lower()
            for dev in devices:
                if query in dev["device_name"].lower() or query in dev["device_id"].lower() or query in dev["operating_system"].lower():
                    return dev["device_id"], dev["device_name"]

        # If not specified, look for default device
        for dev in devices:
            if dev.get("is_default"):
                return dev["device_id"], dev["device_name"]

        # Otherwise pick the first online desktop device
        for dev in devices:
            if dev.get("is_online") and dev.get("client_type") == "desktop":
                return dev["device_id"], dev["device_name"]

        # Fallback to first available device
        return devices[0]["device_id"], devices[0]["device_name"]

    async def execute_tool_call(self, user_id: str, tool_name: str, args: dict) -> dict:
        """
        Executes a tool call by either handling it locally or routing it across the network
        to the appropriate physical device agent.
        """
        if tool_name == "list_user_devices":
            devices = get_user_devices(user_id)
            return {
                "success": True,
                "count": len(devices),
                "devices": [
                    {
                        "name": d["device_name"],
                        "os": d["operating_system"],
                        "status": "Online" if d["is_online"] else "Offline",
                        "is_default": bool(d.get("is_default"))
                    }
                    for d in devices
                ]
            }

        if tool_name == "save_memory":
            from backend.memory_service import central_memory_service
            res = central_memory_service.save_memory(
                user_id=user_id,
                category=args.get("category", "general"),
                content=args.get("content", ""),
                importance=args.get("importance", 2),
                is_core=args.get("is_core", False),
                source="explicit" if args.get("is_core") else "conversation"
            )
            return {
                "success": True,
                "message": f"Successfully remembered: {args.get('content')}",
                "memory_id": res["id"]
            }

        target_name_req = args.pop("target_device", None)
        target_device_id, resolved_device_name = self._resolve_target_device_id(user_id, target_name_req)

        if not target_device_id:
            return {
                "success": False,
                "message": "No registered devices found for this account. Please connect your computer using the ZORIN Device Agent."
            }

        # Dispatch command via DeviceConnectionHub
        result = await device_hub.dispatch_command(
            user_id=user_id,
            target_device_id=target_device_id,
            action=tool_name,
            parameters=args
        )

        # Fallback to local execution if remote WebSocket tunnel is offline
        if result.get("offline") or not result.get("success"):
            try:
                from core.tool_router import ToolRouter
                local_router = ToolRouter()
                local_res = local_router.execute(tool_name, **args)
                if local_res and local_res.get("success"):
                    local_res["target_device_name"] = resolved_device_name
                    return local_res
            except Exception as local_err:
                print("Local tool execution fallback note:", local_err)

        result["target_device_name"] = resolved_device_name
        return result

    def _get_user_context(self, user_id: str, user_profile: dict) -> str:
        """Loads persistent memories and system instructions for the specific user from Central Memory Service."""
        from backend.memory_service import central_memory_service
        memory_str = central_memory_service.get_persistent_memory_context(user_id) or "No saved memories yet."
        past_conv = central_memory_service.get_past_conversation_context(user_id, limit=20)

        devices = get_user_devices(user_id)
        dev_summary = []
        for d in devices:
            status_badge = "ONLINE" if d["is_online"] else "OFFLINE"
            default_badge = " (DEFAULT)" if d.get("is_default") else ""
            dev_summary.append(f"- {d['device_name']} [{d['operating_system']}, {d['client_type']}] -> {status_badge}{default_badge}")

        device_str = "\n".join(dev_summary) if dev_summary else "No devices registered yet."
        display_name = user_profile.get("display_name", "User")

        instructions = (
            f"You are ZORIN, a premier multi-device personal AI assistant. "
            f"You are talking with {display_name}.\n\n"
            f"USER'S REGISTERED DEVICES:\n{device_str}\n\n"
            f"SAVED USER MEMORIES & PREFERENCES:\n{memory_str}\n\n"
            f"RECENT CONVERSATIONS:\n{past_conv}\n\n"
            f"GUIDELINES:\n"
            f"1. You are accessible across any device (phones, tablets, laptops, desktops, web).\n"
            f"2. When the user asks you to remember or save information (e.g. 'Remember my favourite colour is blue', 'Remember my dog is Max'), ALWAYS invoke the save_memory tool.\n"
            f"3. Use the SAVED USER MEMORIES above to answer questions about the user's preferences, background, and facts.\n"
            f"4. When the user asks to launch an application, open a website, or create a project, always call the appropriate tool.\n"
            f"5. Speak naturally, directly, and concisely."
        )
        return instructions

    async def chat(
        self,
        user_id: str,
        user_profile: dict,
        message: str,
        conversation_id: Optional[str] = None,
        origin_device_id: Optional[str] = None
    ) -> dict:
        """
        Process a user conversation turn with multi-device tool handling.
        """
        system_instruction = self._get_user_context(user_id, user_profile)
        tools = self._get_tools()

        # Build prompt contents
        # Fetch previous 6 messages for context
        history_contents = []
        if conversation_id:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC LIMIT 10",
                    (conversation_id,)
                ).fetchall()
                for r in rows:
                    role = "user" if r["role"] == "user" else "model"
                    history_contents.append(
                        types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=r["content"])]
                        )
                    )

        # Append current user message
        history_contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)]
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools,
            temperature=0.7,
        )

        # Call Gemini with fallback
        response = None
        used_model = None
        last_error = None

        for model_name in MODEL_CANDIDATES:
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model_name,
                    contents=history_contents,
                    config=config
                )
                used_model = model_name
                break
            except Exception as err:
                last_error = err
                print(f"[ZORIN ASSISTANT] Model {model_name} failed ({err}). Trying fallback...")

        if not response:
            return {
                "success": False,
                "text": f"I had trouble connecting to the AI brain. Error: {last_error}",
                "tool_results": []
            }

        tool_results = []

        # Check for function calls
        if response.function_calls:
            for call in response.function_calls:
                call_name = call.name
                call_args = dict(call.args or {})
                print(f"[ZORIN CHAT] Function call requested: {call_name} with {call_args}")

                exec_result = await self.execute_tool_call(user_id, call_name, call_args)
                tool_results.append({
                    "tool": call_name,
                    "args": call_args,
                    "result": exec_result
                })

            # Send tool response back to Gemini for final spoken reply
            followup_parts = []
            for tr in tool_results:
                followup_parts.append(
                    types.Part.from_function_response(
                        name=tr["tool"],
                        response={"result": tr["result"]}
                    )
                )

            history_contents.append(response.candidates[0].content)
            history_contents.append(
                types.Content(role="tool", parts=followup_parts)
            )

            try:
                followup_res = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=used_model,
                    contents=history_contents,
                    config=config
                )
                final_text = followup_res.text or "Command executed successfully."
            except Exception:
                final_text = f"I've executed the command on your device."
        else:
            final_text = response.text or ""

        # Extract and save memories asynchronously in background if user revealed preferences
        asyncio.create_task(self._extract_memory_background(user_id, message))

        # Persist conversation & messages
        self._save_interaction(user_id, conversation_id, message, final_text, origin_device_id)

        return {
            "success": True,
            "text": final_text,
            "tool_results": tool_results,
            "model": used_model
        }

    def _save_interaction(self, user_id: str, conversation_id: Optional[str], user_text: str, ai_text: str, device_id: Optional[str]):
        try:
            with get_connection() as conn:
                now = current_timestamp()
                numeric_cid = None
                try:
                    if conversation_id and str(conversation_id).isdigit():
                        numeric_cid = int(conversation_id)
                except Exception:
                    pass

                if numeric_cid:
                    row = conn.execute("SELECT id FROM conversations WHERE id = ?", (numeric_cid,)).fetchone()
                    if not row:
                        conn.execute("""
                            INSERT INTO conversations (id, user_id, title, device_id, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (numeric_cid, user_id, user_text[:30] + "...", device_id, now, now))
                    else:
                        conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, numeric_cid))
                else:
                    cursor = conn.execute("""
                        INSERT INTO conversations (user_id, title, device_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, user_text[:30] + "...", device_id, now, now))
                    numeric_cid = cursor.lastrowid

                # Save user message
                conn.execute("""
                    INSERT INTO messages (conversation_id, user_id, role, content, device_id, created_at)
                    VALUES (?, ?, 'user', ?, ?, ?)
                """, (numeric_cid, user_id, user_text, device_id, now))

                # Save assistant message
                conn.execute("""
                    INSERT INTO messages (conversation_id, user_id, role, content, device_id, created_at)
                    VALUES (?, ?, 'assistant', ?, ?, ?)
                """, (numeric_cid, user_id, ai_text, device_id, now))

                conn.commit()
        except Exception as e:
            print(f"Error saving conversation: {e}")

    async def _extract_memory_background(self, user_id: str, text: str):
        """Simple lightweight memory extractor for preferences and facts."""
        lower = text.lower()
        pref_triggers = ["my name is ", "i like ", "i love ", "i prefer ", "my favorite ", "remember that "]
        for trigger in pref_triggers:
            if trigger in lower:
                fact = text.strip()
                now = current_timestamp()
                try:
                    with get_connection() as conn:
                        conn.execute("""
                            INSERT INTO memories (user_id, category, content, importance, is_core, created_at, updated_at)
                            VALUES (?, 'preference', ?, 2, 1, ?, ?)
                        """, (user_id, fact, now, now))
                        conn.commit()
                        print(f"[ZORIN MEMORY] Saved memory for {user_id}: {fact}")
                except Exception:
                    pass
                break


# Singleton service instance
assistant_service = MultiDeviceAssistantService()
