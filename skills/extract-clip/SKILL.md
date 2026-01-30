---
name: extract-clip
description: Extract a video segment using FFmpeg with precise start/end times
---

# Extract Clip Skill

Use this skill to cut a segment from a longer video file.

## Usage

```bash
python skills/extract-clip/extract.py <input_video> <start_time> <end_time> [output_path]

# Examples
python skills/extract-clip/extract.py video.mp4 01:48 02:25
python skills/extract-clip/extract.py video.mp4 00:30 01:00 output/my_clip.mp4
```

## Arguments

- `input_video`: Path to source video
- `start_time`: Start timestamp (MM:SS or HH:MM:SS)
- `end_time`: End timestamp (MM:SS or HH:MM:SS)
- `output_path`: (optional) Output file path, defaults to `assets/outputs/clips/<name>_<start>-<end>.mp4`

## Output

Creates an MP4 file with the extracted segment. Uses stream copy when possible for fast extraction.
