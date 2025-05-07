import os, tempfile, shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from services.transcript_utils import format_transcript_with_speakers
from services.whisper_service import transcribe_audio
from services.gpt_service import extract_audit_fields_from_text_using_local_llm, extract_audit_fields_from_text_using_openai
from services.audio_format_handler import transcode_to_whisper_wav

router = APIRouter()

@router.post("/audio")
async def extract_from_audio(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in [".wav", ".mp3", ".m4a", ".ogg", ".webm", ".sln"]:
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    audio_path = None
    transcoded_path = None

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(file.file, tmp)
            audio_path = tmp.name

        # Transcode to Whisper-compatible format if needed
        transcoded_path = transcode_to_whisper_wav(audio_path)

        # Transcribe the clean .wav audio
        transcript = transcribe_audio(transcoded_path)

        # Extract audit fields from transcript
        audit_data = extract_audit_fields_from_text_using_local_llm(transcript)
        # audit_data = extract_audit_fields_from_text_using_openai(transcript)
        formatted_transcript = format_transcript_with_speakers(transcript)
        
        return JSONResponse(content={
            "transcript": formatted_transcript,
            "audit_fields": audit_data
        })

    finally:
        # Cleanup temp files
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if transcoded_path and os.path.exists(transcoded_path):
            os.remove(transcoded_path)
