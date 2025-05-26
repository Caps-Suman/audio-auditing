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


# Server Setup and running guide : >------------------------------->

FastAPI Audio Auditing API Deployment on AWS EC2
This document provides a complete step-by-step guide to deploy a FastAPI-based Audio Auditing application on AWS EC2, including server setup, virtual environment, Uvicorn, systemd service, and troubleshooting.

1. Launching the EC2 Instance
1.1 Choose an AMI
Use Ubuntu 22.04 LTS


1.2 Instance Type
Recommended: t3.medium or higher with 16gb volume


1.3 Key Pair
Create/download a key pair to SSH into your instance


1.4 Security Group Configuration
Allow:
SSH (Port 22)

HTTP (Port 80)

Custom TCP Rule (Port 8000) from 0.0.0.0/0


2. SSH into EC2
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>


3. Install Required Packages

```console
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git ffmpeg unzip
```


4. Upload or Clone the Project

Option A: Upload ZIP
scp -i your-key.pem audio-auditing.zip ubuntu@<EC2_PUBLIC_IP>:~

```console
unzip audio-auditing.zip
cd audio-auditing/
```

Option B: Clone Git Repo
```console
git clone https://github.com/your-org/audio-auditing.git
cd audio-auditing/
```


5. Set Up Python Environment
```console
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

Edit requirement.txt to remove llama-cpp-python if not used
```console
nano requirement.txt
```

Comment out or remove: llama-cpp-python

```console
pip install -r requirement.txt
```


6. Setup .env File (Optional)
```console
nano .env
```

Example:
OPENAI_API_KEY=sk-...
ORGANIZATION_ID=org-...
PROJECT_ID=proj-...


7. Test FastAPI Server
```console
uvicorn main:app --host 0.0.0.0 --port 8000
Or
uvicorn main:app --reload
```

Then go to: http://<EC2_PUBLIC_IP>:8000/docs

8. Run FastAPI in Background with systemd (In Use)

8.1 Create systemd service file
```console
sudo nano /etc/systemd/system/fastapi.service
```

Paste:
[Unit]
Description=FastAPI Audio Auditing Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/audio-auditing
Environment="PATH=/home/ubuntu/audio-auditing/venv/bin"
ExecStart=/home/ubuntu/audio-auditing/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

8.2 Start service
```console
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi
```

8.3 Verify status
```console
sudo systemctl status fastapi
```


9. Troubleshooting API Timeout
Check Security Group
Ensure port 8000 is open:
Type: Custom TCP
Port Range: 8000
Source: 0.0.0.0/0

Confirm Listening Port
```console
sudo lsof -i -P -n | grep LISTEN
```

Should show: 0.0.0.0:8000
Use Public IP
Run:
```console
curl ifconfig.me
```

Visit:
http://<public-ip>:8000/docs

Try Port 80 (if 8000 blocked)
Change service to:
```console
ExecStart=/home/ubuntu/audio-auditing/venv/bin/uvicorn main:app --host 0.0.0.0 --port 80
```

Then,
Reload service:

```console
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart fastapi.service
```

Verify status
```console
sudo systemctl status fastapi
```

This setup ensures your FastAPI Audio Auditing API is production-ready, auto-starts, and runs persistently on AWS EC2.

Trace all the 500 Internal server error 
```console
journalctl -u fastapi -n 50 --no-pager
```


To check file content
```console
cat requirement.txt
```


To check local file changes
```console
git diff
```

To delete local file changes
```console
git reset --hard HEAD
```

View Logs for Your FastAPI Service
```console
sudo journalctl -u fastapi.service
```

Show latest logs (tail):
```console
sudo journalctl -u fastapi.service -f
```

Show logs from today only:
```console
sudo journalctl -u fastapi.service --since today
```

Limit to last 100 lines:
```console
sudo journalctl -u fastapi.service -n 100
```

Combine with grep:
```console
sudo journalctl -u fastapi.service | grep "Error"
```

Check space in cpu: 
```console
df -h /
Or
df -h
```

# Server Setup and running guide : <-------------------------------<