import threading
import time
import urllib.request
import json
import uvicorn
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.server import app


class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.config = uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="warning")
        self.server = uvicorn.Server(self.config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def test_api():
    print("=" * 60)
    print("      TESTING ZORIN MULTI-DEVICE FASTAPI SERVER")
    print("=" * 60)
    server_thread = ServerThread()
    server_thread.start()
    time.sleep(2)  # Wait for server to start

    base_url = "http://127.0.0.1:8001"

    try:
        # 1. Health check
        print("[TEST] 1. GET /health ...")
        with urllib.request.urlopen(f"{base_url}/health", timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"       Health status: {data['status']}")
            assert data["status"] == "healthy"

        # 2. Static HTML check
        print("[TEST] 2. GET / (PWA Frontend) ...")
        with urllib.request.urlopen(f"{base_url}/", timeout=5) as resp:
            content = resp.read().decode()
            assert "ZORIN" in content
            assert "aiOrb" in content
            print(f"       Frontend HTML loaded ({len(content)} bytes).")

        # 3. PWA Manifest check
        print("[TEST] 3. GET /manifest.json ...")
        with urllib.request.urlopen(f"{base_url}/manifest.json", timeout=5) as resp:
            manifest = json.loads(resp.read().decode())
            assert manifest["short_name"] == "ZORIN"
            print(f"       PWA Manifest verified: {manifest['name']}")

        # 4. Security Check: Unauthenticated request must return 401 Unauthorized
        print("[TEST] 4. GET /api/devices (unauthenticated -> expect 401) ...")
        unauth_blocked = False
        try:
            with urllib.request.urlopen(f"{base_url}/api/devices", timeout=5) as resp:
                pass
        except urllib.error.HTTPError as err:
            if err.code == 401:
                unauth_blocked = True
                print("       Unauthenticated request correctly rejected with HTTP 401 Unauthorized.")
            else:
                raise
        assert unauth_blocked, "Security Failure: Unauthenticated request was not rejected with 401!"

        # 5. User Auth Check: Login to acquire Bearer token
        print("[TEST] 5. POST /api/auth/login ...")
        login_payload = json.dumps({"email": "niharika@zorin.ai", "password": "password123"}).encode()
        req = urllib.request.Request(f"{base_url}/api/auth/login", data=login_payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            auth_res = json.loads(resp.read().decode())
            assert auth_res["success"] is True
            token = auth_res["token"]
            print(f"       Login successful. Token generated: {token[:20]}...")

        # 6. Authenticated Device listing API check
        print("[TEST] 6. GET /api/devices (authenticated with Bearer token) ...")
        auth_req = urllib.request.Request(
            f"{base_url}/api/devices",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(auth_req, timeout=5) as resp:
            dev_data = json.loads(resp.read().decode())
            print(f"       Registered devices count: {dev_data['count']}")
            assert dev_data["success"] is True

        # 7. Server Restart Token Validity Check
        print("[TEST] 7. Restart server and verify pre-restart token remains valid ...")
        server_thread.stop()
        server_thread.join(timeout=3)
        time.sleep(1)

        server_thread = ServerThread()
        server_thread.start()
        time.sleep(2)

        # Re-verify the pre-restart token against the newly started server instance
        auth_req_restarted = urllib.request.Request(
            f"{base_url}/api/devices",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(auth_req_restarted, timeout=5) as resp:
            dev_data_restarted = json.loads(resp.read().decode())
            assert dev_data_restarted["success"] is True
            print("       Pre-restart token successfully validated on restarted server!")

        print("=" * 60)
        print("      ALL API & STATIC PWA TESTS PASSED!")
        print("=" * 60)

    finally:
        server_thread.stop()
        server_thread.join(timeout=3)


if __name__ == "__main__":
    test_api()
