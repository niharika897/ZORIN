import json
import os
from typing import Optional, List, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from device.identity import get_device_identity

BACKEND_URL = os.getenv(
    "ZORIN_BACKEND_URL",
    "http://127.0.0.1:8000"
).rstrip("/")


class ZorinBackendClient:
    """
    Central HTTP Client for ZORIN.
    Allows all clients (Desktop, Android, Web, Scripts) to communicate with the Central Backend.
    Features automatic fallback to the direct CentralMemoryService when running locally,
    guaranteeing zero downtime and reliable offline/startup resilience.
    """

    def __init__(self, backend_url: Optional[str] = None, user_token: Optional[str] = None):
        self.backend_url = (backend_url or BACKEND_URL).rstrip("/")
        self.user_token = user_token or os.getenv("ZORIN_USER_TOKEN")
        if not self.user_token:
            try:
                from memory.database import get_default_user_id
                from backend.auth import create_access_token, get_user_by_id
                uid = get_default_user_id()
                u = get_user_by_id(uid)
                if u:
                    self.user_token = create_access_token(u["user_id"], u["email"])
            except Exception:
                pass

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.user_token:
            headers["Authorization"] = f"Bearer {self.user_token}"
        return headers

    def _http_request(self, endpoint: str, method: str = "GET", data: Optional[dict] = None) -> Optional[dict]:
        url = f"{self.backend_url}{endpoint}"
        payload = json.dumps(data).encode("utf-8") if data else None

        req = Request(url, data=payload, headers=self._get_headers(), method=method)
        try:
            with urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError):
            return None

    # ---------------------------------------------------------
    # MEMORY OPERATIONS (Shared Across All Devices)
    # ---------------------------------------------------------

    def get_memories(self, core_only: bool = False, query: Optional[str] = None) -> List[dict]:
        params = []
        if core_only:
            params.append("core_only=true")
        if query:
            params.append(f"query={query}")
        query_str = f"?{'&'.join(params)}" if params else ""

        res = self._http_request(f"/api/memory{query_str}")
        if res and res.get("success"):
            return res.get("memories", [])

        # Fallback to direct CentralMemoryService if local
        from backend.memory_service import central_memory_service
        from memory.database import get_default_user_id
        uid = get_default_user_id()
        if core_only:
            return central_memory_service.get_core_memories(uid)
        if query:
            return central_memory_service.search_memories(uid, query)
        return central_memory_service.get_all_memories(uid)

    def save_memory(self, category: str, content: str, importance: int = 1, is_core: bool = False) -> dict:
        data = {
            "category": category,
            "content": content,
            "importance": importance,
            "is_core": is_core
        }
        res = self._http_request("/api/memory", method="POST", data=data)
        if res and res.get("success"):
            return res

        # Fallback to direct CentralMemoryService
        from backend.memory_service import central_memory_service
        from memory.database import get_default_user_id
        uid = get_default_user_id()
        return central_memory_service.save_memory(
            user_id=uid,
            category=category,
            content=content,
            importance=importance,
            is_core=is_core,
            source="explicit" if is_core else "conversation"
        )

    def delete_memory(self, memory_id: int, allow_core: bool = False) -> bool:
        endpoint = f"/api/memory/{memory_id}?allow_core={'true' if allow_core else 'false'}"
        res = self._http_request(endpoint, method="DELETE")
        if res is not None:
            return bool(res.get("success"))

        from backend.memory_service import central_memory_service, CoreMemoryProtectedError
        from memory.database import get_default_user_id
        uid = get_default_user_id()
        try:
            return central_memory_service.delete_memory(uid, memory_id, allow_core=allow_core)
        except CoreMemoryProtectedError:
            return False

    def pin_memory(self, memory_id: int) -> bool:
        res = self._http_request(f"/api/memory/{memory_id}/pin", method="PATCH")
        if res is not None:
            return bool(res.get("success"))

        from backend.memory_service import central_memory_service
        from memory.database import get_default_user_id
        return central_memory_service.pin_memory(get_default_user_id(), memory_id)

    def unpin_memory(self, memory_id: int) -> bool:
        res = self._http_request(f"/api/memory/{memory_id}/unpin", method="PATCH")
        if res is not None:
            return bool(res.get("success"))

        from backend.memory_service import central_memory_service
        from memory.database import get_default_user_id
        return central_memory_service.unpin_memory(get_default_user_id(), memory_id)

    def get_memory_context(self) -> str:
        res = self._http_request("/api/memory/context")
        if res and res.get("success"):
            return res.get("persistent_context", "")

        from backend.memory_service import central_memory_service
        from memory.database import get_default_user_id
        return central_memory_service.get_persistent_memory_context(get_default_user_id())

    # ---------------------------------------------------------
    # MULTI-DEVICE MANAGEMENT OPERATIONS
    # ---------------------------------------------------------

    def get_devices(self) -> List[dict]:
        res = self._http_request("/api/devices")
        if res and res.get("success"):
            return res.get("devices", [])

        # Local fallback
        try:
            from backend.device_registry import get_user_devices
            from memory.database import get_default_user_id
            return get_user_devices(get_default_user_id())
        except Exception:
            return []

    def get_nearby_devices(self) -> List[dict]:
        res = self._http_request("/api/devices/available")
        if res and res.get("success"):
            return res.get("devices", [])

        # Local fallback
        try:
            from backend.device_registry import scan_nearby_devices
            return scan_nearby_devices()
        except Exception:
            return []

    def request_pairing(self, server_url: Optional[str] = None) -> dict:
        data = {"server_url": server_url}
        res = self._http_request("/api/devices/pair/request", method="POST", data=data)
        if res and res.get("success"):
            return res

        # Local fallback
        try:
            from backend.device_registry import create_pairing_token
            from memory.database import get_default_user_id
            return create_pairing_token(get_default_user_id(), server_url)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def confirm_pairing(self, pin_or_token: str, identity: dict) -> dict:
        data = {"pin_or_token": pin_or_token, "identity": identity}
        res = self._http_request("/api/devices/pair/confirm", method="POST", data=data)
        if res and res.get("success"):
            return res

        # Local fallback
        try:
            from backend.device_registry import consume_pairing_token
            return consume_pairing_token(pin_or_token, identity)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def connect_device(self, device_id: str) -> bool:
        res = self._http_request(f"/api/devices/{device_id}/connect", method="POST")
        if res and res.get("success"):
            return True

        try:
            from backend.device_registry import set_device_connection_status
            from memory.database import get_default_user_id
            return set_device_connection_status(get_default_user_id(), device_id, "online")
        except Exception:
            return False

    def disconnect_device(self, device_id: str) -> bool:
        res = self._http_request(f"/api/devices/{device_id}/disconnect", method="POST")
        if res and res.get("success"):
            return True

        try:
            from backend.device_registry import set_device_connection_status
            from memory.database import get_default_user_id
            return set_device_connection_status(get_default_user_id(), device_id, "offline")
        except Exception:
            return False

    def remove_device(self, device_id: str) -> bool:
        res = self._http_request(f"/api/devices/{device_id}", method="DELETE")
        if res and res.get("success"):
            return True

        try:
            from backend.device_registry import delete_device
            from memory.database import get_default_user_id
            return delete_device(get_default_user_id(), device_id)
        except Exception:
            return False

    def set_default_device(self, device_id: str) -> bool:
        res = self._http_request(f"/api/devices/{device_id}/default", method="POST")
        if res and res.get("success"):
            return True

        try:
            from backend.device_registry import set_default_device
            from memory.database import get_default_user_id
            return set_default_device(get_default_user_id(), device_id)
        except Exception:
            return False


# Module-level helper for existing code compatibility
_default_client = ZorinBackendClient()


def register_current_device(user_token: Optional[str] = None):
    token = user_token or os.getenv("ZORIN_USER_TOKEN")
    if not token:
        try:
            from memory.database import get_default_user_id
            from backend.auth import create_access_token, get_user_by_id
            uid = get_default_user_id()
            u = get_user_by_id(uid)
            if u:
                token = create_access_token(u["user_id"], u["email"])
        except Exception:
            pass

    identity = get_device_identity()
    url = f"{BACKEND_URL}/devices/register"
    payload = json.dumps(identity).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url,
        data=payload,
        headers=headers,
        method="POST"
    )

    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            print("ZORIN DEVICE REGISTRATION:", result)
            return result
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print("DEVICE REGISTRATION ERROR:", error.code, details)
        return {"success": False, "error": details}
    except (URLError, TimeoutError, OSError) as error:
        print("DEVICE CONNECTION ERROR:", str(error))
        return {"success": False, "error": str(error)}
