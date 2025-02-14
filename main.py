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
from kivy.clock import Clock
from functools import partial
import json

# Vosk Model Setup
MODEL_PATH = "vosk_model"
if not os.path.exists(MODEL_PATH):
    print("Model not found! Please check the path.")
    exit(1)
vosk_model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(vosk_model, 16000)

# Global variables
recognition_active = False
audio_queue = queue.Queue()

# Audio callback function
def audio_callback(indata, frames, time, status):
    if status:
        print(status, flush=True)
    audio_queue.put(bytes(indata))

# Open Translation Dictionary JSON
with open("translation_dict.json", "r", encoding="utf-8") as file:
    TRANSLATION_DICT = json.load(file)

# Translate Text
def translate_text(text):
    text = text.lower()
    
    # Normalize dictionary to lowercase for better matching
    normalized_dict = {k.lower(): v for k, v in TRANSLATION_DICT.items()}
    reverse_dict = {v.lower(): k for k, v in TRANSLATION_DICT.items()}

    if text in normalized_dict:
        return normalized_dict[text]
    elif text in reverse_dict:
        return reverse_dict[text]

    return "Translation not found"

# Start Recognition
def start_recognition():
    global recognition_active
    if recognition_active:
        return  # Prevent multiple threads from starting

    recognition_active = True
    def process_audio_stream():
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=audio_callback):
            while recognition_active:
                try:
                    data = audio_queue.get(timeout=1)
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result()).get("text", "").strip()
                        if result:
                            translated = translate_text(result)
                            Clock.schedule_once(partial(update_text, result, translated), 0)
                except queue.Empty:
                    continue

    threading.Thread(target=process_audio_stream, daemon=True).start()

# Stop Recognition
def stop_recognition():
    global recognition_active
    recognition_active = False

# Update UI Text
def update_text(input_text, translated_text, *args):
    app.input_text.text = input_text
    app.translation_output.text = translated_text

# Kivy Application
class TranslatorApp(App):
    def build(self):
        self.dark_mode = False
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.status_label = Label(text="Press and hold to start translation", size_hint=(1, 0.1), font_size='20sp')
        main_layout.add_widget(self.status_label)
        
        input_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.3))
        
        self.input_text = TextInput(multiline=True, hint_text="Enter Text", size_hint=(0.9, 1), background_color=(1, 1, 1, 1))
        self.input_text.bind(focus=self.show_keyboard)
        input_layout.add_widget(self.input_text)
        
        self.translate_button = Button(text="Translate", size_hint=(0.1, 1))
        self.translate_button.bind(on_press=self.manual_translate)
        input_layout.add_widget(self.translate_button)
        
        main_layout.add_widget(input_layout)
        
        self.translation_output = TextInput(multiline=True, hint_text="Translation", readonly=True, size_hint=(1, 0.3), background_color=(1, 1, 1, 1))
        main_layout.add_widget(self.translation_output)
        
        self.control_button = Button(text="Hold to Speak", size_hint=(1, 0.07))
        self.control_button.bind(on_touch_down=self.on_button_down)
        self.control_button.bind(on_touch_up=self.on_button_up)
        main_layout.add_widget(self.control_button)
        
        # self.dark_mode_button = Button(text="Toggle Dark Mode", size_hint=(1, 0.1))
        # self.dark_mode_button.bind(on_press=self.toggle_dark_mode)
        # main_layout.add_widget(self.dark_mode_button)
        
        self.main_layout = main_layout
        return main_layout

    def show_keyboard(self, instance, value):
        if value:
            instance.focus = True
    
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

    # def toggle_dark_mode(self, instance):
    #     self.dark_mode = not self.dark_mode
    #     if self.dark_mode:
    #         self.main_layout.background_color = (0, 0, 0, 1)  # Dark mode
    #         self.status_label.color = (1, 1, 1, 1)
    #         self.control_button.background_color = (0.2, 0.2, 0.2, 1)
    #         self.dark_mode_button.background_color = (0.2, 0.2, 0.2, 1)
    #     else:
    #         self.main_layout.background_color = (1, 1, 1, 1)  # Light mode
    #         self.status_label.color = (0, 0, 0, 1)
    #         self.control_button.background_color = (0.8, 0.8, 0.8, 1)
    #         self.dark_mode_button.background_color = (0.8, 0.8, 0.8, 1)
        
    #     if not self.dark_mode:
    #         self.input_text.background_color = (1, 1, 1, 1)
    #         self.translation_output.background_color = (1, 1, 1, 1)
    #         self.input_text.foreground_color = (0, 0, 0, 1)
    #         self.translation_output.foreground_color = (0, 0, 0, 1)
    #         self.input_text.border = (0, 0, 1, 1)
    #         self.translation_output.border = (0, 0, 1, 1)

# Run the app
if __name__ == "__main__":
    app = TranslatorApp()
    app.run()