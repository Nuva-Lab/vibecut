# Inspect Video Skill

Gemini-powered video inspection for quality analysis and debugging.

## Purpose

Use Gemini 3 Pro's video understanding to:
- Describe what's happening in the video
- Identify freeze frames, black frames, glitches
- Detect visual quality issues
- Verify content matches expectations
- Generate quality reports

## Usage

```bash
python skills/inspect-video/inspect.py <video_file> [--prompt "custom query"]
```

## Default Inspection

Without custom prompt, runs a standard quality check:

```bash
python skills/inspect-video/inspect.py video.mp4
```

Output:
```json
{
  "description": "Panel discussion with 3 speakers...",
  "quality_issues": ["Video appears to freeze at 35s"],
  "visual_quality": "good",
  "audio_sync": "appears synchronized",
  "recommendations": ["Check source video at 35s mark"]
}
```

## Custom Queries

Ask specific questions about the video:

```bash
# Check for specific content
python skills/inspect-video/inspect.py video.mp4 --prompt "Who are the speakers and what are they discussing?"

# Debug freeze issue
python skills/inspect-video/inspect.py video.mp4 --prompt "Does the video freeze or loop at any point?"

# Verify captions
python skills/inspect-video/inspect.py video.mp4 --prompt "Are the captions visible and readable?"
```

## Integration

Use for quality assurance after rendering:

```python
from skills.inspect_video.inspect import inspect_video

result = inspect_video("output/final.mp4", "Does the video have any visual glitches?")
if "freeze" in result.lower() or "glitch" in result.lower():
    print("Quality issue detected!")
```

## Gemini Video Understanding

- Supports videos up to 1 hour
- Analyzes visual content, motion, text
- Can detect audio issues (if asked)
- Provides timestamps for issues found
