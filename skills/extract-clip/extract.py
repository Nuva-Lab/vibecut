#!/usr/bin/env python3
"""
Extract a video clip using FFmpeg.
"""
import subprocess
import sys
from pathlib import Path


def parse_timestamp(ts: str) -> str:
    """Normalize timestamp to HH:MM:SS format."""
    parts = ts.split(":")
    if len(parts) == 2:
        return f"00:{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    elif len(parts) == 3:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
    return ts


def timestamp_to_seconds(ts: str) -> float:
    """Convert timestamp to seconds."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(ts)


def timestamp_to_filename(ts: str) -> str:
    """Convert timestamp to filename-safe string."""
    return ts.replace(":", "-")


def extract_clip(
    input_path: str,
    start_time: str,
    end_time: str,
    output_path: str = None,
    reencode: bool = False,
) -> str:
    """
    Extract a clip from a video file.

    Args:
        input_path: Path to input video
        start_time: Start timestamp (MM:SS or HH:MM:SS)
        end_time: End timestamp (MM:SS or HH:MM:SS)
        output_path: Optional output path
        reencode: If True, re-encode video (slower but more precise cuts)

    Returns:
        Path to output file
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    # Normalize timestamps and calculate duration
    start = parse_timestamp(start_time)
    start_sec = timestamp_to_seconds(start_time)
    end_sec = timestamp_to_seconds(end_time)
    duration = end_sec - start_sec

    if duration <= 0:
        raise ValueError(f"End time must be after start time: {start_time} to {end_time}")

    # Generate output path if not provided
    if output_path is None:
        output_dir = input_path.parent / "assets" / "outputs" / "clips"
        if not output_dir.exists():
            # Try project-level output dir
            output_dir = Path(__file__).parent.parent.parent / "assets" / "outputs" / "clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        start_fn = timestamp_to_filename(start_time)
        end_fn = timestamp_to_filename(end_time)
        output_path = output_dir / f"{input_path.stem}_{start_fn}_{end_fn}.mp4"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build FFmpeg command
    # Using -ss before -i for fast seeking, -t for duration
    if reencode:
        # Re-encode for precise cuts (slower but accurate)
        cmd = [
            "ffmpeg", "-y",
            "-ss", start,
            "-i", str(input_path),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            str(output_path)
        ]
    else:
        # Stream copy for fast extraction (may have slight timestamp drift)
        cmd = [
            "ffmpeg", "-y",
            "-ss", start,
            "-i", str(input_path),
            "-t", str(duration),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(output_path)
        ]

    print(f"Extracting {start_time} to {end_time} from {input_path.name}")
    print(f"Output: {output_path}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise RuntimeError("FFmpeg extraction failed")

    print(f"Extracted clip: {output_path}")
    return str(output_path)


def main():
    if len(sys.argv) < 4:
        print("Usage: python extract.py <input_video> <start_time> <end_time> [output_path]")
        print("Example: python extract.py video.mp4 01:48 02:25")
        sys.exit(1)

    input_path = sys.argv[1]
    start_time = sys.argv[2]
    end_time = sys.argv[3]
    output_path = sys.argv[4] if len(sys.argv) > 4 else None

    extract_clip(input_path, start_time, end_time, output_path)


if __name__ == "__main__":
    main()
