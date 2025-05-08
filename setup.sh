#!/bin/bash

echo "🔧 Setting up the audio intelligence environment..."

# Step 1: Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Step 2: Upgrade pip
pip install --upgrade pip

# Step 3: Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Step 4: Ensure ffmpeg is installed
if ! command -v ffmpeg &> /dev/null
then
    echo "❗ ffmpeg could not be found. Please install it manually (e.g., sudo apt install ffmpeg)."
else
    echo "✅ ffmpeg is installed."
fi

# Step 5: Create necessary directories
mkdir -p temp uploads models

# Step 6: Download Whisper model (base)
echo "📥 Downloading Whisper model..."
python3 -c "import whisper; whisper.load_model('base')"

# Step 7: Reminder for local LLM model
echo "📌 Reminder: Place your local LLM model (e.g., .gguf file) inside the 'models/' directory."

echo "✅ Setup complete."
echo "To activate the environment: source venv/bin/activate"
echo "To run the server: ./start.sh"

# Run this setup in terminal using :
#  chmod +x setup.sh
#  ./setup.sh
