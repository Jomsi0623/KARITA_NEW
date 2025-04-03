import os
import queue
import threading
import json
import string
import difflib
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.clock import Clock
from functools import partial
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.togglebutton import ToggleButton
import numpy as np
# from Levenshtein import distance as levenshtein_distance

# --- VOSK MODELS ---
MODEL_PATH_EN = "vosk_model"
MODEL_PATH_HILIGAYNON = "vosk_model_ph"

if not os.path.exists(MODEL_PATH_EN) or not os.path.exists(MODEL_PATH_HILIGAYNON):
    print("Error: Vosk model not found! Check paths.")
    exit(1)

vosk_model_en = Model(MODEL_PATH_EN)
vosk_model_hiligaynon = Model(MODEL_PATH_HILIGAYNON)

# --- LOAD TRANSLATION DICTIONARY ---
with open("translation_dict.json", "r", encoding="utf-8") as file:
    TRANSLATION_DICT = json.load(file)

# --- GLOBAL VARIABLES ---
recognition_active = False
audio_queue = queue.Queue()

# --- DYNAMIC TRANSLATION FUNCTION ---
def translate_text(text):
    print(f"[LOG] Translating text: {text}")
    text = text.lower().strip()
    no_punctuation_text = text.translate(str.maketrans('', '', string.punctuation))

    words = no_punctuation_text.split()
    translated_words = []
    i = 0

    while i < len(words):
        match_found = False
        for phrase_length in range(len(words) - i, 0, -1):
            phrase = " ".join(words[i:i + phrase_length])
            if phrase in TRANSLATION_DICT:
                translated_words.append(TRANSLATION_DICT[phrase])
                i += phrase_length
                match_found = True
                break
        if not match_found:
            word = words[i]
            closest_match = difflib.get_close_matches(word, TRANSLATION_DICT.keys(), n=1, cutoff=0.7)
            translated_words.append(TRANSLATION_DICT.get(closest_match[0], word) if closest_match else word)
            i += 1
    
    translated_sentence = " ".join(translated_words).capitalize()
    if not translated_sentence.strip():
        translated_sentence = "Translation not found"
    
    print(f"[LOG] Translated text: {translated_sentence}")
    return translated_sentence

# --- SPEECH RECOGNITION FUNCTION ---
def audio_callback(indata, frames, time, status):
    if status:
        print(f"[ERROR] Audio callback status: {status}")
    print(f"[LOG] Received audio frames: {len(indata)}")
    audio_queue.put(bytes(indata))

def start_recognition(language="english"):
    global recognition_active
    if recognition_active:
        print("[LOG] Recognition already active.")
        return

    recognition_active = True
    print(f"[LOG] Listening in {language}...")

    recognizer = KaldiRecognizer(vosk_model_en if language == "english" else vosk_model_hiligaynon, 16000)

    def process_audio():
        global recognition_active
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=audio_callback):
            while recognition_active:
                try:
                    print(f"[LOG] Size ka queue audio: {audio_queue.qsize()}")
                    data = audio_queue.get(timeout=1)
                    if recognizer.AcceptWaveform(data):
                        result_text = json.loads(recognizer.Result()).get("text", "").strip()
                        print(f"[LOG] Na recognize nga ({language}), text: {result_text}")
                        if result_text:
                            translated = translate_text(result_text)
                            Clock.schedule_once(partial(update_text, result_text, translated), 0)
                except queue.Empty:
                    print("[WARNING] Wala unod ang Audio.")
                    continue
                except Exception as e:
                    print(f"[ERROR] Recognition error: {e}")
                    break
        recognition_active = False

    threading.Thread(target=process_audio, daemon=True).start()

def stop_recognition():
    global recognition_active
    recognition_active = False
    print("[LOG] Nag untat na recognition sang audio.")

# --- UPDATE UI FUNCTION ---
def update_text(input_text, translated_text, *args):
    print(f"[LOG] Ma update na dapat ang mga Text: Text: {input_text}, Translation: {translated_text}")
    app.input_text.text = input_text
    app.translation_output.text = translated_text

