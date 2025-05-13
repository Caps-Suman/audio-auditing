import os, tempfile, shutil
from typing import List, Optional
from pydantic import BaseModel
import requests
from fastapi import APIRouter, HTTPException
from services.transcript_service import format_transcript_without_speaker, format_transcript_with_speakers
from services.whisper_service import transcribe_audio_whisper
from services.openai_service import evaluate_rules_with_gpt_using_requests
from services.audio_format_handler import transcode_to_whisper_wav

class ParameterRule(BaseModel):
    id: str
    name: Optional[str] = None
    ruleList: List[str]

class AuditRequest(BaseModel):
    audioUrl: str
    sampleId: Optional[str] = None
    parameter: List[ParameterRule]

router = APIRouter()
webhook_url = os.getenv("WEBHOOK_URL")
hugging_face_token = os.getenv("HUGGINGFACE_TOKEN")

@router.post("/analyze-audio")
async def audit_call(request: AuditRequest):
    # print(f"Received request: {request}")
    audio_path = None
    transcoded_path = None

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
        transcript = transcribe_audio_whisper(transcoded_path)

        # Step 5: Evaluate parameters
        evaluations = []
        for param in request.parameter:
            result = evaluate_rules_with_gpt_using_requests(transcript, param.ruleList)
            evaluations.append({
                "id": param.id,
                "name": param.name,
                "rules": result
            })

        # formatted_transcript = format_transcript_with_speakers(transcript)
        formatted_transcript = format_transcript_without_speaker(transcript)

        # Step 6: Send success webhook
        payload = {
            "sampleId": request.sampleId,
            "status": "completed",
            "transcript": formatted_transcript,
            "evaluations": evaluations
        }

        try:
            response = requests.post(webhook_url, json=payload)
            print(f"[Webhook Success] Status: {response.status_code}, Response: {response.text}")
            # print(f"[Webhook Success] Status: {response.status_code}, Response: {response.text}, payload: {payload}")
        except Exception as e:
            print(f"[Webhook Error on success] {str(e)}")

        # return {"message": "Audit completed and webhook sent", "payload": payload}
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


