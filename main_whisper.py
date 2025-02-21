import whisper
import sounddevice as sd
import numpy as np
import queue
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from functools import partial

# Load Whisper model
model = whisper.load_model("small")  # Choose model size: tiny, base, small, medium, large

# Global variables
recognition_active = False
audio_queue = queue.Queue()

# Audio callback function
def audio_callback(indata, frames, time, status):
    if status:
        print(status, flush=True)
    audio_queue.put(indata.copy())

# Process audio data
def process_audio_stream():
    global recognition_active
    with sd.InputStream(samplerate=16000, channels=1, callback=audio_callback):
        while recognition_active:
            if not audio_queue.empty():
                audio_data = []
                while not audio_queue.empty():
                    audio_data.append(audio_queue.get())
                audio_data = np.concatenate(audio_data, axis=0)

                # Convert audio data to float32 numpy array
                audio_data = audio_data.astype(np.float32) / 32768.0

                # Perform transcription
                result = model.transcribe(audio_data, fp16=False)
                text = result['text'].strip()
                if text:
                    Clock.schedule_once(partial(update_text, text), 0)

# Start Recognition
def start_recognition():
    global recognition_active
    if recognition_active:
        return  # Prevent multiple threads from starting
    recognition_active = True
    threading.Thread(target=process_audio_stream, daemon=True).start()

# Stop Recognition
def stop_recognition():
    global recognition_active
    recognition_active = False

# Update UI Text
def update_text(transcribed_text, *args):
    app.input_text.text = transcribed_text
    app.translation_output.text = ""  # Clear previous translation

# Kivy Application
class TranslatorApp(App):
    def build(self):
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.status_label = Label(text="Press and hold to start transcription", size_hint=(1, 0.1), font_size='20sp')
        main_layout.add_widget(self.status_label)

        input_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.3))

        self.input_text = TextInput(multiline=True, hint_text="Transcribed Text", size_hint=(0.9, 1), readonly=True)
        input_layout.add_widget(self.input_text)

        main_layout.add_widget(input_layout)

        self.translation_output = TextInput(multiline=True, hint_text="Translation", readonly=True, size_hint=(1, 0.3))
        main_layout.add_widget(self.translation_output)

        self.control_button = Button(text="Hold to Speak", size_hint=(1, 0.07))
        self.control_button.bind(on_touch_down=self.on_button_down)
        self.control_button.bind(on_touch_up=self.on_button_up)
        main_layout.add_widget(self.control_button)

        return main_layout

    def on_button_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Listening..."
            start_recognition()

    def on_button_up(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.status_label.text = "Stopped Listening"
            stop_recognition()

# Run the app
if __name__ == "__main__":
    app = TranslatorApp()
    app.run()
