---
name: analyze-video
description: Analyze raw video content using Gemini to identify speakers, topics, key moments, and potential clip opportunities
---

# Analyze Video Skill

Use this skill when you need to understand the content of a video file before creating clips.

## What This Skill Does

Sends a video to Gemini 3 Pro for comprehensive analysis, extracting:
- **Speakers**: Who appears in the video, their roles/titles if identifiable
- **Topics**: Main subjects discussed
- **Notable Quotes**: Memorable statements with timestamps
- **Visual Highlights**: Dynamic moments, gestures, reveals
- **Audience Reactions**: Applause, laughter, engagement
- **Panel Exchanges**: Interesting back-and-forth between speakers

## Usage

```bash
# Analyze a single video
python skills/analyze-video/analyze.py <video_path>

# Output goes to assets/outputs/analysis/<video_name>.json
```

## Output Format

```json
{
  "video_file": "path/to/video.mp4",
  "duration_seconds": 120,
  "speakers": [
    {"name": "Speaker Name", "role": "Title/Organization", "first_seen": "00:05"}
  ],
  "topics": ["Topic 1", "Topic 2"],
  "notable_quotes": [
    {"speaker": "Name", "quote": "...", "timestamp": "01:23", "context": "..."}
  ],
  "visual_highlights": [
    {"timestamp": "02:15", "description": "...", "type": "gesture|reveal|reaction"}
  ],
  "clip_opportunities": [
    {
      "start": "01:20",
      "end": "01:45",
      "type": "quote|exchange|highlight",
      "description": "...",
      "score": 8
    }
  ]
}
```

## Notes

- For videos >100MB, upload to Gemini File API (handled automatically)
- Analysis typically takes 30-60 seconds per video
- Timestamps are in MM:SS format
