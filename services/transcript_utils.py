import html
from typing import List
import datetime

def seconds_to_timestamp(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS format."""
    return str(datetime.timedelta(seconds=int(seconds)))

def format_transcript_with_speakers(segments: List[dict]) -> str:
    """
    Format Whisper segments with speaker labels and start time.
    Input: list of dicts like {'start': float, 'text': str}
    Output: formatted transcript HTML string.
    """
    # Cue phrases
    agent_cues = [
        "thank you for calling", "how may i", "can i have", "let me", "i can help", "your order is",
        "this is", "have a nice day", "you're welcome", "we can process", "please hold",
        "i'm the doctor", "you're speaking with", "how can i assist", "what can i do for you",
        "we're open", "i will check", "you can send it", "visiting hours", "prescription is ready",
        "i can check", "we look forward", "have a great day", "mailing address", "insurance coverage"
    ]

    customer_cues = [
        "my name is", "i'd like", "sure", "yes", "okay", "that's fine", "i want", "i need",
        "thank you", "i called", "i'm calling", "i have a question", "me llamo", "necesito",
        "mi abuela", "yo hablé", "fui a llevar", "tengo el formulario", "lo fui a llevar",
        "i was wondering", "i was in the hospital", "my number is", "i take", "my doctor said",
        "my birth date is", "i need help", "i have bills", "can i", "do you offer", "my address is"
    ]


    transcript_lines = []

    for seg in segments:
        text = seg["text"].strip()
        lower = text.lower()
        start_time = seconds_to_timestamp(seg["start"])

        # Determine speaker
        if any(phrase in lower for phrase in customer_cues):
            speaker = "Customer"
        elif any(phrase in lower for phrase in agent_cues):
            speaker = "Agent"
        else:
            speaker = "Agent"  # Default fallback

        # Class name
        className = (
            "agentClass" if speaker == "Agent"
            else "customerClass" if speaker == "Customer"
            else "agentClass"
        )

        # Escape HTML
        escaped_text = html.escape(text)

        # HTML block
        html_block = f"""
        <div class="{className}">
            <span class="timeClass">{start_time}</span>
            <span class="speakerClass">{speaker}</span>
            <span class="textClass">{escaped_text}</span>
        </div>
        """
        clean_html = "".join(line.strip() for line in html_block.splitlines())
        transcript_lines.append(clean_html)

    return "".join(transcript_lines)
