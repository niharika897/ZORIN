import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from device.agent import ZorinDeviceAgent


def main():
    agent = ZorinDeviceAgent()
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\nStopping ZORIN Device Agent.")


if __name__ == "__main__":
    main()