# --- KIVY APP UI ---
class TranslatorApp(App):
    def build(self):
        Window.fullscreen = 'auto'
        self.dark_mode = False

        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        with main_layout.canvas.before:
            self.bg_color = Color(1, 1, 1, 1)
            self.rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
            main_layout.bind(size=self._update_rect, pos=self._update_rect)

        self.status_label = Label(text="Press and hold to start translation", size_hint=(1, 0.1), font_size='20sp', color=(0, 0, 0, 1))
        main_layout.add_widget(self.status_label)

        self.input_text = TextInput(multiline=True, hint_text="Enter Text", size_hint=(1, 0.3), font_size='24sp', disabled=True)
        main_layout.add_widget(self.input_text)

        self.translation_output = TextInput(multiline=True, text="This is a sample output for the voice.", hint_text="Translation", disabled=True, size_hint=(1, 0.3), font_size='24sp')
        main_layout.add_widget(self.translation_output)

        button_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)

        mic_e_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 1))
        self.control_button = Image(source="assets/mic_e.png", size_hint=(1, 0.8))
        self.control_button.bind(on_touch_down=self.on_button_down_english)
        self.control_button.bind(on_touch_up=self.on_button_up)
        mic_e_label = Label(text="English", size_hint=(1, 0.2), font_size='18sp', color=(0, 0, 0, 1))
        mic_e_layout.add_widget(self.control_button)
        mic_e_layout.add_widget(mic_e_label)
        button_layout.add_widget(mic_e_layout)

        mic_h_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 1))
        self.hiligaynon_button = Image(source="assets/mic_h.png", size_hint=(1, 0.8))
        self.hiligaynon_button.bind(on_touch_down=self.on_button_down_hiligaynon)
        self.hiligaynon_button.bind(on_touch_up=self.on_button_up)
        mic_h_label = Label(text="Hiligaynon", size_hint=(1, 0.2), font_size='18sp', color=(0, 0, 0, 1))
        mic_h_layout.add_widget(self.hiligaynon_button)
        mic_h_layout.add_widget(mic_h_label)
        button_layout.add_widget(mic_h_layout)

        main_layout.add_widget(button_layout)

        self.dark_mode_button = ToggleButton(text="Dark Mode", size_hint=(1, 0.1))
        self.dark_mode_button.bind(on_press=self.toggle_dark_mode)
        main_layout.add_widget(self.dark_mode_button)

        return main_layout

    def on_button_down_english(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Listening in English..."
            print("[LOG] Gin tum-ok ang English.")
            start_recognition("english")

    def on_button_down_hiligaynon(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Listening in Hiligaynon..."
            print("[LOG] Gin tum-ok ang Hiligaynon.")
            start_recognition("hiligaynon")

    def on_button_up(self, instance, touch):
        print("[LOG] Nag buya na sa pag tum-ok.")
        stop_recognition()
        self.status_label.text = "Stopped Listening"

    def _update_rect(self, instance, value):
        """Ensures background updates dynamically when resizing."""
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def toggle_dark_mode(self, instance, *args):
        """Toggles between light and dark mode using a ToggleButton."""
        self.dark_mode = instance.state == 'down'  # Toggle state

        # Change colors based on mode
        color = (0, 0, 0, 1) if self.dark_mode else (1, 1, 1, 1)
        text_color = (1, 1, 1, 1) if self.dark_mode else (0, 0, 0, 1)

        with self.root.canvas.before:
            self.bg_color.rgb = color[:3]
            self.rect = Rectangle(size=self.root.size, pos=self.root.pos)
            self.root.bind(size=self._update_rect, pos=self._update_rect)

        # 🔹 Update text colors
        self.status_label.color = text_color
        self.input_text.foreground_color = text_color
        self.translation_output.foreground_color = text_color

        # 🔹 Update button icons
        self.control_button.source = "assets/mic_e_gray.png" if self.dark_mode else "assets/mic_e.png"
        self.hiligaynon_button.source = "assets/mic_h_gray.png" if self.dark_mode else "assets/mic_h.png"
        # self.speak_button.source = "assets/speaker_icon_gray.png" if self.dark_mode else "assets/speaker_icon.png"

        # 🔹 Update toggle button text
        self.dark_mode_button.text = "Light Mode" if self.dark_mode else "Dark Mode"

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()
