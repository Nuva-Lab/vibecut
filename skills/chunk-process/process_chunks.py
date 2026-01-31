#!/usr/bin/env python3
"""
Process video chunks in parallel for transcription.

This skill:
1. Extracts audio from each chunk
2. Transcribes in parallel (up to N workers)
3. Merges results with correct global timestamps
4. Creates a unified transcript index
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse

def get_chunk_info(chunk_path: Path) -> dict:
    """Get duration and offset info for a chunk."""
    result = subprocess.run([
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json', str(chunk_path)
    ], capture_output=True, text=True)

    data = json.loads(result.stdout)
    duration = float(data['format']['duration'])

    # Extract chunk number from filename (chunk_000.mp4 -> 0)
    chunk_num = int(chunk_path.stem.split('_')[1])

    return {
        'path': str(chunk_path),
        'chunk_num': chunk_num,
        'duration': duration,
    }

def extract_audio(chunk_path: Path, output_dir: Path) -> Path:
    """Extract audio from video chunk."""
    audio_path = output_dir / f"{chunk_path.stem}.wav"

    if audio_path.exists():
        print(f"  Audio already exists: {audio_path.name}")
        return audio_path

    subprocess.run([
        'ffmpeg', '-y', '-i', str(chunk_path),
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        str(audio_path)
    ], capture_output=True)

    return audio_path

def transcribe_chunk(audio_path: Path, chunk_info: dict, global_offset: float) -> dict:
    """Transcribe a single audio chunk and adjust timestamps."""
    print(f"  Transcribing {audio_path.name} (offset: {global_offset:.1f}s)...")

    try:
        from qwen_asr import transcribe

        result = transcribe(
            str(audio_path),
            model="Qwen/Qwen3-ASR-1.7B",
            return_timestamps=True,
            device="cpu"
        )

        # Adjust timestamps to global time
        segments = []
        for seg in result.get('segments', []):
            segments.append({
                'start': seg['start'] + global_offset,
                'end': seg['end'] + global_offset,
                'text': seg['text'],
                'chunk': chunk_info['chunk_num']
            })

        words = []
        for word in result.get('words', []):
            words.append({
                'start': word['start'] + global_offset,
                'end': word['end'] + global_offset,
                'text': word['text'],
                'chunk': chunk_info['chunk_num']
            })

        return {
            'chunk_num': chunk_info['chunk_num'],
            'global_offset': global_offset,
            'duration': chunk_info['duration'],
            'text': result.get('text', ''),
            'segments': segments,
            'words': words,
            'success': True
        }

    except Exception as e:
        print(f"  ERROR transcribing {audio_path.name}: {e}")
        return {
            'chunk_num': chunk_info['chunk_num'],
            'global_offset': global_offset,
            'duration': chunk_info['duration'],
            'error': str(e),
            'success': False
        }

def process_single_chunk(args):
    """Worker function for parallel processing."""
    chunk_path, output_dir, global_offset = args
    chunk_info = get_chunk_info(Path(chunk_path))

    # Extract audio
    audio_path = extract_audio(Path(chunk_path), Path(output_dir))

    # Transcribe
    result = transcribe_chunk(audio_path, chunk_info, global_offset)

    return result

def main():
    parser = argparse.ArgumentParser(description='Process video chunks for transcription')
    parser.add_argument('chunks_dir', help='Directory containing video chunks')
    parser.add_argument('--output', '-o', default='transcript_index.json', help='Output index file')
    parser.add_argument('--workers', '-w', type=int, default=2, help='Number of parallel workers')
    parser.add_argument('--sequential', '-s', action='store_true', help='Process sequentially (for debugging)')
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    output_dir = chunks_dir / 'audio'
    output_dir.mkdir(exist_ok=True)

    # Find all chunks and sort by number
    chunks = sorted(chunks_dir.glob('chunk_*.mp4'), key=lambda p: int(p.stem.split('_')[1]))

    if not chunks:
        print(f"No chunks found in {chunks_dir}")
        sys.exit(1)

    print(f"Found {len(chunks)} chunks to process")

    # Calculate global offsets for each chunk
    chunk_tasks = []
    global_offset = 0.0

    for chunk_path in chunks:
        info = get_chunk_info(chunk_path)
        chunk_tasks.append((str(chunk_path), str(output_dir), global_offset))
        global_offset += info['duration']

    print(f"Total duration: {global_offset:.1f}s ({global_offset/60:.1f} min)")
    print(f"Processing with {args.workers} workers...\n")

    # Process chunks
    results = []

    if args.sequential:
        for task in chunk_tasks:
            result = process_single_chunk(task)
            results.append(result)
            print(f"  Completed chunk {result['chunk_num']}")
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(process_single_chunk, task): task for task in chunk_tasks}

            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                status = "✓" if result['success'] else "✗"
                print(f"  {status} Chunk {result['chunk_num']} completed")

    # Sort results by chunk number
    results.sort(key=lambda x: x['chunk_num'])

    # Merge into unified transcript
    all_segments = []
    all_words = []
    full_text_parts = []

    for result in results:
        if result['success']:
            all_segments.extend(result.get('segments', []))
            all_words.extend(result.get('words', []))
            full_text_parts.append(result.get('text', ''))

    # Create index
    index = {
        'source_dir': str(chunks_dir),
        'total_chunks': len(chunks),
        'total_duration': global_offset,
        'chunks': [
            {
                'chunk_num': r['chunk_num'],
                'global_offset': r['global_offset'],
                'duration': r['duration'],
                'success': r['success'],
                'text': r.get('text', ''),
                'error': r.get('error')
            }
            for r in results
        ],
        'full_text': '\n'.join(full_text_parts),
        'segments': all_segments,
        'words': all_words
    }

    # Save index
    output_path = chunks_dir / args.output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved transcript index to {output_path}")
    print(f"  - {len(all_segments)} segments")
    print(f"  - {len(all_words)} words")
    print(f"  - {len(index['full_text'])} characters")

    # Print summary of successful/failed chunks
    success_count = sum(1 for r in results if r['success'])
    print(f"\nProcessed {success_count}/{len(chunks)} chunks successfully")

if __name__ == '__main__':
    main()
