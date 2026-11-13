#!/bin/bash
echo "========================================================"
echo " Launching Catalysis Simulation & Learning Platform..."
echo "========================================================"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "Installing / updating dependencies..."
pip install -r requirements.txt

echo "Starting Streamlit application..."
streamlit run Main_Menu.py
