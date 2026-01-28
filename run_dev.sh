#!/bin/bash
# Development script - runs both backend and frontend

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Options Tracker Development Server...${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required but not installed.${NC}"
    exit 1
fi

# Check if Node is available
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Node.js/npm is required but not installed.${NC}"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install backend dependencies if needed
if [ ! -d "$SCRIPT_DIR/backend/venv" ]; then
    echo "Setting up Python virtual environment..."
    python3 -m venv "$SCRIPT_DIR/backend/venv"
    source "$SCRIPT_DIR/backend/venv/bin/activate"
    pip install -r "$SCRIPT_DIR/backend/requirements.txt"
else
    source "$SCRIPT_DIR/backend/venv/bin/activate"
fi

# Install frontend dependencies if needed
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd "$SCRIPT_DIR/frontend"
    npm install
fi

# Start backend in background
echo -e "${GREEN}Starting backend on http://localhost:8000${NC}"
cd "$SCRIPT_DIR/backend"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend on http://localhost:5173${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Handle Ctrl+C
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

echo ""
echo -e "${GREEN}Development servers running!${NC}"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"

# Wait for processes
wait
