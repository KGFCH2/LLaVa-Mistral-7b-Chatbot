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
        chunk_length_s=30,
        device=device,
    )

    # Load audio from bytes using librosa
    audio, rate = librosa.load(audio_bytes, sr=16000)

    # Perform the transcription
    prediction = pipe(audio, batch_size=8)["text"]

    return prediction