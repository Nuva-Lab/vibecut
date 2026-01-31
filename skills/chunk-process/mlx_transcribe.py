#!/usr/bin/env python3
"""
Fast transcription using mlx-audio Qwen3-ASR on Apple Silicon.

8-bit quantized models run efficiently on Mac M1/M2/M3 with MLX.

V3 Features:
- Word-level timestamps for sentence boundary detection
- Pause detection between words (for sentence_split.py)
- Support for forced alignment with known text
"""

import json
import subprocess
import sys
from pathlib import Path
import argparse

def transcribe_with_mlx(
    audio_path: str,
    model: str = "mlx-community/Qwen3-ASR-1.7B-8bit",
    return_word_timestamps: bool = False,
    language: str = None,
) -> dict:
    """
    Transcribe audio using mlx-audio Qwen3-ASR.

    Args:
        audio_path: Path to audio file (wav preferred)
        model: MLX model ID
        return_word_timestamps: If True, also return word-level timestamps
        language: Language hint (None for auto-detect)

    Returns:
        dict with text, language, and optionally words with timestamps
    """
    from mlx_audio.stt import load

    print(f"Loading {model}...")
    model_obj = load(model)

    print(f"Transcribing: {audio_path}")

    # Get basic transcription
    result = model_obj.generate(audio_path, language=language)
    text = result.text.strip() if hasattr(result, 'text') else str(result).strip()

    output = {
        "text": text,
        "model": model,
    }

    # Get word-level timestamps using forced alignment
    if return_word_timestamps and text:
        words = get_word_timestamps(audio_path, text, language)
        output["words"] = words

        # Calculate pause durations between words
        if len(words) > 1:
            for i in range(1, len(words)):
                pause_ms = int((words[i]["start"] - words[i-1]["end"]) * 1000)
                words[i]["pause_before_ms"] = max(0, pause_ms)
            words[0]["pause_before_ms"] = 0

    return output


def get_word_timestamps(
    audio_path: str,
    text: str,
    language: str = None,
    model: str = "mlx-community/Qwen3-ForcedAligner-0.6B-8bit"
) -> list:
    """
    Get word-level timestamps using Qwen3-ForcedAligner.

    Args:
        audio_path: Path to audio file
        text: Transcribed text to align
        language: Language for alignment (auto-detect if None)
        model: Aligner model ID

    Returns:
        List of {text, start, end, pause_before_ms} dicts
    """
    from mlx_audio.stt import load

    # Detect language from text if not specified
    if language is None:
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text.replace(' ', ''))
        if total_chars > 0:
            chinese_ratio = chinese_chars / total_chars
            language = "Chinese" if chinese_ratio > 0.5 else "English"
        else:
            language = "English"

    print(f"Aligning with {model} (language: {language})...")
    aligner = load(model)

    result = aligner.generate(audio_path, text=text, language=language)

    words = []
    for item in result:
        words.append({
            "text": item.text,
            "start": item.start_time,
            "end": item.end_time,
        })

    return words

def align_with_mlx(audio_path: str, text: str, language: str = "English") -> list:
    """
    Align text to audio using mlx-audio Qwen3-ForcedAligner.

    Returns list of word timestamps.
    """
    from mlx_audio.stt import load

    model = "mlx-community/Qwen3-ForcedAligner-0.6B-8bit"
    print(f"Loading {model}...")
    aligner = load(model)

    print(f"Aligning to audio: {audio_path}")
    result = aligner.generate(audio_path, text=text, language=language)

    words = []
    for item in result:
        words.append({
            "text": item.text,
            "start": item.start_time,
            "end": item.end_time,
        })

    return words

def extract_audio(video_path: str, output_path: str) -> str:
    """Extract audio from video to WAV format."""
    subprocess.run([
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        output_path
    ], capture_output=True)
    return output_path

