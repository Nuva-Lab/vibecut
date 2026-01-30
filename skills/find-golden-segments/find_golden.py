#!/usr/bin/env python3
"""
Find golden segments in video - naturally clean moments worth keeping.
Selection over repair: find what's good, don't try to fix what's broken.
"""
import json
import sys
from pathlib import Path

# Add skills/shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from gemini_client import analyze_video_json, upload_video

FIND_GOLDEN_PROMPT = """
Analyze this video and find "golden segments" - continuous portions that would make excellent short clips WITHOUT any editing or cutting.

Your job is SELECTION, not repair. Find the moments that are already naturally good.

## What Makes a Golden Segment (ALL criteria must be met)

1. **Duration**: 10-30 seconds of continuous content
2. **Complete thought**: Contains a full idea, insight, or statement - not cut mid-sentence
3. **Clean delivery**: Minimal filler words (0-2 "uh/um" max, not 10+)
4. **Speaker confidence**: Clear, confident speech - not stumbling or hesitant
5. **Visual stability**: Camera relatively steady, speaker not moving erratically
6. **Standalone value**: Makes sense without needing extensive context

## What to SKIP (don't try to salvage these)

- Heavy filler usage ("uh", "um" every few words)
- Incomplete thoughts or sentences
- Speaker clearly struggling or losing their train of thought
- Very shaky camera or poor framing
- Background noise or interruptions

## Scoring (only include segments scoring 7+)

- 10: Perfect - could post immediately
- 9: Excellent - minor imperfections
- 8: Very good - clean and coherent
- 7: Good - meets all basic criteria
- Below 7: Skip entirely

Return JSON with:

{
  "golden_segments": [
    {
      "start": "MM:SS",
      "end": "MM:SS",
      "duration_sec": N,
      "score": N,
      "speaker": "Name or description",
      "topic": "Brief 5-10 word topic",
      "quote_preview": "First 10-15 words of what they say...",
      "quality_notes": "Why this segment is good (clean delivery, strong point, etc.)"
    }
  ],
  "skipped_regions": [
    {
      "start": "MM:SS",
      "end": "MM:SS",
      "reason": "Brief reason (heavy fillers, incomplete thought, etc.)"
    }
  ],
  "video_context": {
    "setting": "Brief description of setting/event",
    "main_speakers": ["List of speakers identified"],
    "overall_topic": "Main topic of the video"
  },
  "summary": {
    "total_duration_sec": N,
    "golden_duration_sec": N,
    "golden_percentage": N,
    "segments_found": N,
    "recommendation": "Brief assessment - is this video worth using?"
  }
}

Be selective - it's better to return 2-3 excellent segments than 10 mediocre ones.
If no segments meet the quality bar, return an empty golden_segments array.
"""


def find_golden_segments(
    video_path: str,
    output_path: str = None,
    min_duration: int = 10,
    min_score: int = 7,
) -> dict:
    """
    Find golden segments in a video.

    Args:
        video_path: Path to video file
        output_path: Optional path to save JSON output
        min_duration: Minimum segment duration in seconds
        min_score: Minimum quality score (1-10)

    Returns:
        Detection results with golden_segments
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    file_size_mb = video_path.stat().st_size / 1024 / 1024
    print(f"Analyzing: {video_path.name}")
    print(f"Size: {file_size_mb:.0f} MB")

    # Upload video
    print("Uploading to Gemini (this may take a while for large files)...")
    uploaded = upload_video(str(video_path))

    # Analyze
    print("Finding golden segments...")
    result = analyze_video_json(uploaded, FIND_GOLDEN_PROMPT)

    # Filter by min_duration and min_score
    if "golden_segments" in result:
        original_count = len(result["golden_segments"])
        result["golden_segments"] = [
            s for s in result["golden_segments"]
            if s.get("duration_sec", 0) >= min_duration
            and s.get("score", 0) >= min_score
        ]
        filtered_count = len(result["golden_segments"])
        if original_count != filtered_count:
            print(f"Filtered: {original_count} → {filtered_count} segments (min {min_duration}s, score {min_score}+)")

    # Save output
    if output_path is None:
        output_dir = Path(__file__).parent.parent.parent / "assets" / "outputs" / "golden"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_path.stem}_golden.json"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Results saved to: {output_path}")
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_golden.py <video_path> [--min-duration N] [--min-score N]")
        print("")
        print("Options:")
        print("  --min-duration N  Minimum segment duration in seconds (default: 10)")
        print("  --min-score N     Minimum quality score 1-10 (default: 7)")
        print("")
        print("Example:")
        print("  python find_golden.py video.MOV")
        print("  python find_golden.py video.MOV --min-duration 15 --min-score 8")
        sys.exit(1)

    video_path = sys.argv[1]

    # Parse options
    min_duration = 10
    min_score = 7

    if "--min-duration" in sys.argv:
        idx = sys.argv.index("--min-duration")
        if idx + 1 < len(sys.argv):
            min_duration = int(sys.argv[idx + 1])

    if "--min-score" in sys.argv:
        idx = sys.argv.index("--min-score")
        if idx + 1 < len(sys.argv):
            min_score = int(sys.argv[idx + 1])

    result = find_golden_segments(video_path, min_duration=min_duration, min_score=min_score)

    # Print summary
    segments = result.get("golden_segments", [])
    summary = result.get("summary", {})
    context = result.get("video_context", {})

    print(f"\n{'='*60}")
    print("GOLDEN SEGMENTS FOUND")
    print(f"{'='*60}")

    if context:
        print(f"\nSetting: {context.get('setting', 'Unknown')}")
        print(f"Topic: {context.get('overall_topic', 'Unknown')}")
        if context.get('main_speakers'):
            print(f"Speakers: {', '.join(context['main_speakers'])}")

    print(f"\nTotal duration: {summary.get('total_duration_sec', '?')}s")
    print(f"Golden duration: {summary.get('golden_duration_sec', '?')}s ({summary.get('golden_percentage', '?')}%)")
    print(f"Segments found: {len(segments)}")

    if summary.get('recommendation'):
        print(f"\nRecommendation: {summary['recommendation']}")

    if segments:
        print(f"\n{'-'*60}")
        print("SEGMENTS:")
        print(f"{'-'*60}")
        for i, seg in enumerate(segments, 1):
            print(f"\n[{i}] Score {seg.get('score', '?')}/10 | {seg.get('start', '?')} - {seg.get('end', '?')} ({seg.get('duration_sec', '?')}s)")
            print(f"    Speaker: {seg.get('speaker', 'Unknown')}")
            print(f"    Topic: {seg.get('topic', 'N/A')}")
            print(f"    Quote: \"{seg.get('quote_preview', '...')}\"")
            if seg.get('quality_notes'):
                print(f"    Notes: {seg['quality_notes']}")
    else:
        print("\nNo golden segments found meeting quality criteria.")
        print("Try a different video or lower the --min-score threshold.")


if __name__ == "__main__":
    main()
