import os
import sys
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from downloader import (
    get_video_info,
    download_clip,
    format_seconds_to_time,
    parse_time_to_seconds,
    ensure_ffmpeg_in_path,
)

ensure_ffmpeg_in_path()


class VideoClipperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✂️ Video Range Downloader")
        self.root.geometry("620x540")
        self.root.minsize(560, 480)

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.video_duration = 0
        self.downloaded_path = None

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="16 16 16 16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        title_label = ttk.Label(
            main_frame,
            text="✂️ Video Range Downloader",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(anchor=tk.W, pady=(0, 2))
        subtitle = ttk.Label(
            main_frame,
            text="Download exact video segments in full MP4 / 4K quality",
            font=("Segoe UI", 9),
            foreground="#555555",
        )
        subtitle.pack(anchor=tk.W, pady=(0, 14))

        # URL Input Row
        url_frame = ttk.LabelFrame(main_frame, text=" 1. Video URL ", padding="10 8 10 8")
        url_frame.pack(fill=tk.X, pady=(0, 10))

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Segoe UI", 10))
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        fetch_btn = ttk.Button(url_frame, text="Fetch Info", command=self._fetch_info)
        fetch_btn.pack(side=tk.RIGHT)

        # Video Info Card
        self.info_frame = ttk.Frame(main_frame, padding="8 6 8 6")
        self.info_frame.pack(fill=tk.X, pady=(0, 10))

        self.title_var = tk.StringVar(value="No video loaded yet.")
        self.dur_var = tk.StringVar(value="")

        lbl_title = ttk.Label(
            self.info_frame,
            textvariable=self.title_var,
            font=("Segoe UI", 10, "bold"),
            wraplength=560,
        )
        lbl_title.pack(anchor=tk.W)

        lbl_dur = ttk.Label(
            self.info_frame,
            textvariable=self.dur_var,
            font=("Segoe UI", 9),
            foreground="#0284c7",
        )
        lbl_dur.pack(anchor=tk.W, pady=(2, 0))

        # Timeframe Selection
        time_frame = ttk.LabelFrame(main_frame, text=" 2. Select Time Range (HH:MM:SS) ", padding="10 10 10 10")
        time_frame.pack(fill=tk.X, pady=(0, 10))

        t_row = ttk.Frame(time_frame)
        t_row.pack(fill=tk.X)

        ttk.Label(t_row, text="Start Time:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.start_var = tk.StringVar(value="00:00:00")
        start_entry = ttk.Entry(t_row, textvariable=self.start_var, width=14, font=("Segoe UI", 10))
        start_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 24))

        ttk.Label(t_row, text="End Time:").grid(row=0, column=2, sticky=tk.W, padx=(0, 6))
        self.end_var = tk.StringVar(value="00:00:30")
        end_entry = ttk.Entry(t_row, textvariable=self.end_var, width=14, font=("Segoe UI", 10))
        end_entry.grid(row=0, column=3, sticky=tk.W)

        # Settings: Quality and Output
        opt_frame = ttk.LabelFrame(main_frame, text=" 3. Output Options ", padding="10 10 10 10")
        opt_frame.pack(fill=tk.X, pady=(0, 14))

        opt_grid = ttk.Frame(opt_frame)
        opt_grid.pack(fill=tk.X)

        ttk.Label(opt_grid, text="Quality:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.quality_var = tk.StringVar(value="Fast 1080p MP4 (Recommended)")
        quality_cb = ttk.Combobox(
            opt_grid,
            textvariable=self.quality_var,
            values=[
                "Fast 1080p MP4 (Recommended)",
                "Fast 720p MP4",
                "Source 4K/8K MP4 (Original Codec - Fast)",
                "Source 4K MP4 (Re-encoded H.264)",
                "Audio Only MP3",
            ],
            state="readonly",
            width=28,
        )
        quality_cb.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(opt_grid, text="Folder:").grid(row=0, column=2, sticky=tk.W, padx=(0, 6))
        self.dir_var = tk.StringVar(value=os.path.abspath("downloads"))
        dir_entry = ttk.Entry(opt_grid, textvariable=self.dir_var, width=20)
        dir_entry.grid(row=0, column=3, sticky=tk.W, padx=(0, 6))

        browse_btn = ttk.Button(opt_grid, text="Browse...", width=8, command=self._browse_dir)
        browse_btn.grid(row=0, column=4, sticky=tk.W)

        # Action Button & Progress
        self.download_btn = ttk.Button(
            main_frame,
            text="🚀 Download MP4 Clip Now",
            command=self._start_download,
        )
        self.download_btn.pack(fill=tk.X, ipady=6, pady=(0, 8))

        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 6))

        self.status_var = tk.StringVar(value="Ready.")
        self.status_lbl = ttk.Label(main_frame, textvariable=self.status_var, font=("Segoe UI", 9))
        self.status_lbl.pack(anchor=tk.W)

        # Open Output Folder Button
        self.open_btn = ttk.Button(
            main_frame,
            text="📁 Open Saved Clip in Explorer",
            state=tk.DISABLED,
            command=self._open_folder,
        )
        self.open_btn.pack(anchor=tk.E, pady=(4, 0))

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(os.path.abspath(d))

    def _fetch_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Empty URL", "Please enter a video URL first.")
            return

        self.title_var.set("Fetching video information...")
        self.status_var.set("Loading stream metadata...")

        def worker():
            try:
                info = get_video_info(url)
                dur = float(info.get("duration") or 0)
                self.video_duration = dur
                formatted = format_seconds_to_time(dur)

                self.root.after(0, lambda: self._on_info_loaded(info["title"], formatted, dur))
            except Exception as e:
                self.root.after(0, lambda: self._on_info_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_info_loaded(self, title, dur_str, dur_sec):
        self.title_var.set(f"📺 {title}")
        self.dur_var.set(f"⏱️ Duration: {dur_str} ({int(dur_sec)} seconds)")
        self.status_var.set("Video loaded successfully.")
        if dur_sec > 0:
            self.end_var.set(format_seconds_to_time(min(30.0, dur_sec)))

    def _on_info_error(self, err_msg):
        self.title_var.set("Could not load video metadata.")
        self.dur_var.set("")
        self.status_var.set(f"Error: {err_msg}")
        messagebox.showerror("Fetch Failed", f"Could not retrieve video details:\n{err_msg}")

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a valid video URL.")
            return

        start_t = self.start_var.get().strip()
        end_t = self.end_var.get().strip()

        try:
            s_sec = parse_time_to_seconds(start_t)
            e_sec = parse_time_to_seconds(end_t)
            if e_sec <= s_sec:
                messagebox.showerror("Invalid Range", "End time must be after Start time.")
                return
        except ValueError as ve:
            messagebox.showerror("Time Format Error", str(ve))
            return

        q_map = {
            "Fast 1080p MP4 (Recommended)": "fast_1080p",
            "Fast 720p MP4": "fast_720p",
            "Source 4K/8K MP4 (Original Codec - Fast)": "source_raw",
            "Source 4K MP4 (Re-encoded H.264)": "source_h264",
            "Audio Only MP3": "audio_mp3",
        }
        quality = q_map.get(self.quality_var.get(), "source")
        out_dir = self.dir_var.get().strip() or "downloads"

        self.download_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self.status_var.set("Downloading slice & packaging MP4...")

        def worker():
            try:
                saved = download_clip(
                    url=url,
                    start_time=start_t,
                    end_time=end_t,
                    output_dir=out_dir,
                    quality=quality,
                )
                self.root.after(0, lambda: self._on_download_success(saved))
            except Exception as e:
                self.root.after(0, lambda: self._on_download_failed(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_download_success(self, path):
        self.progress.stop()
        self.download_btn.config(state=tk.NORMAL)
        self.open_btn.config(state=tk.NORMAL)
        self.downloaded_path = path
        self.status_var.set(f"✅ Finished! Saved to: {os.path.basename(path)}")
        messagebox.showinfo("Success", f"Clip downloaded and packaged successfully!\n\nLocation:\n{path}")

    def _on_download_failed(self, err):
        self.progress.stop()
        self.download_btn.config(state=tk.NORMAL)
        self.status_var.set(f"❌ Failed: {err}")
        messagebox.showerror("Download Error", f"Failed to download clip:\n{err}")

    def _open_folder(self):
        if self.downloaded_path and os.path.exists(self.downloaded_path):
            folder = os.path.dirname(os.path.abspath(self.downloaded_path))
            os.startfile(folder)


def main():
    root = tk.Tk()
    app = VideoClipperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
