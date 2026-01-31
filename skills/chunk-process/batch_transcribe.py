#!/usr/bin/env python3
"""
Batch transcribe video chunks with proper global offset tracking.

This script:
1. Extracts audio from each chunk
2. Transcribes each chunk
3. Tracks global offsets for timestamp continuity
4. Merges into unified transcript with chunk boundaries marked
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse

# Add skills to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_duration(file_path: str) -> float:
    """Get duration of media file using ffprobe."""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json', file_path
    ], capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])

def extract_audio(chunk_path: Path, output_dir: Path) -> Path:
    """Extract audio from video chunk."""
    audio_path = output_dir / f"{chunk_path.stem}.wav"

    if audio_path.exists():
        print(f"  [skip] Audio exists: {audio_path.name}")
        return audio_path

    subprocess.run([
        'ffmpeg', '-y', '-i', str(chunk_path),
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        str(audio_path)
    ], capture_output=True)

    print(f"  [audio] Extracted: {audio_path.name}")
    return audio_path

def transcribe_chunk(audio_path: Path, fast_mode: bool = True) -> dict:
    """Transcribe audio using Qwen3-ASR."""
    import torch
    from qwen_asr import Qwen3ASRModel

    model = Qwen3ASRModel.from_pretrained(
        "Qwen/Qwen3-ASR-1.7B",
        dtype=torch.float32,
        device_map="cpu",
    )

    results = model.transcribe(
        audio=str(audio_path),
        language=None,  # Auto-detect
        return_time_stamps=False,  # Fast mode for initial transcription
    )

    result = results[0]
    return {
        "text": result.text.strip(),
        "language": result.language,
    }

def main():
    parser = argparse.ArgumentParser(description='Batch transcribe video chunks')
    parser.add_argument('chunks_dir', help='Directory containing video chunks')
    parser.add_argument('--output', '-o', default='transcript_index.json')
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    audio_dir = chunks_dir / 'audio'
    audio_dir.mkdir(exist_ok=True)

    # Find all chunks
    chunks = sorted(chunks_dir.glob('chunk_*.mp4'), key=lambda p: int(p.stem.split('_')[1]))

    if not chunks:
        print(f"No chunks found in {chunks_dir}")
        sys.exit(1)

    print(f"Found {len(chunks)} chunks")

    # Step 1: Extract all audio (fast with ffmpeg)
    print("\n=== Step 1: Extract Audio ===")
    chunk_info = []
    global_offset = 0.0

    for chunk_path in chunks:
        audio_path = extract_audio(chunk_path, audio_dir)
        duration = get_duration(str(chunk_path))

        chunk_info.append({
            "chunk_num": int(chunk_path.stem.split('_')[1]),
            "video_path": str(chunk_path),
            "audio_path": str(audio_path),
            "duration": duration,
            "global_offset": global_offset,
        })
        global_offset += duration

    print(f"\nTotal duration: {global_offset:.1f}s ({global_offset/60:.1f} min)")

    # Step 2: Transcribe each chunk
    print("\n=== Step 2: Transcribe Chunks ===")

    # Load model once
    import torch
    from qwen_asr import Qwen3ASRModel

    print("Loading Qwen3-ASR-1.7B...")
    model = Qwen3ASRModel.from_pretrained(
        "Qwen/Qwen3-ASR-1.7B",
        dtype=torch.float32,
        device_map="cpu",
    )

    results = []
    for info in chunk_info:
        chunk_num = info["chunk_num"]
        audio_path = info["audio_path"]

        # Check for cached transcript
        transcript_path = Path(audio_path).with_suffix('.json')
        if transcript_path.exists():
            with open(transcript_path) as f:
                cached = json.load(f)
            print(f"  [cached] chunk_{chunk_num:03d}: {len(cached['full_text'])} chars")
            results.append({
                **info,
                "text": cached["full_text"],
                "language": cached["language"],
            })
            continue

        print(f"  [transcribing] chunk_{chunk_num:03d}...", end=" ", flush=True)

        asr_results = model.transcribe(
            audio=audio_path,
            language=None,
            return_time_stamps=False,
        )

        text = asr_results[0].text.strip()
        language = asr_results[0].language

        # Cache result
        with open(transcript_path, "w") as f:
            json.dump({"full_text": text, "language": language, "model": "Qwen3-ASR-1.7B", "segments": []}, f, ensure_ascii=False, indent=2)

        print(f"{len(text)} chars ({language})")

        results.append({
            **info,
            "text": text,
            "language": language,
        })

    # Step 3: Build merged index
    print("\n=== Step 3: Build Index ===")

    full_text_parts = []
    for r in results:
        # Mark chunk boundary in text
        full_text_parts.append(f"\n[CHUNK {r['chunk_num']:03d} @ {r['global_offset']:.1f}s]\n{r['text']}")

    index = {
        "source_dir": str(chunks_dir),
        "total_chunks": len(chunks),
        "total_duration": global_offset,
        "language": results[0]["language"] if results else "unknown",
        "chunks": [
            {
                "chunk_num": r["chunk_num"],
                "global_offset": r["global_offset"],
                "duration": r["duration"],
                "char_count": len(r["text"]),
                "text": r["text"],
            }
            for r in results
        ],
        "full_text": "\n".join(full_text_parts),
    }

    output_path = chunks_dir / args.output
    with open(output_path, "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved: {output_path}")
    print(f"  - {len(chunks)} chunks")
    print(f"  - {len(index['full_text'])} characters total")
    print(f"  - {global_offset/60:.1f} minutes")

    # Show first/last chunk previews
    print("\n=== Preview ===")
    print(f"First chunk: {results[0]['text'][:200]}...")
    print(f"Last chunk: ...{results[-1]['text'][-200:]}")

if __name__ == "__main__":
    main()
