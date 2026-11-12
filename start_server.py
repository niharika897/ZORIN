import socket
import uvicorn
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def get_local_ip():
    """Finds the local network IP address so phones on same Wi-Fi can connect."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def main():
    local_ip = get_local_ip()
    port = 8000

    print("=" * 66)
    print("        🚀 ZORIN MULTI-DEVICE SERVER INITIALIZING")
    print("=" * 66)
    print(f"  ● Desktop / Laptop Access: http://localhost:{port}")
    print(f"  ● Phone / Tablet Access:   http://{local_ip}:{port}")
    print("=" * 66)
    print("  TIP: To access on iPhone / Android:")
    print(f"       1. Connect your phone to the same Wi-Fi network.")
    print(f"       2. Open Safari / Chrome on your phone and go to:")
    print(f"          http://{local_ip}:{port}")
    print(f"       3. Tap 'Share' -> 'Add to Home Screen' to install as App!")
    print("=" * 66)
    print("Starting server on 0.0.0.0:8000...\n")

    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
