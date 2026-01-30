#!/usr/bin/env python3
"""
Media validation for video production.
Checks for common issues before rendering.
"""
import json
import subprocess
import sys
from pathlib import Path


def run_ffprobe(file_path: str, entries: str) -> dict:
    """Run ffprobe and return parsed JSON output."""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", entries,
        "-of", "json",
        file_path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        return {}

    return json.loads(result.stdout)


def get_video_stream(file_path: str) -> dict | None:
    """Get video stream info."""
    data = run_ffprobe(file_path, "stream=codec_name,codec_type,width,height,r_frame_rate,duration")
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    return None


def get_audio_stream(file_path: str) -> dict | None:
    """Get audio stream info."""
    data = run_ffprobe(file_path, "stream=codec_name,codec_type,sample_rate,channels,duration")
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio":
            return stream
    return None


def get_volume_stats(file_path: str) -> dict:
    """Get audio volume statistics."""
    result = subprocess.run([
        "ffmpeg", "-i", file_path,
        "-af", "volumedetect",
        "-f", "null", "-"
    ], capture_output=True, text=True)

    stats = {}
    for line in result.stderr.split("\n"):
        if "mean_volume:" in line:
            stats["mean_volume"] = float(line.split("mean_volume:")[1].split("dB")[0].strip())
        if "max_volume:" in line:
            stats["max_volume"] = float(line.split("max_volume:")[1].split("dB")[0].strip())

    return stats


def parse_frame_rate(rate_str: str) -> float:
    """Parse frame rate string like '30/1' to float."""
    if "/" in rate_str:
        num, den = rate_str.split("/")
        return float(num) / float(den) if float(den) != 0 else 0
    return float(rate_str)


def validate_media(file_path: str, verbose: bool = False) -> dict:
    """
    Validate media file and return report.

    Args:
        file_path: Path to video file
        verbose: Include volume analysis (slower)

    Returns:
        Validation report with issues and recommendations
    """
    path = Path(file_path)
    if not path.exists():
        return {
            "file": str(path),
            "error": "File not found",
            "issues": ["File does not exist"],
            "recommendations": ["Check file path"]
        }

    video = get_video_stream(file_path)
    audio = get_audio_stream(file_path)

    report = {
        "file": str(path.name),
        "path": str(path.resolve()),
        "video_duration": None,
        "audio_duration": None,
        "has_video": video is not None,
        "has_audio": audio is not None,
        "video_codec": None,
        "audio_codec": None,
        "resolution": None,
        "fps": None,
        "issues": [],
        "recommendations": []
    }

    if video:
        report["video_codec"] = video.get("codec_name")
        report["video_duration"] = float(video.get("duration", 0))
        report["resolution"] = [video.get("width"), video.get("height")]
        report["fps"] = round(parse_frame_rate(video.get("r_frame_rate", "0")), 2)

    if audio:
        report["audio_codec"] = audio.get("codec_name")
        report["audio_duration"] = float(audio.get("duration", 0))
        report["sample_rate"] = int(audio.get("sample_rate", 0))
        report["channels"] = audio.get("channels")

    # Check for issues
    if not video:
        report["issues"].append("No video track found")
        report["recommendations"].append("Ensure file contains video")

    if not audio:
        report["issues"].append("No audio track found")
        report["recommendations"].append("Add audio track or use muted video")

    if video and audio:
        video_dur = report["video_duration"]
        audio_dur = report["audio_duration"]

        if video_dur and audio_dur:
            diff = audio_dur - video_dur
            if diff > 0.5:
                report["issues"].append(f"Video track shorter than audio by {diff:.2f}s")
                report["recommendations"].append("Use loop=true in Remotion or trim audio")
            elif diff < -0.5:
                report["issues"].append(f"Audio track shorter than video by {-diff:.2f}s")
                report["recommendations"].append("Extend audio or trim video")

    # Check codec compatibility
    if video and video.get("codec_name") in ["hevc", "prores"]:
        report["issues"].append(f"Codec {video.get('codec_name')} may have compatibility issues")
        report["recommendations"].append("Convert to H.264 for better compatibility")

    # Volume analysis (optional, slower)
    if verbose and audio:
        volume = get_volume_stats(file_path)
        report["volume"] = volume

        if volume.get("mean_volume", 0) < -40:
            report["issues"].append(f"Audio very quiet (mean: {volume.get('mean_volume'):.1f} dB)")
            report["recommendations"].append("Consider normalizing audio")

    report["valid"] = len(report["issues"]) == 0

    return report


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate.py <video_file> [--verbose]")
        print("\nValidates video file for common issues before rendering.")
        sys.exit(1)

    file_path = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    report = validate_media(file_path, verbose=verbose)

    print(json.dumps(report, indent=2))

    if report.get("issues"):
        print(f"\n⚠️  Found {len(report['issues'])} issue(s)")
        sys.exit(1)
    else:
        print("\n✓ Media validation passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
