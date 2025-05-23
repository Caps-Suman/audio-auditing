import gc
import threading
import torch
import whisper
from typing import List, Dict

# Load the model once (use "base", "medium", or "large"), change to "large" for better accuracy
# model = whisper.load_model("base")

# def transcribe_audio(file_path: str) -> str:
#     result = model.transcribe(file_path)
#     return result.get("text", "")

class WhisperModelPool:
    _model = None
    _lock = threading.Lock()

    @classmethod
    def get_model(cls, model_size="base"):
        with cls._lock:
            if cls._model is None:
                print("[WhisperPool] Loading Whisper model...")
                cls._model = whisper.load_model(model_size)
            return cls._model

    @classmethod
    def clear_model(cls):
        with cls._lock:
            if cls._model:
                print("[WhisperPool] Unloading Whisper model...")
                del cls._model
                cls._model = None
                gc.collect()

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    

def transcribe_audio_whisper(audio_path: str) -> List[Dict]:
    """
    Transcribes audio using OpenAI Whisper via a shared model pool.
    Returns a list of segments with start time and text.
    Spanish : language="es"
    English : language="en"
    """
    try:
        model = WhisperModelPool.get_model()
        result = model.transcribe(audio_path, language="en", verbose=False)

        segments = result.get("segments", [])
        return [
            {"start": seg["start"], "text": seg["text"].strip()}
            for seg in segments
        ]
    except Exception as e:
        print(f"[Whisper Error] {e}")
        return []