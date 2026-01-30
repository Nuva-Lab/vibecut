#!/usr/bin/env python3
"""
transcribe-audio: ASR with precise timestamps using Qwen3-ASR.

Uses Qwen3-ASR for transcription and Qwen3-ForcedAligner for ~30ms timestamp precision.
Runs on CPU (quality first).
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict


def transcribe_audio(
    audio_path: str,
    language: str = None,
    return_timestamps: bool = True,
    device: str = "cpu",
) -> dict:
    """
    Transcribe audio with precise timestamps using Qwen3-ASR.

    Args:
        audio_path: Path to audio/video file
        language: Language hint (None for auto-detect)
        return_timestamps: Use ForcedAligner for precise timestamps (~30ms)
        device: Device to use ('cpu' or 'mps')

    Returns:
        dict with segments (timestamped), full_text, language, model
    """
    import torch
    from qwen_asr import Qwen3ASRModel

    audio_path = str(Path(audio_path).resolve())

    print(f"Loading Qwen3-ASR-1.7B on {device}...")

    # Load model with optional ForcedAligner
    if return_timestamps:
        model = Qwen3ASRModel.from_pretrained(
            "Qwen/Qwen3-ASR-1.7B",
            dtype=torch.float32,
            device_map=device,
            forced_aligner="Qwen/Qwen3-ForcedAligner-0.6B",
            forced_aligner_kwargs=dict(
                dtype=torch.float32,
                device_map=device,
            ),
        )
    else:
        model = Qwen3ASRModel.from_pretrained(
            "Qwen/Qwen3-ASR-1.7B",
            dtype=torch.float32,
            device_map=device,
        )

    print(f"Transcribing: {audio_path}")

    # Transcribe
    results = model.transcribe(
        audio=audio_path,
        language=language,
        return_time_stamps=return_timestamps,
    )

    result = results[0]
    detected_language = result.language
    full_text = result.text

    # Build segments from timestamps
    segments = []
    if return_timestamps and hasattr(result, 'time_stamps') and result.time_stamps:
        # time_stamps is a list of aligned words/characters
        for ts in result.time_stamps[0]:  # First (and only) audio result
            segments.append({
                "text": ts.text,
                "startMs": int(ts.start_time * 1000),
                "endMs": int(ts.end_time * 1000),
            })

    return {
        "segments": segments,
        "full_text": full_text.strip(),
        "language": detected_language,
        "model": "Qwen3-ASR-1.7B",
        "aligner": "Qwen3-ForcedAligner-0.6B" if return_timestamps else None,
    }


def transcribe_and_align(
    audio_path: str,
    text: str,
    language: str = "Chinese",
    device: str = "cpu",
) -> dict:
    """
    Align existing text to audio using Qwen3-ForcedAligner.

    Use this when you already have the transcript and just need timestamps.
    ~30ms precision.

    Args:
        audio_path: Path to audio file
        text: Text to align
        language: Language of the text
        device: Device to use ('cpu' or 'mps')

    Returns:
        dict with segments (word-level timestamps)
    """
    import torch
    from qwen_asr import Qwen3ForcedAligner

    audio_path = str(Path(audio_path).resolve())

    print(f"Loading Qwen3-ForcedAligner on {device}...")
    aligner = Qwen3ForcedAligner.from_pretrained(
        "Qwen/Qwen3-ForcedAligner-0.6B",
        dtype=torch.float32,
        device_map=device,
    )

    print(f"Aligning text to audio: {audio_path}")

    results = aligner.align(
        audio=audio_path,
        text=text,
        language=language,
    )

    # Build segments from alignment results
    segments = []
    for word in results[0]:
        segments.append({
            "text": word.text,
            "startMs": int(word.start_time * 1000),
            "endMs": int(word.end_time * 1000),
        })

    return {
        "segments": segments,
        "full_text": text,
        "language": language,
        "model": "Qwen3-ForcedAligner-0.6B",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio with Qwen3-ASR (~30ms timestamp precision)"
    )
    parser.add_argument("audio", help="Path to audio/video file")
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file (default: prints to stdout)"
    )
    parser.add_argument(
        "--language", "-l",
        help="Language hint (e.g., 'Chinese', 'English'). Auto-detects if not specified."
    )
    parser.add_argument(
        "--no-timestamps",
        action="store_true",
        help="Skip timestamp alignment (faster, no ForcedAligner)"
    )
    parser.add_argument(
        "--align-text",
        help="Align this text to audio instead of transcribing (use ForcedAligner only)"
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "mps"],
        default="cpu",
        help="Device to use (default: cpu)"
    )

    args = parser.parse_args()

    # Validate input
    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Error: File not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    # Choose mode
    if args.align_text:
        # Alignment-only mode
        result = transcribe_and_align(
            str(audio_path),
            text=args.align_text,
            language=args.language or "Chinese",
            device=args.device,
        )
    else:
        # Full transcription
        result = transcribe_audio(
            str(audio_path),
            language=args.language,
            return_timestamps=not args.no_timestamps,
            device=args.device,
        )

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Saved to: {output_path}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # Summary
    print(f"\n--- Summary ---")
    print(f"Model: {result['model']}")
    if result.get('aligner'):
        print(f"Aligner: {result['aligner']}")
    print(f"Language: {result.get('language', 'N/A')}")
    print(f"Segments: {len(result['segments'])}")
    print(f"Full text length: {len(result['full_text'])} chars")

    return result


if __name__ == "__main__":
    main()
