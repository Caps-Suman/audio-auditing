import whisper
from typing import List, Dict

# Load the model once (use "base", "medium", or "large"), change to "large" for better accuracy
model = whisper.load_model("base")

def transcribe_audio(file_path: str) -> str:
    result = model.transcribe(file_path)
    return result.get("text", "")

def transcribe_audio_whisper(audio_path: str) -> List[Dict]:
    """
    Transcribes audio using OpenAI Whisper with automatic language detection.
    Returns a list of segments with 'start' (in seconds) and 'text' (transcribed phrase).
    Logs only the language code.
    """
    result = model.transcribe(audio_path, verbose=False)

    # Extract and format segments
    segments = result.get("segments", [])
    return [
        {"start": seg["start"], "text": seg["text"].strip()}
        for seg in segments
    ]