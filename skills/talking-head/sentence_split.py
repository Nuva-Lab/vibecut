#!/usr/bin/env python3
"""
Sentence-level video splitting using Qwen3-ASR word timestamps.

V3 Pipeline: Split at sentence boundaries (pauses >500ms) to create
precise ~10-15s clips for efficient Gemini batch analysis.

Benefits over old approach (60s clips):
- 3-5x smaller uploads (~3MB vs ~20MB per clip)
- Precise sentence boundaries (no mid-word cuts)
- Flexible reordering at sentence level
- Minimal waste on unusable content
"""

import json
import subprocess
import sys
from pathlib import Path
import argparse


def find_sentence_boundaries(
    words: list,
    min_pause_ms: int = 500,
    punctuation_pause_ms: int = 300,
) -> list:
    """
    Find sentence boundaries based on pauses and punctuation.

    Args:
        words: List of word dicts with {text, start, end, pause_before_ms}
        min_pause_ms: Minimum pause duration to consider as sentence boundary
        punctuation_pause_ms: Lower threshold for pauses after punctuation

    Returns:
        List of boundary indices (word index where new sentence starts)
    """
    if not words:
        return []

    # Sentence-ending punctuation patterns
    sentence_enders = {'.', '!', '?', '。', '！', '？', '；', '…'}

    boundaries = [0]  # First word always starts a sentence

    for i in range(1, len(words)):
        word = words[i]
        prev_word = words[i - 1]
        pause_ms = word.get("pause_before_ms", 0)

        # Check if previous word ends with sentence punctuation
        prev_text = prev_word.get("text", "").strip()
        ends_with_punct = prev_text and prev_text[-1] in sentence_enders

        # Boundary conditions:
        # 1. Long pause (>500ms) - natural speech boundary
        # 2. Medium pause (>300ms) after punctuation
        if pause_ms >= min_pause_ms:
            boundaries.append(i)
        elif ends_with_punct and pause_ms >= punctuation_pause_ms:
            boundaries.append(i)

    return boundaries


def group_into_clips(
    words: list,
    boundaries: list,
    max_duration_sec: float = 15.0,
    min_duration_sec: float = 3.0,
    target_duration_sec: float = 10.0,
) -> list:
    """
    Group sentences into clips respecting duration constraints.

    If no natural boundaries exist within max_duration, forces splits at
    word boundaries near target_duration.

    Args:
        words: List of word dicts
        boundaries: Sentence boundary indices
        max_duration_sec: Maximum clip duration
        min_duration_sec: Minimum clip duration
        target_duration_sec: Target clip duration

    Returns:
        List of clip dicts with {clip_id, start_idx, end_idx, start_sec, end_sec, text}
    """
    if not words:
        return []

    # If only one boundary (start), add artificial boundaries at target intervals
    if len(boundaries) <= 1:
        boundaries = [0]
        current_time = words[0]["start"]
        for idx, word in enumerate(words[1:], 1):
            if word["start"] - current_time >= target_duration_sec:
                boundaries.append(idx)
                current_time = word["start"]

    clips = []
    clip_id = 1
    current_idx = 0

    while current_idx < len(words):
        start_idx = current_idx
        start_sec = words[start_idx]["start"]
        target_end_sec = start_sec + target_duration_sec
        max_end_sec = start_sec + max_duration_sec

        # Find best end point
        best_end_idx = start_idx
        best_end_sec = words[start_idx]["end"]

        for idx in range(start_idx + 1, len(words)):
            word_end = words[idx]["end"]
            duration = word_end - start_sec

            if duration > max_duration_sec:
                # Exceeded max, stop here
                break

            best_end_idx = idx
            best_end_sec = word_end

            # Check if next word is a boundary and we've hit target
            if duration >= target_duration_sec:
                # Look for a natural boundary nearby
                is_boundary = (idx + 1) in boundaries
                if is_boundary or idx + 1 >= len(words):
                    break
                # Check if close to a boundary
                for b in boundaries:
                    if b > idx and b <= idx + 5:  # Within 5 words
                        # Extend to boundary if it doesn't exceed max
                        boundary_end_sec = words[b - 1]["end"]
                        if boundary_end_sec - start_sec <= max_duration_sec:
                            best_end_idx = b - 1
                            best_end_sec = boundary_end_sec
                        break
                break

        # Extract text for this clip
        clip_words = words[start_idx:best_end_idx + 1]
        clip_text = " ".join(w["text"] for w in clip_words)

        clips.append({
            "clip_id": clip_id,
            "start_idx": start_idx,
            "end_idx": best_end_idx,
            "start_sec": start_sec,
            "end_sec": best_end_sec,
            "duration_sec": best_end_sec - start_sec,
            "text": clip_text,
            "word_count": len(clip_words),
        })

        clip_id += 1
        current_idx = best_end_idx + 1

    return clips


