from TTS.api import TTS
import sounddevice as sd
import numpy as np

# Load the TTS model (offline)
tts = TTS("tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False).to("cpu")

# Generate speech waveform
audio_output = tts.tts(text="Hello, this is Coqui speaking directly!")

# Play the audio using sounddevice
sd.play(np.array(audio_output), samplerate=22050)
sd.wait()  # Wait until playback is finished
