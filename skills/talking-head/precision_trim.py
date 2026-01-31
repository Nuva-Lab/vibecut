#!/usr/bin/env python3
"""
Precision trimming for talking-head videos.

Phase 2 of the two-phase editing workflow:
1. RECALL (done): Find complete topics with full arcs
2. PRECISION (this): Trim filler, pauses, repetitions for polished output

Key insight: Gemini identifies WHAT to cut (semantic), ASR provides WHERE to cut (precise timestamps).

Pipeline:
1. Qwen3-ASR: Get word-level timestamps (~30-50ms accuracy)
2. Gemini: Identify which words/phrases to cut (by content, not timestamp)
3. Map: Match Gemini's semantic cuts to exact word boundaries
4. FFmpeg: Cut precisely at word boundaries
"""

import json
import sys
from pathlib import Path
import argparse
import re
import subprocess

# Add shared and other skills to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))
sys.path.insert(0, str(Path(__file__).parent.parent / "chunk-process"))


def transcribe_with_words(video_path: str, output_path: str = None) -> dict:
    """
    Transcribe video and get word-level timestamps using MLX Qwen3-ASR + ForcedAligner.

    Returns:
        {
            "text": "full transcript...",
            "words": [
                {"text": "VC", "start": 4.2, "end": 4.5},
                {"text": "are", "start": 4.5, "end": 4.7},
                ...
            ]
        }
    """
    # Import from our chunk-process skill (MLX version)
    from mlx_transcribe import transcribe_with_mlx

    print(f"Transcribing with MLX Qwen3-ASR + ForcedAligner (~30ms precision)...")

    # Extract audio from video
    audio_path = Path(video_path).with_suffix('.wav')
    if not audio_path.exists():
        print(f"  Extracting audio to {audio_path}...")
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
            str(audio_path)
        ], capture_output=True)

    # Transcribe with word timestamps using MLX
    # Use English as default - mixed Chinese/English content is common
    result = transcribe_with_mlx(
        str(audio_path),
        return_word_timestamps=True,
        language="English",  # MLX requires explicit language
    )

    # Words already in correct format from MLX transcribe
    words = result.get("words", [])

    transcript_result = {
        "text": result.get("text", ""),
        "words": words,
        "duration_sec": words[-1]["end"] if words else 0,
        "model": result.get("model", ""),
    }

    print(f"  Found {len(words)} words/characters")
    print(f"  Duration: {transcript_result['duration_sec']:.1f}s")

    if output_path:
        with open(output_path, "w") as f:
            json.dump(transcript_result, f, ensure_ascii=False, indent=2)
        print(f"  Saved to {output_path}")

    return transcript_result


def format_transcript_with_indices(words: list) -> str:
    """Format transcript with word indices for Gemini to reference."""
    lines = []
    for i, word in enumerate(words):
        lines.append(f"[{i}]{word['text']}")
    return " ".join(lines)


PRECISION_CUT_PROMPT = """
Analyze this talking-head video transcript. Your task is to identify FILLER CONTENT to cut.

## TRANSCRIPT (with word indices)
{transcript}

## WHAT TO CUT

Mark word ranges to REMOVE:
1. **Filler words**: "uh", "um", "like", "you know", "so", "basically"
2. **Hesitations**: Pauses, stuttering, false starts
3. **Repetitions**: Same word said twice ("they they"), restating same point
4. **Non-fluent speech**: Broken sentences, rambling
5. **Practice talk**: Chinese phrases, "is that good?", coordination

## WHAT TO KEEP

1. **Strong hooks**: "VC are the most hypocritical animals"
2. **Key insights**: Actual valuable information
3. **Clear explanations**: Well-articulated points
4. **Conclusions**: Clear takeaways

## OUTPUT FORMAT (JSON)

Return word index ranges to CUT:

{{
  "cuts": [
    {{
      "start_word_idx": 0,
      "end_word_idx": 15,
      "reason": "Chinese practice talk at beginning",
      "words": "不要 每句话 都 开始..."
    }},
    {{
      "start_word_idx": 45,
      "end_word_idx": 48,
      "reason": "filler 'uh' and stutter",
      "words": "Uh most of the"
    }}
  ],
  "summary": {{
    "total_words": 500,
    "words_to_cut": 150,
    "estimated_reduction_pct": 30
  }}
}}

## IMPORTANT

1. Use WORD INDICES from the transcript (numbers in brackets)
2. Cut at WORD BOUNDARIES - never mid-word
3. Include a few words of context in "words" field
4. Be aggressive but preserve meaning
5. Target: Cut 30-50% of filler content
"""


