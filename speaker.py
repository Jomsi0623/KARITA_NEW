import piper
import sounddevice as sd
import numpy as np

# Load the voice model (Make sure you have downloaded it!)
engine = piper.PiperVoice("piper/models/en_US-lessac-medium.onnx")  # Change filename if needed

# Convert text to raw PCM audio
pcm_audio, sample_rate = engine.synthesize("Hello! This is a test.", return_audio=True)

# Convert PCM data to NumPy array and play it directly
sd.play(np.array(pcm_audio, dtype=np.int16), samplerate=sample_rate)
sd.wait()  # Wait for playback to finish
