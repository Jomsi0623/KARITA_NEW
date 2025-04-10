import subprocess

class TextToSpeechEngine:
    def __init__(self, voice='en+f3+klatt3', speed=130, pitch=60):
        self.voice = voice
        self.speed = speed
        self.pitch = pitch
        #PATH NA DI KA espeak MO MEG ISLI LANG
        self.espeak_path = r"C:\Program Files (x86)\eSpeak\command_line\espeak.exe"
        print(f"[TTS] Using eSpeak at: {self.espeak_path}")

    def speak(self, text):
        print(f"[TTS] Speaking: {text}")
        subprocess.run([
            self.espeak_path,
            f"-v{self.voice}",
            f"-s{self.speed}",
            f"-p{self.pitch}",
            text
        ])
