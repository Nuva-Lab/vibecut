---
name: align-captions
description: Align script text to audio with karaoke-style word timestamps using Qwen3-ForcedAligner + jieba
---

# align-captions

Align existing script text to audio for karaoke-style captions. Uses Qwen3-ForcedAligner-0.6B for ~30ms timestamp precision and jieba for proper Chinese word segmentation.

## Pipeline

```
Script + Audio
    ↓
Qwen3-ForcedAligner (character-level timestamps)
    ↓
Jieba word segmentation (characters → Chinese words)
    ↓
Position-based phrase matching (words → phrases)
    ↓
Output: phrases with embedded word timestamps
```

## Usage

```bash
# Align script to audio (phrase-level output with word timestamps)
python skills/align-captions/align.py voiceover.wav --script "当全世界都在追AI的时候..."

# Save to file
python skills/align-captions/align.py voiceover.wav --script "..." --output captions.json

# Word-level only (no phrase grouping)
python skills/align-captions/align.py voiceover.wav --script "..." --word-level
```

## Output Format

Designed for Remotion karaoke rendering:

```json
{
  "segments": [
    {
      "text": "当全世界都在追AI的时候，",
      "startMs": 240,
      "endMs": 2080,
      "words": [
        {"text": "当", "startMs": 240, "endMs": 400},
        {"text": "全世界", "startMs": 400, "endMs": 880},
        {"text": "都", "startMs": 880, "endMs": 960},
        {"text": "在", "startMs": 960, "endMs": 1120},
        {"text": "追", "startMs": 1120, "endMs": 1280},
        {"text": "AI", "startMs": 1280, "endMs": 1600},
        {"text": "的", "startMs": 1600, "endMs": 1680},
        {"text": "时候", "startMs": 1680, "endMs": 2080}
      ]
    }
  ],
  "word_segments": [...],  // All words flat
  "language": "Chinese",
  "model": "Qwen3-ForcedAligner-0.6B"
}
```

## Key Feature: Chinese Word Segmentation

Uses jieba to group characters into proper Chinese words:

| Without jieba | With jieba |
|---------------|------------|
| 当-全-世-界 | 当-全世界 |
| (too fast) | (natural pace) |

This is critical for karaoke-style captions to feel natural.

## Programmatic Usage

```python
from align import align_captions

# Get phrases with embedded word timestamps
result = align_captions(
    "voiceover.wav",
    script="当全世界都在追AI的时候...",
    language="Chinese"
)

# Each phrase has a 'words' array for karaoke highlighting
for phrase in result["segments"]:
    print(f"{phrase['text']}: {len(phrase['words'])} words")
```

## Integration with make-video

The `make_video.py` script automatically uses align-captions when:
1. A voiceover file exists
2. A script is provided in project.json
3. `caption_mode` is "auto" or "asr"

The output is passed to Remotion's `RollingCaption` component for karaoke rendering.

## Notes

- First run downloads Qwen3-ForcedAligner (~1GB)
- Runs on CPU by default (quality first)
- ~30ms timestamp precision (SOTA)
- Supports 11 languages for alignment: Chinese, English, Cantonese, French, German, Italian, Japanese, Korean, Portuguese, Russian, Spanish
- Chinese word segmentation uses jieba (must be installed)
