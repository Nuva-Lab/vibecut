# Make Video Skill

Single-script video production from project config.

## Usage

```bash
python skills/make-video/make_video.py video_projects/space_investing/
```

That's it. One command, one output.

## Project Structure

```
video_projects/<name>/
├── project.json      # Config (required)
├── source_video.mp4  # Input video (required)
├── voiceover.wav     # Audio (optional, uses video audio if missing)
└── output/
    └── final.mp4     # Generated output
```

## project.json

```json
{
  "name": "project_name",
  "script": "Chinese voiceover script...",
  "context": {"location": "USA House", "event": "Davos 2026"},
  "speakers": [],
  "output": {"format": "16:9", "resolution": [1920, 1080], "fps": 30}
}
```

## What It Does

1. Reads project.json
2. Generates timed captions from script
3. Prepares Remotion composition
4. Renders to output/final.mp4

No prompts. No interaction. Just runs.