def batch_transcribe_chunks(
    chunks_dir: Path,
    output_file: str = "transcript.json",
    language: str = None,
    word_timestamps: bool = False,
) -> dict:
    """
    Transcribe all chunks in a directory.

    Args:
        chunks_dir: Directory with chunk_*.mp4 files
        output_file: Output filename
        language: Language hint (None for auto-detect, or 'Chinese', 'English', etc.)
        word_timestamps: If True, include word-level timestamps for each chunk

    Returns merged transcript with global offsets and language info.
    """
    from mlx_audio.stt import load
    from collections import Counter

    chunks_dir = Path(chunks_dir)
    audio_dir = chunks_dir / "audio"
    audio_dir.mkdir(exist_ok=True)

    # Load chunk index
    index_path = chunks_dir / "chunk_index.json"
    if index_path.exists():
        with open(index_path) as f:
            chunk_index = json.load(f)
        chunks = chunk_index["chunks"]
    else:
        # Find chunks by glob and get actual durations
        chunk_files = sorted(chunks_dir.glob("chunk_*.mp4"), key=lambda p: int(p.stem.split('_')[1]))
        chunks = []
        cumulative_offset = 0.0
        for p in chunk_files:
            # Get actual duration using ffprobe
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', str(p)],
                capture_output=True, text=True
            )
            duration = float(result.stdout.strip()) if result.stdout.strip() else 180.0
            chunks.append({
                "chunk_num": int(p.stem.split('_')[1]),
                "path": str(p),
                "start": cumulative_offset,
                "duration": duration
            })
            cumulative_offset += duration

    if not chunks:
        print(f"No chunks found in {chunks_dir}")
        sys.exit(1)

    print(f"Found {len(chunks)} chunks to transcribe")
    if language:
        print(f"Language hint: {language}")
    else:
        print("Language: auto-detect")

    # Load model once
    print("\nLoading mlx-audio Qwen3-ASR-1.7B-8bit...")
    model = load("mlx-community/Qwen3-ASR-1.7B-8bit")

    results = []
    detected_languages = []

    for chunk in chunks:
        chunk_num = chunk["chunk_num"]
        video_path = chunk["path"]
        global_offset = chunk.get("start", 0)

        # Extract audio
        audio_path = audio_dir / f"chunk_{chunk_num:03d}.wav"
        if not audio_path.exists():
            print(f"  Extracting audio: chunk_{chunk_num:03d}...", end=" ", flush=True)
            extract_audio(video_path, str(audio_path))
            print("done")

        # Check for cached transcript
        transcript_path = audio_dir / f"chunk_{chunk_num:03d}_transcript.json"
        if transcript_path.exists():
            with open(transcript_path) as f:
                cached = json.load(f)
            text = cached.get("text") or cached.get("full_text", "")
            detected_lang = cached.get("language", "unknown")
            detected_languages.append(detected_lang)
            print(f"  [cached] chunk_{chunk_num:03d}: {len(text)} chars ({detected_lang})")
            results.append({
                "chunk_num": chunk_num,
                "global_offset": global_offset,
                "text": text,
                "language": detected_lang,
            })
            continue

        # Transcribe with language hint or auto-detect
        print(f"  [transcribe] chunk_{chunk_num:03d}...", end=" ", flush=True)

        # Try to transcribe - if language is None, try common languages
        if language:
            result = model.generate(str(audio_path), language=language)
            detected_lang = language
        else:
            # Auto-detect: try English first (common default), model will handle other languages
            try:
                result = model.generate(str(audio_path), language="English")
                detected_lang = "English"
            except Exception:
                # Fallback to Chinese
                result = model.generate(str(audio_path), language="Chinese")
                detected_lang = "Chinese"

        text = result.text.strip() if hasattr(result, 'text') else str(result).strip()

        # Detect if content looks Chinese vs English
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text.replace(' ', ''))
        if total_chars > 0:
            chinese_ratio = chinese_chars / total_chars
            if chinese_ratio > 0.3:
                detected_lang = "Chinese" if chinese_ratio > 0.7 else "Mixed"
            elif detected_lang != "English":
                detected_lang = "English"

        detected_languages.append(detected_lang)

        # Get word-level timestamps if requested
        words = None
        if word_timestamps and text:
            try:
                words = get_word_timestamps(str(audio_path), text, detected_lang)
                # Add global offset to word timestamps
                for w in words:
                    w["start"] += global_offset
                    w["end"] += global_offset
                # Calculate pauses
                if len(words) > 1:
                    for i in range(1, len(words)):
                        pause_ms = int((words[i]["start"] - words[i-1]["end"]) * 1000)
                        words[i]["pause_before_ms"] = max(0, pause_ms)
                    words[0]["pause_before_ms"] = 0
                print(f"{len(text)} chars, {len(words)} words ({detected_lang})")
            except Exception as e:
                print(f"{len(text)} chars ({detected_lang}) [word alignment failed: {e}]")
        else:
            print(f"{len(text)} chars ({detected_lang})")

        # Cache with detected language and words
        cache_data = {
            "text": text,
            "model": "mlx-community/Qwen3-ASR-1.7B-8bit",
            "language": detected_lang,
        }
        if words:
            cache_data["words"] = words

        with open(transcript_path, "w") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        result_data = {
            "chunk_num": chunk_num,
            "global_offset": global_offset,
            "text": text,
            "language": detected_lang,
        }
        if words:
            result_data["words"] = words

        results.append(result_data)

    # Determine primary language
    lang_counts = Counter(detected_languages)
    primary_language = lang_counts.most_common(1)[0][0] if lang_counts else "unknown"

    # Merge results
    full_text_parts = []
    for r in results:
        offset_mins = r['global_offset'] / 60
        full_text_parts.append(f"\n[CHUNK {r['chunk_num']:03d} @ {offset_mins:.1f}min]\n{r['text']}")

    # Merge all words across chunks (with global timestamps already applied)
    all_words = []
    if word_timestamps:
        for r in results:
            if "words" in r:
                all_words.extend(r["words"])

    merged = {
        "source_dir": str(chunks_dir),
        "num_chunks": len(results),
        "primary_language": primary_language,
        "language_distribution": dict(lang_counts),
        "chunks": results,
        "full_text": "\n".join(full_text_parts),
        "total_chars": sum(len(r["text"]) for r in results),
    }

    if word_timestamps and all_words:
        merged["words"] = all_words
        merged["total_words"] = len(all_words)

    output_path = chunks_dir / output_file
    with open(output_path, "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved transcript to {output_path}")
    print(f"  - {merged['num_chunks']} chunks")
    print(f"  - {merged['total_chars']} characters")
    print(f"  - Primary language: {merged['primary_language']}")
    if len(merged['language_distribution']) > 1:
        print(f"  - Language distribution: {merged['language_distribution']}")
    if word_timestamps and all_words:
        print(f"  - {merged['total_words']} words with timestamps")

    return merged

