@echo off
cd /d "%~dp0"
set PYTHONPATH=%CD%
echo Starting Cyber Shield AI Dashboard at http://localhost:8501 ...
python -m streamlit run app/main.py
pause
