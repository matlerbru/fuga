from ser import Serial
import mqtt
import logging
from logging.handlers import RotatingFileHandler
import threading
import time
import yaml
import lock
import json
import udev

# TODO: Check mqtt disconnect stability

log_handler = RotatingFileHandler(
    filename="host.log",
    mode="a",
    maxBytes=10 * 1024 * 1024,
    backupCount=2,
    encoding=None,
    delay=True,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)-8s %(levelname)-8s %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    handlers=[log_handler, logging.StreamHandler()],
)


def scan_devices():

    for device in Serial.get_connected_devices():
        if device not in [connection._Serial__connection.port for connection in Serial]:
            logging.info(f"Device found on {device}")
            serial = Serial(device)
            serial.start()
            serial.send('{"command":"get_name"}\r)')


def check_devices(expected_devices: list):
    devices = expected_devices
    for device in [connection.name.lower() for connection in Serial.connections]:
        try:
            devices.remove(device)
        except ValueError:
            pass
    [logging.warning(f"Device {device} not connected") for device in expected_devices]
    threading.Timer(86400, check_devices, args=(devices,)).start()


def main():

    setup = None
    with open("setup.yml") as stream:
        setup = yaml.safe_load(stream)

    client = mqtt.Mqtt()
    client.connect(setup["mqtt_address"], setup["mqtt_port"])
    client.subscribe("fuga/#")
    client.enable_bridge_mode()

    def mqtt_on_message(client, userdata, msg):
        try:
            message = json.loads(msg.payload.decode("utf-8"))
            if message.get("from_host"):
                return
        except json.JSONDecodeError:
            logging.warning(f'Failed to decode mqtt message "{message}"')

        for connection in Serial.connections:
            if connection.name.lower() == msg.topic.replace("fuga/", "").lower():
                connection.send(msg.payload.decode("utf-8"))

        logging.debug(message)

    client.on_message = mqtt_on_message

    def serial_on_message(self, message: dict):
        client.publish(f"fuga/{self.name}", message)

    def serial_on_timeout(self):
        client.publish(f"fuga/{self.name}", {"error": "timeout"})

    logging.info("Application started")
    client.loop_start()

    scanner = udev.Detektor()
    scanner.__call__ = scan_devices
    scanner.start()

    Serial.start_wdt(setup["wdt_time"])

    Serial.__on_message__ = serial_on_message
    Serial.__on_timeout__ = serial_on_timeout

    time.sleep(1)
    check_devices(setup["devices"])


if __name__ == "__main__":
    mutex = lock.Lock("tini.lock", "/var/lock")
    try:
        mutex.acquire()
        main()
        threading.Event().wait()
    except lock.LockedError:
        pass
    except Exception as e:
        logging.critical(f"Application fail: {str(e)}")
        mutex.release()
    except KeyboardInterrupt:
        mutex.release()
