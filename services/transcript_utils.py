from typing import List
import datetime

def seconds_to_timestamp(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS format."""
    return str(datetime.timedelta(seconds=int(seconds)))

def format_transcript_with_speakers(segments: List[dict]) -> str:
    """
    Format Whisper segments with speaker labels and start time.
    Input: list of dicts like {'start': float, 'text': str}
    Output: formatted transcript string
    """
    # Spanish + English cues to identify speakers
    agent_cues = [
        "thank you for calling", "how may i", "can i have", "let me", "i can help", "your order is",
        "this is", "have a nice day", "you're welcome", "we can process",
        "bienvenido al centro", "le puedo ayudar", "dígame", "está necesitando", "le recuerdo"
    ]

    customer_cues = [
        "my name is", "i'd like", "sure", "yes", "okay", "that's fine", "i want", "i need",
        "thank you", "i called", "i'm calling", "i have a question",
        "me llamo", "necesito", "mi abuela", "yo hablé", "fui a llevar",
        "tengo el formulario", "lo fui a llevar"
    ]

    transcript_lines = []
    last_speaker = "Agent"  # Default to Agent at the start

    for seg in segments:
        text = seg["text"].strip()
        lower = text.lower()
        start_time = seconds_to_timestamp(seg["start"])

        # Detect speaker
        speaker = last_speaker
        if any(phrase in lower for phrase in customer_cues):
            speaker = "User"
        elif any(phrase in lower for phrase in agent_cues):
            speaker = "Assistant"
        last_speaker = speaker

        # Style per speaker
        className = "assistantClass" if speaker == "Assistant" else "userClass"

        # HTML block
        html = f"""
        <div class="{className}">
            <span class="timeClass">{start_time}</span>
            <span class="speakerClass">{speaker}</span>
            <span class="textClass">{text}</span>
        </div>
        """
        clean_html = "".join(line.strip() for line in html.splitlines())
        transcript_lines.append(clean_html)

    return "".join(transcript_lines)
