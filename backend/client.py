import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from device.identity import get_device_identity

BACKEND_URL = os.getenv(
    "ZORIN_BACKEND_URL",
    "http://127.0.0.1:8000"
).rstrip("/")


def register_current_device():
    identity = get_device_identity()
    url = f"{BACKEND_URL}/devices/register"
    payload = json.dumps(identity).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
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