import os
import subprocess
import uuid
import tempfile
from typing import Tuple

WHISPER_FORMAT = {
    "format": "wav",
    "codec": "pcm_s16le",
    "sample_rate": 16000,
    "channels": 1
}

def transcode_to_whisper_wav(input_path: str) -> str:
    """
    Converts an audio file to Whisper-compatible .wav if needed.
    Returns same path if already compatible.
    """
    if input_path.lower().endswith(".wav") and is_whisper_compatible_wav(input_path):
        return input_path  #  Skip transcoding

    output_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")

    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-acodec", WHISPER_FORMAT["codec"],
        "-ar", str(WHISPER_FORMAT["sample_rate"]),
        "-ac", str(WHISPER_FORMAT["channels"]),
        output_path
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed to transcode audio: {e.stderr.decode()}")

def is_whisper_compatible_wav(input_path: str) -> bool:
    """
    Returns True if the file is a .wav file with pcm_s16le codec, 16000 Hz sample rate, and mono.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,sample_rate,channels",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        codec, sample_rate, channels = result.stdout.decode().strip().split("\n")
        return codec == "pcm_s16le" and sample_rate == "16000" and channels == "1"
    except Exception:
        return False


def detect_codec_with_ffprobe(input_path: str) -> Tuple[str, str]:
    """
    Uses ffprobe to detect codec and format.
    Returns (format, codec) tuple.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        codec = result.stdout.decode().strip()
        format_name = os.path.splitext(input_path)[-1].lower()
        return format_name, codec
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFprobe failed: {e.stderr.decode()}")
