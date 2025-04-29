import time
from multiprocessing import Process, Pipe

# Mock GPIO for non-Raspberry Pi environments
try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY_PI = True
except ImportError:
    IS_RASPBERRY_PI = False
    print("Running in mock mode (no RPi.GPIO)")

    class MockGPIO:
        BCM = 11
        IN = 1
        OUT = 0
        PUD_UP = 21
        HIGH = 1
        LOW = 0
        
        def __init__(self):
            self.pin_states = {}
            
        def setmode(self, mode):
            print(f"[MOCK] GPIO mode set to {mode}")
            
        def setup(self, pin, direction, pull_up_down=None):
            print(f"[MOCK] Setup pin {pin} as {'INPUT' if direction == self.IN else 'OUTPUT'}")
            self.pin_states[pin] = self.HIGH if pull_up_down == self.PUD_UP else self.LOW
            
        def input(self, pin):
            return self.pin_states.get(pin, self.HIGH)
            
        def cleanup(self):
            print("[MOCK] GPIO cleanup")
            
        def setwarnings(self, flag):
            print(f"[MOCK] Warnings {'enabled' if flag else 'disabled'}")
    
    GPIO = MockGPIO()

class ButtonController:
    def __init__(self):
        # Button GPIO pins
        self.ENGLISH_BUTTON_PIN = 17
        self.HILIGAYNON_BUTTON_PIN = 27
        self.SPEAKER_BUTTON_PIN = 22
        
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        if IS_RASPBERRY_PI:
            GPIO.setup(self.ENGLISH_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.HILIGAYNON_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.SPEAKER_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        self.english_button_pressed = False
        self.hiligaynon_button_pressed = False
        self.speaker_button_pressed = False
        self.last_speaker_press = 0

        if not IS_RASPBERRY_PI:
            print("\n=== TEST MODE ===")
            print("Press E - English button")
            print("Press H - Hiligaynon button")
            print("Press S - Speaker button")
            print("ESC - Exit\n")

    def monitor_buttons(self, conn):
        try:
            if IS_RASPBERRY_PI:
                # Real hardware implementation
                while True:
                    # Check English button
                    current_english = GPIO.input(self.ENGLISH_BUTTON_PIN)
                    if current_english == GPIO.LOW and not self.english_button_pressed:
                        self.english_button_pressed = True
                        conn.send(('start', 'english'))
                        print("[HARDWARE] English button pressed")
                    
                    if current_english == GPIO.HIGH and self.english_button_pressed:
                        self.english_button_pressed = False
                        conn.send(('stop', None))
                        print("[HARDWARE] English button released")
                    
                    # Check Hiligaynon button
                    current_hiligaynon = GPIO.input(self.HILIGAYNON_BUTTON_PIN)
                    if current_hiligaynon == GPIO.LOW and not self.hiligaynon_button_pressed:
                        self.hiligaynon_button_pressed = True
                        conn.send(('start', 'hiligaynon'))
                        print("[HARDWARE] Hiligaynon button pressed")
                    
                    if current_hiligaynon == GPIO.HIGH and self.hiligaynon_button_pressed:
                        self.hiligaynon_button_pressed = False
                        conn.send(('stop', None))
                        print("[HARDWARE] Hiligaynon button released")
                    
                    # Check Speaker button
                    current_speaker = GPIO.input(self.SPEAKER_BUTTON_PIN)
                    if current_speaker == GPIO.LOW and not self.speaker_button_pressed:
                        self.speaker_button_pressed = True
                        current_time = time.time()
                        if current_time - self.last_speaker_press > 0.3:  # Debounce
                            conn.send(('speak', None))
                            print("[HARDWARE] Speaker button pressed")
                            self.last_speaker_press = current_time
                    
                    if current_speaker == GPIO.HIGH and self.speaker_button_pressed:
                        self.speaker_button_pressed = False
                    
                    time.sleep(0.05)
            else:
                # Keyboard simulation
                import keyboard
                while True:
                    try:
                        if keyboard.is_pressed('e'):
                            conn.send(('start', 'english'))
                            print("[TEST] English button pressed")
                            while keyboard.is_pressed('e'):
                                time.sleep(0.1)
                            conn.send(('stop', None))
                        elif keyboard.is_pressed('h'):
                            conn.send(('start', 'hiligaynon'))
                            print("[TEST] Hiligaynon button pressed")
                            while keyboard.is_pressed('h'):
                                time.sleep(0.1)
                            conn.send(('stop', None))
                        elif keyboard.is_pressed('s'):
                            conn.send(('speak', None))
                            print("[TEST] Speaker button pressed")
                            time.sleep(0.3)
                        elif keyboard.is_pressed('esc'):
                            break
                        time.sleep(0.01)
                    except KeyboardInterrupt:
                        break
                        
        except Exception as e:
            print(f"Button monitoring error: {e}")
        finally:
            if IS_RASPBERRY_PI:
                GPIO.cleanup()
            conn.close()
            print("Button controller stopped")

def start_button_controller(conn):
    controller = ButtonController()
    controller.monitor_buttons(conn)