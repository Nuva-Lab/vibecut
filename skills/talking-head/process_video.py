#!/usr/bin/env python3
"""
Talking-head video processing pipeline.

Text-first analysis with sentence-level precision.

Pipeline:
1. CHUNK: Split video into ~3 min chunks at natural boundaries
2. TRANSCRIBE: MLX Qwen3-ASR with word-level timestamps
3. SENTENCE SPLIT: Split at pauses >500ms into ~10-15s clips
4. SCRIPT ANALYSIS: Gemini reads full transcript, finds highlights
5. CLIP SELECTION: Interactive review in Claude Code
6. STITCH: Concatenate approved high-res clips

Key insight: Text-first analysis is faster and gives Gemini full context.
Instead of uploading video clips, we send the full transcript and map
highlights back to clip IDs using the sentence index.

Usage:
    # Full pipeline (pauses for clip selection)
    python process_video.py raw_footage.mp4 --output-dir ./project/

    # Auto-stitch top clips
    python process_video.py raw_footage.mp4 --output-dir ./project/ --auto-stitch
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe."""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json', video_path
    ], capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])


def format_clip_scores_for_review(clips: list, max_display: int = 15) -> str:
    """
    Format clip scores for Claude Code to present in conversation.

    Returns a nicely formatted string for interactive review.
    """
    lines = [
        "=" * 60,
        "CLIP ANALYSIS COMPLETE - Ready for Review",
        "=" * 60,
        "",
    ]

    # Group by recommendation
    hooks = [c for c in clips if c.get("recommended_use") == "opening" and c.get("viral_score", 0) >= 7]
    middle = [c for c in clips if c.get("recommended_use") == "middle" and c.get("viral_score", 0) >= 6]
    closing = [c for c in clips if c.get("recommended_use") == "closing" and c.get("viral_score", 0) >= 6]
    usable = [c for c in clips if c.get("viral_score", 0) >= 6]
    skip = [c for c in clips if c.get("viral_score", 0) < 5]

    if hooks:
        lines.append("RECOMMENDED HOOKS (strong openers):")
        for c in sorted(hooks, key=lambda x: -x.get("hook_potential", 0))[:5]:
            lines.append(f"  [{c['clip_id']:3d}] {c.get('viral_score', 0)}/10 "
                        f"hook:{c.get('hook_potential', 0)}/10 - {c.get('topic_brief', '')[:35]}")
            if c.get("key_quote"):
                lines.append(f"        \"{c['key_quote'][:50]}...\"")
        lines.append("")

    if middle:
        lines.append("MIDDLE CONTENT (insights, stories):")
        for c in sorted(middle, key=lambda x: -x.get("viral_score", 0))[:7]:
            lines.append(f"  [{c['clip_id']:3d}] {c.get('viral_score', 0)}/10 - {c.get('topic_brief', '')[:40]}")
        lines.append("")

    if closing:
        lines.append("CLOSING CANDIDATES (takeaways):")
        for c in sorted(closing, key=lambda x: -x.get("standalone_value", 0))[:3]:
            lines.append(f"  [{c['clip_id']:3d}] {c.get('viral_score', 0)}/10 - {c.get('topic_brief', '')[:40]}")
        lines.append("")

    # Summary
    lines.append("-" * 60)
    lines.append(f"Total clips: {len(clips)} | Usable (score>=6): {len(usable)} | Skip: {len(skip)}")
    lines.append("")
    lines.append("NEXT: Tell me which clips to include and in what order.")
    lines.append("Examples:")
    lines.append("  - \"Use clips 7, 12, 3, 5 in that order\"")
    lines.append("  - \"Auto-stitch the top 5 clips\"")
    lines.append("  - \"Show me more details about clip 7\"")
    lines.append("-" * 60)

    return "\n".join(lines)


