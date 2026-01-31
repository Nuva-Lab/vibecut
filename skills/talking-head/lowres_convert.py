#!/usr/bin/env python3
"""
Low-resolution video conversion for efficient Gemini analysis.

V3 Pipeline: Convert sentence-level clips to 480p before uploading to Gemini.
Reduces file size by ~85% (20MB → 3MB) while maintaining visual quality
sufficient for content analysis.

Size reduction comparison:
| Resolution | Typical 15s clip | Upload time |
|------------|------------------|-------------|
| 1080p      | ~20MB            | ~30s        |
| 720p       | ~10MB            | ~15s        |
| 480p       | ~3MB             | ~5s         |
| 360p       | ~1.5MB           | ~3s         |
"""

import json
import subprocess
import sys
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed


# Resolution presets
RESOLUTIONS = {
    "1080p": {"width": 1920, "height": 1080, "crf": 23},
    "720p": {"width": 1280, "height": 720, "crf": 25},
    "480p": {"width": 854, "height": 480, "crf": 28},  # Recommended for Gemini
    "360p": {"width": 640, "height": 360, "crf": 30},
}


def convert_clip_lowres(
    input_path: str,
    output_path: str,
    resolution: str = "480p",
    preset: str = "fast",
) -> dict:
    """
    Convert a single clip to low resolution.

    Args:
        input_path: Source clip path
        output_path: Output path
        resolution: Resolution preset (480p recommended)
        preset: FFmpeg preset (fast, medium, slow)

    Returns:
        Dict with conversion stats
    """
    res = RESOLUTIONS.get(resolution, RESOLUTIONS["480p"])
    width = res["width"]
    height = res["height"]
    crf = res["crf"]

    # Scale filter maintains aspect ratio
    scale_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"

    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', scale_filter,
        '-c:v', 'libx264',
        '-preset', preset,
        '-crf', str(crf),
        '-c:a', 'aac',
        '-b:a', '64k',  # Lower audio bitrate for analysis
        '-movflags', '+faststart',
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=300)

    output_file = Path(output_path)
    if output_file.exists():
        input_size = Path(input_path).stat().st_size
        output_size = output_file.stat().st_size
        reduction = (1 - output_size / input_size) * 100 if input_size > 0 else 0

        return {
            "success": True,
            "input_path": input_path,
            "output_path": output_path,
            "input_size_bytes": input_size,
            "output_size_bytes": output_size,
            "size_reduction_pct": reduction,
        }
    else:
        return {
            "success": False,
            "input_path": input_path,
            "output_path": output_path,
            "error": result.stderr.decode()[:200] if result.stderr else "Unknown error",
        }


