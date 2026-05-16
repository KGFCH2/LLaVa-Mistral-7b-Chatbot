<<<<<<< HEAD
from transformers import pipeline
import librosa
import io
from utils import load_config
config = load_config()

def convert_bytes_to_array(audio_bytes):
    audio_bytes = io.BytesIO(audio_bytes)
    audio, sample_rate = librosa.load(audio_bytes)
    print(sample_rate)
    return audio

def transcribe_audio(audio_bytes):
    device = "cpu"
    pipe = pipeline(
        task="automatic-speech-recognition",
        model=config["whisper_model"],
=======
# pyrefly: ignore [missing-import]
import torch 
from transformers import pipeline # pyrefly: ignore [missing-import]
import librosa # pyrefly: ignore [missing-import]


def transcribe_audio(audio_bytes):
    # Use the openai/whisper-tiny model for fast transcription
    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    pipe = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-tiny",
>>>>>>> cf049224449266d41007d6fac7ce8805e96a22cb
        chunk_length_s=30,
        device=device,
    )

<<<<<<< HEAD
    audio_array = convert_bytes_to_array(audio_bytes)
    prediction = pipe(audio_array, batch_size=1)["text"]
=======
    # Load audio from bytes using librosa
    audio, rate = librosa.load(audio_bytes, sr=16000)

    # Perform the transcription
    prediction = pipe(audio, batch_size=8)["text"]
>>>>>>> cf049224449266d41007d6fac7ce8805e96a22cb

    return prediction