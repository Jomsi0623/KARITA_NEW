import os
import queue
import threading
import json
from vosk import Model, KaldiRecognizer
import sounddevice as sd
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from functools import partial
from langdetect import detect

# Paths to Vosk models
MODEL_PATH_EN = "vosk_model"
MODEL_PATH_FIL = "vosk_model_ph"

# Load models
if not os.path.exists(MODEL_PATH_EN) or not os.path.exists(MODEL_PATH_FIL):
    print("One or more models not found! Please check the paths.")
    exit(1)

vosk_model_en = Model(MODEL_PATH_EN)  # English model
vosk_model_fil = Model(MODEL_PATH_FIL)  # Filipino model

# Default recognizer (starts with English)
recognizer = KaldiRecognizer(vosk_model_en, 16000)

# Global variables
recognition_active = False
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        print(status, flush=True)
    audio_queue.put(bytes(indata))

# Load Translation Dictionary
with open("translation_dict.json", "r", encoding="utf-8") as file:
    TRANSLATION_DICT = json.load(file)

def translate_text(text):
    text = text.lower()
    normalized_dict = {k.lower(): v for k, v in TRANSLATION_DICT.items()}
    reverse_dict = {v.lower(): k for k, v in TRANSLATION_DICT.items()}
    return normalized_dict.get(text, reverse_dict.get(text, "Translation not found"))

def detect_language(text):
    try:
        lang = detect(text)
        return "fil" if lang in ["tl", "fil"] else "en" if lang == "en" else "unknown"
    except:
        return "unknown"

def start_recognition():
    global recognition_active
    if recognition_active:
        print("Recognition already active, ignoring duplicate start.")
        return  # Prevent multiple recognitions

    recognition_active = True
    print("Starting voice recognition...")

    def process_audio_stream():
        global recognition_active, recognizer
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=audio_callback):
            while recognition_active:
                try:
                    data = audio_queue.get(timeout=1)
                    if recognizer.AcceptWaveform(data):
                        result_text = json.loads(recognizer.Result()).get("text", "").strip()
                        if result_text:
                            detected_lang = detect_language(result_text)
                            recognizer = KaldiRecognizer(vosk_model_fil, 16000) if detected_lang == "fil" else KaldiRecognizer(vosk_model_en, 16000)
                            translated = translate_text(result_text)
                            Clock.schedule_once(partial(update_text, result_text, translated), 0)
                except queue.Empty:
                    continue
                except Exception as e:
                    print("Error in recognition:", e)
                    break
        recognition_active = False  # Reset flag when finished

    threading.Thread(target=process_audio_stream, daemon=True).start()

def stop_recognition():
    global recognition_active
    recognition_active = False

def update_text(input_text, translated_text, *args):
    app.input_text.text = input_text
    app.translation_output.text = translated_text

class TranslatorApp(App):
    def build(self):
        self.dark_mode = False
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        with main_layout.canvas.before:
            Color(1, 1, 1, 1)  # Set background color to white
            self.rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
            main_layout.bind(size=self._update_rect, pos=self._update_rect)
        
        self.status_label = Label(text="Press and hold to start translation", size_hint=(1, 0.1), font_size='20sp', color=(0, 0, 0, 1))
        main_layout.add_widget(self.status_label)
        
        self.input_text = TextInput(multiline=True, hint_text="Enter Text", size_hint=(1, 0.3), background_color=(1, 1, 1, 1), foreground_color=(0, 0, 0, 1))
        main_layout.add_widget(self.input_text)
        
        self.translation_output = TextInput(multiline=True, hint_text="Translation", readonly=True, size_hint=(1, 0.3), background_color=(1, 1, 1, 1), foreground_color=(0, 0, 0, 1))
        main_layout.add_widget(self.translation_output)
        
        button_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)
        
        self.translate_button = Button(text="Translate", size_hint=(0.5, 1), background_color=(0.2, 0.6, 0.8, 1))
        self.translate_button.bind(on_press=self.manual_translate)
        button_layout.add_widget(self.translate_button)
        
        self.control_button = Button(text="Hold to Speak", size_hint=(0.5, 1), background_color=(0.8, 0.2, 0.2, 1))
        self.control_button.bind(on_touch_down=self.on_button_down)
        self.control_button.bind(on_touch_up=self.on_button_up)
        button_layout.add_widget(self.control_button)
        
        main_layout.add_widget(button_layout)
        
        self.dark_mode_toggle = ToggleButton(text="Dark Mode", size_hint=(1, 0.1), background_color=(0.4, 0.4, 0.4, 1))
        self.dark_mode_toggle.bind(on_press=self.toggle_dark_mode)
        main_layout.add_widget(self.dark_mode_toggle)
        
        return main_layout
    
    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos
    
    def manual_translate(self, instance):
        input_text = self.input_text.text.strip()
        translated_text = translate_text(input_text)
        self.translation_output.text = translated_text
    
    def on_button_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Listening..."
            start_recognition()
    
    def on_button_up(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Stopped Listening"
            stop_recognition()
    
    def toggle_dark_mode(self, instance):
        self.dark_mode = not self.dark_mode
        color = (0, 0, 0, 1) if self.dark_mode else (1, 1, 1, 1)
        with self.root.canvas.before:
            Color(*color)
            self.rect = Rectangle(size=self.root.size, pos=self.root.pos)
            self.root.bind(size=self._update_rect, pos=self._update_rect)

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()