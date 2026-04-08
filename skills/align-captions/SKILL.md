---
name: align-captions
description: >
  Generate karaoke-style word-level timestamps by aligning script text to audio
  using Qwen3-ForcedAligner + jieba for Chinese word segmentation.
  Use when the user says 'align captions', 'karaoke timestamps', 'word timestamps',
  'caption alignment', 'sync text to audio'.
---

# align-captions

Align existing script text to audio for karaoke-style captions. Uses Qwen3-ForcedAligner-0.6B (~30ms precision) and jieba for Chinese word segmentation (groups characters into natural words).

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
      "text": "当全世界...",
      "startMs": 240, "endMs": 2080,
      "words": [
        {"text": "当", "startMs": 240, "endMs": 400},
        {"text": "全世界", "startMs": 400, "endMs": 880}
      ]
    }
  ],
  "word_segments": [...],
  "language": "Chinese",
  "model": "Qwen3-ForcedAligner-0.6B"
}
```

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

## Error Recovery

- **Audio file not found**: Verify the path exists before calling. The script will raise `FileNotFoundError` -- check `project.json` for the correct voiceover path.
- **Model download fails**: Qwen3-ForcedAligner (~1GB) downloads on first run. If it fails (network/disk), retry or manually download to the HuggingFace cache (`~/.cache/huggingface/`).
- **jieba not installed**: Run `pip install jieba`. Without it, Chinese text falls back to character-level timestamps (no word grouping).

## Notes

- Supports 11 languages: Chinese, English, Cantonese, French, German, Italian, Japanese, Korean, Portuguese, Russian, Spanish
