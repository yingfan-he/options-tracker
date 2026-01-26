#!/bin/bash
cd "$(dirname "$0")"

# Check if dependencies installed
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install streamlit pandas
fi

# Run the app
python3 -m streamlit run app.py
