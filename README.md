# ✂️ Video Range Downloader (yt-dlp)

A local web application that allows you to download only a specific timeframe (from start time to end time) of any video using `yt-dlp` and `FFmpeg`.

---

## 🚀 Features

- **Precise Slicing**: Downloads and cuts only the exact timestamp range you select (no need to download entire multi-gigabyte videos).
- **Interactive Web Interface**: Enter a URL, preview title/thumbnail/duration, drag time sliders or enter exact timestamps.
- **Multiple Formats**: Download as merged **MP4 video** or audio-only **MP3**.
- **Browser Playback & Direct Download**: Play the trimmed clip right in the browser or save it to your local machine.
- **FFmpeg Auto-Discovery**: Automatically locates FFmpeg on Windows.

---

## 💻 Running the App

### Option 1: Double-Click Launcher
Double-click [`run.bat`](file:///C:/Users/kk/Desktop/ytdlp_app/run.bat) in this folder.

### Option 2: Terminal
```bash
python -m streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your web browser.

---

## ⏱️ Supported Timestamp Formats

You can enter timestamps in any of the following formats:
- Seconds: `90` or `125.5`
- Minutes and Seconds: `01:30` or `1:30`
- Hours, Minutes, and Seconds: `00:01:30` or `01:15:45`
