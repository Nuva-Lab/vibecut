#!/usr/bin/env python3
"""
Transcribe a video clip using Gemini with timestamped segments.
"""
import json
import sys
from pathlib import Path

# Add skills/shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from gemini_client import analyze_video_json, upload_video

TRANSCRIBE_PROMPT = """
Transcribe this video clip with precise timestamps.

Return a JSON object with:

1. **segments**: Array of transcript segments, each with:
   - start: Start time in seconds (float, e.g., 0.0, 3.5)
   - end: End time in seconds (float)
   - text: The spoken text for this segment
   - speaker: Speaker name if identifiable (optional)

2. **full_text**: Complete transcript as a single string

Guidelines:
- Break segments at natural sentence boundaries
- Each segment should be 3-8 seconds long for readable captions
- Timestamps should be precise - they will be used for caption timing
- Include all spoken words, even filler words like "um", "uh"
- If there are multiple speakers, note speaker changes

Example output:
{
  "segments": [
    {"start": 0.0, "end": 4.2, "text": "Mining Bitcoin also pays off the infrastructure.", "speaker": "Jihan Wu"},
    {"start": 4.2, "end": 8.5, "text": "The CapEx very easily within the first two or three years.", "speaker": "Jihan Wu"}
  ],
  "full_text": "Mining Bitcoin also pays off the infrastructure. The CapEx very easily within the first two or three years."
}
"""


def transcribe_clip(video_path: str, output_path: str = None) -> dict:
    """
    Transcribe a video clip with timestamps.

    Args:
        video_path: Path to video file
        output_path: Optional path to save JSON output

    Returns:
        Transcript dict with segments and full_text
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    print(f"Transcribing: {video_path.name}")

    # Upload and transcribe
    uploaded = upload_video(str(video_path))
    result = analyze_video_json(uploaded, TRANSCRIBE_PROMPT)

    # Validate structure
    if "segments" not in result:
        result["segments"] = []
    if "full_text" not in result:
        result["full_text"] = " ".join(s.get("text", "") for s in result.get("segments", []))

    # Save output if path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Transcript saved to: {output_path}")
    else:
        # Default output path
        output_dir = Path(__file__).parent.parent.parent / "assets" / "outputs" / "transcripts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{video_path.stem}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Transcript saved to: {output_file}")

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <video_path> [output_json]")
        print("Example: python transcribe.py clip.mp4")
        sys.exit(1)

    video_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = transcribe_clip(video_path, output_path)

    # Print summary
    print(f"\nTranscript ({len(result.get('segments', []))} segments):")
    print("-" * 50)
    for seg in result.get("segments", [])[:5]:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "")[:60]
        print(f"[{start:.1f}s - {end:.1f}s] {text}...")


if __name__ == "__main__":
    main()
