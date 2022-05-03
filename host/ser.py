import serial.tools.list_ports
import serial
import threading
import time
import json
import logging


class Serial_meta(type):
    def __len__(self):
        return len(self.connections)

    def __iter__(self):
        return iter(self.connections)


class Serial(metaclass=Serial_meta):

    connections = []
    __wdt_thread = None

    def __init__(self, interface: str) -> None:
        try:
            self.__connection = serial.Serial(interface, 115200)
        except serial.SerialException:
            logging.critical(f"Unable to connect to device on {interface}")
            return

        self.__thread = None
        self.__wdt = 0
        self.__wdt_out = False
        self.__kill = False
        self.name = ""
        Serial.connections.append(self)

    def send(self, message: str) -> None:
        try:
            self.__connection.write(bytes(message, "UTF-8") + b"\r")
        except AttributeError:
            pass

    def __readline(self) -> dict:
        message = ""
        try:
            message = self.__connection.readline().decode("utf-8").rstrip()
            return json.loads(message)
        except serial.serialutil.SerialException:
            self.__kill = True
            Serial.connections.remove(self)
            logging.error(
                f"Device {self.name} has disconnected from {self.__connection.port}"
            )
        except json.JSONDecodeError:
            logging.warning(
                f'Failed to decode message "{message}" from device {self.name}'
            )

    def __ser_t(self) -> None:
        while True:
            message = self.__readline()
            if self.__kill:
                break

            if message.get("name") is not None:
                self.name = message["name"]
                logging.info(
                    f"Name acquired for device on {self.__connection.port}: {message['name']}"
                )
            elif message.get("wdt") is not None:
                self.__wdt = message["wdt"]
            else:
                self.__on_message__(message)

    def start(self) -> None:
        try:
            self.__thread = threading.Thread(target=self.__ser_t, daemon=True)
            self.__thread.setName(self.__connection.port)
            self.__thread.start()
        except AttributeError:
            pass

    def join(self):
        self.__thread.join()

    def __on_timeout__(self) -> None:
        raise NotImplementedError

    def __on_message__(self, message: dict) -> None:
        raise NotImplementedError

    @staticmethod
    def get_connected_devices() -> list:
        try:
            return [
                str(port).split(" ")[0]
                for port in serial.tools.list_ports.comports()
                if "ACM" in str(port)
            ]
        except TypeError:
            return []

    @staticmethod
    def start_wdt(time: int = 10) -> None:
        Serial.__wdt_thread = threading.Thread(
            target=Serial.__t_wdt, args=(time,), daemon=True
        )
        Serial.__wdt_thread.setName("WatchdogTimer")
        Serial.__wdt_thread.start()
        logging.info(f"Watchdog started, running every {time} seconds")

    @staticmethod
    def __t_wdt(t: int = 10) -> None:
        last = {}
        while True:
            for connection in Serial.connections:
                if connection.__wdt == last.get(connection):
                    connection.__wdt_out = True
                    connection.__on_timeout__()
                    logging.error(connection.name, "Deviced timed out")
                else:
                    if connection.__wdt_out:
                        logging.info(connection.name, "Deviced regained connection")
                    connection.__wdt_out = False
                last.update({connection: connection.__wdt})
            time.sleep(t)