def main():
    parser = argparse.ArgumentParser(description='MLX-accelerated transcription')
    parser.add_argument('input', help='Audio file or chunks directory')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--batch', '-b', action='store_true', help='Batch process chunks directory')
    parser.add_argument('--align', '-a', help='Text to align (forced alignment mode)')
    parser.add_argument('--language', '-l', default=None,
                        help='Language hint (auto-detect if not specified). '
                             'For transcription: English, Chinese, etc. '
                             'For alignment: must specify language.')
    parser.add_argument('--word-timestamps', '-w', action='store_true',
                        help='Include word-level timestamps (uses forced alignment)')
    args = parser.parse_args()

    input_path = Path(args.input)

    if args.batch or input_path.is_dir():
        # Batch mode
        batch_transcribe_chunks(
            input_path,
            args.output or "transcript.json",
            language=args.language,
            word_timestamps=args.word_timestamps,
        )
    elif args.align:
        # Alignment mode (language required for alignment)
        align_language = args.language or "English"
        words = align_with_mlx(str(input_path), args.align, align_language)
        output = {"text": args.align, "words": words}
        if args.output:
            with open(args.output, "w") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
        else:
            print(json.dumps(output, indent=2))
    else:
        # Single file transcription
        result = transcribe_with_mlx(
            str(input_path),
            return_word_timestamps=args.word_timestamps,
            language=args.language,
        )
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        else:
            print(result["text"])
            if args.word_timestamps and "words" in result:
                print(f"\n[{len(result['words'])} words with timestamps]")

if __name__ == "__main__":
    main()
