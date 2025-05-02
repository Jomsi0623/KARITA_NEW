import os
import queue
import threading
import json
import string
import difflib
import re
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from functools import partial
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.togglebutton import ToggleButton
from tts_component import TextToSpeechEngine
from multiprocessing import Process, Pipe
from button_controller import start_button_controller
import time
from kivy.uix.image import Image
from kivy.uix.modalview import ModalView
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, RoundedRectangle

# --- VOSK MODELS ---
MODEL_PATH_EN = "vosk_model"
MODEL_PATH_HILIGAYNON = "vosk_model_ph"

# TTS
tts_engine = TextToSpeechEngine()

if not os.path.exists(MODEL_PATH_EN) or not os.path.exists(MODEL_PATH_HILIGAYNON):
    print("Error: Vosk model not found! Check paths.")
    exit(1)

vosk_model_en = Model(MODEL_PATH_EN)
vosk_model_hiligaynon = Model(MODEL_PATH_HILIGAYNON)

# --- LOAD TRANSLATION DICTIONARY ---
with open("translation_dict.json", "r", encoding="utf-8") as f:
    raw_dict = json.load(f)

# --- GLOBAL VARIABLES ---
recognition_active = False
audio_queue = queue.Queue()

# Normalize keys in the dictionary
TRANSLATION_DICT = {
    k.strip().lower(): v.strip() for k, v in raw_dict.items()
}

# Normalize input text
def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text.strip()

# Translation function
def translate_text(text):
    print(f"[LOG] Translating text: {text}")
    original_text = text
    text = normalize_text(text)
    words = text.split()
    
    translated_words = []
    i = 0

    while i < len(words):
        match_found = False
        for phrase_len in range(len(words) - i, 0, -1):
            phrase = " ".join(words[i:i + phrase_len])

            # Exact match
            if phrase in TRANSLATION_DICT:
                translated_words.append(TRANSLATION_DICT[phrase])
                i += phrase_len
                match_found = True
                break

            # Fuzzy match
            close_matches = difflib.get_close_matches(phrase, TRANSLATION_DICT.keys(), n=1, cutoff=0.9)
            if close_matches:
                translated_words.append(TRANSLATION_DICT[close_matches[0]])
                i += phrase_len
                match_found = True
                break

        if not match_found:
            word = words[i]
            close_word = difflib.get_close_matches(word, TRANSLATION_DICT.keys(), n=1, cutoff=0.9)
            translated_words.append(TRANSLATION_DICT.get(close_word[0], word) if close_word else word)
            i += 1

    translated_sentence = " ".join(translated_words).capitalize()
    if not translated_sentence.strip():
        translated_sentence = "Translation not found"

    print(f"[LOG] Original: {original_text}")
    print(f"[LOG] Translated: {translated_sentence}")
    return translated_sentence

# --- SPEECH RECOGNITION FUNCTION ---
def audio_callback(indata, frames, time, status):
    if status:
        print(f"[ERROR] Audio callback status: {status}")
    audio_queue.put(bytes(indata))

def start_recognition(language="english"):
    global recognition_active
    if recognition_active:
        return

    recognition_active = True
    print(f"[LOG] Listening in {language}...")

    recognizer = KaldiRecognizer(vosk_model_en if language == "english" else vosk_model_hiligaynon, 16000)

    def process_audio():
        global recognition_active
        with sd.RawInputStream(samplerate=16000, blocksize=4096, dtype="int16", channels=1, callback=audio_callback):
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
                    print(f"[ERROR] Recognition error: {e}")
                    break
        recognition_active = False

    threading.Thread(target=process_audio, daemon=True).start()

def stop_recognition():
    global recognition_active
    recognition_active = False
    print("[LOG] Stopped recognition")

