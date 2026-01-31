#!/usr/bin/env python3
"""
Render talking-head video with rolling captions and section titles.

Takes:
- Trimmed video from precision_trim.py
- Captions from generate_captions.py
- Optional section markers

Outputs:
- Horizontal (16:9) video with captions
- Vertical (9:16) video with captions (TikTok/Reels)
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
import argparse


def get_duration(path: str) -> float:
    """Get media duration in seconds."""
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def render_talking_head(
    video_path: str,
    captions_dir: str,
    output_dir: str,
    sections_path: str = None,
    speaker_center_x: float = 0.5,
    title: str = None,
    speaker_name: str = None,
    speaker_title: str = None,
    fps: int = 30,
) -> dict:
    """
    Render talking-head video with captions using Remotion.

    Args:
        video_path: Trimmed video file
        captions_dir: Directory with captions_horizontal.json and captions_vertical.json
        output_dir: Output directory
        sections_path: Optional sections JSON for pop-up titles
        speaker_center_x: X position (0-1) to center crop for vertical
        title: Optional title card text
        speaker_name: Speaker name for label
        speaker_title: Speaker title/role for label
        fps: Frame rate (default 30)

    Returns:
        Dict with output paths
    """
    video_path = Path(video_path)
    captions_dir = Path(captions_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load horizontal captions
    captions_h_path = captions_dir / "captions_horizontal.json"
    if captions_h_path.exists():
        with open(captions_h_path) as f:
            captions_h_data = json.load(f)
        captions_horizontal = captions_h_data.get("captions", [])
    else:
        # Fallback to single captions.json
        with open(captions_dir / "captions.json") as f:
            captions_h_data = json.load(f)
        captions_horizontal = captions_h_data.get("captions", [])

    # Load vertical captions
    captions_v_path = captions_dir / "captions_vertical.json"
    if captions_v_path.exists():
        with open(captions_v_path) as f:
            captions_v_data = json.load(f)
        captions_vertical = captions_v_data.get("captions", [])
    else:
        captions_vertical = captions_horizontal  # Use same if no vertical file

    # Load sections if provided
    sections = []
    if sections_path and Path(sections_path).exists():
        with open(sections_path) as f:
            sections_data = json.load(f)
        sections = sections_data.get("sections", [])

    # Get video duration
    duration = get_duration(str(video_path))

    print(f"=== Rendering Talking-Head Video ===")
    print(f"Video: {video_path}")
    print(f"Duration: {duration:.1f}s")
    print(f"Horizontal captions: {len(captions_horizontal)} phrases")
    print(f"Vertical captions: {len(captions_vertical)} phrases")
    print(f"Sections: {len(sections)} markers")
    if speaker_name:
        print(f"Speaker: {speaker_name}" + (f" ({speaker_title})" if speaker_title else ""))

    # Setup Remotion
    remotion_dir = Path(__file__).parent.parent / "remotion-render"
    public_dir = remotion_dir / "public"
    public_dir.mkdir(exist_ok=True)

    # Copy video to Remotion public/
    video_dest = public_dir / video_path.name
    if video_dest.exists() or video_dest.is_symlink():
        video_dest.unlink()
    shutil.copy2(video_path, video_dest)
    print(f"\nCopied video to Remotion public/")

    # Prepare title card
    title_card = None
    if title:
        title_card = {
            "title": title,
            "subtitle": "",
            "durationMs": 3000,
        }

    # Prepare speaker label - positioned at bottom center
    speakers = []
    if speaker_name:
        speakers.append({
            "name": speaker_name,
            "title": speaker_title or "",
            "box2d": [800, 500, 0, 0],  # y=800 (near bottom), x=500 (center)
            "showFromMs": 0,
            "showUntilMs": 8000,  # Show for first 8 seconds
        })

    props_path = remotion_dir / "props.json"

    # Calculate frames
    duration_frames = int(duration * fps)
    title_frames = int(3 * fps) if title_card else 0
    total_frames = duration_frames + title_frames

    # Update Root.tsx with correct duration
    root_path = remotion_dir / "src" / "Root.tsx"
    if root_path.exists():
        root_content = root_path.read_text()
        # Update TalkingHead duration
        root_content = re.sub(
            r'(id="TalkingHead"[^>]*durationInFrames=\{)\d+(\})',
            f'\\g<1>{total_frames}\\2',
            root_content
        )
        # Update TalkingHeadVertical duration
        root_content = re.sub(
            r'(id="TalkingHeadVertical"[^>]*durationInFrames=\{)\d+(\})',
            f'\\g<1>{total_frames}\\2',
            root_content
        )
        root_path.write_text(root_content)

    outputs = {}

    # Render horizontal (16:9)
    print(f"\n[1/2] Rendering horizontal (16:9)...")
    output_horizontal = output_dir / f"{video_path.stem}_captioned.mp4"

    # Props for horizontal
    props_horizontal = {
        "videoSrc": video_path.name,
        "captions": captions_horizontal,
        "sections": sections,
        "speakers": speakers,
        "titleCard": title_card,
        "cropToVertical": False,
        "speakerCenterX": speaker_center_x,
        "audioVolume": 1.0,
    }
    with open(props_path, "w") as f:
        json.dump(props_horizontal, f, ensure_ascii=False, indent=2)

    result = subprocess.run([
        "npx", "remotion", "render",
        "TalkingHead",
        str(output_horizontal.resolve()),
        f"--props={props_path.resolve()}",
        "--log=error"
    ], cwd=remotion_dir)

    if result.returncode == 0 and output_horizontal.exists():
        print(f"✓ Created: {output_horizontal}")
        outputs["horizontal"] = str(output_horizontal)
    else:
        print(f"✗ Failed to render horizontal")

    # Render vertical (9:16)
    print(f"\n[2/2] Rendering vertical (9:16)...")
    output_vertical = output_dir / f"{video_path.stem}_vertical.mp4"

    # Props for vertical - different captions, cropped view
    props_vertical = {
        "videoSrc": video_path.name,
        "captions": captions_vertical,
        "sections": sections,
        "speakers": speakers,
        "titleCard": title_card,
        "cropToVertical": True,
        "speakerCenterX": speaker_center_x,
        "audioVolume": 1.0,
    }
    with open(props_path, "w") as f:
        json.dump(props_vertical, f, ensure_ascii=False, indent=2)

    result = subprocess.run([
        "npx", "remotion", "render",
        "TalkingHeadVertical",
        str(output_vertical.resolve()),
        f"--props={props_path.resolve()}",
        "--log=error"
    ], cwd=remotion_dir)

    if result.returncode == 0 and output_vertical.exists():
        print(f"✓ Created: {output_vertical}")
        outputs["vertical"] = str(output_vertical)
    else:
        print(f"✗ Failed to render vertical")

    # Cleanup
    if video_dest.exists():
        video_dest.unlink()

    print(f"\n=== Rendering Complete ===")
    return outputs


def main():
    parser = argparse.ArgumentParser(
        description='Render talking-head video with captions using Remotion'
    )
    parser.add_argument('video', help='Trimmed video file')
    parser.add_argument('captions_dir', help='Directory with captions_horizontal.json and captions_vertical.json')
    parser.add_argument('--output', '-o', default='output',
                        help='Output directory')
    parser.add_argument('--sections', help='Sections JSON for pop-up titles')
    parser.add_argument('--title', help='Optional title card text')
    parser.add_argument('--speaker', help='Speaker name')
    parser.add_argument('--speaker-title', help='Speaker title/role')
    parser.add_argument('--speaker-center', type=float, default=0.5,
                        help='Speaker X position (0-1) for vertical crop')
    parser.add_argument('--fps', type=int, default=30,
                        help='Frame rate')

    args = parser.parse_args()

    render_talking_head(
        args.video,
        args.captions_dir,
        args.output,
        sections_path=args.sections,
        speaker_center_x=args.speaker_center,
        title=args.title,
        speaker_name=args.speaker,
        speaker_title=args.speaker_title,
        fps=args.fps,
    )


if __name__ == "__main__":
    main()
