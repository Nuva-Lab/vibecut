#!/usr/bin/env python3
"""
Batch video analysis using Gemini API.

V3 Pipeline: Upload sentence-level clips in batches of 10 to Gemini
for efficient viral potential scoring and speaker identification.

Benefits:
- Process many small clips instead of few large ones
- 10 clips per batch = optimal for Gemini's 10-file limit
- Pre-scored clips enable smart ordering decisions
"""

import json
import sys
from pathlib import Path
import argparse
from typing import Optional

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))


BATCH_ANALYSIS_PROMPT = """
Analyze these video clips for viral potential and content quality.

For EACH clip in order, provide:

## Output Format (JSON array)

Return a JSON array with one object per clip, in the SAME ORDER as uploaded:

[
  {
    "clip_num": 1,
    "viral_score": 8,
    "content_quality": 9,
    "hook_potential": 7,
    "quotability": 8,
    "standalone_value": 9,
    "speaker_name": "Name if identifiable",
    "speaker_visible": true,
    "speaker_emotion": "confident/thoughtful/passionate/etc",
    "topic_brief": "5-10 word topic summary",
    "key_quote": "Most quotable phrase from clip",
    "issues": ["any problems: audio, visual, delivery"],
    "clip_type": "hook/insight/story/advice/reaction",
    "recommended_use": "opening/middle/closing/skip",
    "notes": "Brief analysis notes"
  },
  ...
]

## Scoring Guide

**viral_score** (1-10): Would this clip perform well on social media?
- 10: Extremely shareable, controversial, or insightful
- 7-9: Strong content, clear value
- 5-6: Decent but not standout
- 1-4: Weak, skip this clip

**hook_potential** (1-10): Does this grab attention in first 3 seconds?
- 10: Impossible to scroll past
- 7-9: Strong opener
- 1-6: Not suitable as hook

**standalone_value** (1-10): Does this make sense without prior context?
- 10: Completely self-contained
- 5-7: Needs some setup
- 1-4: Too dependent on context

## Clip Types

- **hook**: Great for opening - provocative, credibility, or question
- **insight**: Key takeaway or revelation
- **story**: Personal anecdote or example
- **advice**: Actionable recommendation
- **reaction**: Emotional moment, audience reaction

Be selective and honest. Not every clip deserves a high score.
"""


def analyze_batch(
    clip_paths: list[str],
    clip_metadata: list[dict] = None,
) -> list[dict]:
    """
    Analyze a batch of clips with Gemini (max 10 per batch).

    Args:
        clip_paths: List of video file paths (max 10)
        clip_metadata: Optional metadata about each clip

    Returns:
        List of analysis results for each clip
    """
    from gemini_client import upload_videos, client, DEFAULT_MODEL
    from google.genai import types
    import re

    if len(clip_paths) > 10:
        raise ValueError("Max 10 clips per batch (Gemini limit)")

    # Build context-aware prompt
    prompt_parts = []

    if clip_metadata:
        prompt_parts.append("## Clip Context\n\n")
        for i, meta in enumerate(clip_metadata, 1):
            transcript = meta.get("text", "")[:200]
            duration = meta.get("duration_sec", 0)
            prompt_parts.append(
                f"**Clip {i}** ({duration:.1f}s): {transcript}...\n\n"
            )
        prompt_parts.append("---\n\n")

    prompt_parts.append(BATCH_ANALYSIS_PROMPT)
    full_prompt = "".join(prompt_parts)

    # Upload clips
    print(f"  Uploading {len(clip_paths)} clips...")
    uploaded = upload_videos(clip_paths, parallel=True, max_workers=5)

    # Analyze
    print(f"  Analyzing with Gemini...")
    contents = uploaded + [full_prompt]

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    # Parse response
    text = response.text
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        results = json.loads(json_match.group(1))
    else:
        results = json.loads(text)

    return results


