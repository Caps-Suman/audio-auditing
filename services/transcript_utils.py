import re

def format_transcript_with_speakers(transcript: str) -> str:
    """
    Attempt to label speakers based on common phrases for Agent and Customer.
    """

    agent_cues = [
        "thank you for calling",
        "how may i",
        "can i have",
        "let me",
        "your order is",
        "i can help",
        "have a nice day",
    ]

    customer_cues = [
        "i'd like",
        "my name is",
        "sure",
        "yes",
        "okay",
        "that's fine",
        "i want",
        "i was thinking",
        "thank you",
    ]

    # Split into sentences based on punctuation followed by a capital letter
    sentences = re.split(r"(?<=[.?!])\s+(?=[A-Z])", transcript.strip())
    formatted_lines = []

    for sentence in sentences:
        sentence_lower = sentence.lower()
        speaker = "Agent"  # default

        if any(phrase in sentence_lower for phrase in customer_cues):
            speaker = "Customer"
        elif any(phrase in sentence_lower for phrase in agent_cues):
            speaker = "Agent"

        formatted_lines.append(f"{speaker}: {sentence.strip()}")

    return "\n".join(formatted_lines)