import sounddevice as sd
import queue
import json
from vosk import Model, KaldiRecognizer

MODEL_PATH = "vosk_model"
vosk_model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(vosk_model, 16000)
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=callback):
    print("Say something...")
    while True:
        try:
            data = q.get(timeout=5)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                print(f"Recognized: {result['text']}")
        except queue.Empty:
            print("No audio detected")
