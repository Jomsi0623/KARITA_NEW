from TTS.utils.downloaders import load_model_path

model_path = load_model_path("tts_models/en/ljspeech/tacotron2-DDC")
print("Model is stored at:", model_path)
