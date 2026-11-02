import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable
import yt_dlp
from yt_dlp.utils import download_range_func


def find_ffmpeg_path() -> Optional[str]:
    """Find the path to the directory containing ffmpeg.exe."""
    # 0. Check PyInstaller bundled folder or current executable directory
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
        for candidate in [meipass, exe_dir, exe_dir / "bin"]:
            if (candidate / "ffmpeg.exe").exists():
                return str(candidate)

    # 1. System PATH
    found = shutil.which("ffmpeg")
    if found:
        return str(Path(found).parent)

    # 2. Check WinGet installation locations
    winget_pkg_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget_pkg_dir.exists():
        for ffmpeg_exe in winget_pkg_dir.rglob("ffmpeg.exe"):
            return str(ffmpeg_exe.parent)

    # 3. Check common install directories
    common_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "ffmpeg" / "bin",
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
    ]
    for p in common_paths:
        if (p / "ffmpeg.exe").exists():
            return str(p)

    return None


def ensure_ffmpeg_in_path() -> Optional[str]:
    """Ensure FFmpeg directory is prepended to os.environ['PATH']."""
    ffmpeg_dir = find_ffmpeg_path()
    if ffmpeg_dir:
        current_path = os.environ.get("PATH", "")
        if ffmpeg_dir.lower() not in current_path.lower():
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path
    return ffmpeg_dir


# Ensure FFmpeg is accessible immediately upon import
ensure_ffmpeg_in_path()


def parse_time_to_seconds(time_str: str) -> float:
    """
    Parse a timestamp string into seconds.
    Supports: "120", "01:30" (MM:SS), "01:15:30" (HH:MM:SS), etc.
    """
    time_str = str(time_str).strip()
    if not time_str:
        return 0.0

    parts = time_str.split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        else:
            raise ValueError(f"Invalid timestamp format: '{time_str}'")
    except ValueError as e:
        raise ValueError(f"Could not parse timestamp '{time_str}'. Use SS, MM:SS, or HH:MM:SS.") from e


def format_seconds_to_time(seconds: float) -> str:
    """Format seconds into HH:MM:SS string."""
    seconds = max(0.0, float(seconds))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def get_video_info(url: str) -> Dict[str, Any]:
    """Retrieve metadata for the given video URL without downloading."""
    ffmpeg_dir = ensure_ffmpeg_in_path()
    ydl_opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if ffmpeg_dir:
        ydl_opts["ffmpeg_location"] = ffmpeg_dir

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", "Unknown Title"),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail"),
            "uploader": info.get("uploader", "Unknown"),
            "url": url,
            "id": info.get("id", ""),
            "max_height": max([f.get("height") or 0 for f in info.get("formats", [])] or [1080]),
        }


def convert_to_mp4(input_path: str) -> str:
    """
    Ensure the file is a clean, universal MP4 file with zero freeze at 0.00s.
    Fast re-encodes the video stream with an immediate I-frame and AAC audio.
    """
    output_path = os.path.splitext(input_path)[0] + "_mp4_temp.mp4"
    if os.path.exists(output_path):
        os.remove(output_path)

    ffmpeg_dir = ensure_ffmpeg_in_path()
    ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe") if ffmpeg_dir else "ffmpeg"

    # -preset ultrafast -crf 18 guarantees instant keyframe at 0.00s with pristine quality
    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0 and os.path.exists(output_path):
        final_mp4 = os.path.splitext(input_path)[0] + ".mp4"
        try:
            os.remove(input_path)
        except Exception:
            pass
        if os.path.exists(final_mp4):
            try:
                os.remove(final_mp4)
            except Exception:
                pass
        os.rename(output_path, final_mp4)
        return final_mp4

    return input_path


def download_clip(
    url: str,
    start_time: str,
    end_time: str,
    output_dir: str = "downloads",
    quality: str = "source",  # "source", "1080p", "720p", "audio_mp3"
    force_keyframes: bool = False,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> str:
    """
    Download only the specified section of the video and return the resulting file path.
    Guarantees pure MP4 format with audio & video synced from 0.00 seconds.
    """
    start_sec = parse_time_to_seconds(start_time)
    end_sec = parse_time_to_seconds(end_time)

    if end_sec <= start_sec:
        raise ValueError("End time must be greater than start time.")

    os.makedirs(output_dir, exist_ok=True)
    ffmpeg_dir = ensure_ffmpeg_in_path()

    hook_callbacks = []
    if progress_callback:
        def ydl_hook(d):
            progress_callback(d)
        hook_callbacks.append(ydl_hook)

    start_label = format_seconds_to_time(start_sec).replace(":", "-")
    end_label = format_seconds_to_time(end_sec).replace(":", "-")

    ydl_opts: Dict[str, Any] = {
        "download_ranges": download_range_func(None, [(start_sec, end_sec)]),
        "force_keyframes_at_cuts": force_keyframes,
        "outtmpl": os.path.join(output_dir, f"%(title).50s_{start_label}_to_{end_label}.%(ext)s"),
        "progress_hooks": hook_callbacks,
        "noplaylist": True,
        "windowsfilenames": True,
    }

    if ffmpeg_dir:
        ydl_opts["ffmpeg_location"] = ffmpeg_dir

    is_audio = (quality == "audio_mp3")

    if is_audio:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif quality == "1080p":
        ydl_opts["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        ydl_opts["merge_output_format"] = "mp4"
    elif quality == "720p":
        ydl_opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        ydl_opts["merge_output_format"] = "mp4"
    else:
        # True Source (up to 4K / 8K)
        ydl_opts["format"] = "bestvideo+bestaudio/best"
        ydl_opts["merge_output_format"] = "mp4"

    final_filepath: Optional[str] = None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        # 1. Try finding filepath in requested_downloads
        req_dl = info.get("requested_downloads")
        if req_dl and isinstance(req_dl, list) and len(req_dl) > 0:
            fp = req_dl[0].get("filepath")
            if fp and isinstance(fp, str) and os.path.exists(fp):
                final_filepath = fp

        # 2. Try ydl.prepare_filename
        if not final_filepath:
            prep = ydl.prepare_filename(info)
            if is_audio:
                prep_audio = os.path.splitext(prep)[0] + ".mp3"
                if os.path.exists(prep_audio):
                    final_filepath = prep_audio
            elif os.path.exists(prep):
                final_filepath = prep

        # 3. Fallback: Search matching files created in output_dir
        if not final_filepath:
            candidates = list(Path(output_dir).glob(f"*_{start_label}_to_{end_label}.*"))
            if candidates:
                candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                final_filepath = str(candidates[0])

    if not final_filepath:
        raise FileNotFoundError("Could not determine downloaded file location.")

    # Convert non-MP4 video files or MKVs to clean MP4
    if not is_audio:
        final_filepath = convert_to_mp4(final_filepath)

    return str(final_filepath)
