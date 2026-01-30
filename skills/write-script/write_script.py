#!/usr/bin/env python3
"""
Generate voiceover script prompts from golden segments.
Outputs formatted context for Claude Code to generate the script interactively.
"""
import json
import sys
from pathlib import Path


def load_style_guide() -> str:
    """Load Joyce's style guide."""
    style_path = Path(__file__).parent / "style_guide.md"
    if style_path.exists():
        return style_path.read_text()
    return ""


def format_segments_for_prompt(golden_data: dict) -> str:
    """Format golden segments data for the prompt."""
    segments = golden_data.get("golden_segments", [])
    context = golden_data.get("video_context", {})
    summary = golden_data.get("summary", {})

    output = []

    # Video context
    output.append("## Video Context")
    output.append(f"- **Setting**: {context.get('setting', 'Unknown')}")
    output.append(f"- **Topic**: {context.get('overall_topic', 'Unknown')}")
    if context.get('main_speakers'):
        output.append(f"- **Speakers**: {', '.join(context['main_speakers'])}")
    output.append(f"- **Total Duration**: {summary.get('total_duration_sec', '?')}s")
    output.append(f"- **Golden Duration**: {summary.get('golden_duration_sec', '?')}s")
    output.append("")

    # Segments
    output.append("## Golden Segments to Use")
    for i, seg in enumerate(segments, 1):
        output.append(f"\n### Segment {i}: {seg.get('start', '?')} - {seg.get('end', '?')} ({seg.get('duration_sec', '?')}s)")
        output.append(f"**Score**: {seg.get('score', '?')}/10")
        output.append(f"**Speaker**: {seg.get('speaker', 'Unknown')}")
        output.append(f"**Topic**: {seg.get('topic', 'N/A')}")
        output.append(f"**Quote**: \"{seg.get('quote_preview', '...')}\"")
        if seg.get('quality_notes'):
            output.append(f"**Notes**: {seg['quality_notes']}")

    return "\n".join(output)


def generate_prompt(golden_path: str, angle: str = None) -> str:
    """
    Generate a complete prompt for script writing.

    Args:
        golden_path: Path to golden segments JSON
        angle: Optional angle/thesis to emphasize

    Returns:
        Formatted prompt string
    """
    golden_path = Path(golden_path)
    if not golden_path.exists():
        raise FileNotFoundError(f"Golden segments not found: {golden_path}")

    with open(golden_path) as f:
        golden_data = json.load(f)

    style_guide = load_style_guide()
    segments_info = format_segments_for_prompt(golden_data)

    # Build the prompt
    prompt_parts = []

    prompt_parts.append("=" * 70)
    prompt_parts.append("VOICEOVER SCRIPT REQUEST")
    prompt_parts.append("=" * 70)
    prompt_parts.append("")

    prompt_parts.append("I need you to write a voiceover script in Joyce's style.")
    prompt_parts.append("")

    if angle:
        prompt_parts.append(f"**Angle/Thesis to Emphasize**: {angle}")
        prompt_parts.append("")

    prompt_parts.append("-" * 70)
    prompt_parts.append("STYLE GUIDE")
    prompt_parts.append("-" * 70)
    prompt_parts.append(style_guide)
    prompt_parts.append("")

    prompt_parts.append("-" * 70)
    prompt_parts.append("SOURCE MATERIAL")
    prompt_parts.append("-" * 70)
    prompt_parts.append(segments_info)
    prompt_parts.append("")

    prompt_parts.append("-" * 70)
    prompt_parts.append("YOUR TASK")
    prompt_parts.append("-" * 70)
    prompt_parts.append("""
Write a voiceover script (45-60 seconds, ~150-180 words) using the golden segments above.

Follow the structure:
1. **HOOK** (5-10s): Grab attention with conflict/contrast
2. **CONTEXT** (10-15s): Set the scene, establish who/what/where
3. **INSIGHT** (15-30s): The key quote/moment from the segments
4. **ANALYSIS** (10-15s): Why this matters, your synthesis
5. **PIVOT** (5-10s): Connect to broader trend or thesis

Output format:
```
**HOOK**:
[Your hook text]

**CONTEXT**:
[Your context text]

**INSIGHT**:
[Your insight text]

**ANALYSIS**:
[Your analysis text]

**PIVOT**:
[Your pivot text]

---
**FULL SCRIPT** (for voice recording):
[Complete script as flowing text]

**Word Count**: X words (~Y seconds)
```
""")

    return "\n".join(prompt_parts)


def main():
    if len(sys.argv) < 2:
        print("Usage: python write_script.py <golden_segments.json> [--angle 'thesis']")
        print("")
        print("Example:")
        print("  python write_script.py golden_segments.json")
        print("  python write_script.py golden_segments.json --angle 'space investment'")
        sys.exit(1)

    golden_path = sys.argv[1]

    # Parse angle
    angle = None
    if "--angle" in sys.argv:
        idx = sys.argv.index("--angle")
        if idx + 1 < len(sys.argv):
            angle = sys.argv[idx + 1]

    prompt = generate_prompt(golden_path, angle)
    print(prompt)


if __name__ == "__main__":
    main()
