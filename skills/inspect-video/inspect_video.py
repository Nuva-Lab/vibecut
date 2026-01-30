#!/usr/bin/env python3
"""
Gemini-powered video inspection for quality analysis.
"""
import json
import os
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.gemini_client import analyze_video as gemini_analyze


DEFAULT_QUALITY_PROMPT = """Analyze this video for quality issues. Please check for:

1. **Visual Quality**: Any freezes, black frames, glitches, or artifacts?
2. **Motion**: Does the video play smoothly or are there stutters/jumps?
3. **Audio Sync**: If there's audio, does it appear synchronized with video?
4. **Content**: Briefly describe what's happening in the video.
5. **Overlays**: Are there any text overlays, captions, or graphics? Are they readable?

Provide your analysis in this JSON format:
{
  "description": "Brief description of video content",
  "duration_observed": "approximate duration",
  "visual_quality": "excellent/good/fair/poor",
  "issues_found": ["list of specific issues with timestamps if possible"],
  "overlays_present": ["list of overlays like captions, badges, titles"],
  "recommendations": ["suggestions for improvement"]
}

Be specific about any problems and include timestamps where possible (e.g., "freeze at 35s")."""


def inspect_video(video_path: str, prompt: str = None) -> dict:
    """
    Inspect video using Gemini.

    Args:
        video_path: Path to video file
        prompt: Custom inspection prompt (uses default quality check if None)

    Returns:
        Inspection results
    """
    path = Path(video_path)
    if not path.exists():
        return {"error": f"Video not found: {video_path}"}

    inspection_prompt = prompt or DEFAULT_QUALITY_PROMPT

    try:
        result = gemini_analyze(
            video_file=str(path),
            prompt=inspection_prompt
        )

        # Try to parse as JSON if using default prompt
        if prompt is None:
            try:
                # Extract JSON from response
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    return json.loads(result[json_start:json_end])
            except json.JSONDecodeError:
                pass

        return {"response": result}

    except Exception as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_video.py <video_file> [--prompt 'custom query']")
        print("\nInspects video using Gemini for quality issues and content analysis.")
        print("\nExamples:")
        print("  python inspect_video.py video.mp4")
        print("  python inspect_video.py video.mp4 --prompt 'Who are the speakers?'")
        sys.exit(1)

    video_path = sys.argv[1]

    # Parse optional prompt
    prompt = None
    if "--prompt" in sys.argv:
        prompt_idx = sys.argv.index("--prompt")
        if prompt_idx + 1 < len(sys.argv):
            prompt = sys.argv[prompt_idx + 1]

    print(f"Inspecting: {video_path}")
    if prompt:
        print(f"Query: {prompt}")
    print()

    result = inspect_video(video_path, prompt)

    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Summary for default inspection
    if "issues_found" in result:
        issues = result.get("issues_found", [])
        if issues:
            print(f"\n⚠️  Found {len(issues)} issue(s)")
        else:
            print("\n✓ No quality issues detected")


if __name__ == "__main__":
    main()
