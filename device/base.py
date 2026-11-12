from abc import ABC, abstractmethod


class DeviceController(ABC):
    """
    Common interface for device-specific ZORIN controllers.

    Each device implements its own application launching,
    website opening and device capabilities.
    """

    @abstractmethod
    def open_app(self, app_name: str) -> dict:
        """Open an installed application on this device."""
        raise NotImplementedError

    @abstractmethod
    def open_website(self, website: str) -> dict:
        """Open a website using this device's browser."""
        raise NotImplementedError

    @abstractmethod
    def get_device_info(self) -> dict:
        """Return information about this device and its capabilities."""
        raise NotImplementedError