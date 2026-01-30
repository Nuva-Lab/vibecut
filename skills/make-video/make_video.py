#!/usr/bin/env python3
"""
Single-script video production.
Usage: python make_video.py <project_folder>

Supports two caption modes:
- ASR-based: Uses mlx-audio for precise timestamps (default when voiceover exists)
- Character-based: Estimates timing from script length (fallback)
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Add skills to path for imports
SKILLS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILLS_DIR / "transcribe-audio"))
sys.path.insert(0, str(SKILLS_DIR / "align-captions"))


def split_into_phrases(text: str) -> list[str]:
    """Split Chinese/English text into natural phrases."""
    phrases = re.split(r'([。！？.!?])', text)
    combined = []
    for i, part in enumerate(phrases):
        if i % 2 == 0:
            combined.append(part)
        else:
            if combined:
                combined[-1] += part
    
    result = []
    for phrase in combined:
        if not phrase.strip():
            continue
        if len(phrase) > 20:
            sub_phrases = re.split(r'([，,])', phrase)
            temp = []
            for j, sub in enumerate(sub_phrases):
                if j % 2 == 0:
                    temp.append(sub)
                else:
                    if temp:
                        temp[-1] += sub
            result.extend([p.strip() for p in temp if p.strip()])
        else:
            result.append(phrase.strip())
    return result


def generate_captions(script: str, duration_sec: float) -> list[dict]:
    """Generate timed captions from script (character-based fallback)."""
    phrases = split_into_phrases(script)
    if not phrases:
        return []

    total_chars = sum(len(p) for p in phrases)
    actual_rate = total_chars / duration_sec

    captions = []
    current_ms = 0

    for phrase in phrases:
        char_count = len(phrase)
        duration_ms = int((char_count / actual_rate) * 1000)
        duration_ms = max(500, duration_ms)
        end_ms = min(current_ms + duration_ms, int(duration_sec * 1000))

        captions.append({
            "text": phrase,
            "startMs": current_ms,
            "endMs": end_ms,
            "timestampMs": current_ms,
            "confidence": None
        })
        current_ms = end_ms

    return captions


def generate_captions_asr(audio_path: str, script: str = None) -> dict:
    """
    Generate captions using Qwen3-ForcedAligner for ~30ms precision.

    Returns dict with:
    - segments: phrase-level captions
    - word_segments: word-level timestamps for karaoke highlighting
    """
    try:
        if script:
            # Use align-captions: ForcedAligner for ~30ms precision
            from align import align_captions
            print("Using Qwen3-ForcedAligner for precise timing...")
            result = align_captions(audio_path, script, language="Chinese", device="cpu")
        else:
            # Direct ASR transcription with timestamps
            from transcribe import transcribe_audio
            print("Using Qwen3-ASR for transcription...")
            result = transcribe_audio(audio_path, return_timestamps=True, device="cpu")

        segments = result.get("segments", [])
        word_segments = result.get("word_segments", [])

        # Ensure segments have required fields
        for cap in segments:
            if "timestampMs" not in cap:
                cap["timestampMs"] = cap.get("startMs", 0)
            if "confidence" not in cap:
                cap["confidence"] = None

        return {
            "segments": segments,
            "word_segments": word_segments,
        }
    except Exception as e:
        print(f"Warning: ASR captioning failed: {e}")
        import traceback
        traceback.print_exc()
        print("Falling back to character-based timing...")
        return None


def get_duration(file_path: str) -> float:
    """Get media duration using ffprobe."""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def make_video(project_dir: str):
    """Main video production pipeline."""
    project_dir = Path(project_dir)
    config_path = project_dir / "project.json"
    
    if not config_path.exists():
        print(f"Error: project.json not found in {project_dir}")
        sys.exit(1)
    
    with open(config_path) as f:
        config = json.load(f)
    
    print(f"\n{'='*60}")
    print(f"Making video: {config.get('name', project_dir.name)}")
    print(f"{'='*60}\n")
    
    # Paths - resolve source video (can be local, absolute, or in raw_assets/)
    source_video_config = config.get("source_video", "source_video.mp4")
    source_video = project_dir / source_video_config

    # Check if it's an absolute path or in raw_assets/
    if not source_video.exists():
        source_video = Path(source_video_config)  # Try as absolute
    if not source_video.exists():
        raw_assets = Path(__file__).parent.parent.parent / "raw_assets"
        source_video = raw_assets / source_video_config

    voiceover = project_dir / config.get("voiceover", "voiceover.wav")
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)

    if not source_video.exists():
        print(f"Error: Source video not found: {source_video_config}")
        print(f"  Checked: {project_dir / source_video_config}")
        print(f"  Checked: raw_assets/{source_video_config}")
        sys.exit(1)

    source_video = source_video.resolve()
    
    # Get duration from voiceover or video
    if voiceover.exists():
        duration = get_duration(str(voiceover))
        print(f"Voiceover duration: {duration:.2f}s")
    else:
        duration = get_duration(str(source_video))
        print(f"Video duration: {duration:.2f}s")
    
    # Generate captions
    script = config.get("script", "")
    caption_mode = config.get("caption_mode", "auto")  # auto, asr, character
    word_segments = []  # Word-level timestamps for karaoke

    if script:
        caption_result = None

        # Try ASR-based captioning if voiceover exists and mode allows
        if caption_mode in ("auto", "asr") and voiceover.exists():
            caption_result = generate_captions_asr(str(voiceover), script)

        # Handle result
        if caption_result and isinstance(caption_result, dict):
            captions = caption_result.get("segments", [])
            word_segments = caption_result.get("word_segments", [])
        elif caption_result:
            # Legacy format (list)
            captions = caption_result
        else:
            # Fallback to character-based timing
            print("Using character-based caption timing...")
            captions = generate_captions(script, duration)

        print(f"Generated {len(captions)} caption segments, {len(word_segments)} word segments")

        captions_path = project_dir / "captions.json"
        with open(captions_path, "w") as f:
            json.dump({"segments": captions, "word_segments": word_segments}, f, ensure_ascii=False, indent=2)
    else:
        captions = []
    
    # Prepare Remotion (skill located in skills/remotion-render)
    remotion_dir = (Path(__file__).parent.parent / "remotion-render").resolve()
    public_dir = remotion_dir / "public"
    public_dir.mkdir(exist_ok=True)

    # Copy video to public (Remotion bundler doesn't follow symlinks)
    video_dest = public_dir / source_video.name
    if video_dest.exists() or video_dest.is_symlink():
        video_dest.unlink()
    shutil.copy2(source_video, video_dest)
    print(f"Copied video to Remotion public/")
    
    # Prepare props
    title_config = config.get("titleCard", {})
    if not title_config and config.get("title"):
        # Auto-generate title card from title field
        title_config = {
            "title": config.get("title"),
            "subtitle": config.get("subtitle", ""),
            "durationMs": 3000
        }

    # Audio config
    audio_config = config.get("audio", {})
    original_audio_volume = audio_config.get("original_volume", 0.3)

    # Context badge - support both field names
    context_badge = config.get("context_badge") or config.get("context", {"location": "", "event": ""})

    props = {
        "videoSrc": source_video.name,
        "captions": captions,
        "speakers": config.get("speakers", []),
        "contextBadge": context_badge,
        "titleCard": title_config if title_config else None,
        "originalAudioVolume": original_audio_volume
    }
    
    props_path = remotion_dir / "props.json"
    with open(props_path, "w") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)
    
    # Calculate frames
    output_config = config.get("output", {})
    fps = output_config.get("fps", 30)
    duration_frames = int(duration * fps)
    
    # Update Root.tsx with correct duration
    root_path = remotion_dir / "src" / "Root.tsx"
    if root_path.exists():
        root_content = root_path.read_text()
        # Update duration
        root_content = re.sub(
            r'durationInFrames={[^}]+}',
            f'durationInFrames={{{duration_frames}}}',
            root_content
        )
        root_path.write_text(root_content)
    
    # Render - use absolute paths to avoid cwd issues
    output_path = (output_dir / "final.mp4").resolve()
    props_path = props_path.resolve()
    print(f"\nRendering with Remotion...")
    print(f"Duration: {duration_frames} frames @ {fps}fps")

    result = subprocess.run([
        "npx", "remotion", "render",
        "VideoClip",
        str(output_path),
        f"--props={props_path}",
        "--log=error"
    ], cwd=remotion_dir)
    
    # Cleanup copied video
    if video_dest.exists():
        video_dest.unlink()

    if result.returncode != 0:
        print("Render failed!")
        sys.exit(1)

    # Mix voiceover with Remotion output (which already has original audio)
    voiceover_volume = audio_config.get("voiceover_volume", 1.0)

    if voiceover.exists():
        print("\nMixing voiceover with rendered video...")
        final_with_audio = output_dir / "final_with_voiceover.mp4"

        # Remotion output already has original audio at configured volume
        # Mix voiceover on top, keeping original audio audible
        # Equal weights so original speaker audio can be heard alongside voiceover
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(output_path),
            "-i", str(voiceover),
            "-filter_complex",
            f"[1:a]aresample=48000,volume={voiceover_volume}[vo]; "
            "[0:a][vo]amix=inputs=2:duration=shortest:weights='1 1'[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            str(final_with_audio)
        ], capture_output=True)

        # Replace output
        shutil.move(final_with_audio, output_path)
    else:
        # No voiceover - Remotion output already has original audio
        print("No voiceover found, using original audio from Remotion")
    
    print(f"\n{'='*60}")
    print(f"Done! Output: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_video.py <project_folder>")
        print("Example: python make_video.py video_projects/space_investing/")
        sys.exit(1)
    
    make_video(sys.argv[1])
