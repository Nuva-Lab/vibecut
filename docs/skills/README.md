# Skills Reference

vibecut is built on modular "skills" - each handles a specific task
in the video production pipeline.

## Core Skills

### Video Analysis

| Skill | Purpose | API Required |
|-------|---------|--------------|
| [analyze-video](../../skills/analyze-video/SKILL.md) | AI video understanding | Google AI |
| [find-golden-segments](../../skills/find-golden-segments/SKILL.md) | Find clip-worthy moments | Google AI |
| [inspect-video](../../skills/inspect-video/SKILL.md) | Quality verification | Google AI |

### Video Processing

| Skill | Purpose | API Required |
|-------|---------|--------------|
| [extract-clip](../../skills/extract-clip/SKILL.md) | FFmpeg segment cutting | None |
| [validate-media](../../skills/validate-media/SKILL.md) | Pre-flight media checks | None |

### Audio & Voice

| Skill | Purpose | API Required |
|-------|---------|--------------|
| [voice-clone](../../skills/voice-clone/SKILL.md) | Clone voice + generate speech | fal.ai |
| [audio-process](../../skills/audio-process/SKILL.md) | Audio enhancement | fal.ai |
| [transcribe-audio](../../skills/transcribe-audio/SKILL.md) | Speech recognition | None (local) |
| [align-captions](../../skills/align-captions/SKILL.md) | Karaoke caption timing | None (local) |

### Content Generation

| Skill | Purpose | API Required |
|-------|---------|--------------|
| [write-script](../../skills/write-script/SKILL.md) | Generate voiceover scripts | None (uses Claude) |

### Rendering

| Skill | Purpose | API Required |
|-------|---------|--------------|
| [make-video](../../skills/make-video/SKILL.md) | Full production pipeline | Varies |
| [remotion-render](../../skills/remotion-render/SKILL.md) | Motion graphics + captions | None |

## Skill Architecture

Each skill follows a consistent structure:

```
skills/my-skill/
├── SKILL.md          # Documentation
├── my_skill.py       # Main implementation
└── requirements.txt  # Additional dependencies (optional)
```

## Using Skills

### From Command Line

```bash
python skills/analyze-video/analyze.py /path/to/video.mp4
```

### From Python

```python
from skills.analyze_video.analyze import analyze_video
result = analyze_video("/path/to/video.mp4")
```

### With Claude Code

Ask Claude to use skills directly:

> "Analyze this video and find the best clips"
> "Write a script for the moment at 2:30"
> "Generate a video with karaoke captions"

## Creating New Skills

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines on creating new skills.
