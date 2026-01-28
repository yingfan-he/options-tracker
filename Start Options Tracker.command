#!/bin/bash
# Double-click this file to start Options Tracker

# Get the directory where this script is located
cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

echo "=========================================="
echo "   Options Trading Tracker"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required."
    echo "Install it from: https://www.python.org/downloads/"
    echo ""
    echo "Press Enter to close..."
    read
    exit 1
fi

# Setup Python virtual environment if needed
if [ ! -d "$SCRIPT_DIR/backend/venv" ]; then
    echo "First time setup - installing dependencies..."
    echo "(This may take a few minutes)"
    echo ""
    python3 -m venv "$SCRIPT_DIR/backend/venv"
    source "$SCRIPT_DIR/backend/venv/bin/activate"
    pip install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet
    echo "Setup complete!"
    echo ""
else
    source "$SCRIPT_DIR/backend/venv/bin/activate"
fi

# Build frontend if not already built
if [ ! -d "$SCRIPT_DIR/frontend/dist" ]; then
    echo "Building frontend (first time only)..."
    if command -v npm &> /dev/null; then
        cd "$SCRIPT_DIR/frontend"
        npm install --silent
        npm run build --silent
        cd "$SCRIPT_DIR"
        echo "Build complete!"
        echo ""
    else
        echo "WARNING: npm not found. Frontend may not work properly."
        echo "Install Node.js from: https://nodejs.org/"
    fi
fi

# Start the server
echo "Starting server..."
echo ""
echo "=========================================="
echo "   App running at: http://localhost:8000"
echo "=========================================="
echo ""
echo "Opening browser..."
sleep 1

# Open browser
open "http://localhost:8000"

echo ""
echo "Keep this window open while using the app."
echo "Close this window or press Ctrl+C to stop."
echo ""

# Run the backend server
cd "$SCRIPT_DIR/backend"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
