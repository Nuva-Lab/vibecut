#!/usr/bin/env python3
"""
Smart video chunking with content-aware boundaries.

Strategy:
1. Analyze audio for energy dips AND pause detection
2. Target ~3 min chunks (2.5-3.5 min flexible)
3. Split at natural sentence boundaries (pauses > 300ms)
4. Never cut mid-sentence

Uses FFmpeg astats for energy detection and silence detection.
"""

import json
import subprocess
import sys
from pathlib import Path
import argparse
import re


def detect_silence_gaps(video_path: str, threshold_db: float = -35.0, min_duration: float = 0.3) -> list:
    """
    Detect silence gaps in audio using FFmpeg silencedetect.

    Returns list of (timestamp, duration, confidence) tuples.
    Longer silences = higher confidence as sentence boundary.
    """
    cmd = [
        'ffmpeg', '-i', video_path,
        '-af', f'silencedetect=noise={threshold_db}dB:d={min_duration}',
        '-f', 'null', '-'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    gaps = []
    silence_start = None

    for line in result.stderr.split('\n'):
        if 'silence_start:' in line:
            match = re.search(r'silence_start:\s*([\d.]+)', line)
            if match:
                silence_start = float(match.group(1))
        elif 'silence_end:' in line and silence_start is not None:
            match = re.search(r'silence_end:\s*([\d.]+)', line)
            if match:
                silence_end = float(match.group(1))
                duration = silence_end - silence_start
                # Midpoint of silence is the best cut point
                midpoint = silence_start + duration / 2
                # Longer silence = higher confidence
                confidence = min(1.0, duration / 1.0)
                gaps.append((midpoint, duration, confidence))
                silence_start = None

    return gaps


def analyze_audio_energy(video_path: str, window_sec: float = 0.3) -> list:
    """
    Analyze audio energy over time using FFmpeg astats.

    Returns list of (timestamp, rms_level) tuples.
    """
    # Use FFmpeg to compute RMS levels over short windows
    cmd = [
        'ffmpeg', '-i', video_path,
        '-af', f'astats=metadata=1:reset={window_sec},ametadata=print:key=lavfi.astats.Overall.RMS_level',
        '-f', 'null', '-'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    # Parse RMS levels from stderr
    energy_data = []
    current_time = 0.0

    for line in result.stderr.split('\n'):
        if 'RMS_level' in line:
            try:
                # Format: lavfi.astats.Overall.RMS_level=-XX.XX
                rms = float(line.split('=')[-1])
                energy_data.append((current_time, rms))
                current_time += window_sec
            except (ValueError, IndexError):
                continue

    return energy_data

def find_split_points(
    energy_data: list,
    total_duration: float,
    target_chunk_sec: float = 180,  # 3 min target
    min_chunk_sec: float = 150,     # 2.5 min minimum
    max_chunk_sec: float = 210,     # 3.5 min maximum
    search_window_sec: float = 30,  # Look ±30s around target
    silence_gaps: list = None,      # From detect_silence_gaps()
) -> list:
    """
    Find optimal split points combining silence gaps AND energy dips.

    Priority:
    1. High-confidence silence gap (natural sentence boundary)
    2. Any silence gap in search window
    3. Lowest energy point (fallback)

    Returns list of timestamps where chunks should start.
    """
    if not energy_data and not silence_gaps:
        # Fallback to fixed intervals
        return list(range(0, int(total_duration), int(target_chunk_sec)))

    split_points = [0.0]  # Always start at 0
    current_pos = 0.0

    while current_pos + min_chunk_sec < total_duration:
        target_pos = current_pos + target_chunk_sec

        # Search window around target
        search_start = max(current_pos + min_chunk_sec, target_pos - search_window_sec)
        search_end = min(total_duration, target_pos + search_window_sec, current_pos + max_chunk_sec)

        best_point = None

        # PRIORITY 1: Look for silence gaps (best for not cutting sentences)
        if silence_gaps:
            gap_candidates = [
                (t, dur, conf) for t, dur, conf in silence_gaps
                if search_start <= t <= search_end
            ]

            if gap_candidates:
                # Pick highest confidence (longest silence) closest to target
                # Score = confidence - distance_penalty
                scored = [
                    (t, conf - abs(t - target_pos) / search_window_sec * 0.3)
                    for t, dur, conf in gap_candidates
                ]
                best_point = max(scored, key=lambda x: x[1])[0]

        # PRIORITY 2: Fall back to energy dips
        if best_point is None and energy_data:
            energy_candidates = [
                (t, e) for t, e in energy_data
                if search_start <= t <= search_end
            ]

            if energy_candidates:
                best_point = min(energy_candidates, key=lambda x: x[1])[0]

        # PRIORITY 3: Last resort - use target position
        if best_point is None:
            best_point = target_pos

        split_points.append(best_point)
        current_pos = best_point

    return split_points

def split_video_at_points(
    video_path: str,
    split_points: list,
    output_dir: Path,
    total_duration: float
) -> list:
    """
    Split video at specified timestamps using FFmpeg segment copy.

    Returns list of chunk info dicts.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = []
    for i, start in enumerate(split_points):
        end = split_points[i + 1] if i + 1 < len(split_points) else total_duration
        duration = end - start

        output_path = output_dir / f"chunk_{i:03d}.mp4"

        # Use stream copy for speed (no re-encoding)
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', video_path,
            '-t', str(duration),
            '-map', '0:v:0', '-map', '0:a:0',  # Only main video and audio
            '-c', 'copy',
            '-avoid_negative_ts', '1',
            str(output_path)
        ]

        subprocess.run(cmd, capture_output=True, timeout=120)

        if output_path.exists():
            chunks.append({
                "chunk_num": i,
                "path": str(output_path),
                "start": start,
                "end": end,
                "duration": duration,
            })
            print(f"  chunk_{i:03d}: {start:.1f}s - {end:.1f}s ({duration:.1f}s)")

    return chunks

def get_duration(video_path: str) -> float:
    """Get video duration using ffprobe."""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json', video_path
    ], capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])

def main():
    parser = argparse.ArgumentParser(description='Smart content-aware video chunking')
    parser.add_argument('video', help='Input video file')
    parser.add_argument('--output-dir', '-o', default='chunks', help='Output directory')
    parser.add_argument('--target', '-t', type=float, default=180, help='Target chunk duration (seconds)')
    parser.add_argument('--min', type=float, default=150, help='Minimum chunk duration')
    parser.add_argument('--max', type=float, default=210, help='Maximum chunk duration')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze, don\'t split')
    parser.add_argument('--silence-threshold', type=float, default=-35.0,
                        help='Silence detection threshold in dB (default: -35)')
    parser.add_argument('--min-silence', type=float, default=0.3,
                        help='Minimum silence duration to detect (default: 0.3s)')
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: File not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)

    print(f"=== Smart Video Chunking ===")
    print(f"Input: {video_path}")
    print(f"Target chunk: {args.target/60:.1f} min (range: {args.min/60:.1f}-{args.max/60:.1f} min)")

    # Get duration
    total_duration = get_duration(str(video_path))
    print(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")

    # Detect silence gaps (sentence boundaries)
    print(f"\nDetecting silence gaps (threshold: {args.silence_threshold}dB, min: {args.min_silence}s)...")
    silence_gaps = detect_silence_gaps(
        str(video_path),
        threshold_db=args.silence_threshold,
        min_duration=args.min_silence
    )
    print(f"  Found {len(silence_gaps)} silence gaps")

    # Analyze audio energy (fallback)
    print(f"\nAnalyzing audio energy...")
    energy_data = analyze_audio_energy(str(video_path))
    print(f"  Collected {len(energy_data)} energy samples")

    # Find optimal split points
    print(f"\nFinding optimal split points...")
    split_points = find_split_points(
        energy_data,
        total_duration,
        target_chunk_sec=args.target,
        min_chunk_sec=args.min,
        max_chunk_sec=args.max,
        silence_gaps=silence_gaps,
    )

    num_chunks = len(split_points)
    print(f"  Found {num_chunks} chunks:")
    for i, t in enumerate(split_points):
        end = split_points[i+1] if i+1 < len(split_points) else total_duration
        print(f"    {i}: {t:.1f}s - {end:.1f}s ({(end-t):.1f}s)")

    if args.analyze_only:
        print("\n[Analyze only mode - not splitting]")
        return

    # Split video
    print(f"\nSplitting video...")
    chunks = split_video_at_points(str(video_path), split_points, output_dir, total_duration)

    # Save chunk index
    index = {
        "source": str(video_path),
        "total_duration": total_duration,
        "num_chunks": len(chunks),
        "target_duration": args.target,
        "min_duration": args.min,
        "max_duration": args.max,
        "silence_threshold_db": args.silence_threshold,
        "min_silence_sec": args.min_silence,
        "silence_gaps_found": len(silence_gaps),
        "energy_samples": len(energy_data),
        "chunks": chunks,
    }

    index_path = output_dir / "chunk_index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"\n✓ Created {len(chunks)} chunks in {output_dir}/")
    print(f"✓ Saved index to {index_path}")

if __name__ == "__main__":
    main()
