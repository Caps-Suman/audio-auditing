#!/bin/bash

echo "🔧 Setting up Python virtual environment..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

echo "📦 Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup complete. Virtual environment is ready and dependencies are installed."
echo "➡️ To activate it later, run: source venv/bin/activate"


# chmod +x setup.sh
# ./setup.sh