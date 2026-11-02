@echo off
title Video Range Downloader (Web)

REM Ensure FFmpeg on WinGet path is loaded
for /d %%D in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*") do (
    if exist "%%D\ffmpeg-*\bin\ffmpeg.exe" (
        for /d %%B in ("%%D\ffmpeg-*\bin") do set "PATH=%%B;%PATH%"
    )
)

echo Starting Video Range Downloader Web UI...
python -m streamlit run app.py
pause