def split_video_by_clips(
    video_path: str,
    clips: list,
    output_dir: Path,
    add_padding_ms: int = 0,
    precise_cut: bool = True,
) -> list:
    """
    Extract video clips at specified boundaries using FFmpeg.

    Args:
        video_path: Source video path
        clips: List of clip dicts from group_into_clips()
        output_dir: Output directory for clips
        add_padding_ms: Padding to add before/after each clip
        precise_cut: If True, re-encode for frame-accurate cuts (no overlap).
                     If False, use stream copy (faster but may have extra frames).

    Returns:
        Updated clips list with output paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    padding_sec = add_padding_ms / 1000.0

    for clip in clips:
        clip_id = clip["clip_id"]
        start_sec = max(0, clip["start_sec"] - padding_sec)
        end_sec = clip["end_sec"] + padding_sec
        duration = end_sec - start_sec

        output_path = output_dir / f"clip_{clip_id:03d}.mp4"

        if precise_cut:
            # Re-encode for frame-accurate cuts (no overlapping frames)
            # -ss before -i for fast seeking, then re-encode for precision
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_sec),
                '-i', video_path,
                '-t', str(duration),
                '-map', '0:v:0', '-map', '0:a:0',
                # Video: re-encode with x264, quality CRF 18
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                # Audio: re-encode AAC for clean cuts
                '-c:a', 'aac', '-b:a', '192k',
                # Ensure audio sync
                '-async', '1',
                '-avoid_negative_ts', 'make_zero',
                str(output_path),
            ]
        else:
            # Stream copy (fast but may have keyframe boundary issues)
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_sec),
                '-i', video_path,
                '-t', str(duration),
                '-map', '0:v:0', '-map', '0:a:0',
                '-c', 'copy',
                '-avoid_negative_ts', '1',
                str(output_path),
            ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)

        if output_path.exists():
            clip["path"] = str(output_path)
            clip["actual_start_sec"] = start_sec
            clip["actual_end_sec"] = end_sec
            print(f"  ✓ clip_{clip_id:03d}.mp4 ({duration:.1f}s) - {clip['text'][:40]}...")
        else:
            clip["path"] = None
            print(f"  ✗ clip_{clip_id:03d}.mp4 FAILED")
            if result.stderr:
                print(f"    Error: {result.stderr.decode()[:100]}")

    return clips


def split_by_sentences(
    video_path: str,
    transcript_path: str,
    output_dir: str,
    max_clip_duration: float = 15.0,
    min_clip_duration: float = 3.0,
    target_clip_duration: float = 10.0,
    min_pause_ms: int = 500,
    add_padding_ms: int = 0,
    precise_cut: bool = True,
) -> dict:
    """
    Split video at sentence boundaries.

    Uses Qwen3-ASR word timestamps to find sentence ends (pauses >500ms).
    Each clip is 1-3 complete sentences, never mid-word.

    By default uses precise_cut=True which re-encodes for frame-accurate cuts
    with zero overlapping frames between clips.

    Args:
        video_path: Path to source video
        transcript_path: Path to transcript JSON with word-level timestamps
        output_dir: Output directory for clips
        max_clip_duration: Maximum clip duration in seconds
        min_clip_duration: Minimum clip duration in seconds
        target_clip_duration: Target clip duration in seconds
        min_pause_ms: Minimum pause duration to detect sentence boundary
        add_padding_ms: Padding to add before/after each clip

    Returns:
        Dict with clips list and metadata
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load transcript
    with open(transcript_path) as f:
        transcript = json.load(f)

    # Get words with timestamps
    words = transcript.get("words", [])
    if not words:
        # Try to get from chunks
        for chunk in transcript.get("chunks", []):
            if "words" in chunk:
                words.extend(chunk["words"])

    if not words:
        print("Error: No word-level timestamps found in transcript.", file=sys.stderr)
        print("Run transcription with --word-timestamps flag first.", file=sys.stderr)
        sys.exit(1)

    print(f"=== Sentence-Level Video Splitting ===")
    print(f"Source: {video_path}")
    print(f"Words: {len(words)}")
    print(f"Duration constraints: {min_clip_duration}s - {max_clip_duration}s (target: {target_clip_duration}s)")

    # Find sentence boundaries
    print(f"\nFinding sentence boundaries (pause threshold: {min_pause_ms}ms)...")
    boundaries = find_sentence_boundaries(words, min_pause_ms=min_pause_ms)
    print(f"  Found {len(boundaries)} sentence boundaries")

    # Group into clips
    print(f"\nGrouping into clips...")
    clips = group_into_clips(
        words,
        boundaries,
        max_duration_sec=max_clip_duration,
        min_duration_sec=min_clip_duration,
        target_duration_sec=target_clip_duration,
    )
    print(f"  Created {len(clips)} clips")

    # Stats
    total_duration = sum(c["duration_sec"] for c in clips)
    avg_duration = total_duration / len(clips) if clips else 0
    print(f"  Total: {total_duration:.1f}s, Avg: {avg_duration:.1f}s per clip")

    # Extract clips
    cut_mode = "precise (re-encode)" if precise_cut else "fast (stream copy)"
    print(f"\nExtracting clips to {output_dir}/ [{cut_mode}]...")
    clips = split_video_by_clips(
        str(video_path),
        clips,
        output_dir,
        add_padding_ms=add_padding_ms,
        precise_cut=precise_cut,
    )

    # Save clip index
    result = {
        "source_video": str(video_path),
        "source_transcript": str(transcript_path),
        "num_clips": len(clips),
        "total_duration_sec": total_duration,
        "avg_duration_sec": avg_duration,
        "settings": {
            "max_clip_duration": max_clip_duration,
            "min_clip_duration": min_clip_duration,
            "target_clip_duration": target_clip_duration,
            "min_pause_ms": min_pause_ms,
            "add_padding_ms": add_padding_ms,
        },
        "clips": clips,
    }

    index_path = output_dir / "clip_index.json"
    with open(index_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Created {len(clips)} sentence-level clips")
    print(f"✓ Saved index to {index_path}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Split video at sentence boundaries using word timestamps'
    )
    parser.add_argument('video', help='Input video file')
    parser.add_argument('transcript', help='Transcript JSON with word-level timestamps')
    parser.add_argument('--output', '-o', default='sentence_clips',
                        help='Output directory for clips')
    parser.add_argument('--max-duration', '-m', type=float, default=15.0,
                        help='Maximum clip duration in seconds (default: 15)')
    parser.add_argument('--min-duration', type=float, default=3.0,
                        help='Minimum clip duration in seconds (default: 3)')
    parser.add_argument('--target-duration', '-t', type=float, default=10.0,
                        help='Target clip duration in seconds (default: 10)')
    parser.add_argument('--min-pause', '-p', type=int, default=500,
                        help='Minimum pause for sentence boundary in ms (default: 500)')
    parser.add_argument('--padding', type=int, default=0,
                        help='Padding before/after clips in ms (default: 0 for zero overlap)')
    parser.add_argument('--fast', action='store_true',
                        help='Use stream copy (faster but may have overlapping frames at boundaries)')
    args = parser.parse_args()

    # Validate inputs
    if not Path(args.video).exists():
        print(f"Error: Video not found: {args.video}", file=sys.stderr)
        sys.exit(1)
    if not Path(args.transcript).exists():
        print(f"Error: Transcript not found: {args.transcript}", file=sys.stderr)
        sys.exit(1)

    result = split_by_sentences(
        args.video,
        args.transcript,
        args.output,
        max_clip_duration=args.max_duration,
        min_clip_duration=args.min_duration,
        target_clip_duration=args.target_duration,
        min_pause_ms=args.min_pause,
        add_padding_ms=args.padding,
        precise_cut=not args.fast,  # Default is precise (re-encode)
    )

    print(f"\nNext steps:")
    print(f"  1. Convert to low-res: python lowres_convert.py {args.output}/ -o lowres_clips/")
    print(f"  2. Batch analyze: python batch_analyze.py lowres_clips/ -o clip_scores.json")


if __name__ == "__main__":
    main()
