# tts_engine.py

import sounddevice as sd
import numpy as np
from TTS.api import TTS

class TextToSpeechEngine:
    def __init__(self, model_name="tts_models/en/ljspeech/tacotron2-DDC"):
        print("[TTS] Initializing Text-to-Speech Engine...")
        self.tts = TTS(model_name, progress_bar=False).to("cpu")
        print("[TTS] TTS Engine initialized.")

    def speak(self, text):
        print(f"[TTS] Speaking: {text}")
        audio_output = self.tts.tts(text=text)
        sd.play(np.array(audio_output), samplerate=22050)
        sd.wait()
