---
name: audio-process
description: Audio processing utilities - noise reduction, normalization, enhancement
---

# Audio Process Skill

Audio processing utilities for cleaning and enhancing voice recordings.

## Usage

```bash
# Remove background noise
python skills/audio-process/denoise.py input.wav output.wav

# Normalize audio levels
python skills/audio-process/normalize.py input.wav output.wav

# Full voice cleanup pipeline (denoise + normalize + enhance)
python skills/audio-process/clean_voice.py input.wav output.wav
```

## Available Operations

| Operation | Description | Use Case |
|-----------|-------------|----------|
| `denoise` | Remove background noise | Voice cloning prep |
| `normalize` | Normalize audio levels | Consistent volume |
| `clean_voice` | Full cleanup pipeline | Best for voice samples |

## Notes

- Uses FFmpeg's `afftdn` and `anlmdn` filters
- Optimized for speech/voice content
- Preserves voice characteristics while removing noise
