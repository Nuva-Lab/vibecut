---
name: transcribe-audio
description: ASR with ~30ms timestamp precision using Qwen3-ASR + ForcedAligner
---

# transcribe-audio

Transcribe audio/video files with precise timestamps using Qwen3-ASR and Qwen3-ForcedAligner.
Runs on CPU for maximum quality.

## Models

| Model | Purpose | Precision |
|-------|---------|-----------|
| **Qwen3-ASR-1.7B** | Speech recognition (52 languages) | SOTA accuracy |
| **Qwen3-ForcedAligner-0.6B** | Timestamp alignment | ~30ms |

## Usage

```bash
# Full transcription with timestamps (default)
python skills/transcribe-audio/transcribe.py audio.wav

# Save to file
python skills/transcribe-audio/transcribe.py audio.wav --output captions.json

# Specify language (auto-detects if not specified)
python skills/transcribe-audio/transcribe.py audio.wav --language Chinese

# Fast mode (no timestamps)
python skills/transcribe-audio/transcribe.py audio.wav --no-timestamps

# Align existing text to audio (ForcedAligner only)
python skills/transcribe-audio/transcribe.py audio.wav --align-text "Your transcript text here"
```

## Output Format

Compatible with Remotion captions.json:

```json
{
  "segments": [
    {"text": "当", "startMs": 0, "endMs": 150},
    {"text": "全", "startMs": 150, "endMs": 280},
    {"text": "世界", "startMs": 280, "endMs": 520},
    ...
  ],
  "full_text": "当全世界都在追AI的时候...",
  "language": "Chinese",
  "model": "Qwen3-ASR-1.7B",
  "aligner": "Qwen3-ForcedAligner-0.6B"
}
```

## Two Modes

### 1. Transcription Mode (default)
Transcribes audio and aligns timestamps:
```bash
python transcribe.py audio.wav
```

### 2. Alignment Mode
Use when you already have the transcript:
```bash
python transcribe.py audio.wav --align-text "已知的文字内容"
```
This skips ASR and uses ForcedAligner directly for ~30ms precision.

## Programmatic Usage

```python
from transcribe import transcribe_audio, transcribe_and_align

# Full transcription with timestamps
result = transcribe_audio("audio.wav", language="Chinese")
print(result["segments"])  # Word-level timestamps

# Align existing text
result = transcribe_and_align("audio.wav", text="已知的文字", language="Chinese")
print(result["segments"])  # ~30ms precision timestamps
```

## Notes

- First run downloads model weights (~3GB for ASR, ~1GB for Aligner)
- Runs on CPU by default (quality first)
- Supports 52 languages including Chinese dialects
- ForcedAligner achieves ~30ms average absolute shift (SOTA)
- For best results, use WAV or high-quality audio
