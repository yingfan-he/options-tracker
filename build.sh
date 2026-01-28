#!/bin/bash
# Build script for production deployment

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Building frontend..."
cd "$SCRIPT_DIR/frontend"
npm install
npm run build

echo ""
echo "Build complete!"
echo "Frontend built to: frontend/dist/"
echo ""
echo "To run in production:"
echo "  cd backend"
echo "  pip install -r requirements.txt"
echo "  uvicorn main:app --host 0.0.0.0 --port 8000"
