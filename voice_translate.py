import sounddevice as sd
import queue
import json
import vosk
from langdetect import detect

# Vosk Model Setup
MODEL_PATH = "vosk_model"
vosk_model = vosk.Model(MODEL_PATH)
recognizer = vosk.KaldiRecognizer(vosk_model, 16000)

# Audio Recording Setup
q = queue.Queue()

def callback(indata, frames, time, status):
    """Audio stream callback"""
    if status:
        print(status)
    q.put(bytes(indata))

# Translation Dictionary
TRANSLATION_DICT = {
    "hello": "kumusta",
    "goodbye": "paalam",
    "thank you": "salamat",
    "how are you": "kamusta ka",
    "I love you": "ginahigugma ta ka",
    "kumusta": "hello",
    "paalam": "goodbye",
    "salamat": "thank you",
    "kamusta ka": "how are you",
    "ginahigugma ta ka": "I love you"
}

def detect_language(text):
    """Detect if the text is English or Hiligaynon"""
    try:
        return detect(text)
    except:
        return "unknown"

def translate_text(text):
    """Translate between English and Hiligaynon"""
    return TRANSLATION_DICT.get(text.lower(), "Translation not found")

def recognize_speech():
    """Records and processes voice input"""
    print("Press ENTER and speak...")

    input("Press ENTER to start recording...")
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                           channels=1, callback=callback):
        audio_data = b""
        print("Listening... Speak now.")

        while True:
            try:
                audio_data += q.get(timeout=5)
            except queue.Empty:
                break

        recognizer.AcceptWaveform(audio_data)
        result = json.loads(recognizer.Result())
        return result.get("text", "")

def main():
    print("Ready. Press ENTER to start recording.")

    while True:
        text = recognize_speech()
        if text:
            print(f"Recognized: {text}")
            lang = detect_language(text)
            
            if lang == "en":
                translated = translate_text(text)
                print(f"Translated to Hiligaynon: {translated}")
            elif lang == "tl":  # Hiligaynon may sometimes be detected as Tagalog
                translated = translate_text(text)
                print(f"Translated to English: {translated}")
            else:
                print("Could not detect language.")

if __name__ == "__main__":
    main()
