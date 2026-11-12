import os
import shutil
import subprocess
import webbrowser
import platform
from pathlib import Path

from device.base import DeviceController


class LinuxDeviceController(DeviceController):
    """
    Linux Device Controller for ZORIN.
    Uses 'gtk-launch', 'xdg-open', or desktop entry search.
    """

    def __init__(self):
        self.app_aliases = {
            "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
            "google chrome": ["google-chrome", "google-chrome-stable", "chromium"],
            "firefox": ["firefox"],
            "vs code": ["code"],
            "vscode": ["code"],
            "code": ["code"],
            "terminal": ["gnome-terminal", "x-terminal-emulator", "konsole", "xfce4-terminal"],
            "files": ["nautilus", "dolphin", "thunar"],
            "calculator": ["gnome-calculator", "kcalc"],
            "vlc": ["vlc"],
            "spotify": ["spotify"],
        }

    def open_app(self, app_name: str) -> dict:
        app_name = str(app_name).strip()
        normalized = app_name.lower()

        candidates = self.app_aliases.get(normalized, [normalized])

        for candidate in candidates:
            binary_path = shutil.which(candidate)
            if binary_path:
                try:
                    subprocess.Popen(
                        [binary_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    return {
                        "success": True,
                        "message": f"Successfully launched {candidate} on Linux.",
                        "app_name": candidate,
                    }
                except Exception as error:
                    return {
                        "success": False,
                        "message": f"Error launching {candidate}: {error}",
                        "app_name": candidate,
                    }

        # Try gtk-launch as fallback
        if shutil.which("gtk-launch"):
            try:
                result = subprocess.run(["gtk-launch", normalized], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return {
                        "success": True,
                        "message": f"Successfully launched {app_name} via gtk-launch.",
                        "app_name": app_name,
                    }
            except Exception:
                pass

        return {
            "success": False,
            "message": f"Application '{app_name}' not found on this Linux system.",
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
                "message": f"Failed to open website on Linux: {error}",
                "url": url,
            }

    def get_device_info(self) -> dict:
        return {
            "device_name": platform.node(),
            "operating_system": "Linux",
            "architecture": platform.machine(),
            "client_type": "desktop",
            "capabilities": [
                "open_app",
                "open_website",
                "create_website",
                "remote_execution",
            ],
        }
