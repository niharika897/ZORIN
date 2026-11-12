import platform


def create_device_controller(system=None):
    operating_system = (
        system or platform.system()
    ).strip().lower()

    if operating_system == "windows":
        from device.windows.app_launcher import WindowsDeviceController
        return WindowsDeviceController()

    if operating_system == "darwin":
        from device.darwin.app_launcher import DarwinDeviceController
        return DarwinDeviceController()

    if operating_system == "linux":
        from device.linux.app_launcher import LinuxDeviceController
        return LinuxDeviceController()

    if operating_system in ("android", "ios"):
        # For mobile platforms, a Web/Generic controller handles URL openings and returns device info
        from device.base import DeviceController

        class MobileDeviceController(DeviceController):
            def open_app(self, app_name: str) -> dict:
                return {
                    "success": False,
                    "message": f"Direct app launching on {operating_system} is limited by mobile sandbox; please open {app_name} from your home screen.",
                    "app_name": app_name,
                }

            def open_website(self, website: str) -> dict:
                import webbrowser
                url = str(website).strip()
                if not (url.startswith("http://") or url.startswith("https://")):
                    url = f"https://{url}" if "." in url else f"https://www.google.com/search?q={url}"
                webbrowser.open(url)
                return {"success": True, "message": f"Opened {url}", "url": url}

            def get_device_info(self) -> dict:
                return {
                    "device_name": platform.node() or f"{operating_system.capitalize()} Client",
                    "operating_system": operating_system.capitalize(),
                    "architecture": platform.machine(),
                    "client_type": "mobile",
                    "capabilities": ["open_website", "voice_chat", "mobile_pwa"],
                }

        return MobileDeviceController()

    raise RuntimeError(
        f"Unsupported operating system: {operating_system}"
    )
