@echo off
cd /d %~dp0

call venv\Scripts\activate >nul 2>&1
pip install -r requirements.txt >nul 2>&1

start "" pythonw main_app.py
exit