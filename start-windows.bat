@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m quran_reels.setup_windows
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m streamlit run app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Setup or startup failed. Check Python and FFmpeg installation in README.md.
pause
exit /b 1
