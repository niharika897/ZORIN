import os
import subprocess
import webbrowser
import platform
from pathlib import Path

from device.base import DeviceController


class DarwinDeviceController(DeviceController):
    """
    macOS Device Controller for ZORIN.
    Uses 'open -a' and AppleScript for launching apps and URLs.
    """

    def __init__(self):
        self.app_aliases = {
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "safari": "Safari",
            "vs code": "Visual Studio Code",
            "vscode": "Visual Studio Code",
            "code": "Visual Studio Code",
            "terminal": "Terminal",
            "finder": "Finder",
            "spotify": "Spotify",
            "calculator": "Calculator",
            "notes": "Notes",
            "slack": "Slack",
            "discord": "Discord",
        }

    def open_app(self, app_name: str) -> dict:
        app_name = str(app_name).strip()
        normalized = app_name.lower()
        target_name = self.app_aliases.get(normalized, app_name)

        try:
            # Use macOS 'open -a' command
            cmd = ["open", "-a", target_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"Successfully launched {target_name} on macOS.",
                    "app_name": target_name,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to launch {target_name}: {result.stderr.strip() or 'App not found'}",
                    "app_name": target_name,
                }
        except Exception as error:
            return {
                "success": False,
                "message": f"Error opening {app_name} on macOS: {error}",
                "app_name": app_name,
            }

    def open_website(self, website: str) -> dict:
        url = str(website).strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            if "." in url:
                url = f"https://{url}"
            else:
                url = f"https://www.google.com/search?q={url}"

        try:
            webbrowser.open(url)
            return {
                "success": True,
                "message": f"Opened website: {url}",
                "url": url,
            }
        except Exception as error:
            return {
                "success": False,
                "message": f"Failed to open website on macOS: {error}",
                "url": url,
            }

    def get_device_info(self) -> dict:
        return {
            "device_name": platform.node(),
            "operating_system": "macOS",
            "architecture": platform.machine(),
            "client_type": "desktop",
            "capabilities": [
                "open_app",
                "open_website",
                "create_website",
                "remote_execution",
            ],
        }
