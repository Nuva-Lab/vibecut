#!/usr/bin/env python3
"""
Generate rolling captions and section titles for trimmed talking-head videos.

Takes:
- Word-level transcript (from precision_trim.py)
- Kept segments (from apply_precise_cuts)
- Section info (from topic analysis)

Outputs:
- captions.json for Remotion RollingCaption component
- sections.json for pop-up section titles
"""

import json
import sys
from pathlib import Path
import argparse

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))


def map_timestamps_to_trimmed(
    words: list,
    kept_segments: list,
) -> list:
    """
    Map word timestamps from original video to trimmed video.

    Since we removed segments, timestamps shift. This function adjusts
    each word's timestamp based on which kept segment it falls into.

    Returns:
        List of words with adjusted timestamps for the trimmed video.
        Words that were cut are excluded.
    """
    mapped_words = []
    cumulative_offset = 0.0

    for segment in kept_segments:
        seg_start = segment["start_sec"]
        seg_end = segment["end_sec"]

        # Find words that fall within this segment
        for word in words:
            word_start = word["start"]
            word_end = word["end"]

            # Word is within this kept segment
            if word_start >= seg_start and word_end <= seg_end:
                # Adjust timestamp: subtract original start, add cumulative offset
                adjusted_start = word_start - seg_start + cumulative_offset
                adjusted_end = word_end - seg_start + cumulative_offset

                mapped_words.append({
                    "text": word["text"],
                    "start": adjusted_start,
                    "end": adjusted_end,
                    "startMs": int(adjusted_start * 1000),
                    "endMs": int(adjusted_end * 1000),
                    "original_start": word_start,
                    "original_end": word_end,
                })

        # Update cumulative offset for next segment
        cumulative_offset += segment["end_sec"] - segment["start_sec"]

    return mapped_words


def group_words_into_phrases(
    words: list,
    max_words_per_phrase: int = 6,
    max_chars_per_phrase: int = 40,
    max_duration_ms: int = 3000,
    min_pause_for_break_ms: int = 200,
) -> list:
    """
    Group words into readable phrases for caption display.

    Args:
        words: List of word dicts with startMs/endMs
        max_words_per_phrase: Maximum words per phrase (default 6 for readability)
        max_chars_per_phrase: Maximum characters per phrase (default 40)
        max_duration_ms: Maximum phrase duration (default 3s)
        min_pause_for_break_ms: Minimum pause to force a phrase break (default 200ms)

    Returns:
        List of phrase dicts with text, startMs, endMs, and words array
    """
    if not words:
        return []

    phrases = []
    current_phrase_words = []
    current_phrase_start = None

    for i, word in enumerate(words):
        # Start new phrase if empty
        if not current_phrase_words:
            current_phrase_start = word["startMs"]
            current_phrase_words.append(word)
            continue

        # Check if we should break the phrase
        should_break = False

        # Calculate current phrase length
        current_text = " ".join(w["text"] for w in current_phrase_words)
        next_text = current_text + " " + word["text"]

        # Check word count
        if len(current_phrase_words) >= max_words_per_phrase:
            should_break = True

        # Check character count (important for screen width)
        elif len(next_text) > max_chars_per_phrase:
            should_break = True

        # Check duration
        elif word["endMs"] - current_phrase_start > max_duration_ms:
            should_break = True

        # Check for natural pause
        else:
            prev_word = current_phrase_words[-1]
            pause_ms = word["startMs"] - prev_word["endMs"]
            if pause_ms >= min_pause_for_break_ms:
                should_break = True

        # Also break on sentence-ending punctuation
        prev_text = current_phrase_words[-1]["text"].strip()
        if prev_text and prev_text[-1] in '.!?。！？':
            should_break = True

        if should_break:
            # Save current phrase
            # Join with space for readability
            phrase_text = " ".join(w["text"] for w in current_phrase_words)
            phrases.append({
                "text": phrase_text,
                "startMs": current_phrase_start,
                "endMs": current_phrase_words[-1]["endMs"],
                "words": current_phrase_words.copy(),
            })
            # Start new phrase
            current_phrase_words = [word]
            current_phrase_start = word["startMs"]
        else:
            current_phrase_words.append(word)

    # Don't forget the last phrase
    if current_phrase_words:
        phrase_text = " ".join(w["text"] for w in current_phrase_words)
        phrases.append({
            "text": phrase_text,
            "startMs": current_phrase_start,
            "endMs": current_phrase_words[-1]["endMs"],
            "words": current_phrase_words.copy(),
        })

    return phrases


def generate_section_titles(
    kept_segments: list,
    topic_info: dict = None,
    min_gap_for_section_ms: int = 500,
) -> list:
    """
    Generate section title markers for pop-up animations.

    Creates section breaks when there are significant gaps between
    kept segments (indicating topic transitions).

    Args:
        kept_segments: List of kept segment dicts
        topic_info: Optional topic analysis with titles
        min_gap_for_section_ms: Minimum gap to consider a new section

    Returns:
        List of section dicts with title, startMs, durationMs
    """
    sections = []

    # Default section titles if no topic info provided
    default_titles = [
        "The Hook",
        "Key Insight",
        "Real Talk",
        "The Truth",
        "Takeaway",
    ]

    cumulative_time = 0.0
    section_index = 0

    for i, segment in enumerate(kept_segments):
        seg_duration = segment["end_sec"] - segment["start_sec"]

        # Check if this is the start or after a significant gap
        is_start = (i == 0)

        if i > 0:
            # Calculate gap in the original video between this and previous segment
            prev_seg = kept_segments[i - 1]
            gap_in_original = segment["start_sec"] - prev_seg["end_sec"]

            if gap_in_original * 1000 >= min_gap_for_section_ms:
                # Significant gap - might be a new section
                # For now, we'll mark major gaps (>2s) as section transitions
                if gap_in_original >= 2.0:
                    is_start = True

        if is_start and section_index < len(default_titles):
            sections.append({
                "title": default_titles[section_index],
                "startMs": int(cumulative_time * 1000),
                "durationMs": 2000,  # 2 second display
            })
            section_index += 1

        cumulative_time += seg_duration

    return sections


