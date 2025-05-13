from dotenv import load_dotenv
from pyannote.audio import Pipeline
import os
from typing import List, Dict

# <-------- How to use the Hugging Face token: check read me file -------->
load_dotenv()
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

# Load the diarization pipeline
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization",
    use_auth_token=HUGGINGFACE_TOKEN
)

def diarize_audio(file_path: str) -> List[Dict]:
    """
    Perform speaker diarization on an audio file.
    Returns a list of segments with speaker labels and timestamps.
    """
    diarization = pipeline(file_path)

    results = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        results.append({
            "start": turn.start,
            "end": turn.end,
            "speaker": speaker,
        })

    return results
