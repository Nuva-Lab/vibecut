# Validate Media Skill

Pre-flight media validation and diagnostics using ffprobe.

## Purpose

Check video/audio files for common issues before rendering:
- Duration mismatches between video and audio tracks
- Missing audio tracks
- Codec compatibility
- Volume levels
- Potential freeze points

## Usage

```bash
python skills/validate-media/validate.py <video_file> [--verbose]
```

## Output

JSON report with issues and recommendations:

```json
{
  "file": "video.mp4",
  "video_duration": 35.14,
  "audio_duration": 37.07,
  "has_audio": true,
  "video_codec": "h264",
  "audio_codec": "aac",
  "resolution": [1920, 1080],
  "fps": 30,
  "issues": [
    "Video track shorter than audio by 1.93s"
  ],
  "recommendations": [
    "Use loop=true in Remotion to handle shorter video"
  ]
}
```

## Integration

Call before `make-video` to catch issues early:

```python
from skills.validate_media.validate import validate_media

result = validate_media("video.mp4")
if result["issues"]:
    print("Warning:", result["issues"])
```

## Common Issues Detected

| Issue | Cause | Fix |
|-------|-------|-----|
| Video shorter than audio | Mismatched source files | Loop video or trim audio |
| No audio track | Video-only file | Add audio track or use silent |
| Low audio volume | Quiet recording | Normalize audio |
| Unsupported codec | HEVC/ProRes | Convert to H.264 |
