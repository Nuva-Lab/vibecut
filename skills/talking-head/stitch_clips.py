#!/usr/bin/env python3
"""
Stitch approved clips into final video.

V3 Pipeline: Concatenate high-resolution clips in approved order
to create the final output video.

Key features:
- Uses high-res originals (not low-res analysis versions)
- Supports custom ordering via --approved flag
- Optional crossfade transitions
- Interactive clip selection with scores display
"""

import json
import subprocess
import sys
from pathlib import Path
import argparse
import tempfile


def format_clip_summary(clip: dict) -> str:
    """Format a clip for display."""
    clip_id = clip.get("clip_id", "?")
    score = clip.get("viral_score", 0)
    topic = clip.get("topic_brief", "")[:35]
    rec = clip.get("recommended_use", "?")
    duration = clip.get("duration_sec", clip.get("original_end_sec", 0) - clip.get("original_start_sec", 0))

    return f"  [{clip_id:3d}] {score}/10 {rec:8s} ({duration:.1f}s) {topic}"


def display_clips_for_review(clips: list) -> str:
    """Generate a formatted display of clips for user review."""
    lines = [
        "=" * 60,
        "CLIP SCORES (sorted by viral_score)",
        "=" * 60,
        "",
    ]

    # Group by recommendation
    hooks = [c for c in clips if c.get("recommended_use") == "opening"]
    middle = [c for c in clips if c.get("recommended_use") == "middle"]
    closing = [c for c in clips if c.get("recommended_use") == "closing"]
    skip = [c for c in clips if c.get("recommended_use") == "skip" or c.get("viral_score", 0) < 5]

    if hooks:
        lines.append("RECOMMENDED HOOKS (opening):")
        for c in hooks[:5]:
            lines.append(format_clip_summary(c))
        lines.append("")

    if middle:
        lines.append("MIDDLE CONTENT:")
        for c in middle[:10]:
            lines.append(format_clip_summary(c))
        lines.append("")

    if closing:
        lines.append("CLOSING CANDIDATES:")
        for c in closing[:5]:
            lines.append(format_clip_summary(c))
        lines.append("")

    if skip:
        lines.append(f"SKIP ({len(skip)} clips with score < 5)")
        lines.append("")

    lines.append("-" * 60)
    lines.append("To create video, use:")
    lines.append("  --approved CLIP_IDS (e.g., --approved 3,7,12,5)")
    lines.append("  --auto (use recommended order)")
    lines.append("-" * 60)

    return "\n".join(lines)


def get_clip_path(clip: dict, highres_clips_dir: str = None) -> str:
    """Get the best available path for a clip (prefer high-res)."""
    # Priority: highres_path > original path > lowres_path
    if clip.get("highres_path") and Path(clip["highres_path"]).exists():
        return clip["highres_path"]

    # Try to find in highres_clips_dir
    if highres_clips_dir:
        clip_id = clip.get("clip_id")
        hires_path = Path(highres_clips_dir) / f"clip_{clip_id:03d}.mp4"
        if hires_path.exists():
            return str(hires_path)

    # Fallback to original path from clip_index
    if clip.get("path") and Path(clip["path"]).exists():
        return clip["path"]

    # Last resort: lowres path
    if clip.get("lowres_path") and Path(clip["lowres_path"]).exists():
        return clip["lowres_path"]

    return None


