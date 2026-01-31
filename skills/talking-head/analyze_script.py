#!/usr/bin/env python3
"""
Script-first analysis for talking-head videos.

Instead of uploading many video clips to Gemini:
1. Send the FULL transcript as text (fast, cheap)
2. Gemini identifies highlight moments with sentence references
3. Map highlights back to clip IDs using the sentence index

Benefits:
- Full context: Gemini sees entire narrative arc
- Fast: Text analysis vs video upload
- Precise: We maintain exact clip mappings
"""

import json
import sys
from pathlib import Path
import argparse

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))


SCRIPT_ANALYSIS_PROMPT = """
Analyze this transcript from a talking-head video. Identify TOPICS with complete narrative arcs.

## TRANSCRIPT
{transcript}

## TASK: TWO-PHASE ANALYSIS

### PHASE 1: RECALL - Find ALL Topics
Identify every distinct TOPIC in the video. For each topic, include the FULL range of sentences
that cover it - from introduction through conclusion. Optimize for RECALL (don't miss content).

A complete topic has:
- **Setup/Hook**: How the topic is introduced
- **Elaboration**: The main content, examples, explanations
- **Conclusion/Takeaway**: Resolution, actionable advice, or key insight

### PHASE 2: PRECISION - Mark Key Moments
Within each topic, identify which sentences are:
- **essential**: Must include (the hook, key insight, conclusion)
- **supporting**: Good context but could be trimmed
- **skippable**: Filler, repetition, or tangents

Also identify if sentences could be REORDERED for better flow (e.g., move a strong hook earlier).

## WHAT TO LOOK FOR

**Strong hooks:**
- Credibility: "I've raised $50M...", "As a former Google..."
- Provocative: "VCs are the most hypocritical...", "Nobody tells you..."
- Promise: "Here's the secret...", "The trick is..."

**Good conclusions:**
- Actionable advice: "So what you should do is..."
- Key insight: "The takeaway here is..."
- Memorable quote: Something tweetable

**Skip/trim candidates:**
- Filler words, hesitations, false starts
- Repetitive explanations
- Off-topic tangents
- Coordination/practice talk (e.g., "Is that good?", "Let me try again")

## OUTPUT FORMAT (JSON)

{{
  "topics": [
    {{
      "topic_id": 1,
      "title": "Brief topic title",
      "sentence_range": "176-192",
      "duration_estimate_sec": 170,
      "viral_potential": 9,
      "summary": "One sentence summary of the topic",
      "arc": {{
        "hook": {{
          "sentences": "176-177",
          "quote": "VCs are the most hypocritical animals...",
          "strength": 9
        }},
        "elaboration": {{
          "sentences": "178-188",
          "key_points": ["They ghost you", "Real reasons they reject", "How their process works"]
        }},
        "conclusion": {{
          "sentences": "189-192",
          "quote": "If they're not moving fast, that means no",
          "strength": 8
        }}
      }},
      "trimming_guide": {{
        "essential_sentences": [176, 177, 178, 185, 189, 192],
        "supporting_sentences": [179, 180, 181, 182, 183, 184, 186, 187, 188, 190, 191],
        "skippable_sentences": [],
        "suggested_trim_to_60s": "176-178, 185, 189-192"
      }},
      "reorder_suggestion": {{
        "recommended": false,
        "reason": "Natural flow is already good",
        "alternative_order": null
      }}
    }}
  ],
  "coordination_segments": [
    {{
      "sentences": "1-5",
      "type": "practice_talk",
      "note": "Speaker coordinating with camera operator"
    }}
  ],
  "summary": {{
    "total_topics": 5,
    "best_topic_for_short": 1,
    "speaker_style": "Confident, insider knowledge, conversational",
    "recommended_video_structure": "Topic 3 hook → Topic 1 body → Topic 2 conclusion"
  }}
}}

## IMPORTANT

1. **Optimize for RECALL first** - include ALL sentences that might be relevant to each topic
2. Don't fragment topics - keep the full arc together
3. Mark coordination/practice segments separately (Chinese phrases like "好的", "再来一遍", "怎么说")
4. Each topic should be self-contained and make sense on its own
"""