# --- UPDATE UI FUNCTION ---
def update_text(input_text, translated_text, *args):
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

        self.status_label = Label(text="KARITA", size_hint=(1, 0.1), font_size='50sp', color=(0, 0, 0, 1))
        main_layout.add_widget(self.status_label)

        ################# TRANSLATION INPUT START #################
        input_container = FloatLayout(size_hint=(1, 0.3))

        with input_container.canvas.before:
            Color(0.53, 0.81, 0.92, 1)  # Sky blue
            self.border_rect = RoundedRectangle(radius=[20], pos=input_container.pos, size=input_container.size)

            Color(0.9, 0.9, 0.9, 1)  # Light gray
            self.input_bg = RoundedRectangle(radius=[18], pos=(input_container.x + 2, input_container.y + 2),
                                            size=(input_container.width - 4, input_container.height - 4))

        def update_bg(instance, value):
            self.border_rect.pos = instance.pos
            self.border_rect.size = instance.size

            self.input_bg.pos = (instance.x + 5, instance.y + 5)
            self.input_bg.size = (instance.width - 10, instance.height - 10)

        input_container.bind(pos=update_bg, size=update_bg)

        self.input_text = TextInput(
            multiline=True,
            hint_text="Press button and speak",
            font_size='24sp',
            background_color=(0, 0, 0, 0),
            foreground_color=(0, 0, 0, 1),
            size_hint=(0.96, 0.9),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            disabled=True
        )

        input_container.add_widget(self.input_text)
        main_layout.add_widget(input_container)
        ################# TRANSLATION INPUT END #################

        # TRANSLATE ICON STARTS HERE
        icon_container = AnchorLayout(size_hint=(1, 0.1))
        self.translation_icon = Image(
            source='assets/translate_icon.png',
            size_hint=(None, None),
            size=(80, 80),
            allow_stretch=True,
            keep_ratio=True
        )
        icon_container.add_widget(self.translation_icon)
        main_layout.add_widget(icon_container)
        # TRANSLATE ICON ENDS HERE

        ################# TRANSLATION OUTPUT START #################
        output_container = FloatLayout(size_hint=(1, 0.3))

        with output_container.canvas.before:
            Color(0.53, 0.81, 0.92, 1)  # Sky blue
            self.border_rect_output = RoundedRectangle(radius=[20], pos=output_container.pos, size=output_container.size)

            Color(0.9, 0.9, 0.9, 1)  # Light gray
            self.output_bg = RoundedRectangle(radius=[18], pos=(output_container.x + 5, output_container.y + 5),
                                            size=(output_container.width - 10, output_container.height - 10))

        def update_output_bg(instance, value):
            self.border_rect_output.pos = instance.pos
            self.border_rect_output.size = instance.size

            self.output_bg.pos = (instance.x + 5, instance.y + 5)
            self.output_bg.size = (instance.width - 10, instance.height - 10)

        output_container.bind(pos=update_output_bg, size=update_output_bg)

        self.translation_output = TextInput(
            multiline=True,
            hint_text="Translation",
            font_size='24sp',
            background_color=(0, 0, 0, 0),
            foreground_color=(0, 0, 0, 1),
            size_hint=(0.96, 0.9),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            disabled=True
        )

        output_container.add_widget(self.translation_output)
        main_layout.add_widget(output_container)
        ################# TRANSLATION OUTPUT END #################

        # self.loader_modal = ModalView(size_hint=(None, None), size=(200, 200), background_color=(0, 0, 0, 0.5), auto_dismiss=False)
        # loader_image = Image(source='assets/loader.gif', anim_delay=0.05)
        # self.loader_modal.add_widget(loader_image)

        self.loader_modal = ModalView(size_hint=(1, 1), background_color=(0, 0, 0, 0.5), auto_dismiss=False)
        anchor = AnchorLayout()
        loader_image = Image(source='assets/loader.gif', anim_delay=0.05, size_hint=(None, None), size=(150, 150))
        anchor.add_widget(loader_image)
        self.loader_modal.add_widget(anchor)

        # Dark mode toggle
        self.dark_mode_button = ToggleButton(text="Dark Mode", size_hint=(1, 0.1))
        self.dark_mode_button.bind(on_press=self.toggle_dark_mode)
        main_layout.add_widget(self.dark_mode_button)

        # Start hardware button monitoring
        self.setup_hardware_buttons()

        return main_layout

    def setup_hardware_buttons(self):
        """Start the hardware button monitoring in a separate process"""
        self.parent_conn, child_conn = Pipe()
        self.hardware_process = Process(
            target=start_button_controller, 
            args=(child_conn,)
        )
        self.hardware_process.start()
        
        threading.Thread(target=self.handle_hardware_messages, daemon=True).start()
        print("[HARDWARE] Started hardware button monitoring")

    def handle_hardware_messages(self):
        """Handle messages from the hardware controller"""
        while True:
            if self.parent_conn.poll():
                command, language = self.parent_conn.recv()
                if command == 'start':
                    if language == 'english':
                        Clock.schedule_once(lambda dt: self.update_hint_text("Listening to English..."))
                        start_recognition("english")
                    elif language == 'hiligaynon':
                        Clock.schedule_once(lambda dt: self.update_hint_text("Listening to Hiligaynon..."))
                        start_recognition("hiligaynon")
                elif command == 'stop':
                    Clock.schedule_once(lambda dt: self.update_hint_text("Press button and speak"))
                    stop_recognition()
                elif command == 'speak':
                    text = self.translation_output.text.strip()
                    if text:
                        Clock.schedule_once(lambda dt: self.show_loader())
                        Clock.schedule_once(lambda dt: self.start_speaking(text), 2)
            time.sleep(0.1)

    def show_loader(self):
        if not self.loader_modal.parent:
            self.loader_modal.open()

    def hide_loader(self):
        if self.loader_modal.parent:
            self.loader_modal.dismiss()

    def start_speaking(self, text):
        Clock.schedule_once(lambda dt: self.hide_loader())
        threading.Thread(target=self.speak_text, args=(text,), daemon=True).start()

    def speak_and_hide_loader(self, text):
        tts_engine.speak(text)
        Clock.schedule_once(lambda dt: self.show_loader(False))

    def speak_text(self, text):
        tts_engine.speak(text)

    def update_hint_text(self, text):
        """Update hint text safely on the main thread"""
        self.input_text.hint_text = text
        self.input_text.text = ""

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def toggle_dark_mode(self, instance, *args):
        self.dark_mode = instance.state == 'down'
        color = (0, 0, 0, 1) if self.dark_mode else (1, 1, 1, 1)
        text_color = (1, 1, 1, 1) if self.dark_mode else (0, 0, 0, 1)

        with self.root.canvas.before:
            self.bg_color.rgb = color[:3]
        
        self.status_label.color = text_color
        self.input_text.foreground_color = text_color
        self.translation_output.foreground_color = text_color
        self.dark_mode_button.text = "Light Mode" if self.dark_mode else "Dark Mode"

        self.translation_icon.source = 'assets/translate_icon_gray.png' if self.dark_mode else 'assets/translate_icon.png'
        self.translation_icon.reload()

    def on_stop(self):
        if hasattr(self, 'hardware_process'):
            self.hardware_process.terminate()
            self.hardware_process.join()
            print("[HARDWARE] Stopped hardware button monitoring")

# Make app instance accessible globally
app = None

if __name__ == "__main__":
    app = TranslatorApp()
    app.run()
    
