---
name: separate-audio
description: Text-guided audio source separation using SAM-Audio via mlx-audio
---

# separate-audio

Isolate specific sounds from audio using natural language text prompts. Uses Meta's SAM-Audio model via mlx-audio for native Mac M2/M3 inference.

## Capabilities

- **Text prompts**: Describe what to extract ("man speaking", "piano", "applause")
- **Time span hints**: Specify when target sound occurs for better isolation
- **Source separation**: Get both the target sound and the residual (everything else)

## Usage

```bash
# Extract speaker by description
python skills/separate-audio/separate.py panel.wav --prompt "man speaking" --output speaker.wav

# Extract with time hint
python skills/separate-audio/separate.py video.mp4 --prompt "applause" --span 10.5-12.0

# Save both target and residual
python skills/separate-audio/separate.py audio.wav --prompt "woman singing" --save-residual
```

## Use Cases for Video Production

| Use Case | Prompt Example |
|----------|----------------|
| Extract single speaker | "man speaking about investments" |
| Remove background music | Separate, keep residual |
| Isolate applause | "audience applause" |
| Clean panel discussion | Run multiple times with different prompts |

## Programmatic Usage

```python
from separate import separate_audio

result = separate_audio(
    audio_path="panel.wav",
    prompt="man speaking about space",
    output_path="speaker.wav",
    span=(10.5, 12.0),  # Optional time hint
)
print(result["target_path"])
```

## Notes

- Requires mlx-audio: `pip install mlx-audio`
- Runs natively on Mac M2/M3 via MLX framework
- First run downloads SAM-Audio model (~2GB)
- Works best with clear, specific descriptions
- Time spans help isolate sounds at specific moments

## Status

This skill is implemented but not extensively tested in the main video pipeline. The primary audio workflow uses Qwen3-ForcedAligner for caption alignment. SAM-Audio is available for advanced use cases like:
- Cleaning up panel discussion audio
- Extracting speaker voices for analysis
- Separating background noise from speech
