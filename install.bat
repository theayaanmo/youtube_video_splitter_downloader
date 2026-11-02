@echo off
title Video Clipper Installer
echo ============================================================
echo   Installing Video Range Downloader Dependencies...
echo ============================================================

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python is not installed. Installing Python via WinGet...
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Could not automatically install Python. Please install Python from https://python.org
        pause
        exit /b 1
    )
)

REM Check FFmpeg
ffmpeg -version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] FFmpeg not found in PATH. Checking / installing via WinGet...
    winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
)

echo [*] Installing required Python libraries (yt-dlp, streamlit)...
python -m pip install -r requirements.txt

echo ============================================================
echo   Installation Complete!
echo   You can now launch:
echo     - start_web.bat  (Browser interface)
echo     - start_gui.bat  (Desktop window interface)
echo     - start_cli.bat  (Terminal interface)
echo ============================================================
pause
