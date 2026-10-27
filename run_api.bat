@echo off
cd /d "%~dp0"
set PYTHONPATH=%CD%
echo Starting Cyber Shield AI REST API at http://localhost:8000 (docs: http://localhost:8000/docs) ...
python -m uvicorn core.api:app --host 127.0.0.1 --port 8000
pause