def build_sentence_index(clip_index_path: str) -> dict:
    """
    Build an index mapping sentences to clips.

    Returns:
        {
            "sentences": [
                {"id": 1, "text": "...", "clip_id": 1, "start_sec": 0.0, "end_sec": 5.2},
                ...
            ],
            "clip_to_sentences": {1: [1, 2, 3], 2: [4, 5, 6], ...},
            "sentence_to_clip": {1: 1, 2: 1, 3: 1, 4: 2, ...}
        }
    """
    with open(clip_index_path) as f:
        clip_index = json.load(f)

    sentences = []
    clip_to_sentences = {}
    sentence_to_clip = {}

    sentence_id = 1

    for clip in clip_index.get("clips", []):
        clip_id = clip.get("clip_id")
        text = clip.get("text", "")
        start_sec = clip.get("start_sec", 0)
        end_sec = clip.get("end_sec", 0)

        # Split clip text into sentences (rough split)
        # Note: The clip IS roughly a sentence, so often 1:1
        clip_sentences = split_into_sentences(text)

        clip_to_sentences[clip_id] = []

        for sent_text in clip_sentences:
            sentences.append({
                "id": sentence_id,
                "text": sent_text.strip(),
                "clip_id": clip_id,
                "start_sec": start_sec,
                "end_sec": end_sec,
            })
            clip_to_sentences[clip_id].append(sentence_id)
            sentence_to_clip[sentence_id] = clip_id
            sentence_id += 1

    return {
        "sentences": sentences,
        "clip_to_sentences": clip_to_sentences,
        "sentence_to_clip": sentence_to_clip,
        "total_sentences": len(sentences),
        "total_clips": len(clip_index.get("clips", [])),
    }


def split_into_sentences(text: str) -> list:
    """
    Split text into sentences.
    Handles both English and Chinese punctuation.
    """
    import re

    # Sentence-ending punctuation
    pattern = r'(?<=[.!?。！？；])\s*'

    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def format_transcript_with_numbers(sentences: list) -> str:
    """Format transcript with sentence numbers for Gemini."""
    lines = []
    for sent in sentences:
        lines.append(f"[{sent['id']}] {sent['text']}")
    return "\n".join(lines)


def parse_sentence_range(range_str: str) -> tuple:
    """Parse sentence range like '15-18' or '15'."""
    range_str = range_str.strip()
    if '-' in range_str:
        parts = range_str.split('-')
        return int(parts[0]), int(parts[1])
    else:
        num = int(range_str)
        return num, num


def map_range_to_clips(range_str: str, sentence_to_clip: dict) -> list:
    """Map a sentence range string to clip IDs."""
    try:
        start_sent, end_sent = parse_sentence_range(range_str)
    except ValueError:
        return []

    clip_ids = set()
    for sent_id in range(start_sent, end_sent + 1):
        if sent_id in sentence_to_clip:
            clip_ids.add(sentence_to_clip[sent_id])

    return sorted(clip_ids)


