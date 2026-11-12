import platform


def create_device_controller(system=None):

    operating_system = (
        system or platform.system()
    ).strip().lower()

    if operating_system == "windows":

        from device.windows.app_launcher import (
            WindowsDeviceController
        )

        return WindowsDeviceController()

    if operating_system == "darwin":

        raise NotImplementedError(
            "The macOS device controller has not been implemented yet."
        )

    if operating_system == "linux":

        raise NotImplementedError(
            "The Linux device controller has not been implemented yet."
        )

    if operating_system == "android":

        raise NotImplementedError(
            "Android requires its native device client."
        )

    if operating_system == "ios":

        raise NotImplementedError(
            "iOS requires its native device client."
        )

    raise RuntimeError(
        f"Unsupported operating system: {operating_system}"
    )