#!/usr/bin/env python3
"""
separate-audio: Text-guided audio source separation.

Uses SAM-Audio via mlx-audio for native Mac M2 inference.
Isolate specific sounds from audio using text descriptions.
"""

import argparse
import sys
from pathlib import Path


def separate_audio(
    audio_path: str,
    prompt: str,
    output_path: str = None,
    span: tuple = None,
    save_residual: bool = False,
    model_size: str = "large",
) -> dict:
    """
    Isolate sounds from audio using text prompt.

    Args:
        audio_path: Path to audio/video file
        prompt: Text description of sound to extract (e.g., "man speaking")
        output_path: Path to save extracted audio (optional)
        span: Time span tuple (start, end) in seconds where target sound occurs
        save_residual: Also save the residual (background) audio
        model_size: Model size ('small', 'base', 'large')

    Returns:
        dict with target_path, residual_path (if saved), prompt, metadata
    """
    import mlx.core as mx
    from mlx_audio.s2s.sam import SAMAudio, SAMAudioProcessor
    import soundfile as sf
    import numpy as np

    audio_path = str(Path(audio_path).resolve())

    # Select model
    model_id = f"mlx-community/sam-audio-{model_size}"

    print(f"Loading SAM-Audio ({model_size})...")
    model = SAMAudio.from_pretrained(model_id)
    processor = SAMAudioProcessor.from_pretrained(model_id)

    print(f"Processing: {audio_path}")
    print(f"Prompt: '{prompt}'")

    # Build batch with optional time span anchor
    if span:
        start, end = span
        print(f"Time span: {start:.1f}s - {end:.1f}s")
        batch = processor(
            audios=[audio_path],
            descriptions=[prompt],
            anchors=[[["+", start, end]]],  # Positive anchor
        )
    else:
        batch = processor(
            audios=[audio_path],
            descriptions=[prompt],
        )

    # Run separation
    print("Separating audio...")
    result = model.separate(batch)

    # Get sample rate from processor
    sample_rate = processor.audio_sampling_rate

    # Convert to numpy
    target_audio = np.array(result.target[0])
    residual_audio = np.array(result.residual[0]) if hasattr(result, 'residual') else None

    # Save outputs
    result_dict = {
        "prompt": prompt,
        "model": f"sam-audio-{model_size}",
        "sample_rate": sample_rate,
    }

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), target_audio, sample_rate)
        result_dict["target_path"] = str(output_path)
        print(f"Saved target: {output_path}")

        if save_residual and residual_audio is not None:
            residual_path = output_path.with_stem(f"{output_path.stem}_residual")
            sf.write(str(residual_path), residual_audio, sample_rate)
            result_dict["residual_path"] = str(residual_path)
            print(f"Saved residual: {residual_path}")
    else:
        result_dict["target_audio"] = target_audio
        if residual_audio is not None:
            result_dict["residual_audio"] = residual_audio

    if span:
        result_dict["span"] = span

    return result_dict


def main():
    parser = argparse.ArgumentParser(
        description="Isolate sounds from audio using text prompts (SAM-Audio)"
    )
    parser.add_argument("audio", help="Path to audio/video file")
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Text description of sound to extract (e.g., 'man speaking')"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path for extracted audio"
    )
    parser.add_argument(
        "--span", "-s",
        help="Time span where target occurs (e.g., '10.5-12.0')"
    )
    parser.add_argument(
        "--save-residual",
        action="store_true",
        help="Also save residual (background) audio"
    )
    parser.add_argument(
        "--model-size",
        choices=["small", "base", "large"],
        default="large",
        help="Model size (default: large)"
    )

    args = parser.parse_args()

    # Validate input
    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Error: File not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    # Parse time span
    span = None
    if args.span:
        try:
            start, end = args.span.split("-")
            span = (float(start), float(end))
        except ValueError:
            print(f"Error: Invalid span format. Use 'start-end' (e.g., '10.5-12.0')", file=sys.stderr)
            sys.exit(1)

    # Generate default output path if not specified
    output_path = args.output
    if not output_path:
        # Create output in same directory as input
        output_path = audio_path.with_stem(f"{audio_path.stem}_separated")

    # Separate
    result = separate_audio(
        str(audio_path),
        prompt=args.prompt,
        output_path=str(output_path),
        span=span,
        save_residual=args.save_residual,
        model_size=args.model_size,
    )

    print(f"\n--- Done ---")
    print(f"Model: {result['model']}")
    print(f"Prompt: {result['prompt']}")
    if result.get("target_path"):
        print(f"Target: {result['target_path']}")
    if result.get("residual_path"):
        print(f"Residual: {result['residual_path']}")

    return result


if __name__ == "__main__":
    main()
