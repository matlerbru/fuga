import serial

class connection:

    def __init__(self, interface : str):
        self.interface = interface
        self.ser = serial.Serial(interface, 115200)

    def get_host(self) -> str:
        message = '{"command": "get_name"}'
        self.ser.write(bytes(message, "UTF-8") + b"\r")

    def enable_led(self, state : bool) -> str:
        message = '{"command": "enable_led", "value": ' + str(state).lower() + '}'
        self.ser.write(bytes(message, "UTF-8") + b"\r")

    def set_led(self, number : int, state : str):
        message = '{"command": "set_led", "number": ' + str(number) + ', "state": "' + state + '"} '
        self.ser.write(bytes(message, "UTF-8") + b"\r")

    def readline(self) -> str:
        return self.ser.readline().decode("utf-8").rstrip()

    def close(self):
        self.ser.close()
