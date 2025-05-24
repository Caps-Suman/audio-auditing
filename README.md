# Audio-Auditing
This is python based project used to get the audio data as per need
# Python normal Mode:
uvicorn main:app --host 0.0.0.0 --port 9001
# Python debug mode :
uvicorn main:app --reload --port 9000
# Run/select with venv interpreter cmd+shift+p
source venv/bin/activate

<!-----##### Hugging Face Token Account (Can create a new one also if required) #####----->
emailId: ai@marvelsync.com
password: Marvelsync#123

Goto both link : 
https://huggingface.co/pyannote/speaker-diarization  &&
https://huggingface.co/pyannote/segmentation

Accept repostory access (Provide a name, website link and task type).

Then in your project virtual env (venv) terminal run : huggingface-cli login
Provide token and then proceed.
<!----------------------------- ########################## ------------------------------->

# General Pipeline Summary
Client → POST /analyze-audio
         └─> Audio Download
             └─> Transcode (FFmpeg)
                 └─> Transcribe (Whisper)
                     └─> Rule Evaluation (OpenAI/Local LLM)
                         └─> HTML Transcript Generation
                             └─> Webhook POST with audit result