def generate_captions_for_trimmed(
    transcript_path: str,
    kept_segments_path: str,
    output_dir: str,
    topic_info_path: str = None,
    speaker_name: str = None,
    speaker_title: str = None,
) -> dict:
    """
    Generate captions and section titles for a trimmed video.

    Generates TWO caption files:
    - captions_horizontal.json: For 16:9 (max 50 chars, 8 words)
    - captions_vertical.json: For 9:16 (max 30 chars, 5 words)

    Args:
        transcript_path: Path to word_transcript.json from precision_trim
        kept_segments_path: Path to JSON with kept_segments from apply
        output_dir: Output directory for caption files
        speaker_name: Optional speaker name for label
        speaker_title: Optional speaker title/role

    Returns:
        Dict with captions and sections data
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    with open(transcript_path) as f:
        transcript = json.load(f)

    with open(kept_segments_path) as f:
        kept_data = json.load(f)

    # Get kept segments - might be nested or at top level
    kept_segments = kept_data.get("kept_segments", kept_data)
    if isinstance(kept_segments, dict):
        kept_segments = [kept_segments]

    words = transcript.get("words", [])

    print(f"=== Generating Captions for Trimmed Video ===")
    print(f"Original words: {len(words)}")
    print(f"Kept segments: {len(kept_segments)}")

    # Map timestamps to trimmed video
    print("\nMapping timestamps to trimmed video...")
    mapped_words = map_timestamps_to_trimmed(words, kept_segments)
    print(f"  Mapped words: {len(mapped_words)} (in trimmed video)")

    # Group into phrases for HORIZONTAL (16:9) - more generous limits
    print("\nGrouping words for horizontal (16:9)...")
    phrases_horizontal = group_words_into_phrases(
        mapped_words,
        max_words_per_phrase=8,
        max_chars_per_phrase=50,
        max_duration_ms=3500,
        min_pause_for_break_ms=200,
    )
    print(f"  Created {len(phrases_horizontal)} phrases")

    # Group into phrases for VERTICAL (9:16) - stricter limits
    print("\nGrouping words for vertical (9:16)...")
    phrases_vertical = group_words_into_phrases(
        mapped_words,
        max_words_per_phrase=5,
        max_chars_per_phrase=30,
        max_duration_ms=2500,
        min_pause_for_break_ms=150,
    )
    print(f"  Created {len(phrases_vertical)} phrases")

    # Generate section titles (same for both)
    print("\nGenerating section titles...")
    sections = generate_section_titles(kept_segments)
    print(f"  Created {len(sections)} section markers")

    # Prepare speaker info if provided
    speaker_info = None
    if speaker_name:
        speaker_info = {
            "name": speaker_name,
            "title": speaker_title or "",
        }

    # Save horizontal captions
    captions_h = {
        "captions": phrases_horizontal,
        "total_phrases": len(phrases_horizontal),
        "total_words": len(mapped_words),
        "speaker": speaker_info,
    }
    captions_h_path = output_dir / "captions_horizontal.json"
    with open(captions_h_path, "w") as f:
        json.dump(captions_h, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Saved horizontal captions to {captions_h_path}")

    # Save vertical captions
    captions_v = {
        "captions": phrases_vertical,
        "total_phrases": len(phrases_vertical),
        "total_words": len(mapped_words),
        "speaker": speaker_info,
    }
    captions_v_path = output_dir / "captions_vertical.json"
    with open(captions_v_path, "w") as f:
        json.dump(captions_v, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved vertical captions to {captions_v_path}")

    # Save sections
    sections_data = {"sections": sections}
    sections_path = output_dir / "sections.json"
    with open(sections_path, "w") as f:
        json.dump(sections_data, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved sections to {sections_path}")

    # Also save mapped words for debugging
    words_path = output_dir / "mapped_words.json"
    with open(words_path, "w") as f:
        json.dump({"words": mapped_words}, f, ensure_ascii=False, indent=2)

    return {
        "captions_horizontal": phrases_horizontal,
        "captions_vertical": phrases_vertical,
        "sections": sections,
        "mapped_words": mapped_words,
        "speaker": speaker_info,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Generate rolling captions for trimmed talking-head video'
    )
    parser.add_argument('transcript', help='Word transcript JSON from precision_trim')
    parser.add_argument('kept_segments', help='Kept segments JSON from apply')
    parser.add_argument('--output', '-o', default='captions_output',
                        help='Output directory')
    parser.add_argument('--topic-info', help='Optional topic analysis JSON')
    parser.add_argument('--speaker', help='Speaker name (e.g., "Xiaoyin Qu")')
    parser.add_argument('--speaker-title', help='Speaker title (e.g., "Founder of heyboss.ai")')

    args = parser.parse_args()

    generate_captions_for_trimmed(
        args.transcript,
        args.kept_segments,
        args.output,
        args.topic_info,
        speaker_name=args.speaker,
        speaker_title=args.speaker_title,
    )


if __name__ == "__main__":
    main()
