import os
import queue
import threading
import json
import pyttsx3
from vosk import Model, KaldiRecognizer
import sounddevice as sd
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from functools import partial
from kivy.core.window import Window
import string
import difflib

# Paths to Vosk Models
MODEL_PATH_EN = "vosk_model"
MODEL_PATH_HILIGAYNON = "vosk_model_ph"

# Load English Model
if not os.path.exists(MODEL_PATH_EN):
    print("English model not found! Please check the path.")
    exit(1)
vosk_model_en = Model(MODEL_PATH_EN)

# Load Hiligaynon Model
if not os.path.exists(MODEL_PATH_HILIGAYNON):
    print("Hiligaynon model not found! Please check the path.")
    exit(1)
vosk_model_hiligaynon = Model(MODEL_PATH_HILIGAYNON)

# Global Variables
recognition_active = False
audio_queue = queue.Queue()

# Load Translation Dictionary
with open("translation_dict.json", "r", encoding="utf-8") as file:
    TRANSLATION_DICT = json.load(file)

def translate_text(text):
    """Translates the given text based on the dictionary."""
    text = text.lower().strip()
    no_punctuation_text = text.translate(str.maketrans('', '', string.punctuation))  # Remove punctuation

    if text in TRANSLATION_DICT:
        return TRANSLATION_DICT[text]
    if no_punctuation_text in TRANSLATION_DICT:
        return TRANSLATION_DICT[no_punctuation_text]

    closest_match = difflib.get_close_matches(no_punctuation_text, TRANSLATION_DICT.keys(), n=1, cutoff=0.8)
    if closest_match:
        return TRANSLATION_DICT[closest_match[0]]

    return "Translation not found"

def audio_callback(indata, frames, time, status):
    """Handles audio input and places it in a queue."""
    if status:
        print(status, flush=True)
    audio_queue.put(bytes(indata))

def start_recognition(language="english"):
    """Starts voice recognition based on the selected language."""
    global recognition_active
    if recognition_active:
        print("Recognition already active, ignoring duplicate start.")
        return

    recognition_active = True
    print(f"Starting {language} voice recognition...")

    recognizer = KaldiRecognizer(vosk_model_en if language == "english" else vosk_model_hiligaynon, 16000)

    def process_audio_stream():
        """Processes the live audio stream and performs speech recognition."""
        global recognition_active
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=audio_callback):
            while recognition_active:
                try:
                    data = audio_queue.get(timeout=1)
                    if recognizer.AcceptWaveform(data):
                        result_text = json.loads(recognizer.Result()).get("text", "").strip()
                        if result_text:
                            translated = translate_text(result_text)
                            Clock.schedule_once(partial(update_text, result_text, translated), 0)
                except queue.Empty:
                    continue
                except Exception as e:
                    print("Error in recognition:", e)
                    break
        recognition_active = False

    threading.Thread(target=process_audio_stream, daemon=True).start()

def stop_recognition():
    """Stops voice recognition."""
    global recognition_active
    recognition_active = False

def update_text(input_text, translated_text, *args):
    """Updates the UI with the recognized and translated text."""
    app.input_text.text = input_text
    app.translation_output.text = translated_text

def speak_translation(text):
    """Converts text to speech."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

class TranslatorApp(App):
    def build(self):
        Window.fullscreen = 'auto'
        self.dark_mode = False
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        # Background
        with main_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
            main_layout.bind(size=self._update_rect, pos=self._update_rect)

        self.status_label = Label(text="Press and hold to start translation", size_hint=(1, 0.1), font_size='20sp', color=(0, 0, 0, 1))
        main_layout.add_widget(self.status_label)

        self.input_text = TextInput(multiline=True, hint_text="Enter Text", size_hint=(1, 0.3), font_size='24sp')
        main_layout.add_widget(self.input_text)

        self.translation_output = TextInput(multiline=True, hint_text="Translation", readonly=True, size_hint=(1, 0.3), font_size='24sp')
        main_layout.add_widget(self.translation_output)

        button_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)

        # Translate Button
        # self.translate_button = Image(source="assets/translate_icon.png", size_hint=(0.2, 1))
        # self.translate_button.bind(on_touch_down=self.manual_translate)
        # button_layout.add_widget(self.translate_button)

        # English Mic Button
        self.control_button = Image(source="assets/mic_e.png", size_hint=(0.2, 1))
        self.control_button.bind(on_touch_down=self.on_button_down_english)
        self.control_button.bind(on_touch_up=self.on_button_up)
        button_layout.add_widget(self.control_button)

        # Speak Button
        self.speak_button = Image(source="assets/speaker_icon.png", size_hint=(0.2, 1))
        self.speak_button.bind(on_touch_down=self.speak_translation_output)
        button_layout.add_widget(self.speak_button)

        # Hiligaynon Mic Button
        self.hiligaynon_button = Image(source="assets/mic_h.png", size_hint=(0.2, 1))
        self.hiligaynon_button.bind(on_touch_down=self.on_button_down_hiligaynon)
        self.hiligaynon_button.bind(on_touch_up=self.on_button_up)
        button_layout.add_widget(self.hiligaynon_button)

        main_layout.add_widget(button_layout)

        self.dark_mode_toggle = ToggleButton(text="Dark Mode", size_hint=(1, 0.1))
        self.dark_mode_toggle.bind(on_press=self.toggle_dark_mode)
        main_layout.add_widget(self.dark_mode_toggle)

        return main_layout

    def _update_rect(self, instance, value):
        """Updates the background rectangle size and position."""
        if hasattr(self, 'rect'):
            self.rect.size = instance.size
            self.rect.pos = instance.pos

    def manual_translate(self, instance, touch):
        if instance.collide_point(*touch.pos):
            input_text = self.input_text.text.strip()
            translated_text = translate_text(input_text)
            self.translation_output.text = translated_text

    def on_button_down_english(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Listening in English..."
            start_recognition("english")

    def on_button_down_hiligaynon(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Listening in Hiligaynon..."
            start_recognition("hiligaynon")

    def on_button_up(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Stopped Listening"
            stop_recognition()
    
    def speak_translation_output(self, instance, touch):
        if instance.collide_point(*touch.pos):
            text = self.translation_output.text.strip()
            if text:
                speak_translation(text)

    def toggle_dark_mode(self, instance):
        self.dark_mode = not self.dark_mode
        color = (0, 0, 0, 1) if self.dark_mode else (1, 1, 1, 1)
        with self.root.canvas.before:
            Color(*color)
            self.rect = Rectangle(size=self.root.size, pos=self.root.pos)
            self.root.bind(size=self._update_rect, pos=self._update_rect)
        
        if self.dark_mode:
            self.control_button.source = "assets/mic_e_gray.png"
            self.hiligaynon_button.source = "assets/mic_h_gray.png"
            self.speak_button.source = "assets/speaker_icon_gray.png"
            # self.translate_button.source = "assets/translate_icon_gray.png"
        else:
            self.control_button.source = "assets/mic_e.png"
            self.hiligaynon_button.source = "assets/mic_h.png"
            self.speak_button.source = "assets/speaker_icon.png"
            # self.translate_button.source = "assets/translate_icon.png"

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()
