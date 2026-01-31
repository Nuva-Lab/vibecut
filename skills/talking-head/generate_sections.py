#!/usr/bin/env python3
"""
Generate meaningful section titles using Gemini.

Analyzes the transcript to identify topic transitions and creates
descriptive section titles for display in the video.
"""

import json
import os
import sys
from pathlib import Path
import argparse
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def generate_section_titles(
    transcript_path: str,
    kept_segments_path: str,
    output_path: str = None,
    num_sections: int = 3,
) -> list:
    """
    Use Gemini to generate meaningful section titles.

    Args:
        transcript_path: Path to word_transcript.json
        kept_segments_path: Path to kept_segments.json
        output_path: Where to save sections JSON
        num_sections: Number of sections to create (default 3)

    Returns:
        List of section dicts with title, startMs, durationMs
    """
    # Load transcript
    with open(transcript_path) as f:
        transcript = json.load(f)

    with open(kept_segments_path) as f:
        kept_data = json.load(f)

    kept_segments = kept_data.get("kept_segments", kept_data)
    words = transcript.get("words", [])

    # Build full transcript text
    full_text = " ".join(w["text"] for w in words)

    # Calculate total duration
    total_duration_sec = sum(s["end_sec"] - s["start_sec"] for s in kept_segments)

    print(f"=== Generating Section Titles with Gemini ===")
    print(f"Transcript: {len(words)} words")
    print(f"Duration: {total_duration_sec:.1f}s")
    print(f"Requested sections: {num_sections}")

    # Prompt Gemini
    prompt = f"""Analyze this transcript and identify {num_sections} distinct topic sections.

For each section, provide:
1. A SHORT, PUNCHY title (2-4 words max, like YouTube chapter titles)
2. The approximate percentage through the video where it starts (0-100)

The titles should be:
- Engaging and descriptive (not generic like "Introduction" or "Key Point")
- Action-oriented or provocative when possible
- Specific to the actual content being discussed

TRANSCRIPT:
{full_text}

Respond in this exact JSON format:
{{
  "sections": [
    {{"title": "Short Punchy Title", "start_percent": 0}},
    {{"title": "Another Title", "start_percent": 33}},
    {{"title": "Final Point", "start_percent": 66}}
  ]
}}

Only output valid JSON, nothing else."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    response = response.text

    # Parse response
    try:
        # Extract JSON from response
        json_str = response.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]

        data = json.loads(json_str)
        raw_sections = data.get("sections", [])
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini response: {e}")
        print(f"Response: {response[:500]}")
        return []

    # Convert percentages to timestamps
    total_ms = int(total_duration_sec * 1000)
    sections = []

    for sec in raw_sections:
        start_percent = sec.get("start_percent", 0)
        start_ms = int((start_percent / 100) * total_ms)

        sections.append({
            "title": sec["title"],
            "startMs": start_ms,
            "durationMs": 3000,  # Show for 3 seconds
            "style": "bold",  # Use bold style for prominence
        })

    print(f"\nGenerated {len(sections)} sections:")
    for sec in sections:
        print(f"  [{sec['startMs']/1000:.1f}s] {sec['title']}")

    # Save if output path provided
    if output_path:
        output_data = {"sections": sections}
        with open(output_path, "w") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Saved to {output_path}")

    return sections


def main():
    parser = argparse.ArgumentParser(
        description='Generate section titles using Gemini'
    )
    parser.add_argument('transcript', help='Word transcript JSON')
    parser.add_argument('kept_segments', help='Kept segments JSON')
    parser.add_argument('--output', '-o', help='Output JSON path')
    parser.add_argument('--sections', '-n', type=int, default=3,
                        help='Number of sections (default 3)')

    args = parser.parse_args()

    generate_section_titles(
        args.transcript,
        args.kept_segments,
        args.output,
        args.sections,
    )


if __name__ == "__main__":
    main()
