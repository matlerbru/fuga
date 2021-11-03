from machine import Pin, Timer
from time import ticks_ms, time, sleep
import select
import sys
import _thread
import ujson

NAME = 'KITCHEN'

class Button:
    buttons = list()

    def __init__(self, pin : int) -> None:
        self.pin = pin
        self.button = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.__time = 0
        Button.buttons.append(self)
        
    __timer = Timer()

    @staticmethod
    def __get_state(timer):
        try:
            def get_time_pressed(button):
                if not button.button.value():
                    if button.__time == 0:
                        button.__time = ticks_ms()
                    return 0
                elif button.__time > 0:
                    time_pressed = ticks_ms() - button.__time
                    button.__time = 0
                    return time_pressed
                return 0

            for i, button in enumerate(Button.buttons):
                time_pressed = get_time_pressed(button)
                if time_pressed > 1000:
                    message = i*10+41
                    print(ujson.dumps({'button' : i, 'press' : 'long'}))
                elif time_pressed > 1:
                    print(ujson.dumps({'button' : i, 'press' : 'short'}))

        except Exception as e:
            print(ujson.dumps({'exception' : e}))

    @staticmethod
    def start():
        Button.__timer.init(freq=100, mode=Timer.PERIODIC, callback=Button.__get_state)

class Led:
    leds = list()

    def __init__(self, pin : int) -> None:
        self.pin = pin
        self.led = Pin(pin, Pin.OUT)
        self.state = 0
        Led.leds.append(self)

    def set_state(self, state : str) -> None:
        self.state = state

    def update_led(self) -> None:
        if not Led.__disable:
            if self.state == 'off':
                self.led.low()
            elif self.state == 'on':
                self.led.high()
            elif self.state == 'short':
                self.led.low() if Led.__short else self.led.high()
            elif self.state == 'long':
                self.led.low() if Led.__long else self.led.high()
        else:
            self.led.low()

    __short : bool = False
    __long : bool = False
    __multiplier : int
    __count : int = False
    __timer = Timer()

    @staticmethod
    def __blink(timer) -> None:
        try:
            Led.__short = not Led.__short
            if Led.__count >= Led.__multiplier:
                Led.__long = not Led.__long
                Led.__count = 0
            else:
                Led.__count += 1
            for led in Led.leds:
                led.update_led()
        except Exception as e:
            print(ujson.dumps({'exception' : e}))

    @staticmethod
    def start(short_frequency : float = 1, long_x : int = 2) -> None:
        Led.__multiplier = long_x
        Led.__timer.init(freq=short_frequency, mode=Timer.PERIODIC, callback=Led.__blink)

    __disable = False

    @staticmethod
    def disable_led(disable : bool):
        Led.__disable = disable

def scan(n : int = 1) -> str:
    while True:
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:   
            ch = sys.stdin.read(n)
            if ch != None:
                return ch

def scanline() -> str:
    l = str()
    while True:
        ch = scan()
        if int(ord(ch)) == 10 :
            return l.strip()
        else:
            l += ch

class watchdog:

    count_max = 99
    count = -1
    __timer = Timer()
    n = 0

    @staticmethod
    def start(period):
        watchdog.__timer.init(freq=2, mode=Timer.PERIODIC, callback=watchdog.__wdt)

    @staticmethod
    def __wdt(timer) -> None:
        if watchdog.n == 5:
            if watchdog.count >= watchdog.count_max:
                watchdog.count = 0
            else:
                watchdog.count += 1
            print(ujson.dumps({'wdt' : watchdog.count}))
            watchdog.n = 0
        else:
            watchdog.n += 1

def Core1():   
    try:
        Led(3)
        Led(4)
        Led(5)
        
        Led.start(2.5, 8)
        watchdog.start(1)
        
        while True:
            try:
                cmd = dict()
                try:
                    cmd = ujson.loads(str(scanline()))
                except ValueError:
                    pass
                if cmd.get('command') == 'get_name':
                    print(ujson.dumps({'name' : NAME}))

                elif cmd.get('command') == 'enable_led':
                    Led.disable_led(not cmd.get('value'))

                elif cmd.get('command') == 'set_led':
                    l = Led.leds[cmd.get('number')]
                    l.set_state(cmd.get('state'))

            except AttributeError:
                print(ujson.dumps({'exception' : 'Not able to recognize command'}))

    except Exception as e:
        print(type(e))
        print(ujson.dumps({'exception' : e}))
    
def Core2():
    try:
        Button(9)
        Button(10)
        Button(11)
        Button(12)
        Button(14)
        Button(15)
        Button.start()

    except Exception as e:
        print(ujson.dumps({'exception' : e}))

_thread.start_new_thread(Core2, ())
Core1()

#{"command": "get_name"}
#{"command": "enable_led", "value": true} 
#{"command": "enable_led", "value": false} 
#{"command": "set_led", "number": 0, "state": "short"} 
#{"command": "set_led", "number": 1, "state": "long"} 

#{"location" : "KITCHEN", "command": "set_led", "number": 0, "state": "short"}