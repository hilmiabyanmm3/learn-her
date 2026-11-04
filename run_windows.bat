@echo off
echo ========================================================
echo  Launching HER Interactive Streamlit Application...
echo ========================================================

IF NOT EXIST ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate
echo Installing / updating dependencies...
pip install -r requirements.txt

echo Starting Streamlit application...
streamlit run Main_Menu.py
pause