def batch_analyze_clips(
    clips_dir: str,
    output_path: str,
    batch_size: int = 10,
    clip_index_path: str = None,
    highres_index_path: str = None,
) -> dict:
    """
    Analyze all clips in directory with Gemini in batches.

    Args:
        clips_dir: Directory with low-res clips
        output_path: Output JSON file
        batch_size: Clips per batch (max 10)
        clip_index_path: Optional index JSON with clip metadata
        highres_index_path: Optional index of high-res originals

    Returns:
        Dict with all clip scores and metadata
    """
    clips_dir = Path(clips_dir)

    # Load clip metadata if available
    clip_metadata = {}
    if clip_index_path and Path(clip_index_path).exists():
        with open(clip_index_path) as f:
            index = json.load(f)
        for clip in index.get("clips", []):
            clip_id = clip.get("clip_id")
            if clip_id:
                clip_metadata[clip_id] = clip

    # Also check for index in clips_dir
    lowres_index_path = clips_dir / "lowres_index.json"
    if lowres_index_path.exists() and not clip_index_path:
        with open(lowres_index_path) as f:
            lowres_index = json.load(f)
        # Get original clip info
        source_dir = lowres_index.get("source_dir")
        if source_dir:
            source_index_path = Path(source_dir) / "clip_index.json"
            if source_index_path.exists():
                with open(source_index_path) as f:
                    index = json.load(f)
                for clip in index.get("clips", []):
                    clip_id = clip.get("clip_id")
                    if clip_id:
                        clip_metadata[clip_id] = clip

    # Find clips
    clip_files = sorted(clips_dir.glob("clip_*.mp4"))

    if not clip_files:
        print(f"Error: No clips found in {clips_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"=== Batch Video Analysis ===")
    print(f"Clips: {len(clip_files)}")
    print(f"Batch size: {batch_size}")
    print(f"Batches: {(len(clip_files) + batch_size - 1) // batch_size}")

    all_results = []
    batch_num = 0

    for i in range(0, len(clip_files), batch_size):
        batch_num += 1
        batch_clips = clip_files[i:i + batch_size]

        print(f"\n--- Batch {batch_num} ({len(batch_clips)} clips) ---")

        # Get metadata for this batch
        batch_metadata = []
        for clip_path in batch_clips:
            # Extract clip_id from filename (clip_001.mp4 -> 1)
            try:
                clip_id = int(clip_path.stem.split('_')[1])
            except (IndexError, ValueError):
                clip_id = None

            if clip_id and clip_id in clip_metadata:
                batch_metadata.append(clip_metadata[clip_id])
            else:
                batch_metadata.append({"text": "", "duration_sec": 0})

        try:
            results = analyze_batch(
                [str(p) for p in batch_clips],
                clip_metadata=batch_metadata,
            )

            # Map results back to clip files
            for j, result in enumerate(results):
                clip_path = batch_clips[j]
                clip_id = int(clip_path.stem.split('_')[1])

                # Merge with original metadata
                if clip_id in clip_metadata:
                    result["original_text"] = clip_metadata[clip_id].get("text", "")
                    result["original_start_sec"] = clip_metadata[clip_id].get("start_sec", 0)
                    result["original_end_sec"] = clip_metadata[clip_id].get("end_sec", 0)

                result["clip_id"] = clip_id
                result["lowres_path"] = str(clip_path)

                # Find high-res path
                if highres_index_path:
                    with open(highres_index_path) as f:
                        hires_index = json.load(f)
                    for hc in hires_index.get("clips", []):
                        if hc.get("clip_id") == clip_id:
                            result["highres_path"] = hc.get("path")
                            break

                all_results.append(result)

                # Print summary
                score = result.get("viral_score", 0)
                topic = result.get("topic_brief", "")[:30]
                rec = result.get("recommended_use", "")
                print(f"  Clip {clip_id:3d}: score={score}/10, {rec:8s}, {topic}")

        except Exception as e:
            print(f"  Batch {batch_num} FAILED: {e}")
            # Add placeholder results for failed batch
            for clip_path in batch_clips:
                clip_id = int(clip_path.stem.split('_')[1])
                all_results.append({
                    "clip_id": clip_id,
                    "lowres_path": str(clip_path),
                    "viral_score": 0,
                    "error": str(e),
                })

    # Sort by viral score descending
    all_results.sort(key=lambda x: x.get("viral_score", 0), reverse=True)

    # Save results
    output_data = {
        "source_dir": str(clips_dir),
        "num_clips": len(all_results),
        "batch_size": batch_size,
        "clips": all_results,
        "summary": {
            "top_hooks": [
                c for c in all_results
                if c.get("hook_potential", 0) >= 8
            ][:3],
            "recommended_order": [
                c["clip_id"] for c in all_results
                if c.get("recommended_use") != "skip" and c.get("viral_score", 0) >= 6
            ],
            "skip_list": [
                c["clip_id"] for c in all_results
                if c.get("recommended_use") == "skip" or c.get("viral_score", 0) < 5
            ],
        },
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"\n=== Analysis Complete ===")
    print(f"Clips analyzed: {len(all_results)}")

    top_clips = [c for c in all_results if c.get("viral_score", 0) >= 8]
    skip_clips = [c for c in all_results if c.get("viral_score", 0) < 5]
    print(f"Top clips (score >= 8): {len(top_clips)}")
    print(f"Skip clips (score < 5): {len(skip_clips)}")

    if top_clips:
        print(f"\nTop 5 clips:")
        for c in top_clips[:5]:
            print(f"  Clip {c['clip_id']}: {c.get('viral_score', 0)}/10 - {c.get('topic_brief', '')[:40]}")

    print(f"\n✓ Saved results to {output_path}")

    return output_data


def main():
    parser = argparse.ArgumentParser(
        description='Batch analyze video clips with Gemini'
    )
    parser.add_argument('clips_dir', help='Directory with low-res clips')
    parser.add_argument('--output', '-o', default='clip_scores.json',
                        help='Output JSON file')
    parser.add_argument('--batch-size', '-b', type=int, default=10,
                        help='Clips per batch (default: 10, max: 10)')
    parser.add_argument('--clip-index', '-i',
                        help='Clip index JSON with metadata')
    parser.add_argument('--highres-index',
                        help='High-res clip index for final output paths')
    args = parser.parse_args()

    # Validate
    if not Path(args.clips_dir).exists():
        print(f"Error: Clips directory not found: {args.clips_dir}", file=sys.stderr)
        sys.exit(1)

    if args.batch_size > 10:
        print("Warning: Max batch size is 10 (Gemini limit), using 10")
        args.batch_size = 10

    result = batch_analyze_clips(
        args.clips_dir,
        args.output,
        batch_size=args.batch_size,
        clip_index_path=args.clip_index,
        highres_index_path=args.highres_index,
    )

    print(f"\nNext steps:")
    print(f"  1. Review clip_scores.json")
    print(f"  2. Stitch approved clips: python stitch_clips.py {args.output} --approved 1,3,5,2")


if __name__ == "__main__":
    main()