def create_lowres_clips(
    clips_dir: str,
    output_dir: str,
    resolution: str = "480p",
    preset: str = "fast",
    parallel: int = 4,
) -> dict:
    """
    Convert all clips in a directory to low resolution.

    Args:
        clips_dir: Directory with sentence clips
        output_dir: Output directory for low-res clips
        resolution: Resolution preset (480p recommended for Gemini)
        preset: FFmpeg preset
        parallel: Number of parallel conversions

    Returns:
        Dict with conversion stats and file list
    """
    clips_dir = Path(clips_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all clip files
    clip_files = sorted(clips_dir.glob("clip_*.mp4"))

    if not clip_files:
        # Try loading from clip_index.json
        index_path = clips_dir / "clip_index.json"
        if index_path.exists():
            with open(index_path) as f:
                index = json.load(f)
            clip_files = [
                Path(c["path"]) for c in index.get("clips", [])
                if c.get("path") and Path(c["path"]).exists()
            ]

    if not clip_files:
        print(f"Error: No clips found in {clips_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"=== Low-Resolution Conversion ===")
    print(f"Input: {clips_dir}")
    print(f"Output: {output_dir}")
    print(f"Resolution: {resolution}")
    print(f"Clips to convert: {len(clip_files)}")

    res = RESOLUTIONS.get(resolution, RESOLUTIONS["480p"])
    print(f"Target: {res['width']}x{res['height']}, CRF {res['crf']}")

    results = []
    total_input_size = 0
    total_output_size = 0

    if parallel > 1:
        print(f"\nConverting {len(clip_files)} clips in parallel (workers: {parallel})...")
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {}
            for clip_path in clip_files:
                output_path = output_dir / clip_path.name
                future = executor.submit(
                    convert_clip_lowres,
                    str(clip_path),
                    str(output_path),
                    resolution,
                    preset,
                )
                futures[future] = clip_path

            for i, future in enumerate(as_completed(futures), 1):
                clip_path = futures[future]
                result = future.result()
                results.append(result)

                if result["success"]:
                    total_input_size += result["input_size_bytes"]
                    total_output_size += result["output_size_bytes"]
                    print(f"  [{i}/{len(clip_files)}] ✓ {clip_path.name} "
                          f"({result['size_reduction_pct']:.0f}% smaller)")
                else:
                    print(f"  [{i}/{len(clip_files)}] ✗ {clip_path.name} FAILED")
    else:
        print(f"\nConverting {len(clip_files)} clips sequentially...")
        for i, clip_path in enumerate(clip_files, 1):
            output_path = output_dir / clip_path.name
            result = convert_clip_lowres(
                str(clip_path),
                str(output_path),
                resolution,
                preset,
            )
            results.append(result)

            if result["success"]:
                total_input_size += result["input_size_bytes"]
                total_output_size += result["output_size_bytes"]
                print(f"  [{i}/{len(clip_files)}] ✓ {clip_path.name} "
                      f"({result['size_reduction_pct']:.0f}% smaller)")
            else:
                print(f"  [{i}/{len(clip_files)}] ✗ {clip_path.name} FAILED")

    # Calculate stats
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    total_reduction = (1 - total_output_size / total_input_size) * 100 if total_input_size > 0 else 0

    # Save conversion index
    output_data = {
        "source_dir": str(clips_dir),
        "output_dir": str(output_dir),
        "resolution": resolution,
        "num_clips": len(successful),
        "num_failed": len(failed),
        "total_input_size_mb": total_input_size / (1024 * 1024),
        "total_output_size_mb": total_output_size / (1024 * 1024),
        "total_size_reduction_pct": total_reduction,
        "clips": [
            {
                "clip_id": i + 1,
                "path": str(output_dir / Path(r["input_path"]).name),
                "original_path": r["input_path"],
                "size_bytes": r["output_size_bytes"],
            }
            for i, r in enumerate(results) if r["success"]
        ],
    }

    index_path = output_dir / "lowres_index.json"
    with open(index_path, "w") as f:
        json.dump(output_data, f, indent=2)

    # Print summary
    print(f"\n=== Conversion Complete ===")
    print(f"Successful: {len(successful)}/{len(results)}")
    print(f"Total size: {total_input_size / (1024*1024):.1f}MB → "
          f"{total_output_size / (1024*1024):.1f}MB "
          f"({total_reduction:.0f}% reduction)")

    if failed:
        print(f"\nFailed conversions:")
        for r in failed:
            print(f"  - {Path(r['input_path']).name}: {r.get('error', 'Unknown')[:50]}")

    print(f"\n✓ Saved index to {index_path}")

    return output_data


def main():
    parser = argparse.ArgumentParser(
        description='Convert clips to low resolution for Gemini analysis'
    )
    parser.add_argument('clips_dir', help='Directory with sentence clips')
    parser.add_argument('--output', '-o', default='lowres_clips',
                        help='Output directory')
    parser.add_argument('--resolution', '-r', default='480p',
                        choices=['1080p', '720p', '480p', '360p'],
                        help='Target resolution (default: 480p)')
    parser.add_argument('--preset', '-p', default='fast',
                        choices=['ultrafast', 'fast', 'medium', 'slow'],
                        help='FFmpeg preset (default: fast)')
    parser.add_argument('--parallel', '-j', type=int, default=4,
                        help='Parallel conversions (default: 4)')
    args = parser.parse_args()

    # Validate input
    if not Path(args.clips_dir).exists():
        print(f"Error: Clips directory not found: {args.clips_dir}", file=sys.stderr)
        sys.exit(1)

    result = create_lowres_clips(
        args.clips_dir,
        args.output,
        resolution=args.resolution,
        preset=args.preset,
        parallel=args.parallel,
    )

    print(f"\nNext step:")
    print(f"  python batch_analyze.py {args.output}/ -o clip_scores.json")


if __name__ == "__main__":
    main()