def identify_cuts_with_gemini(
    video_path: str,
    transcript: dict,
    output_path: str = None,
) -> dict:
    """
    Have Gemini watch video and identify what to cut by word indices.
    """
    from gemini_client import client, upload_video, DEFAULT_MODEL
    from google.genai import types

    words = transcript.get("words", [])
    indexed_transcript = format_transcript_with_indices(words)

    print(f"\nUploading video to Gemini for analysis...")
    video_file = upload_video(video_path)

    print(f"Identifying filler content...")
    prompt = PRECISION_CUT_PROMPT.format(transcript=indexed_transcript)

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=[video_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    # Parse response
    text = response.text
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        result = json.loads(json_match.group(1))
    else:
        result = json.loads(text)

    # Validate and enrich cuts with actual timestamps
    cuts = result.get("cuts", [])
    validated_cuts = []

    for cut in cuts:
        start_idx = cut.get("start_word_idx", 0)
        end_idx = cut.get("end_word_idx", 0)

        # Validate indices
        if start_idx >= len(words) or end_idx >= len(words):
            print(f"  Warning: Invalid word indices {start_idx}-{end_idx}, skipping")
            continue

        # Get precise timestamps from word data
        start_word = words[start_idx]
        end_word = words[end_idx]

        validated_cuts.append({
            **cut,
            "start_sec": start_word["start"],
            "end_sec": end_word["end"],
            "duration_sec": end_word["end"] - start_word["start"],
        })

    result["cuts"] = validated_cuts
    result["total_words"] = len(words)

    # Calculate stats
    total_cut_sec = sum(c["duration_sec"] for c in validated_cuts)
    original_duration = transcript.get("duration_sec", 0)
    result["total_cut_sec"] = total_cut_sec
    result["estimated_final_sec"] = original_duration - total_cut_sec

    print(f"\n=== Analysis Results ===")
    print(f"Cuts identified: {len(validated_cuts)}")
    print(f"Total cut time: {total_cut_sec:.1f}s")
    print(f"Estimated final: {result['estimated_final_sec']:.1f}s")

    if output_path:
        with open(output_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nSaved analysis to {output_path}")

    return result


def merge_overlapping_cuts(cuts: list) -> list:
    """Merge overlapping or adjacent cut segments."""
    if not cuts:
        return []

    # Sort by start time
    sorted_cuts = sorted(cuts, key=lambda x: x["start_sec"])

    merged = [sorted_cuts[0].copy()]

    for cut in sorted_cuts[1:]:
        last = merged[-1]
        # If overlapping or adjacent (within 0.1s), merge
        if cut["start_sec"] <= last["end_sec"] + 0.1:
            last["end_sec"] = max(last["end_sec"], cut["end_sec"])
            last["end_word_idx"] = max(last.get("end_word_idx", 0), cut.get("end_word_idx", 0))
            last["duration_sec"] = last["end_sec"] - last["start_sec"]
            last["reason"] = last.get("reason", "") + " + " + cut.get("reason", "")
        else:
            merged.append(cut.copy())

    return merged


def generate_keep_segments(
    cuts: list,
    duration: float,
    words: list,
    min_keep_duration: float = 1.0,
) -> list:
    """
    Convert cut list to keep list (inverse).
    Ensures we keep from word end to word start for clean boundaries.

    Args:
        cuts: List of cut segments
        duration: Total video duration
        words: Word list (for reference)
        min_keep_duration: Minimum duration for a kept segment.
            Segments shorter than this will be merged into adjacent cuts
            to avoid jittery micro-segments.
    """
    merged_cuts = merge_overlapping_cuts(cuts)

    # First pass: generate raw keeps
    raw_keeps = []
    current = 0.0

    for cut in merged_cuts:
        if cut["start_sec"] > current + 0.05:  # At least 50ms segment
            raw_keeps.append({
                "start_sec": current,
                "end_sec": cut["start_sec"],
                "duration_sec": cut["start_sec"] - current,
            })
        current = cut["end_sec"]

    # Add final segment
    if current < duration - 0.05:
        raw_keeps.append({
            "start_sec": current,
            "end_sec": duration,
            "duration_sec": duration - current,
        })

    # Second pass: filter out micro-segments that cause jitter
    # Segments shorter than min_keep_duration are dropped (merged into cuts)
    keeps = []
    dropped_count = 0
    dropped_duration = 0.0

    for keep in raw_keeps:
        if keep["duration_sec"] >= min_keep_duration:
            keeps.append(keep)
        else:
            dropped_count += 1
            dropped_duration += keep["duration_sec"]

    if dropped_count > 0:
        print(f"  Note: Dropped {dropped_count} micro-segments (<{min_keep_duration}s) totaling {dropped_duration:.1f}s to reduce jitter")

    return keeps


def apply_precise_cuts(
    video_path: str,
    cuts_analysis: dict,
    transcript: dict,
    output_path: str,
    min_keep_duration: float = 1.0,
) -> dict:
    """
    Apply precision cuts using FFmpeg with exact timestamps.

    Uses filter_complex to trim and concatenate segments.

    Args:
        min_keep_duration: Minimum duration for kept segments.
            Shorter segments are dropped to avoid jittery micro-cuts.
    """
    words = transcript.get("words", [])
    duration = transcript.get("duration_sec", 0)
    cuts = cuts_analysis.get("cuts", [])

    print(f"\n=== Applying Precision Cuts ===")
    print(f"Source: {video_path}")
    print(f"Output: {output_path}")
    print(f"Min keep duration: {min_keep_duration}s (to avoid jitter)")

    # Generate keep segments
    keeps = generate_keep_segments(cuts, duration, words, min_keep_duration)

    print(f"\nKeeping {len(keeps)} segments:")
    total_kept = 0
    for i, keep in enumerate(keeps):
        dur = keep["duration_sec"]
        total_kept += dur
        print(f"  {i+1}. {keep['start_sec']:.2f}s - {keep['end_sec']:.2f}s ({dur:.2f}s)")

    print(f"\nTotal kept: {total_kept:.1f}s (from {duration:.1f}s original)")

    if len(keeps) == 0:
        print("Error: No segments to keep!")
        return {"error": "No segments to keep"}

    # Build FFmpeg filter complex
    filter_parts = []
    concat_inputs = []

    for i, keep in enumerate(keeps):
        start = keep["start_sec"]
        end = keep["end_sec"]

        # Use precise timestamps with setpts to reset
        filter_parts.append(
            f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}]"
        )
        filter_parts.append(
            f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}]"
        )
        concat_inputs.append(f"[v{i}][a{i}]")

    # Concatenate all segments
    concat_str = "".join(concat_inputs)
    filter_parts.append(f"{concat_str}concat=n={len(keeps)}:v=1:a=1[outv][outa]")

    filter_complex = ";".join(filter_parts)

    # Build and run FFmpeg command
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-c:a', 'aac', '-b:a', '192k',
        output_path,
    ]

    print(f"\nRunning FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if Path(output_path).exists():
        # Verify output
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', output_path],
            capture_output=True, text=True
        )
        actual_duration = float(probe.stdout.strip())

        print(f"\n✓ Created: {output_path}")
        print(f"Duration: {actual_duration:.1f}s")

        return {
            "output": output_path,
            "duration_sec": actual_duration,
            "segments_kept": len(keeps),
            "kept_segments": keeps,
        }
    else:
        print(f"\n✗ FAILED to create video")
        print(f"Error: {result.stderr[:500]}")
        return {"error": result.stderr}


