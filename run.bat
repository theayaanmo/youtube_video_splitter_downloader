@echo off
title Video Range Downloader

echo [1/2] Detecting FFmpeg...
for /d %%D in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*") do (
    if exist "%%D\ffmpeg-*\bin\ffmpeg.exe" (
        for /d %%B in ("%%D\ffmpeg-*\bin") do set "PATH=%%B;%PATH%"
    )
)

echo [2/2] Starting Video Range Downloader...
python -m streamlit run app.py
pause
