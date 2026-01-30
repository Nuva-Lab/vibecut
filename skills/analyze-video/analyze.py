#!/usr/bin/env python3
"""
Analyze video content using Gemini to identify speakers, topics, and clip opportunities.
"""
import json
import sys
from pathlib import Path

# Add skills/shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from gemini_client import analyze_video_json, upload_video

ANALYSIS_PROMPT = """
Analyze this video from Davos 2026 and provide a comprehensive breakdown in JSON format.

Identify and extract:

1. **speakers**: Array of people who appear/speak
   - name: Their name if identifiable, otherwise descriptive (e.g., "Male panelist in blue suit")
   - role: Their title/organization if mentioned or identifiable
   - first_seen: Timestamp (MM:SS) when they first appear

2. **topics**: Array of main subjects/themes discussed

3. **notable_quotes**: Array of memorable statements
   - speaker: Who said it
   - quote: The exact or near-exact quote
   - timestamp: When it was said (MM:SS)
   - context: Brief context of why it's notable

4. **visual_highlights**: Array of visually interesting moments
   - timestamp: When it occurs (MM:SS)
   - description: What happens
   - type: One of "gesture", "reveal", "reaction", "visual_aid", "other"

5. **audience_reactions**: Array of audience engagement moments
   - timestamp: When it occurs (MM:SS)
   - type: One of "applause", "laughter", "murmur", "silence", "other"
   - description: Brief description

6. **panel_exchanges**: Array of interesting back-and-forth moments
   - start: Start timestamp (MM:SS)
   - end: End timestamp (MM:SS)
   - participants: Array of speaker names involved
   - description: What the exchange is about

7. **clip_opportunities**: Array of segments that would make good 15-60 second clips
   - start: Start timestamp (MM:SS)
   - end: End timestamp (MM:SS)
   - duration_seconds: Length in seconds
   - type: One of "quote", "exchange", "highlight", "reaction", "insight"
   - description: Why this would make a good clip
   - score: 1-10 rating of clip potential (10 = must include)

Also include:
- **video_duration**: Total duration in seconds
- **summary**: 2-3 sentence summary of the video content

Focus on finding genuinely engaging moments that would work as standalone short clips.
Timestamps must be accurate - they will be used for video cutting.
"""


def analyze_video_file(video_path: str, output_dir: str = None) -> dict:
    """
    Analyze a video file and save results to JSON.

    Args:
        video_path: Path to video file
        output_dir: Directory for output JSON (default: assets/outputs/analysis)

    Returns:
        Analysis results dict
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Set up output directory
    if output_dir is None:
        output_dir = video_path.parent.parent / "assets" / "outputs" / "analysis"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing: {video_path.name}")
    print(f"Size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Upload and analyze
    uploaded = upload_video(str(video_path))
    print("Running analysis...")

    result = analyze_video_json(uploaded, ANALYSIS_PROMPT)

    # Add metadata
    result["source_file"] = str(video_path)
    result["file_size_mb"] = round(video_path.stat().st_size / 1024 / 1024, 1)

    # Save output
    output_path = output_dir / f"{video_path.stem}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Analysis saved to: {output_path}")
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <video_path>")
        print("Example: python analyze.py ./video.mp4")
        sys.exit(1)

    video_path = sys.argv[1]
    result = analyze_video_file(video_path)

    # Print summary
    print("\n" + "=" * 50)
    print("ANALYSIS SUMMARY")
    print("=" * 50)

    if "summary" in result:
        print(f"\n{result['summary']}")

    if "speakers" in result:
        print(f"\nSpeakers ({len(result['speakers'])}):")
        for s in result["speakers"]:
            print(f"  - {s.get('name', 'Unknown')} ({s.get('role', 'N/A')})")

    if "topics" in result:
        print(f"\nTopics: {', '.join(result['topics'])}")

    if "clip_opportunities" in result:
        clips = result["clip_opportunities"]
        print(f"\nClip Opportunities ({len(clips)}):")
        for c in sorted(clips, key=lambda x: x.get("score", 0), reverse=True)[:5]:
            print(f"  [{c.get('score', '?')}/10] {c.get('start', '?')}-{c.get('end', '?')}: {c.get('description', '')[:60]}")


if __name__ == "__main__":
    main()
