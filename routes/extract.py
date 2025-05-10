import os, tempfile, shutil
from typing import List, Optional
from pydantic import BaseModel
import requests
from fastapi import APIRouter, File, UploadFile, HTTPException, logger
from fastapi.responses import JSONResponse

from services.transcript_utils import format_transcript_with_speakers
from services.whisper_service import transcribe_audio
from services.gpt_service import evaluate_rules_with_gpt, evaluate_rules_with_gpt_using_requests
# from services.gpt_service import evaluate_rules_with_local_llm, extract_audit_fields_from_text_using_local_llm, extract_audit_fields_from_text_using_openai
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
        # audit_data = extract_audit_fields_from_text_using_local_llm(transcript)
        # audit_data = extract_audit_fields_from_text_using_openai(transcript)
        formatted_transcript = format_transcript_with_speakers(transcript)
        
        return JSONResponse(content={
            "transcript": formatted_transcript,
            # "audit_fields": audit_data
        })

    finally:
        # Cleanup temp files
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if transcoded_path and os.path.exists(transcoded_path):
            os.remove(transcoded_path)

class ParameterRule(BaseModel):
    id: str
    name: Optional[str] = None
    ruleList: List[str]

class AuditRequest(BaseModel):
    audioUrl: str
    sampleId: str
    parameter: List[ParameterRule]


@router.post("/analyze-audio")
async def audit_call(request: AuditRequest):
    # print(f"Received request: {request}")
    audio_path = None
    transcoded_path = None
    webhook_url = os.getenv("WEBHOOK_URL")

    if not webhook_url:
        raise HTTPException(status_code=500, detail="Webhook URL not configured.")

    try:
        # Step 1: Download the audio
        response = requests.get(request.audioUrl, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download audio")

        # Step 2: Save audio to temp file
        ext = os.path.splitext(request.audioUrl)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(response.raw, tmp)
            audio_path = tmp.name

        # Step 3: Transcode if needed
        transcoded_path = transcode_to_whisper_wav(audio_path)

        # Step 4: Transcribe
        transcript = transcribe_audio(transcoded_path)

        # Step 5: Evaluate parameters
        evaluations = []
        for param in request.parameter:
            result = evaluate_rules_with_gpt_using_requests(request.sampleId, transcript, param.ruleList)
            evaluations.append({
                "id": param.id,
                "name": param.name,
                "rules": result
            })

        # Step 6: Send success webhook
        payload = {
            "sampleId": request.sampleId,
            "status": "completed",
            "transcript": transcript,
            "evaluations": evaluations
        }

        try:
            response = requests.post(webhook_url, json=payload)
            print(f"[Webhook Success] Status: {response.status_code}, Response: {response.text}")
            # print(f"[Webhook Success] Status: {response.status_code}, Response: {response.text}, payload: {payload}")
        except Exception as e:
            print(f"[Webhook Error on success] {str(e)}")

        return {"message": "Audit completed and webhook sent"}

    except Exception as e:
        # Step 7: Send failure webhook
        error_payload = {
            "sampleId": request.sampleId,
            "status": "error",
            "error": str(e)
        }

        try:
            response = requests.post(webhook_url, json=error_payload)
            print(f"[Webhook Error Notified] Status: {response.status_code}, Response: {response.text}")
        except Exception as inner:
            print(f"[Webhook Send Failed] {str(inner)}")

        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")

    finally:
        for path in [audio_path, transcoded_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Failed to remove temp file {path}: {e}")


