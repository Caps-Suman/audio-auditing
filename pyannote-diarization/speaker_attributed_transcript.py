import html
import datetime
from typing import List, Dict

def seconds_to_timestamp(seconds: float) -> str:
    return str(datetime.timedelta(seconds=int(seconds)))

def match_diarization_with_transcript(diarization: List[Dict], whisper_segments: List[Dict]) -> str:
    """
    Match Whisper transcription segments to diarized speaker segments.
    Returns HTML-formatted transcript with speaker classes.
    """
    output_lines = []

    for segment in whisper_segments:
        text_start = segment['start']
        speaker = "Unknown"

        for d in diarization:
            if d["start"] <= text_start < d["end"]:
                speaker = d["speaker"]
                break

        className = "agentClass" if speaker == "SPEAKER_00" else "customerClass"
        timestamp = seconds_to_timestamp(segment["start"])
        escaped_text = html.escape(segment["text"].strip())

        block = f"""
        <div class=\"{className}\">
            <span class=\"timeClass\">{timestamp}</span>
            <span class=\"speakerClass\">{speaker}</span>
            <span class=\"textClass\">{escaped_text}</span>
        </div>
        """
        output_lines.append("".join(line.strip() for line in block.splitlines()))

    return "".join(output_lines)
