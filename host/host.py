import serial.tools.list_ports as port_list
import paho.mqtt.client as mqtt
import threading
import logging
import yaml
from logging.handlers import RotatingFileHandler
from datetime import datetime
from connection import connection
from serial import SerialException
import time
import json

connections = dict()
setup = None
client = mqtt.Client() 

def get_connected_devices():
    ports = list(port_list.comports())
    devices = list()
    for port in ports:
        if 'ACM' in str(port):
            devices.append(str(port)[:str(port).index(' ')])
    return devices

class struct:

    def __init__(self):
        self.interface = None
        self.ser = None
        self.thread = None
        self.location = None
        self.wdt = None

def thr(stru):
    stru.ser.get_host()
    while True:
        try:
            message = stru.ser.readline()
            message = json.loads(message)

            if message.get('name') != None:
                for conn in connections.keys():
                    if connections.get(conn).interface == stru.interface:
                        connections.get(conn).location = message.get('name')
                        connections.get(conn).thread.name = connections.get(conn).location.lower()
                        logging.info('Location recieved for device on ' + connections.get(conn).interface + ': ' + connections.get(conn).location)

            elif message.get('wdt'):
                for conn in connections.keys():
                    if connections.get(conn).interface == stru.interface:
                        connections.get(conn).wdt = time.time()

            elif message.get('button') != None:
                result = client.publish('FUGA/' + stru.location, json.dumps(message))
                if result[0] != 0:
                    logging.error('Failed to send message, errorcode: ' + str(result[0]))

            elif message.get('exception') != None:
                result = client.publish('FUGA/' + stru.location, json.dumps(message))
                if result[0] != 0:
                    logging.error('Failed to send message, errorcode: ' + str(result[0])) 

        except json.decoder.JSONDecodeError:
            logging.warning('Not able to decode json: ' + message)
            result = client.publish('FUGA/' + 'MESSAGE_DECODER', 'Not able to decode json: ' + message)
            if result[0] != 0:
                logging.error('Failed to send message, errorcode: ' + str(result[0])) 
        except SerialException:
            logging.warning('Device disconnected: ' + stru.location)
            result = client.publish('FUGA/' + stru.location, 'Device disconnected')
            if result[0] != 0:
                logging.error('Failed to send message, errorcode: ' + str(result[0])) 
            stru.ser.close()
            del connections[stru.interface]
            return

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info('mqtt connected, errorcode: ' + str(rc))
        client.subscribe('FUGA')
    else:
        logging.error('Failed to connect to mqtt, errorcode: ' + str(rc))
        client.connect(setup.get('server_address'), setup.get('server_port'))

def on_disconnect(client, userdata, rc):
    logging.error('Disconnected from mqtt, errorcode: ' + str(rc))
    client.connect(setup.get('server_address'), setup.get('server_port'))

def on_message(client, userdata, msg):
    cmd = None
    try:
        cmd = json.loads(msg.payload.decode())

        for conn in connections.keys():
            if connections.get(conn).location == cmd.get('location'):
                if cmd.get('command') == 'enable_led':
                    connections.get(conn).ser.enable_led(cmd.get('state'))
                    logging.info('enable_led command recieved on ' + connections.get(conn).location + ':' + json.dumps(cmd))
                    break
                if cmd.get('command') == 'set_led':
                    connections.get(conn).ser.set_led(cmd.get('number'), cmd.get('state'))
                    logging.info('set_led command recieved on ' + connections.get(conn).location + ':' + json.dumps(cmd))
                    break

    except json.decoder.JSONDecodeError:
        result = client.publish('FUGA/' + 'MESSAGE_DECODER', 'Unable to pass command: ' + msg.payload.decode())
        if result[0] != 0:
            logging.error('Failed to send message, errorcode: ' + str(result[0])) 
            return

def main():

    log_handler = RotatingFileHandler(
        filename='fuga.log', 
        mode='a',
        maxBytes=5*1024*1024,
        backupCount=2,
        encoding=None,
        delay=0
    )

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)-8s %(levelname)-8s %(message)s",
        datefmt="%y-%m-%d %H:%M:%S",
        handlers=[
            log_handler
        ]
    )

    logging.info('_________________ host.py is started _________________')

    try:
        file = open('setup.yml')
        setup = yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        logging.error('Not able to load setup.yml: File not found')
    except yaml.scanner.ScannerError:
        logging.error('Not able to load setup.yml: File not formatted correct')

    '''
    devices = get_connected_devices()
    for device in devices:
        s = struct()
        s.interface = device
        s.ser = connection(s.interface)
        s.thread = threading.Thread(target=thr, args=(s,))
        s.thread.start()
        logging.info('Thread started for device on interface: ' + s.interface)
        connections.update({device : s})
    '''
    def watchdog():
        while True:
            time.sleep(10)
            for conn in connections.keys():
                if connections.get(conn).wdt + setup.get('wdt_time') < time.time():
                    result = client.publish('FUGA/' + connections.get(conn).location, 'wdt: timer expired')
                    logging.error('Watchdog timer expired on ' + connections.get(conn).location)
                    if result[0] != 0:
                        logging.error('Failed to send message, errorcode: ' + str(result[0])) 
            time.sleep(5)

    wdt = threading.Thread(target=watchdog, args=())
    wdt.name = 'watchdog'
    wdt.start()

    def device_handler():
        while True:
            devices = get_connected_devices()
            for conn in connections.copy().keys():
                try:
                    devices.remove(conn)
                except Exception as e:
                    print(type(e))
            for device in devices:
                s = struct()
                s.interface = device
                s.ser = connection(s.interface)
                s.thread = threading.Thread(target=thr, args=(s,))
                s.thread.start()
                logging.info('Thread started for device on interface: ' + s.interface)
                connections.update({device : s})
            
            time.sleep(60)

            l = setup.get('devices').copy()
            for conn in connections.keys():
                l.remove(connections.get(conn).location)
            for device in l:
                result = client.publish('FUGA/' + device, 'handler: not able to connect to device')
                logging.error('handler: not able to connect to device ' + device) 
                if result[0] != 0:
                    logging.error('Failed to send message, errorcode: ' + str(result[0]))

    dh = threading.Thread(target=device_handler, args=())
    dh.name = 'device_handler'
    dh.start()

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message   

    client.connect(setup.get('server_address'), setup.get('server_port'))
    client.subscribe('FUGA/#')
    client.loop_forever()

if __name__ == "__main__":
    try:
        main()
    finally:
        for conn in connections:
            connections.get(conn).ser.close()
        logging.info('host.py is shutting down\n')

#{"location" : "KITCHEN", "command": "enable_led", "state": "true"}
#{"location" : "KITCHEN", "command": "enable_led", "state": "false"}
#{"location" : "KITCHEN", "command": "set_led", "number": 0, "state": "short"} 
#{"location" : "KITCHEN", "command": "set_led", "number": 1, "state": "on"} 