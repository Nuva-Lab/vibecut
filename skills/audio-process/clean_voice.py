#!/usr/bin/env python3
"""
Clean voice audio - denoise, normalize, and enhance for voice cloning.
"""
import subprocess
import sys
from pathlib import Path


def clean_voice(
    input_path: str,
    output_path: str = None,
    noise_reduction: float = 0.21,
    highpass: int = 80,
    lowpass: int = 8000,
) -> str:
    """
    Clean voice audio for voice cloning.

    Pipeline:
    1. High-pass filter (remove low rumble)
    2. Non-local means denoiser (remove background noise)
    3. FFT denoiser (additional noise reduction)
    4. Low-pass filter (remove high frequency hiss)
    5. Normalize volume

    Args:
        input_path: Path to input audio
        output_path: Path for output (default: input_clean.wav)
        noise_reduction: Noise reduction strength (0.0-1.0, default 0.21)
        highpass: High-pass filter frequency (default 80Hz)
        lowpass: Low-pass filter frequency (default 8000Hz)

    Returns:
        Path to cleaned audio
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Cleaning: {input_path.name}")
    print(f"Noise reduction: {noise_reduction}")

    # Build filter chain
    filters = [
        f"highpass=f={highpass}",           # Remove low rumble
        f"anlmdn=s={noise_reduction}",      # Non-local means denoiser
        "afftdn=nf=-20",                    # FFT denoiser
        f"lowpass=f={lowpass}",             # Remove high hiss
        "loudnorm=I=-16:TP=-1.5:LRA=11",    # Normalize loudness
    ]

    filter_str = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-af", filter_str,
        "-ar", "44100",  # Ensure consistent sample rate
        "-ac", "1",      # Mono
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}")
        raise RuntimeError("Audio cleaning failed")

    print(f"Cleaned audio: {output_path}")
    return str(output_path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_voice.py <input.wav> [output.wav] [--nr 0.21]")
        print("")
        print("Options:")
        print("  --nr N    Noise reduction strength (0.0-1.0, default 0.21)")
        print("")
        print("Example:")
        print("  python clean_voice.py voice.wav voice_clean.wav")
        print("  python clean_voice.py voice.wav --nr 0.3  # stronger noise reduction")
        sys.exit(1)

    input_path = sys.argv[1]

    # Parse output path
    output_path = None
    for i, arg in enumerate(sys.argv[2:], 2):
        if not arg.startswith("--") and arg.endswith((".wav", ".mp3")):
            output_path = arg
            break

    # Parse noise reduction
    noise_reduction = 0.21
    if "--nr" in sys.argv:
        idx = sys.argv.index("--nr")
        if idx + 1 < len(sys.argv):
            noise_reduction = float(sys.argv[idx + 1])

    clean_voice(input_path, output_path, noise_reduction)


if __name__ == "__main__":
    main()
