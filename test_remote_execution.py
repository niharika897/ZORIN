import asyncio
import threading
import time
import json
import uvicorn
import websockets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.server import app
from backend.device_hub import device_hub
from backend.auth import create_access_token, get_user_by_email, decode_token
from device.agent import ZorinDeviceAgent


class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.config = uvicorn.Config(app, host="127.0.0.1", port=8002, log_level="warning")
        self.server = uvicorn.Server(self.config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


async def assert_ws_rejected(url: str, description: str):
    rejected = False
    try:
        async with websockets.connect(url, ping_interval=None, close_timeout=2) as ws:
            await ws.recv()
    except Exception as err:
        rejected = True
        print(f"       [REJECTED AS EXPECTED] {description} -> {type(err).__name__}")
    assert rejected, f"Security failure: {description} was not rejected!"


async def run_loop_test():
    print("=" * 60)
    print("   TESTING DEVICE & CLIENT WEBSOCKET SECURITY & REMOTE DISPATCH")
    print("=" * 60)

    user = get_user_by_email("niharika@zorin.ai")
    assert user is not None, "Primary user must exist for testing"
    valid_token = create_access_token(user["user_id"], user["email"])
    expired_token = create_access_token(user["user_id"], user["email"], expires_in=-30)

    # 1. Device WebSocket without token must be rejected
    print("[TEST] 1. Device WebSocket without token ...")
    await assert_ws_rejected(
        "ws://127.0.0.1:8002/ws/device/dev_no_token",
        "Device WebSocket without token"
    )
    assert not device_hub.is_device_online("dev_no_token")

    # 2. Device WebSocket with invalid token must be rejected
    print("[TEST] 2. Device WebSocket with invalid token ...")
    await assert_ws_rejected(
        "ws://127.0.0.1:8002/ws/device/dev_bad_token?token=bad.token.signature",
        "Device WebSocket with invalid token"
    )
    assert not device_hub.is_device_online("dev_bad_token")

    # 3. Device WebSocket with expired token must be rejected
    print("[TEST] 3. Device WebSocket with expired token ...")
    await assert_ws_rejected(
        f"ws://127.0.0.1:8002/ws/device/dev_expired?token={expired_token}",
        "Device WebSocket with expired token"
    )
    assert not device_hub.is_device_online("dev_expired")

    # 4. Client WebSocket without token must be rejected
    print("[TEST] 4. Client WebSocket without token ...")
    await assert_ws_rejected(
        "ws://127.0.0.1:8002/ws/client/client_no_token",
        "Client WebSocket without token"
    )

    # 5. Client WebSocket with valid token must connect
    print("[TEST] 5. Client WebSocket with valid token ...")
    async with websockets.connect(
        f"ws://127.0.0.1:8002/ws/client/client_valid?token={valid_token}",
        ping_interval=None
    ) as client_ws:
        await client_ws.send(json.dumps({"type": "ping"}))
        resp = await client_ws.recv()
        data = json.loads(resp)
        assert data.get("type") == "pong"
        print("       Client WebSocket connected and ping-pong verified!")

    # 6. Device WebSocket with valid token must connect
    print("[TEST] 6. Device Agent connecting with valid token ...")
    agent = ZorinDeviceAgent(backend_url="http://127.0.0.1:8002")
    agent_task = asyncio.create_task(agent.run())

    # Wait for connection
    await asyncio.sleep(2)
    assert device_hub.is_device_online(agent.device_id), "Agent should be marked online in hub."
    print(f"       Agent successfully connected via WebSocket: {agent.device_id}")

    # 7. Dispatch remote command to connected device agent
    print("[TEST] 7. Dispatching remote 'open_website' command to device agent...")
    dispatch_result = await device_hub.dispatch_command(
        user_id=user["user_id"],
        target_device_id=agent.device_id,
        action="open_website",
        parameters={"website": "https://www.google.com"},
        timeout=10.0
    )

    print(f"       Dispatch result: {dispatch_result}")
    assert dispatch_result.get("success") is True, f"Command execution failed: {dispatch_result}"
    print("       Remote execution acknowledgment received successfully!")

    # Stop agent gracefully
    agent.stop()
    try:
        await asyncio.wait_for(agent_task, timeout=2.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        agent_task.cancel()

    # 8. Token persistence across restart check
    print("[TEST] 8. Pre-restart token validity verification ...")
    decoded = decode_token(valid_token)
    assert decoded["user_id"] == user["user_id"]
    print("       Pre-restart token decoded and signature verified successfully!")

    print("=" * 60)
    print("   ALL DEVICE & CLIENT WEBSOCKET SECURITY TESTS PASSED!")
    print("=" * 60)


def main():
    server = ServerThread()
    server.start()
    time.sleep(2)

    try:
        asyncio.run(run_loop_test())
    finally:
        server.stop()
        server.join(timeout=3)


if __name__ == "__main__":
    main()