def map_topics_to_clips(topics: list, sentence_to_clip: dict) -> list:
    """
    Map topic sentence ranges to clip IDs.

    For each topic, maps:
    - Full range to clip_ids (all clips for recall)
    - Essential sentences to essential_clip_ids (for trimmed version)
    - Hook/conclusion to specific clip IDs
    """
    for topic in topics:
        # Map full topic range
        range_str = topic.get("sentence_range", "1")
        topic["clip_ids"] = map_range_to_clips(range_str, sentence_to_clip)
        topic["start_clip"] = min(topic["clip_ids"]) if topic["clip_ids"] else None
        topic["end_clip"] = max(topic["clip_ids"]) if topic["clip_ids"] else None

        # Map arc components
        arc = topic.get("arc", {})
        if arc.get("hook", {}).get("sentences"):
            arc["hook"]["clip_ids"] = map_range_to_clips(
                arc["hook"]["sentences"], sentence_to_clip
            )
        if arc.get("conclusion", {}).get("sentences"):
            arc["conclusion"]["clip_ids"] = map_range_to_clips(
                arc["conclusion"]["sentences"], sentence_to_clip
            )

        # Map trimming guide
        trimming = topic.get("trimming_guide", {})
        essential = trimming.get("essential_sentences", [])
        if essential:
            essential_clips = set()
            for sent_id in essential:
                if sent_id in sentence_to_clip:
                    essential_clips.add(sentence_to_clip[sent_id])
            trimming["essential_clip_ids"] = sorted(essential_clips)

        # Map suggested trim
        if trimming.get("suggested_trim_to_60s"):
            # Parse comma-separated ranges like "176-178, 185, 189-192"
            trim_clips = set()
            for part in trimming["suggested_trim_to_60s"].split(","):
                part = part.strip()
                trim_clips.update(map_range_to_clips(part, sentence_to_clip))
            trimming["trimmed_clip_ids"] = sorted(trim_clips)

    return topics


def map_highlights_to_clips(highlights: list, sentence_to_clip: dict) -> list:
    """
    Map highlight sentence ranges to clip IDs (legacy support).
    """
    for highlight in highlights:
        range_str = highlight.get("sentence_range", "1")
        highlight["clip_ids"] = map_range_to_clips(range_str, sentence_to_clip)
        highlight["primary_clip_id"] = min(highlight["clip_ids"]) if highlight["clip_ids"] else None

    return highlights