def run_precision_pipeline(
    video_path: str,
    output_dir: str,
    skip_transcribe: bool = False,
) -> dict:
    """
    Run the full precision trimming pipeline.

    1. Transcribe with word-level timestamps (Qwen3-ASR)
    2. Identify cuts with Gemini (semantic analysis)
    3. Apply precise cuts (FFmpeg)
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PRECISION TRIM PIPELINE")
    print("=" * 60)
    print(f"Input: {video_path}")
    print(f"Output: {output_dir}")

    # Step 1: Transcribe
    transcript_path = output_dir / "word_transcript.json"
    if skip_transcribe and transcript_path.exists():
        print(f"\nLoading existing transcript from {transcript_path}")
        with open(transcript_path) as f:
            transcript = json.load(f)
    else:
        print(f"\n[Step 1/3] Transcribing with Qwen3-ASR...")
        transcript = transcribe_with_words(str(video_path), str(transcript_path))

    # Step 2: Identify cuts with Gemini
    cuts_path = output_dir / "precision_cuts.json"
    print(f"\n[Step 2/3] Identifying cuts with Gemini...")
    cuts_analysis = identify_cuts_with_gemini(
        str(video_path),
        transcript,
        str(cuts_path),
    )

    # Step 3: Apply cuts
    output_video = output_dir / f"{video_path.stem}_trimmed.mp4"
    print(f"\n[Step 3/3] Applying precision cuts...")
    result = apply_precise_cuts(
        str(video_path),
        cuts_analysis,
        transcript,
        str(output_video),
    )

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)

    return result


def format_cuts_for_review(cuts_analysis: dict, transcript: dict) -> str:
    """Format cuts for user review."""
    lines = [
        "=" * 60,
        "PRECISION CUT ANALYSIS",
        "=" * 60,
        "",
    ]

    cuts = cuts_analysis.get("cuts", [])
    total_cut = sum(c.get("duration_sec", 0) for c in cuts)
    original = transcript.get("duration_sec", 0)

    lines.append(f"Original duration: {original:.1f}s")
    lines.append(f"Total to cut: {total_cut:.1f}s")
    lines.append(f"Estimated final: {original - total_cut:.1f}s ({100*(original-total_cut)/original:.0f}%)")
    lines.append("")
    lines.append("CUTS (by word index):")

    for i, cut in enumerate(cuts, 1):
        start_idx = cut.get("start_word_idx", 0)
        end_idx = cut.get("end_word_idx", 0)
        start_sec = cut.get("start_sec", 0)
        end_sec = cut.get("end_sec", 0)
        reason = cut.get("reason", "")
        words = cut.get("words", "")[:40]

        lines.append(f"  {i}. Words [{start_idx}-{end_idx}] @ {start_sec:.2f}s-{end_sec:.2f}s")
        lines.append(f"     Reason: {reason}")
        if words:
            lines.append(f"     \"{words}...\"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Precision trim talking-head video using ASR + Gemini'
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Full pipeline
    pipeline_parser = subparsers.add_parser('run', help='Run full precision pipeline')
    pipeline_parser.add_argument('video', help='Video to process')
    pipeline_parser.add_argument('--output', '-o', default='precision_output',
                                 help='Output directory')
    pipeline_parser.add_argument('--skip-transcribe', action='store_true',
                                 help='Skip transcription if already done')

    # Transcribe only
    transcribe_parser = subparsers.add_parser('transcribe', help='Transcribe with word timestamps')
    transcribe_parser.add_argument('video', help='Video to transcribe')
    transcribe_parser.add_argument('--output', '-o', help='Output JSON file')

    # Identify cuts only
    identify_parser = subparsers.add_parser('identify', help='Identify cuts with Gemini')
    identify_parser.add_argument('video', help='Video file')
    identify_parser.add_argument('transcript', help='Transcript JSON with word timestamps')
    identify_parser.add_argument('--output', '-o', default='precision_cuts.json',
                                 help='Output JSON file')

    # Apply cuts only
    apply_parser = subparsers.add_parser('apply', help='Apply precision cuts')
    apply_parser.add_argument('video', help='Source video')
    apply_parser.add_argument('cuts', help='Cuts analysis JSON')
    apply_parser.add_argument('transcript', help='Transcript JSON')
    apply_parser.add_argument('--output', '-o', required=True, help='Output video')

    args = parser.parse_args()

    if args.command == 'run':
        run_precision_pipeline(args.video, args.output, args.skip_transcribe)

    elif args.command == 'transcribe':
        output = args.output or Path(args.video).with_suffix('.words.json')
        transcribe_with_words(args.video, str(output))

    elif args.command == 'identify':
        with open(args.transcript) as f:
            transcript = json.load(f)
        result = identify_cuts_with_gemini(args.video, transcript, args.output)
        print("\n" + format_cuts_for_review(result, transcript))

    elif args.command == 'apply':
        with open(args.cuts) as f:
            cuts = json.load(f)
        with open(args.transcript) as f:
            transcript = json.load(f)
        apply_precise_cuts(args.video, cuts, transcript, args.output)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
