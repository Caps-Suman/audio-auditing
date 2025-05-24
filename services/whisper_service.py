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
    

import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
USE_FASTER = os.getenv("USE_FASTER_WHISPER", "true").lower() == "true"

def transcribe_audio_hybrid_whisper(audio_path: str) -> List[Dict]:
    """
    Transcribes audio using either OpenAI Whisper or faster-whisper.
    Returns list of dicts with segment-level timestamps.
    """
    try:
        if USE_FASTER:
            print("[Whisper] Using faster-whisper for transcription")
            try:
                from faster_whisper import WhisperModel as FastWhisperModel
                model = FastWhisperModel("base", device="cuda" if torch.cuda.is_available() else "cpu", compute_type="int8")
                segments, _ = model.transcribe(audio_path)
                return [{"start": seg.start, "text": seg.text.strip()} for seg in segments]
            except ImportError:
                print("[Whisper Warning] faster-whisper not installed, falling back to OpenAI Whisper")
            except Exception as fe:
                print(f"[Whisper Faster Error] {fe}, falling back to OpenAI Whisper")

        else:
            print("[Whisper] Using openai-whisper for transcription")
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
