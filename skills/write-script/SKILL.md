---
name: write-script
description: Generate voiceover scripts in Joyce's style for video clips
---

# Write Script Skill

Use this skill to create voiceover scripts for video clips, matching Joyce's energetic insider style.

## Usage

```bash
# Generate script prompt from golden segments
python skills/write-script/write_script.py golden_segments.json

# With custom angle/thesis
python skills/write-script/write_script.py golden_segments.json --angle "space investment"
```

## Workflow

1. Run `write_script.py` with golden segments JSON
2. Script outputs formatted context and prompt
3. Claude Code generates the script interactively
4. Review, tweak, and save

## Output Structure

```
HOOK (5-10s)     → Grab attention, conflict/contrast
CONTEXT (10-15s) → Who/what/where, establish scene
INSIGHT (15-30s) → Key quote/moment, why it matters
ANALYSIS (10-15s)→ What this means, your take
PIVOT (5-10s)    → Connect to broader trend
```

## Style Reference

See `style_guide.md` for Joyce's full style profile including:
- Tone and voice
- Writing techniques
- What to avoid
- Example phrases