def run_pipeline(
    video_path: str,
    output_dir: str,
    chunk_duration: int = 180,
    language: str = None,
    skip_chunking: bool = False,
    skip_transcription: bool = False,
    skip_sentence_split: bool = False,
    skip_analysis: bool = False,
    auto_stitch: bool = False,
    min_score: int = 6,
) -> dict:
    """
    Run pipeline with sentence-level clipping and text-first analysis.

    Pipeline:
    1. Chunk video at natural pauses
    2. Transcribe with word-level timestamps
    3. Split at sentence boundaries (~10-15s clips)
    4. Analyze full transcript (text-first, fast)
    5. Review and stitch selected clips

    Args:
        video_path: Path to input video
        output_dir: Directory for all outputs
        chunk_duration: Target chunk duration in seconds
        language: Language hint for transcription (None = auto-detect)
        skip_chunking: Skip chunking phase (use existing chunks)
        skip_transcription: Skip transcription phase
        skip_sentence_split: Skip sentence splitting phase
        skip_analysis: Skip script analysis
        auto_stitch: Automatically stitch top-scoring clips
        min_score: Minimum viral score for auto-stitch

    Returns:
        Dict with pipeline state and outputs
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks_dir = output_dir / "chunks"
    sentence_clips_dir = output_dir / "sentence_clips"

    state = {
        "pipeline": "talking-head-v3",
        "source": str(video_path),
        "output_dir": str(output_dir),
        "phases_completed": [],
    }

    # Get video duration
    total_duration = get_video_duration(str(video_path))
    state["source_duration"] = total_duration
    print(f"=== Talking-Head Pipeline (V3) ===")
    print(f"Source: {video_path}")
    print(f"Duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")

    # ========== PHASE 1: CHUNKING ==========
    print("\n" + "=" * 60)
    print("PHASE 1: Smart Chunking")
    print("=" * 60)

    if skip_chunking and chunks_dir.exists():
        print(f"Skipping chunking (using existing chunks)")
    else:
        chunk_script = Path(__file__).parent.parent / "chunk-process" / "smart_chunk.py"
        subprocess.run([
            sys.executable, str(chunk_script),
            str(video_path),
            "--output-dir", str(chunks_dir),
            "--target", str(chunk_duration),
        ])

    state["phases_completed"].append("chunking")

    # ========== PHASE 2: TRANSCRIPTION WITH WORD TIMESTAMPS ==========
    print("\n" + "=" * 60)
    print("PHASE 2: Transcription with Word Timestamps")
    print("=" * 60)

    transcript_path = chunks_dir / "transcript.json"

    if skip_transcription and transcript_path.exists():
        print(f"Skipping transcription (using existing)")
        with open(transcript_path) as f:
            transcript = json.load(f)
        if "words" not in transcript:
            print("Warning: Existing transcript missing word timestamps")
            print("Re-run without --skip-transcription to get word timestamps")
    else:
        transcribe_script = Path(__file__).parent.parent / "chunk-process" / "mlx_transcribe.py"
        cmd = [
            sys.executable, str(transcribe_script),
            str(chunks_dir),
            "--batch",
            "--output", "transcript.json",
            "--word-timestamps",
        ]
        if language:
            cmd.extend(["--language", language])

        subprocess.run(cmd)

        if transcript_path.exists():
            with open(transcript_path) as f:
                transcript = json.load(f)
            print(f"Transcribed {transcript.get('total_chars', 0)} characters")
            print(f"Words with timestamps: {transcript.get('total_words', 0)}")
        else:
            print("Error: Transcription failed")
            return state

    state["transcript_path"] = str(transcript_path)
    state["phases_completed"].append("transcription")

    # ========== PHASE 3: SENTENCE-LEVEL SPLITTING ==========
    print("\n" + "=" * 60)
    print("PHASE 3: Sentence-Level Splitting")
    print("=" * 60)

    clip_index_path = sentence_clips_dir / "clip_index.json"

    if skip_sentence_split and clip_index_path.exists():
        print(f"Skipping sentence split (using existing clips)")
    else:
        from sentence_split import split_by_sentences

        split_result = split_by_sentences(
            str(video_path),
            str(transcript_path),
            str(sentence_clips_dir),
            max_clip_duration=15.0,
            min_clip_duration=3.0,
            target_clip_duration=10.0,
            min_pause_ms=500,
        )

        print(f"Created {split_result.get('num_clips', 0)} sentence-level clips")

    state["sentence_clips_dir"] = str(sentence_clips_dir)
    state["phases_completed"].append("sentence_split")

    # Note: Low-res conversion skipped by default (text-first analysis doesn't need it)
    # Use lowres_convert.py manually if you need video verification later

    # ========== PHASE 4: SCRIPT ANALYSIS ==========
    print("\n" + "=" * 60)
    print("PHASE 4: Script Analysis (Text-First)")
    print("=" * 60)

    scores_path = output_dir / "clip_scores.json"

    if skip_analysis and scores_path.exists():
        print(f"Skipping analysis (using existing scores)")
    else:
        from analyze_script import analyze_script, format_analysis_for_review

        # Text-first: Gemini reads full transcript, identifies highlights
        # Maps highlights back to clip IDs using sentence index
        analysis_result = analyze_script(
            str(clip_index_path),
            str(scores_path),
        )

        num_highlights = len(analysis_result.get("highlights", []))
        print(f"Found {num_highlights} highlight moments")

        # Convert highlights to clip scores format for compatibility
        clips = []
        for h in analysis_result.get("highlights", []):
            for clip_id in h.get("clip_ids", []):
                # Check if we already have this clip
                existing = next((c for c in clips if c["clip_id"] == clip_id), None)
                if existing:
                    # Update if this highlight has higher score
                    if h.get("viral_score", 0) > existing.get("viral_score", 0):
                        existing.update({
                            "viral_score": h.get("viral_score", 0),
                            "hook_potential": h.get("hook_potential", 0),
                            "standalone_value": h.get("standalone", 0),
                            "topic_brief": h.get("quote", "")[:40],
                            "key_quote": h.get("quote", ""),
                            "recommended_use": "opening" if h.get("hook_potential", 0) >= 8 else "middle",
                        })
                else:
                    clips.append({
                        "clip_id": clip_id,
                        "viral_score": h.get("viral_score", 0),
                        "hook_potential": h.get("hook_potential", 0),
                        "standalone_value": h.get("standalone", 0),
                        "topic_brief": h.get("quote", "")[:40],
                        "key_quote": h.get("quote", ""),
                        "recommended_use": "opening" if h.get("hook_potential", 0) >= 8 else "middle",
                        "clip_type": h.get("type", "insight"),
                    })

        # Sort by viral score
        clips.sort(key=lambda x: x.get("viral_score", 0), reverse=True)

        # Save in clip_scores format
        scores_data = {
            "source_dir": str(sentence_clips_dir),
            "num_clips": len(clips),
            "analysis_type": "script_first",
            "clips": clips,
            "summary": analysis_result.get("summary", {}),
            "highlights": analysis_result.get("highlights", []),
        }

        with open(scores_path, "w") as f:
            json.dump(scores_data, f, ensure_ascii=False, indent=2)

    state["scores_path"] = str(scores_path)
    state["phases_completed"].append("script_analysis")

    # ========== PHASE 5: CLIP SELECTION ==========
    print("\n" + "=" * 60)
    print("PHASE 5: Clip Selection & Stitching")
    print("=" * 60)

    # Load scores
    with open(scores_path) as f:
        scores = json.load(f)

    clips = scores.get("clips", [])

    # Format clips for Claude Code to present
    review_display = format_clip_scores_for_review(clips)
    state["clip_review"] = {
        "display": review_display,
        "clips": clips,
        "scores_path": str(scores_path),
        "sentence_clips_dir": str(sentence_clips_dir),
    }

    # Print for direct CLI use
    print(review_display)

    if auto_stitch:
        # Automatically stitch clips above threshold
        from stitch_clips import stitch_clips

        approved_ids = [
            c["clip_id"] for c in clips
            if c.get("viral_score", 0) >= min_score
        ]

        if approved_ids:
            final_path = output_dir / "final.mp4"
            stitch_result = stitch_clips(
                approved_ids,
                str(scores_path),
                str(final_path),
                highres_clips_dir=str(sentence_clips_dir),
            )

            if stitch_result:
                state["final_path"] = str(final_path)
                state["final_duration"] = stitch_result.get("duration_sec", 0)
                print(f"\n✓ Auto-stitched {len(approved_ids)} clips to {final_path}")
        else:
            print(f"\nNo clips with score >= {min_score} found")
    else:
        # Set checkpoint for Claude Code to present to user
        state["checkpoint"] = "clip_review"
        state["awaiting_user_input"] = True
        state["phases_completed"].append("clip_review_pending")

    # Save state
    state_path = output_dir / "pipeline_state.json"
    with open(state_path, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    if state.get("awaiting_user_input"):
        print("PIPELINE - AWAITING CLIP SELECTION")
        print("=" * 60)
        print("Analysis complete. Waiting for clip selection.")
    else:
        print("PIPELINE COMPLETE")
        print("=" * 60)
        if state.get("final_path"):
            print(f"Final video: {state['final_path']}")

    print(f"\nState saved: {state_path}")
    print(f"Clip scores: {scores_path}")
    print(f"Sentence clips: {sentence_clips_dir}/")

    return state


def stitch_selected_clips(
    output_dir: str,
    clip_ids: list[int],
    output_filename: str = "final.mp4",
) -> dict:
    """
    Stitch selected clips after user review.

    Called by Claude Code after user selects clips from the review.

    Args:
        output_dir: Pipeline output directory
        clip_ids: List of clip IDs in desired order
        output_filename: Name for final video

    Returns:
        Dict with stitch results
    """
    from stitch_clips import stitch_clips

    output_dir = Path(output_dir)
    scores_path = output_dir / "clip_scores.json"
    sentence_clips_dir = output_dir / "sentence_clips"
    final_path = output_dir / output_filename

    if not scores_path.exists():
        return {"error": f"Scores not found: {scores_path}"}

    result = stitch_clips(
        clip_ids,
        str(scores_path),
        str(final_path),
        highres_clips_dir=str(sentence_clips_dir),
    )

    if result:
        # Update pipeline state
        state_path = output_dir / "pipeline_state.json"
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
            state["final_path"] = str(final_path)
            state["final_duration"] = result.get("duration_sec", 0)
            state["selected_clips"] = clip_ids
            state["awaiting_user_input"] = False
            state["checkpoint"] = "complete"
            with open(state_path, "w") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "final_path": str(final_path),
            "duration_sec": result.get("duration_sec", 0),
            "num_clips": len(clip_ids),
            "clip_order": clip_ids,
        }
    else:
        return {"success": False, "error": "Stitch failed"}


def main():
    parser = argparse.ArgumentParser(description='Talking-head video processing (V3)')
    parser.add_argument('video', help='Input video file')
    parser.add_argument('--output-dir', '-o', default='./talking_head_output',
                        help='Output directory')
    parser.add_argument('--chunk-duration', '-c', type=int, default=180,
                        help='Target chunk duration in seconds (default: 180)')
    parser.add_argument('--language', '-l', default=None,
                        help='Language hint for transcription (auto-detect if not specified)')
    parser.add_argument('--skip-chunking', action='store_true',
                        help='Skip chunking phase (use existing chunks)')
    parser.add_argument('--skip-transcription', action='store_true',
                        help='Skip transcription phase')
    parser.add_argument('--skip-sentence-split', action='store_true',
                        help='Skip sentence split phase')
    parser.add_argument('--skip-analysis', action='store_true',
                        help='Skip script analysis phase')
    parser.add_argument('--auto-stitch', action='store_true',
                        help='Automatically stitch top-scoring clips')
    parser.add_argument('--min-score', type=int, default=6,
                        help='Minimum viral score for auto-stitch (default: 6)')

    args = parser.parse_args()

    # Validate input
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    # Run pipeline
    run_pipeline(
        str(video_path),
        args.output_dir,
        chunk_duration=args.chunk_duration,
        language=args.language,
        skip_chunking=args.skip_chunking,
        skip_transcription=args.skip_transcription,
        skip_sentence_split=args.skip_sentence_split,
        skip_analysis=args.skip_analysis,
        auto_stitch=args.auto_stitch,
        min_score=args.min_score,
    )


if __name__ == "__main__":
    main()
