import os
import re
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from downloader import (
    get_video_info,
    download_clip,
    parse_time_to_seconds,
    format_seconds_to_time,
    find_ffmpeg_path,
    ensure_ffmpeg_in_path,
)

# Ensure FFmpeg is registered in PATH
ensure_ffmpeg_in_path()

st.set_page_config(
    page_title="Video Range Downloader",
    page_icon="✂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Clean styling: Hide Streamlit header, deploy button, hamburger menu, and footer
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    div[data-testid="stDecoration"] {display:none;}
    div[data-testid="stStatusWidget"] {visibility:hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("✂️ Video Range Downloader")
st.caption("Watch, scrub timeline, and download exact video sections in full MP4 / 4K quality")

# FFmpeg check
ffmpeg_dir = find_ffmpeg_path()
if not ffmpeg_dir:
    st.error("⚠️ FFmpeg was not detected on your system. Please restart the application.")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


def extract_youtube_id(video_url: str) -> str | None:
    """Extract 11-char YouTube ID from any YouTube URL."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)",
        r"(?:embed\/|shorts\/)([0-9A-Za-z_-]{11})(?:[&?]|$)",
        r"youtu\.be\/([0-9A-Za-z_-]{11})(?:[&?]|$)",
    ]
    for p in patterns:
        m = re.search(p, video_url)
        if m:
            return m.group(1)
    return None


# Initialize session states
if "loaded_url" not in st.session_state:
    st.session_state.loaded_url = ""
if "video_info" not in st.session_state:
    st.session_state.video_info = None
if "downloaded_file" not in st.session_state:
    st.session_state.downloaded_file = None
if "download_error" not in st.session_state:
    st.session_state.download_error = None

# URL input
url_input = st.text_input(
    "Enter Video URL:",
    value=st.session_state.loaded_url if st.session_state.loaded_url else "",
    placeholder="https://www.youtube.com/watch?v=...",
    help="Paste any YouTube or video URL here.",
)

# Detect if user pasted a completely different URL: automatically reset previous download
if url_input.strip() and url_input.strip() != st.session_state.loaded_url:
    st.session_state.downloaded_file = None
    st.session_state.download_error = None

c_fetch, c_reset = st.columns([3, 1])
with c_fetch:
    fetch_btn = st.button("🔍 Load Video & Player", use_container_width=True)
with c_reset:
    if st.button("Clear", use_container_width=True):
        st.session_state.loaded_url = ""
        st.session_state.video_info = None
        st.session_state.downloaded_file = None
        st.session_state.download_error = None
        st.rerun()

if fetch_btn and url_input:
    clean_url = url_input.strip()
    with st.spinner("Loading video streams & player..."):
        try:
            info = get_video_info(clean_url)
            st.session_state.loaded_url = clean_url
            st.session_state.video_info = info
            st.session_state.downloaded_file = None
            st.session_state.download_error = None
            st.rerun()
        except Exception as e:
            st.error(f"Error loading video: {e}")

video_info = st.session_state.video_info

if video_info and st.session_state.loaded_url:
    duration_sec = float(video_info.get("duration") or 0)
    formatted_duration = format_seconds_to_time(duration_sec)
    max_h = video_info.get("max_height", 1080)
    res_label = f"{max_h}p" if max_h < 2160 else "4K UHD (2160p)"
    yt_id = extract_youtube_id(st.session_state.loaded_url)

    st.markdown("---")
    st.subheader(f"📺 {video_info.get('title', 'Video')}")
    st.write(f"👤 **Channel:** {video_info.get('uploader', 'Unknown')} | ⏱️ **Total Duration:** `{formatted_duration}` | 🎬 **Max Quality:** `{res_label}`")

    # --- INTERACTIVE PLAYER SECTION ---
    st.markdown("### 🎬 Watch & Scrub Video")
    
    if yt_id:
        player_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f4f4f5;">
          <div style="position: relative; width: 100%; padding-bottom: 56.25%; height: 0; border-radius: 10px; overflow: hidden; background: #000; box-shadow: 0 4px 16px rgba(0,0,0,0.5);">
            <iframe id="ytplayer" type="text/html" width="100%" height="100%"
              src="https://www.youtube.com/embed/{yt_id}?enablejsapi=1&origin=http://localhost:8501&playsinline=1&rel=0"
              frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen
              style="position: absolute; top:0; left: 0; width: 100%; height: 100%;">
            </iframe>
          </div>
          <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center; background: #27272a; padding: 10px 14px; border-radius: 8px;">
            <span style="font-size: 13px; color: #a1a1aa;">💡 <i>Tip: Play/pause at your desired moment, then pick timestamps below.</i></span>
            <span style="font-size: 13px; font-weight: 600; color: #38bdf8;">Duration: {formatted_duration}</span>
          </div>
        </div>
        """
        components.html(player_html, height=440)
    else:
        st.video(st.session_state.loaded_url)

    # --- TIMELINE RANGE SELECTION ---
    st.markdown("### ⏱️ Select Cut Timeline")

    if duration_sec > 0:
        slider_range = st.slider(
            "Drag handles to select timeline range:",
            min_value=0.0,
            max_value=float(duration_sec),
            value=(0.0, min(30.0, float(duration_sec))),
            step=1.0,
            help="Drag left handle for start time and right handle for end time.",
        )
        slider_s = format_seconds_to_time(slider_range[0])
        slider_e = format_seconds_to_time(slider_range[1])
    else:
        slider_s = "00:00:00"
        slider_e = "00:00:30"

    cs, ce = st.columns(2)
    with cs:
        start_input = st.text_input(
            "Start Time (HH:MM:SS):",
            value=slider_s,
            help="Enter start time, e.g. 00:01:30 or 90 seconds",
        )
    with ce:
        end_input = st.text_input(
            "End Time (HH:MM:SS):",
            value=slider_e,
            help="Enter end time, e.g. 00:02:45 or 165 seconds",
        )

    # Calculate selected clip length
    try:
        s_val = parse_time_to_seconds(start_input)
        e_val = parse_time_to_seconds(end_input)
        clip_len = max(0.0, e_val - s_val)
        st.info(f"📏 Selected Clip Length: **{format_seconds_to_time(clip_len)}** ({int(clip_len)} seconds)")
    except Exception:
        clip_len = 0.0

    st.markdown("### ⚙️ Output Format")
    col_q, col_cut = st.columns(2)
    with col_q:
        quality_choice = st.selectbox(
            "Quality / Format:",
            options=[
                "Source / Best Available MP4 (Up to 4K / 8K)",
                "1080p Full HD (MP4)",
                "720p HD (MP4)",
                "Audio Only (MP3)",
            ],
            index=0,
        )
    with col_cut:
        cut_mode = st.radio(
            "Cutting Mode:",
            options=[
                "⚡ Fast Lossless Cut (Instant, lossless raw stream)",
                "🎯 Frame-Accurate Cut (Exact keyframe match)",
            ],
            index=0,
            help="Fast Lossless finishes in seconds without CPU re-encoding lag.",
        )

    quality_map = {
        "Source / Best Available MP4 (Up to 4K / 8K)": "source",
        "1080p Full HD (MP4)": "1080p",
        "720p HD (MP4)": "720p",
        "Audio Only (MP3)": "audio_mp3",
    }
    selected_quality = quality_map[quality_choice]
    force_kf = "Frame-Accurate" in cut_mode

    # Download action
    if st.button("🚀 Download MP4 Clip Now", type="primary", use_container_width=True):
        try:
            s_sec = parse_time_to_seconds(start_input)
            e_sec = parse_time_to_seconds(end_input)

            if e_sec <= s_sec:
                st.error("End time must be after start time.")
            elif duration_sec > 0 and s_sec >= duration_sec:
                st.error(f"Start time ({start_input}) exceeds total video duration ({formatted_duration}).")
            else:
                with st.spinner("⏳ Downloading slice and packaging into MP4..."):
                    saved_path = download_clip(
                        url=st.session_state.loaded_url,
                        start_time=start_input,
                        end_time=end_input,
                        output_dir=str(DOWNLOAD_DIR),
                        quality=selected_quality,
                        force_keyframes=force_kf,
                    )
                    if saved_path and os.path.exists(saved_path):
                        st.session_state.downloaded_file = saved_path
                        st.session_state.download_error = None
                        st.rerun()
                    else:
                        st.session_state.download_error = "Download completed but output file was not found."
                        st.session_state.downloaded_file = None
                        st.rerun()
        except Exception as err:
            st.session_state.download_error = str(err)
            st.session_state.downloaded_file = None
            st.rerun()

    # --- DOWNLOAD RESULT SECTION (PERSISTENT & CLEAN) ---
    if st.session_state.download_error:
        st.error(f"Download failed: {st.session_state.download_error}")

    downloaded_path = st.session_state.downloaded_file
    if downloaded_path and os.path.exists(downloaded_path):
        st.markdown("---")
        st.success("🎉 **Your MP4 clip is ready!**")
        st.caption(f"📁 Saved locally to: `{downloaded_path}`")

        ext = Path(downloaded_path).suffix.lower()
        if ext in [".mp4", ".webm", ".mkv"]:
            st.video(downloaded_path)
        elif ext in [".mp3", ".m4a", ".wav"]:
            st.audio(downloaded_path)

        with open(downloaded_path, "rb") as f:
            file_data = f.read()

        mime_type = "audio/mpeg" if ext == ".mp3" else "video/mp4"
        st.download_button(
            label="💾 Save MP4 File to Computer",
            data=file_data,
            file_name=Path(downloaded_path).name,
            mime=mime_type,
            use_container_width=True,
        )

# History section
st.markdown("---")
st.subheader("📁 Downloaded Clips History")
existing_files = sorted(
    [p for p in DOWNLOAD_DIR.glob("*") if p.is_file() and not p.name.endswith(".part") and not p.name.startswith("test_")],
    key=lambda x: x.stat().st_mtime,
    reverse=True,
)

if existing_files:
    for f in existing_files[:5]:
        col_name, col_size, col_btn = st.columns([3, 1, 1])
        with col_name:
            st.write(f"📄 `{f.name}`")
        with col_size:
            size_mb = f.stat().st_size / (1024 * 1024)
            st.write(f"{size_mb:.2f} MB")
        with col_btn:
            with open(f, "rb") as file_data:
                st.download_button(
                    label="⬇️ Save",
                    data=file_data.read(),
                    file_name=f.name,
                    key=f"hist_{f.name}",
                )
else:
    st.info("No clips downloaded yet.")
