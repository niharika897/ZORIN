
import os
import re
import shutil
import subprocess
import webbrowser
import difflib
import platform

from pathlib import Path

from device.base import DeviceController


class WindowsDeviceController(DeviceController):

    def __init__(self):
        self._app_index = None

        self.app_aliases = {
            "google chrome": "chrome",
            "chrome browser": "chrome",
            "browser": "chrome",
            "visual studio code": "code",
            "vs code": "code",
            "vscode": "code",
            "code editor": "code",
            "file explorer": "explorer",
            "windows explorer": "explorer",
            "calc": "calculator",
            "command prompt": "cmd",
            "terminal": "windows terminal",
            "whatsapp": "whatsapp",
            "whatsapp desktop": "whatsapp",
            "whats app": "whatsapp",
            "whatsapp app": "whatsapp",
            "ms word": "word",
            "microsoft word": "word",
            "ms excel": "excel",
            "microsoft excel": "excel",
            "ms powerpoint": "powerpoint",
            "microsoft powerpoint": "powerpoint",
            "vs": "code",
        }

        self.app_commands = {
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "explorer": ["explorer.exe"],
            "cmd": ["cmd.exe"],
            "powershell": ["powershell.exe"],
            "windows terminal": ["wt.exe"],
        }

        self.app_paths = {
            "chrome": [
                Path(os.environ.get("PROGRAMFILES", "")) /
                "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "")) /
                "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) /
                "Google/Chrome/Application/chrome.exe",
            ],
            "code": [
                Path(os.environ.get("LOCALAPPDATA", "")) /
                "Programs/Microsoft VS Code/Code.exe",
                Path(os.environ.get("PROGRAMFILES", "")) /
                "Microsoft VS Code/Code.exe",
            ],
        }

        self.website_aliases = {
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com",
            "github": "https://github.com",
            "gmail": "https://mail.google.com",
            "whatsapp": "https://web.whatsapp.com",
            "linkedin": "https://www.linkedin.com",
            "chatgpt": "https://chatgpt.com",
            "stackoverflow": "https://stackoverflow.com",
            "spotify": "https://open.spotify.com",
        }

    @staticmethod
    def normalize_name(name):
        name = str(name).lower().strip()
        name = re.sub(r"\.(exe|lnk|url)$", "", name)
        name = re.sub(r"[^a-z0-9 ]", " ", name)
        name = re.sub(r"\s+", " ", name)
        return name.strip()

    def discover_applications(self):

        if self._app_index is not None:
            return self._app_index

        applications = {}

        def add_application(name, path):
            name = self.normalize_name(name)

            if name and name not in applications:
                applications[name] = path

        # 1. Start Menu shortcuts
        locations = [
            Path(os.environ.get("APPDATA", "")) /
            "Microsoft/Windows/Start Menu/Programs",

            Path(os.environ.get("PROGRAMDATA", "")) /
            "Microsoft/Windows/Start Menu/Programs",
        ]

        for folder in locations:
            if not folder.is_dir():
                continue

            try:
                for shortcut in folder.rglob("*"):
                    if shortcut.suffix.lower() in (".lnk", ".url"):
                        add_application(shortcut.stem, shortcut)
            except OSError:
                continue

        # 2. Windows Registry
        try:
            import winreg

            registry_locations = [
                (
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\App Paths"
                ),
                (
                    winreg.HKEY_LOCAL_MACHINE,
                    r"Software\Microsoft\Windows\CurrentVersion\App Paths"
                ),
            ]

            for root, registry_path in registry_locations:
                try:
                    with winreg.OpenKey(root, registry_path) as registry:
                        index = 0

                        while True:
                            try:
                                key_name = winreg.EnumKey(registry, index)
                                index += 1

                                with winreg.OpenKey(
                                    registry, key_name
                                ) as app_key:

                                    executable, _ = winreg.QueryValueEx(
                                        app_key, ""
                                    )

                                    executable = str(executable).strip('"')

                                    if Path(executable).is_file():
                                        add_application(
                                            Path(key_name).stem,
                                            Path(executable)
                                        )

                            except OSError:
                                break

                except OSError:
                    continue

        except ImportError:
            pass

        # 3. Known application locations
        for app_name, paths in self.app_paths.items():
            for path in paths:
                if path.is_file():
                    add_application(app_name, path)

        # 4. PATH applications
        for app_name, command in self.app_commands.items():
            executable = shutil.which(command[0])

            if executable:
                add_application(app_name, Path(executable))

        self._app_index = applications

        print(
            f"ZORIN WINDOWS DISCOVERY: Found "
            f"{len(applications)} applications."
        )

        return applications

    def open_app(self, app_name):

        original_name = str(app_name).strip()

        if not original_name:
            return {
                "success": False,
                "message": "Please specify an application."
            }

        name = self.normalize_name(original_name)
        name = self.app_aliases.get(name, name)

        try:
            # Direct Windows URI protocols (e.g. WhatsApp, Microsoft Store apps)
            if name in ("whatsapp", "whatsapp desktop", "whatsapp app", "whats app"):
                opened = False
                try:
                    subprocess.Popen(["cmd.exe", "/c", "start", "whatsapp:"], shell=True)
                    opened = True
                except Exception:
                    try:
                        os.startfile("whatsapp:")
                        opened = True
                    except Exception:
                        opened = False

                if opened:
                    return {
                        "success": True,
                        "message": f"Opened {original_name} application."
                    }
                else:
                    webbrowser.open("https://web.whatsapp.com")
                    return {
                        "success": True,
                        "message": "Opened WhatsApp Web in your default browser."
                    }

            # Direct Windows commands
            if name in self.app_commands:
                subprocess.Popen(self.app_commands[name])

                return {
                    "success": True,
                    "message": f"Opened {original_name}."
                }

            # Known installation paths
            if name in self.app_paths:
                for path in self.app_paths[name]:
                    if path.is_file():
                        os.startfile(str(path))

                        return {
                            "success": True,
                            "message": f"Opened {original_name}."
                        }

            # Discover installed applications
            applications = self.discover_applications()
            target = applications.get(name)

            # Partial matching
            if target is None:
                matches = [
                    app for app in applications
                    if name == app or name in app or app in name
                ]

                if len(matches) == 1:
                    target = applications[matches[0]]

            # Similar-name matching
            if target is None:
                matches = difflib.get_close_matches(
                    name,
                    list(applications.keys()),
                    n=1,
                    cutoff=0.78
                )

                if matches:
                    target = applications[matches[0]]

            # Launch discovered application
            if target is not None:
                target = Path(target)

                if target.exists():
                    os.startfile(str(target))

                    return {
                        "success": True,
                        "message": f"Opened {original_name}.",
                        "application_path": str(target)
                    }

            # PATH fallback
            executable = shutil.which(name)

            if executable:
                subprocess.Popen([executable])

                return {
                    "success": True,
                    "message": f"Opened {original_name}."
                }

            return {
                "success": False,
                "message": (
                    f"I couldn't find {original_name} "
                    "among the installed applications."
                )
            }

        except Exception as error:
            return {
                "success": False,
                "message": f"Could not open {original_name}: {error}"
            }

    def open_website(self, website):

        website = str(website).strip().lower()

        if not website:
            return {
                "success": False,
                "message": "No website was specified."
            }

        url = self.website_aliases.get(website)

        if not url:
            if website.startswith(("https://", "http://")):
                url = website
            else:
                url = "https://" + website

        if not re.match(
            r"^https?://[a-zA-Z0-9.-]+(?::\d+)?(?:/.*)?$",
            url
        ):
            return {
                "success": False,
                "message": "The website address is invalid."
            }

        try:
            opened = webbrowser.open(url)

            return {
                "success": bool(opened),
                "message": (
                    f"Opening {website}."
                    if opened
                    else f"Could not open {website}."
                ),
                "url": url
            }

        except Exception as error:
            return {
                "success": False,
                "message": f"Website opening failed: {error}"
            }

    def get_device_info(self):

        return {
            "device_name": platform.node(),
            "operating_system": platform.system(),
            "operating_system_version": platform.version(),
            "architecture": platform.machine(),
            "capabilities": [
                "open_app",
                "open_website",
                "discover_applications"
            ]
        }