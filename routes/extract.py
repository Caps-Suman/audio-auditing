import os, tempfile, shutil
from typing import List
from pydantic import BaseModel
import requests
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from services.transcript_utils import format_transcript_with_speakers
from services.whisper_service import transcribe_audio
from services.gpt_service import evaluate_rules_with_gpt, extract_audit_fields_from_text_using_local_llm, extract_audit_fields_from_text_using_openai
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

class ParameterRule(BaseModel):
    id: str
    name: str
    ruleList: List[str]

class AuditRequest(BaseModel):
    audioUrl: str
    sampleId: str
    parameter: List[ParameterRule]


@router.post("/analyze-audio")
async def audit_call(request: AuditRequest):
    audio_path = None
    transcoded_path = None

    try:
        # Download the audio
        response = requests.get(request.audioUrl, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download audio")

        # Save audio to temp file
        ext = os.path.splitext(request.audioUrl)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(response.raw, tmp)
            audio_path = tmp.name

        # Transcode to Whisper-compatible format if needed
        transcoded_path = transcode_to_whisper_wav(audio_path)

        # Transcribe the clean .wav audio
        transcript = transcribe_audio(transcoded_path)

        # Step 4: GPT-based parameter evaluations
        evaluations = []
        for param in request.parameter:
            result = evaluate_rules_with_gpt(transcript, param.ruleList)
            evaluations.append({
                "id": param.id,
                "name": param.name,
                "rules": result  # detailed GPT evaluation
            })

        # Step 5: Return structured response
        return {
            "sampleId": request.sampleId,
            "transcript": transcript,
            "evaluations": evaluations
        } 
     
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if transcoded_path and os.path.exists(transcoded_path):
            os.remove(transcoded_path)