def stitch_clips(
    clip_ids: list[int],
    scores_path: str,
    output_path: str,
    highres_clips_dir: str = None,
    crossfade_ms: int = 0,
    precise_cut: bool = True,
) -> dict:
    """
    Stitch clips together in specified order.

    Args:
        clip_ids: List of clip IDs in desired order
        scores_path: Path to clip_scores.json
        output_path: Output video path
        highres_clips_dir: Directory with high-res clips
        crossfade_ms: Crossfade duration between clips (0 = hard cut)
        precise_cut: If True, re-encode for frame-accurate concatenation.
                     If False, use stream copy (faster but may have boundary issues).

    Returns:
        Dict with output info
    """
    # Load scores
    with open(scores_path) as f:
        scores = json.load(f)

    # Build clip lookup
    clip_lookup = {c.get("clip_id"): c for c in scores.get("clips", [])}

    # Validate clip IDs
    valid_clips = []
    for clip_id in clip_ids:
        if clip_id not in clip_lookup:
            print(f"Warning: Clip {clip_id} not found in scores, skipping")
            continue

        clip = clip_lookup[clip_id]
        clip_path = get_clip_path(clip, highres_clips_dir)

        if not clip_path:
            print(f"Warning: No video file found for clip {clip_id}, skipping")
            continue

        valid_clips.append({
            "clip_id": clip_id,
            "path": clip_path,
            "data": clip,
        })

    if not valid_clips:
        print("Error: No valid clips to stitch", file=sys.stderr)
        sys.exit(1)

    print(f"=== Stitching {len(valid_clips)} Clips ===")
    for i, vc in enumerate(valid_clips, 1):
        score = vc["data"].get("viral_score", 0)
        topic = vc["data"].get("topic_brief", "")[:30]
        print(f"  {i}. Clip {vc['clip_id']} ({score}/10) - {topic}")

    # Calculate total duration
    total_duration = 0
    for vc in valid_clips:
        clip_path = Path(vc["path"])
        result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json', str(clip_path)
        ], capture_output=True, text=True)
        try:
            duration = float(json.loads(result.stdout)['format']['duration'])
            vc["duration"] = duration
            total_duration += duration
        except (KeyError, json.JSONDecodeError):
            vc["duration"] = 0

    print(f"\nTotal duration: {total_duration:.1f}s ({total_duration/60:.1f}min)")

    # Create concat file
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        concat_path = f.name
        for vc in valid_clips:
            # FFmpeg concat demuxer needs escaped paths
            escaped_path = vc["path"].replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")

    # Stitch with FFmpeg
    cut_mode = "precise (re-encode)" if precise_cut else "fast (stream copy)"
    print(f"\nStitching clips [{cut_mode}]...")

    if crossfade_ms > 0:
        # With crossfade (requires re-encoding)
        # Build complex filter for crossfades
        # This is more complex, fall back to simple concat for now
        print(f"Note: Crossfade not yet implemented, using hard cuts")

    if precise_cut:
        # Re-encode for clean concatenation (no boundary artifacts)
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_path,
            # Video: re-encode with x264
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            # Audio: re-encode AAC
            '-c:a', 'aac', '-b:a', '192k',
            output_path,
        ]
    else:
        # Stream copy (faster but may have issues at clip boundaries)
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_path,
            '-c', 'copy',
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=True, timeout=600)

    # Clean up
    Path(concat_path).unlink()

    if Path(output_path).exists():
        output_size = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"\n✓ Created {output_path}")
        print(f"  Size: {output_size:.1f}MB")
        print(f"  Duration: {total_duration:.1f}s")

        return {
            "output_path": output_path,
            "num_clips": len(valid_clips),
            "duration_sec": total_duration,
            "clip_order": [vc["clip_id"] for vc in valid_clips],
            "clips": [
                {
                    "clip_id": vc["clip_id"],
                    "path": vc["path"],
                    "duration": vc.get("duration", 0),
                    "viral_score": vc["data"].get("viral_score", 0),
                    "topic": vc["data"].get("topic_brief", ""),
                }
                for vc in valid_clips
            ],
        }
    else:
        print(f"\n✗ Failed to create {output_path}")
        if result.stderr:
            print(f"Error: {result.stderr.decode()[:200]}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Stitch approved clips into final video'
    )
    parser.add_argument('scores', help='clip_scores.json from batch_analyze')
    parser.add_argument('--approved', '-a',
                        help='Comma-separated clip IDs in desired order (e.g., 3,7,12,5)')
    parser.add_argument('--auto', action='store_true',
                        help='Use automatically recommended order')
    parser.add_argument('--output', '-o', default='final.mp4',
                        help='Output video path')
    parser.add_argument('--highres-dir', '-d',
                        help='Directory with high-res original clips')
    parser.add_argument('--crossfade', '-c', type=int, default=0,
                        help='Crossfade duration in ms (default: 0 = hard cut)')
    parser.add_argument('--review', '-r', action='store_true',
                        help='Display clips for review without stitching')
    parser.add_argument('--min-score', '-m', type=int, default=6,
                        help='Minimum viral score for auto mode (default: 6)')
    parser.add_argument('--fast', action='store_true',
                        help='Use stream copy (faster but may have boundary artifacts)')
    args = parser.parse_args()

    # Validate
    if not Path(args.scores).exists():
        print(f"Error: Scores file not found: {args.scores}", file=sys.stderr)
        sys.exit(1)

    # Load scores
    with open(args.scores) as f:
        scores = json.load(f)

    clips = scores.get("clips", [])

    # Review mode
    if args.review or (not args.approved and not args.auto):
        print(display_clips_for_review(clips))
        return

    # Get clip order
    if args.approved:
        # Parse approved list
        try:
            clip_ids = [int(x.strip()) for x in args.approved.split(',')]
        except ValueError:
            print("Error: --approved must be comma-separated integers", file=sys.stderr)
            sys.exit(1)
    elif args.auto:
        # Use recommended order from scores
        recommended = scores.get("summary", {}).get("recommended_order", [])
        if recommended:
            clip_ids = recommended
        else:
            # Fall back to all clips above min_score, sorted by viral_score
            clip_ids = [
                c["clip_id"] for c in clips
                if c.get("viral_score", 0) >= args.min_score
            ]

        if not clip_ids:
            print("Error: No clips meet minimum score threshold", file=sys.stderr)
            sys.exit(1)

        print(f"Auto-selected {len(clip_ids)} clips: {clip_ids}")
    else:
        print("Error: Specify --approved or --auto", file=sys.stderr)
        sys.exit(1)

    # Stitch
    result = stitch_clips(
        clip_ids,
        args.scores,
        args.output,
        highres_clips_dir=args.highres_dir,
        crossfade_ms=args.crossfade,
        precise_cut=not args.fast,  # Default is precise (re-encode)
    )

    if result:
        # Save manifest
        manifest_path = Path(args.output).with_suffix('.json')
        with open(manifest_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved manifest to {manifest_path}")


if __name__ == "__main__":
    main()
