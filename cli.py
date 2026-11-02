import sys
import argparse
import os
from pathlib import Path

from downloader import (
    get_video_info,
    download_clip,
    format_seconds_to_time,
    parse_time_to_seconds,
    find_ffmpeg_path,
    ensure_ffmpeg_in_path,
)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ensure_ffmpeg_in_path()


def print_banner():
    print("=" * 60)
    print("  Video Range Downloader CLI (yt-dlp + FFmpeg)")
    print("=" * 60)


def interactive_mode():
    print_banner()
    ffmpeg = find_ffmpeg_path()
    if not ffmpeg:
        print("[WARNING] FFmpeg not found in PATH. Slicing may fail.")

    url = input("\n[1/4] Enter Video URL: ").strip()
    if not url:
        print("URL cannot be empty. Exiting.")
        sys.exit(1)

    print("\nFetching video info...")
    try:
        info = get_video_info(url)
        print(f"Title   : {info['title']}")
        print(f"Channel : {info['uploader']}")
        print(f"Duration: {format_seconds_to_time(info['duration'])} ({info['duration']}s)")
    except Exception as e:
        print(f"Could not fetch metadata: {e}")

    start_t = input("\n[2/4] Enter Start Time (e.g. 00:01:30 or 90): ").strip()
    end_t = input("[3/4] Enter End Time   (e.g. 00:02:45 or 165): ").strip()

    print("\n[4/4] Choose Quality:")
    print("  1. Fast 1080p Full HD MP4 (Default, Fastest, Universal)")
    print("  2. Fast 720p HD MP4")
    print("  3. Source Quality 4K/8K MP4 (Original Codec, Fast)")
    print("  4. Source Quality 4K MP4 (Re-encoded H.264, Universal)")
    print("  5. Audio Only MP3")
    q_choice = input("Select (1-5, default 1): ").strip() or "1"
    
    q_map = {
        "1": "fast_1080p",
        "2": "fast_720p",
        "3": "source_raw",
        "4": "source_h264",
        "5": "audio_mp3",
    }
    quality = q_map.get(q_choice, "fast_1080p")

    out_dir = input("\nOutput Directory (default 'downloads'): ").strip() or "downloads"

    print("\nStarting download and MP4 packaging...")
    try:
        saved_file = download_clip(
            url=url,
            start_time=start_t,
            end_time=end_t,
            output_dir=out_dir,
            quality=quality,
        )
        print(f"\n✅ SUCCESS! Clip saved to:\n   {os.path.abspath(saved_file)}")
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download and trim video ranges in MP4 quality.")
    parser.add_argument("-u", "--url", help="Video URL (YouTube or any supported site)")
    parser.add_argument("-s", "--start", help="Start time (e.g. 00:01:30 or 90)")
    parser.add_argument("-e", "--end", help="End time (e.g. 00:02:45 or 165)")
    parser.add_argument(
        "-q", "--quality",
        choices=["fast_1080p", "fast_720p", "source_raw", "source_h264", "audio_mp3", "1080p", "720p", "source"],
        default="fast_1080p",
        help="Quality preset (default: fast_1080p)"
    )
    parser.add_argument("-o", "--output", default="downloads", help="Output directory (default: downloads)")

    args = parser.parse_args()

    if not args.url or not args.start or not args.end:
        interactive_mode()
        return

    print_banner()
    print(f"URL     : {args.url}")
    print(f"Range   : {args.start} -> {args.end}")
    print(f"Quality : {args.quality}")
    print(f"Output  : {args.output}\n")

    try:
        saved_file = download_clip(
            url=args.url.strip(),
            start_time=args.start.strip(),
            end_time=args.end.strip(),
            output_dir=args.output,
            quality=args.quality,
        )
        print(f"\n✅ SUCCESS! File saved to: {os.path.abspath(saved_file)}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
