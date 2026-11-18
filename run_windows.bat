@echo off
echo ========================================================
echo  Launching Catalysis Simulation ^& Learning Platform...
echo ========================================================

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
echo Installing / updating dependencies...
pip install -r requirements.txt

echo Starting Streamlit application...
streamlit run Main_Menu.py
if errorlevel 1 pause
