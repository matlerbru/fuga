import pyudev
import threading


class Detektor:
    def __init__(self) -> None:
        self._context = pyudev.Context()
        self._monitor = pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem="usb")

    def start(self) -> None:
        self._thread = threading.Thread(target=self._udev_t, daemon=True)
        self._thread.setName("Scanner")
        self._thread.start()

    def __call__() -> None:
        raise NotImplementedError

    def _udev_t(self):
        self.__call__()
        for device in iter(self._monitor.poll, None):
            if device.action == "add":
                self.__call__()
