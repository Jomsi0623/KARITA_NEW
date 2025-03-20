import os
import queue
import threading
import json
import pyttsx3
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
    """Dynamically translates text while preserving greetings."""
    text = text.lower().strip()
    no_punctuation_text = text.translate(str.maketrans('', '', string.punctuation))

    words = no_punctuation_text.split()
    translated_words = []

    for word in words:
        if word in TRANSLATION_DICT:
            translated_words.append(TRANSLATION_DICT[word])
        else:
            closest_match = difflib.get_close_matches(word, TRANSLATION_DICT.keys(), n=1, cutoff=0.8)
            translated_words.append(TRANSLATION_DICT[closest_match[0]] if closest_match else word)

    translated_sentence = " ".join(translated_words)

    # --- Dynamically extract greetings from dictionary ---
    greetings = list(TRANSLATION_DICT.keys())  # Get all English phrases in the dictionary
    first_word = " ".join(words[:2]) if " ".join(words[:2]) in greetings else words[0]  # Check 2-word greetings

    if first_word in TRANSLATION_DICT:
        translated_sentence = f"{TRANSLATION_DICT[first_word].capitalize()}, {translated_sentence}"

    return translated_sentence.capitalize()

# --- SPEECH RECOGNITION FUNCTION ---
def audio_callback(indata, frames, time, status):
    """Handles real-time audio input."""
    if status:
        print(status, flush=True)
    audio_queue.put(bytes(indata))

def start_recognition(language="english"):
    """Starts real-time speech recognition in English or Hiligaynon."""
    global recognition_active
    if recognition_active:
        print("Recognition already active.")
        return

    recognition_active = True
    print(f"Listening in {language}...")

    recognizer = KaldiRecognizer(vosk_model_en if language == "english" else vosk_model_hiligaynon, 16000)

    def process_audio():
        """Processes audio and updates UI with translation."""
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
                    print("Recognition Error:", e)
                    break
        recognition_active = False

    threading.Thread(target=process_audio, daemon=True).start()

def stop_recognition():
    """Stops voice recognition."""
    global recognition_active
    recognition_active = False

# --- TEXT-TO-SPEECH FUNCTION ---
def speak_translation(text):
    """Speaks the translated text using offline TTS."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# --- UPDATE UI FUNCTION ---
def update_text(input_text, translated_text, *args):
    """Updates the UI with recognized speech and its translation."""
    app.input_text.text = input_text
    app.translation_output.text = translated_text

# --- KIVY APP UI ---
class TranslatorApp(App):
    def build(self):
        Window.fullscreen = 'auto'
        self.dark_mode = False  # Start in light mode

        # --- Main Layout ---
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        # --- Background Color Setup ---
        with main_layout.canvas.before:
            self.bg_color = Color(1, 1, 1, 1)  # Default to white
            self.rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
            main_layout.bind(size=self._update_rect, pos=self._update_rect)

        # --- Status Label ---
        self.status_label = Label(text="Press and hold to start translation", size_hint=(1, 0.1), font_size='20sp', color=(0, 0, 0, 1))
        main_layout.add_widget(self.status_label)

        # --- Text Fields ---
        self.input_text = TextInput(multiline=True, hint_text="Enter Text", size_hint=(1, 0.3), font_size='24sp', disabled=True)
        main_layout.add_widget(self.input_text)

        self.translation_output = TextInput(multiline=True, hint_text="Translation", disabled=True, size_hint=(1, 0.3), font_size='24sp')
        main_layout.add_widget(self.translation_output)

        # --- Button Layout ---
        button_layout = BoxLayout(size_hint=(1, 0.2), spacing=10)

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

        # Dark Mode Toggle Button (ToggleButton)
        self.dark_mode_button = ToggleButton(text="Dark Mode", size_hint=(1, 0.1))
        self.dark_mode_button.bind(on_press=self.toggle_dark_mode)
        main_layout.add_widget(self.dark_mode_button)

        return main_layout

    def on_button_down_english(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Listening in English..."
            start_recognition("english")

    def on_button_down_hiligaynon(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Listening in Hiligaynon..."
            start_recognition("hiligaynon")

    def on_button_up(self, instance, touch):
        stop_recognition()
        self.status_label.text = "Stopped Listening"

    def speak_translation_output(self, instance, touch):
        speak_translation(self.translation_output.text.strip())

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
        self.speak_button.source = "assets/speaker_icon_gray.png" if self.dark_mode else "assets/speaker_icon.png"

        # 🔹 Update toggle button text
        self.dark_mode_button.text = "Light Mode" if self.dark_mode else "Dark Mode"

    def _update_rect(self, instance, value):
        """Ensures background updates dynamically when resizing."""
        self.rect.size = instance.size
        self.rect.pos = instance.pos

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()
