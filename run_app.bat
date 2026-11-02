@echo off
cd /d "%~dp0"
echo Starting FinPilot AI... your browser will open automatically.
python -m streamlit run app.py
pause
