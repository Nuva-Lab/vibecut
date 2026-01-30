---
name: find-golden-segments
description: Find naturally clean, coherent video segments worth keeping (selection over repair)
---

# Find Golden Segments Skill

Use this skill to identify the best moments in raw footage - segments that are already clean and don't need repair.

## Philosophy

**Selection over Repair**: Instead of trying to fix broken footage by cutting out fillers, find the moments that are naturally good.

## What Makes a Golden Segment

- **10-30 seconds** of continuous clean speech
- **Complete thought**: Full sentence or insight, not cut mid-idea
- **Minimal fillers**: 0-2 max (not 10+)
- **Stable delivery**: Speaker confident, camera relatively steady
- **Standalone value**: Makes sense without heavy context

## Usage

```bash
python skills/find-golden-segments/find_golden.py <video_path>

# Examples
python skills/find-golden-segments/find_golden.py video.MOV
python skills/find-golden-segments/find_golden.py video.MOV --min-duration 15
```

## Output

```json
{
  "golden_segments": [
    {
      "start": "02:15",
      "end": "02:38",
      "duration_sec": 23,
      "score": 9,
      "speaker": "Speaker Name",
      "topic": "Brief topic",
      "quote_preview": "First few words...",
      "quality_notes": "Why this segment is good"
    }
  ],
  "summary": {
    "total_duration": 140,
    "golden_duration": 45,
    "segments_found": 3
  }
}
```

## Minimum Quality

Only segments scoring **7/10 or higher** are included. Lower-quality sections are skipped entirely.
