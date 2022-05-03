from collections import namedtuple
import paho.mqtt.client as mqtt
import json
import logging


class Mqtt(mqtt.Client):
    def __init__(self, client_id=""):
        self.subscriptions = []
        super().__init__(client_id)

    def connect(self, address : str, port : int):
        logged = False
        while True:
            try:
                super().connect(address, port)
                break
            except OSError:
                if not logged:
                    logging.error("Failed to connect to mqtt broker")
                    logged = True

    def subscribe(self, topic, qos=2, options=None, properties=None) -> None:
        sub = namedtuple("subscription", "topic qos options properties")
        subscription = sub(topic, qos, options, properties)
        logging.info(f'Subscribed to topic "{subscription.topic}"')
        self.subscriptions.append(subscription)
        super().subscribe(*subscription)

    def publish(self, topic: str, message: dict) -> None:
        msg = message
        msg.update({"from_host": True})
        r = super().publish(topic.lower(), json.dumps(message))
        if r[0] != 0:
            logging.critical("Failed to send message, errorcode: " + str(r[0]))

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("mqtt connected, errorcode: " + str(rc))
            for subscription in client.subscriptions:
                super().subscribe(*subscription)
        else:
            logging.error("Failed to connect to mqtt broker, errorcode: " + str(rc))
            self.connect(client._host, client._port)

    def on_disconnect(self, client, userdata, rc):
        logging.error("Disconnected from mqtt broker, errorcode: " + str(rc))