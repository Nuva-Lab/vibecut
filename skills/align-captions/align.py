#!/usr/bin/env python3
"""
align-captions: Align script text to audio timestamps.

Uses Qwen3-ForcedAligner for ~30ms precision timestamps.
Perfect for voiceover scripts where you have the exact text.

For Chinese: Groups characters into proper words using jieba segmentation.
For English: Uses space-separated words.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def segment_chinese_words(text: str) -> list:
    """Segment Chinese text into words using jieba."""
    import jieba
    # Use precise mode for better word boundaries
    words = list(jieba.cut(text, cut_all=False))
    # Filter empty strings and pure punctuation
    return [w for w in words if w.strip() and not re.match(r'^[，。！？；：""''（）【】、\s]+$', w)]


def split_into_phrases(text: str, language: str = "Chinese") -> list:
    """Split text into caption-sized phrases."""
    if language.lower() in ["chinese", "zh", "mandarin"]:
        # Split by Chinese punctuation
        pattern = r'([。！？；])'
        parts = re.split(pattern, text)
        combined = []
        for i, part in enumerate(parts):
            if i % 2 == 0:
                combined.append(part)
            else:
                if combined:
                    combined[-1] += part

        # Further split long phrases by comma
        result = []
        for phrase in combined:
            if not phrase.strip():
                continue
            if len(phrase) > 20:
                sub_parts = re.split(r'([，,])', phrase)
                temp = []
                for j, sub in enumerate(sub_parts):
                    if j % 2 == 0:
                        temp.append(sub)
                    else:
                        if temp:
                            temp[-1] += sub
                result.extend([p.strip() for p in temp if p.strip()])
            else:
                result.append(phrase.strip())
        return result
    else:
        # English: split by sentence boundaries
        pattern = r'[.!?;]'
        parts = re.split(pattern, text)
        return [p.strip() for p in parts if p.strip()]


def group_chars_into_words(char_segments: list, script: str, language: str = "Chinese") -> list:
    """
    Group character-level timestamps into word-level timestamps.

    For Chinese: Uses jieba segmentation
    For English: Characters are already words (space-separated)
    """
    if language.lower() not in ["chinese", "zh", "mandarin"]:
        # For non-Chinese, character segments are likely already word-level
        return char_segments

    # Get Chinese word segmentation
    words = segment_chinese_words(script)

    word_segments = []
    char_idx = 0

    for word in words:
        word_len = len(word)

        # Find matching characters in char_segments
        start_idx = char_idx
        matched_chars = 0

        while char_idx < len(char_segments) and matched_chars < word_len:
            char_text = char_segments[char_idx]["text"]
            # Skip punctuation in char_segments
            if re.match(r'^[，。！？；：""''（）【】、\s]+$', char_text):
                char_idx += 1
                continue
            matched_chars += len(char_text)
            char_idx += 1

        if start_idx < len(char_segments) and char_idx > start_idx:
            word_segments.append({
                "text": word,
                "startMs": char_segments[start_idx]["startMs"],
                "endMs": char_segments[char_idx - 1]["endMs"],
            })

    return word_segments


def align_captions(
    audio_path: str,
    script: str,
    language: str = "Chinese",
    device: str = "cpu",
    phrase_level: bool = True,
) -> dict:
    """
    Align script text to audio timestamps using Qwen3-ForcedAligner.

    Args:
        audio_path: Path to audio file
        script: The script text to align
        language: Language of the script
        device: Device to use ('cpu' or 'mps')
        phrase_level: Group word-level timestamps into phrases for captions

    Returns:
        dict with:
        - segments: phrase-level timestamps
        - word_segments: word-level timestamps (proper words, not characters)
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

    print(f"Aligning script to audio: {audio_path}")

    # Get character-level alignment from ForcedAligner
    results = aligner.align(
        audio=audio_path,
        text=script,
        language=language,
    )

    # Build character-level segments
    char_segments = []
    for char in results[0]:
        char_segments.append({
            "text": char.text,
            "startMs": int(char.start_time * 1000),
            "endMs": int(char.end_time * 1000),
        })

    # Group characters into proper words (for Chinese, using jieba)
    print("Grouping characters into words...")
    word_segments = group_chars_into_words(char_segments, script, language)
    print(f"  {len(char_segments)} chars -> {len(word_segments)} words")

    if not phrase_level:
        return {
            "segments": word_segments,
            "full_text": script,
            "language": language,
            "model": "Qwen3-ForcedAligner-0.6B",
            "level": "word",
        }

    # Group into phrases for caption display
    phrases = split_into_phrases(script, language)
    phrase_segments = []

    # Build a clean text from all words for position finding
    all_words_text = ""
    word_positions = []  # (start_pos, end_pos, word_idx) in all_words_text

    for i, w in enumerate(word_segments):
        text = w["text"]
        if re.match(r'^[，。！？；：""''（）【】、—\s]+$', text):
            continue
        start_pos = len(all_words_text)
        all_words_text += text
        word_positions.append((start_pos, len(all_words_text), i))

    # Build clean script text (no punctuation)
    script_clean = re.sub(r'[，。！？；：""''（）【】、—\s]', '', script)

    # For each phrase, find its position in the clean script and map to words
    current_script_pos = 0

    for phrase in phrases:
        phrase_clean = re.sub(r'[，。！？；：""''（）【】、—\s]', '', phrase)

        # Find phrase start position in script
        phrase_start_in_script = current_script_pos
        phrase_end_in_script = phrase_start_in_script + len(phrase_clean)
        current_script_pos = phrase_end_in_script

        # Find words that overlap with this phrase position
        phrase_words = []
        for start_pos, end_pos, word_idx in word_positions:
            # Word overlaps with phrase if: word_start < phrase_end AND word_end > phrase_start
            if start_pos < phrase_end_in_script and end_pos > phrase_start_in_script:
                phrase_words.append(word_segments[word_idx])

        if phrase_words:
            phrase_segments.append({
                "text": phrase,
                "startMs": phrase_words[0]["startMs"],
                "endMs": phrase_words[-1]["endMs"],
                "words": phrase_words,
            })

    return {
        "segments": phrase_segments,
        "word_segments": word_segments,
        "full_text": script,
        "language": language,
        "model": "Qwen3-ForcedAligner-0.6B",
        "level": "phrase",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Align script text to audio timestamps (Qwen3-ForcedAligner)"
    )
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument(
        "--script", "-s",
        help="Script text to align"
    )
    parser.add_argument(
        "--script-file", "-f",
        help="Path to file containing script text"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file (default: prints to stdout)"
    )
    parser.add_argument(
        "--language", "-l",
        default="Chinese",
        help="Language of the script (default: Chinese)"
    )
    parser.add_argument(
        "--word-level",
        action="store_true",
        help="Output word-level timestamps instead of phrases"
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

    # Get script text
    if args.script:
        script = args.script
    elif args.script_file:
        script_path = Path(args.script_file)
        if not script_path.exists():
            print(f"Error: Script file not found: {script_path}", file=sys.stderr)
            sys.exit(1)
        script = script_path.read_text(encoding="utf-8").strip()
    else:
        print("Error: Must provide --script or --script-file", file=sys.stderr)
        sys.exit(1)

    # Align
    result = align_captions(
        str(audio_path),
        script,
        language=args.language,
        device=args.device,
        phrase_level=not args.word_level,
    )

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {output_path}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # Summary
    print(f"\n--- Summary ---")
    print(f"Model: {result['model']}")
    print(f"Level: {result['level']}")
    print(f"Segments: {len(result['segments'])}")
    if result.get('word_segments'):
        print(f"Word segments: {len(result['word_segments'])}")

    return result


if __name__ == "__main__":
    main()
