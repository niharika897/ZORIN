import asyncio
import json
import os
import signal
import sys
import platform
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse
import websockets

from device.identity import get_device_identity
from device.controller_factory import create_device_controller
from core.tool_router import ToolRouter

# Configuration
BACKEND_HTTP_URL = os.getenv("ZORIN_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
parsed_url = urlparse(BACKEND_HTTP_URL)
ws_scheme = "wss" if parsed_url.scheme == "https" else "ws"
BACKEND_WS_URL = f"{ws_scheme}://{parsed_url.netloc}/ws/device"


class ZorinDeviceAgent:
    """
    Background Device Agent daemon for ZORIN.
    Connects any physical machine (Windows, macOS, Linux) to the ZORIN Multi-Device Hub,
    enabling it to receive and execute remote commands dispatched from any phone, tablet, or web client.
    """

    def __init__(self, backend_url: str = None):
        self.backend_http = (backend_url or BACKEND_HTTP_URL).rstrip("/")
        parsed = urlparse(self.backend_http)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        self.backend_ws = f"{scheme}://{parsed.netloc}/ws/device"

        self.controller = create_device_controller()
        self.tool_router = ToolRouter(controller=self.controller)
        self.identity = get_device_identity(controller=self.controller)
        self.device_id = self.identity["device_id"]
        self.stop_event = asyncio.Event()

    def _get_user_token(self) -> Optional[str]:
        user_token = os.getenv("ZORIN_USER_TOKEN")
        if not user_token:
            try:
                from memory.database import get_default_user_id
                from backend.auth import create_access_token, get_user_by_id
                uid = get_default_user_id()
                u = get_user_by_id(uid)
                if u:
                    user_token = create_access_token(u["user_id"], u["email"])
            except Exception:
                pass
        return user_token

    def register_http(self):
        """Register or announce device presence via HTTP before opening WebSocket."""
        import urllib.request
        import urllib.error

        url = f"{self.backend_http}/devices/register"
        headers = {"Content-Type": "application/json"}
        user_token = self._get_user_token()
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"

        payload = json.dumps(self.identity).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"[ZORIN AGENT] Device registered successfully: {data.get('device', {}).get('device_name')}")
                return True
        except urllib.error.URLError as err:
            print(f"[ZORIN AGENT] Notice: HTTP pre-registration skipped ({err}). Connecting via WebSocket...")
            return False

    async def execute_remote_action(self, action: str, parameters: dict) -> dict:
        """Executes a tool action on this physical device."""
        print(f"\n[ZORIN AGENT] >>> EXECUTING REMOTE COMMAND: {action}")
        print(f"[ZORIN AGENT] Arguments: {parameters}")

        try:
            # Run in thread pool to avoid blocking the event loop
            result = await asyncio.to_thread(
                self.tool_router.execute,
                action,
                **parameters
            )
            print(f"[ZORIN AGENT] <<< RESULT: {result}")
            return result
        except Exception as error:
            print(f"[ZORIN AGENT] !!! EXECUTION ERROR: {error}")
            return {
                "success": False,
                "message": f"Execution error on {platform.node()}: {error}"
            }

    async def run(self):
        print("=" * 60)
        print("          ZORIN MULTI-DEVICE AGENT DAEMON")
        print("=" * 60)
        print(f"Device Name: {self.identity.get('device_name')}")
        print(f"Device ID:   {self.device_id}")
        print(f"Platform:    {self.identity.get('operating_system')} ({self.identity.get('architecture')})")
        print(f"Server URL:  {self.backend_http}")
        print("=" * 60)

        # Register via HTTP first
        self.register_http()

        ws_endpoint = f"{self.backend_ws}/{self.device_id}"
        agent_token = self._get_user_token()
        if agent_token:
            ws_endpoint = f"{ws_endpoint}?token={agent_token}"
        reconnect_delay = 2

        while not self.stop_event.is_set():
            try:
                print(f"\n[ZORIN AGENT] Connecting to Multi-Device Hub at {ws_endpoint}...")
                async with websockets.connect(
                    ws_endpoint,
                    ping_interval=20,
                    ping_timeout=10
                ) as ws:
                    print("[ZORIN AGENT] Connected and READY to receive commands from your phones & devices!")
                    reconnect_delay = 2

                    # Send initial handshake with identity
                    await ws.send(json.dumps({
                        "type": "handshake",
                        "identity": self.identity
                    }))

                    async for raw_message in ws:
                        if self.stop_event.is_set():
                            break

                        try:
                            message = json.loads(raw_message)
                        except json.JSONDecodeError:
                            continue

                        msg_type = message.get("type")

                        if msg_type == "ping":
                            await ws.send(json.dumps({"type": "pong"}))

                        elif msg_type == "execute_command":
                            command_id = message.get("command_id")
                            action = message.get("action", "")
                            params = message.get("parameters", {})

                            # Execute locally
                            result = await self.execute_remote_action(action, params)

                            # Send response back to Hub
                            reply = {
                                "type": "command_result",
                                "command_id": command_id,
                                "device_id": self.device_id,
                                "action": action,
                                "result": result
                            }
                            await ws.send(json.dumps(reply))

            except (websockets.ConnectionClosed, OSError, Exception) as error:
                if self.stop_event.is_set():
                    break
                print(f"[ZORIN AGENT] Connection lost ({error}). Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, 30)

        print("[ZORIN AGENT] Daemon shut down cleanly.")

    def stop(self):
        self.stop_event.set()


async def main():
    agent = ZorinDeviceAgent()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, agent.stop)
        except NotImplementedError:
            # Signal handling on Windows
            pass

    try:
        await agent.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        agent.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting ZORIN Device Agent.")