def analyze_script(
    clip_index_path: str,
    output_path: str = None,
) -> dict:
    """
    Analyze full transcript to find TOPICS with complete arcs.

    Two-phase approach:
    1. RECALL: Find all topics with full clip ranges
    2. PRECISION: Mark essential vs trimmable content within each topic

    Args:
        clip_index_path: Path to clip_index.json from sentence_split.py
        output_path: Where to save analysis results

    Returns:
        Dict with topics mapped to clip IDs, including trimming guides
    """
    from gemini_client import client, DEFAULT_MODEL
    from google.genai import types
    import re

    # Build sentence index
    print("Building sentence index...")
    index = build_sentence_index(clip_index_path)
    print(f"  {index['total_sentences']} sentences across {index['total_clips']} clips")

    # Format transcript
    transcript = format_transcript_with_numbers(index["sentences"])

    # Analyze with Gemini
    print("Analyzing transcript with Gemini (recall-first)...")
    prompt = SCRIPT_ANALYSIS_PROMPT.format(transcript=transcript)

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    # Parse response
    text = response.text
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        result = json.loads(json_match.group(1))
    else:
        result = json.loads(text)

    # Map topics to clips (new format)
    topics = result.get("topics", [])
    if topics:
        topics = map_topics_to_clips(topics, index["sentence_to_clip"])
        result["topics"] = topics
        # Sort by viral potential
        result["topics"].sort(key=lambda x: x.get("viral_potential", 0), reverse=True)
        print(f"  Found {len(topics)} topics")

    # Also handle legacy highlights format if present
    highlights = result.get("highlights", [])
    if highlights:
        highlights = map_highlights_to_clips(highlights, index["sentence_to_clip"])
        result["highlights"] = highlights

    # Add index info
    result["sentence_index"] = index
    result["clip_index_path"] = clip_index_path
    result["analysis_type"] = "topic_recall" if topics else "highlight_precision"

    # Save
    if output_path:
        with open(output_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved analysis to {output_path}")

    return result


def format_analysis_for_review(result: dict) -> str:
    """Format analysis for Claude Code to present."""
    lines = [
        "=" * 60,
        "TOPIC ANALYSIS COMPLETE (Recall-First)",
        "=" * 60,
        "",
    ]

    summary = result.get("summary", {})
    if summary:
        lines.append(f"Speaker style: {summary.get('speaker_style', 'N/A')}")
        lines.append(f"Total topics: {summary.get('total_topics', 'N/A')}")
        lines.append("")

    # Handle new topic-based format
    topics = result.get("topics", [])
    if topics:
        for topic in topics:
            topic_id = topic.get("topic_id", "?")
            title = topic.get("title", "Untitled")
            viral = topic.get("viral_potential", 0)
            clip_ids = topic.get("clip_ids", [])
            duration = topic.get("duration_estimate_sec", 0)

            lines.append(f"TOPIC {topic_id}: {title}")
            lines.append(f"  Viral potential: {viral}/10")
            lines.append(f"  Full clips: {clip_ids[0]}-{clip_ids[-1] if clip_ids else '?'} ({len(clip_ids)} clips, ~{duration}s)")

            # Show arc
            arc = topic.get("arc", {})
            if arc.get("hook"):
                hook = arc["hook"]
                lines.append(f"  Hook: \"{hook.get('quote', '')[:50]}...\" (clips {hook.get('clip_ids', [])})")
            if arc.get("conclusion"):
                concl = arc["conclusion"]
                lines.append(f"  Conclusion: \"{concl.get('quote', '')[:50]}...\" (clips {concl.get('clip_ids', [])})")

            # Show trimming options
            trimming = topic.get("trimming_guide", {})
            if trimming.get("trimmed_clip_ids"):
                lines.append(f"  Trimmed (~60s): clips {trimming['trimmed_clip_ids']}")

            lines.append("")

        lines.append("-" * 60)
        lines.append("OPTIONS:")
        lines.append("  - \"Use topic 1 full\" - all clips for topic 1")
        lines.append("  - \"Use topic 1 trimmed\" - essential clips only")
        lines.append("  - \"Use clips 176-192\" - specific range")
        lines.append("-" * 60)

    # Fallback to legacy highlights format
    else:
        highlights = result.get("highlights", [])
        hooks = [h for h in highlights if h.get("hook_potential", 0) >= 8]
        content = [h for h in highlights if h.get("hook_potential", 0) < 8 and h.get("viral_score", 0) >= 6]

        if hooks:
            lines.append("BEST HOOKS:")
            for h in hooks[:3]:
                clip_ids = h.get("clip_ids", [])
                lines.append(f"  Clips {clip_ids}: {h.get('viral_score', 0)}/10")
                lines.append(f"    \"{h.get('quote', '')[:60]}...\"")
            lines.append("")

        if content:
            lines.append("GOOD CONTENT:")
            for h in content[:5]:
                clip_ids = h.get("clip_ids", [])
                lines.append(f"  Clips {clip_ids}: {h.get('viral_score', 0)}/10 - {h.get('type', '')}")
            lines.append("")

        # Recommended clips
        recommended_clips = []
        for h in highlights:
            if h.get("viral_score", 0) >= 6:
                for cid in h.get("clip_ids", []):
                    if cid not in recommended_clips:
                        recommended_clips.append(cid)

        if recommended_clips:
            lines.append("-" * 60)
            lines.append(f"RECOMMENDED CLIPS: {recommended_clips[:10]}")
            lines.append("-" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze full transcript to find highlights'
    )
    parser.add_argument('clip_index', help='clip_index.json from sentence_split.py')
    parser.add_argument('--output', '-o', default='script_analysis.json',
                        help='Output JSON file')
    args = parser.parse_args()

    if not Path(args.clip_index).exists():
        print(f"Error: Clip index not found: {args.clip_index}", file=sys.stderr)
        sys.exit(1)

    result = analyze_script(args.clip_index, args.output)

    # Print summary
    print("\n" + format_analysis_for_review(result))


if __name__ == "__main__":
    main()
