@echo off
echo ========================================================
echo  Launching Catalysis Simulation & Learning Platform...
echo ========================================================

IF NOT EXIST ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
echo Installing / updating dependencies...
pip install -r requirements.txt

echo Starting Streamlit application...
streamlit run Main_Menu.py
pause
