from transformers import pipeline
import librosa
import io
from utils import load_config
config = load_config()

def convert_bytes_to_array(audio_bytes):
    try:
        audio_bytes = io.BytesIO(audio_bytes)
        audio, sample_rate = librosa.load(audio_bytes)
        print(f"Loaded audio sample rate: {sample_rate}")
        return audio
    except Exception as e:
        print(f"Error converting audio bytes to array: {e}")
        raise ValueError(f"Invalid or corrupted audio file: {e}")

def transcribe_audio(audio_bytes):
    if not audio_bytes:
        return "[Error: Empty audio input received]"
        
    device = "cpu"
    try:
        pipe = pipeline(
            task="automatic-speech-recognition",
            model=config["whisper_model"],
            chunk_length_s=30,
            device=device,
        )

        audio_array = convert_bytes_to_array(audio_bytes)
        prediction = pipe(audio_array, batch_size=1)["text"]
        return prediction
    except Exception as e:
        print(f"Error during audio transcription: {e}")
        return f"[Transcription Error: {str(e)}]"