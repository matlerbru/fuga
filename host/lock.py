import os


class Lock:
    def __init__(self, name: str, location: str = "") -> None:
        self._path = f"{location}/{name}" if location != "" else name

    def acquire(self) -> None:

        try:
            with open(self._path, "r") as stream:
                pid = int(stream.read())
                try:
                    os.kill(pid, 0)
                    raise LockedError
                except OSError:
                    self.release()

        except FileNotFoundError:
            pass

        with open(self._path, "w") as stream:
            stream.write(str(os.getpid()))

    def release(self) -> None:
        os.remove(self._path)


class LockedError(Exception):
    """Raised when application is already running"""

    pass
