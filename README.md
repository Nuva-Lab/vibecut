# vibecut

> AI-powered video clip production using agent skills

Turn raw video footage into polished short-form content with AI-driven analysis,
voice cloning, karaoke captions, and motion graphics.

## Quick Start

```bash
# Clone
git clone https://github.com/yourusername/vibecut.git
cd vibecut

# Setup with uv (recommended)
uv sync
uv sync --extra all  # optional: install all features

# Or with pip
pip install -e ".[all]"

# Configure API keys
cp .env.example .env
# Edit .env with your keys
```

**Prerequisites**: Python 3.11+, Node.js 18+, FFmpeg

## Using Individual Skills

Don't need the full repo? Download just the skills you want:

```bash
# Download a single skill
curl -L https://github.com/user/vibecut/archive/main.tar.gz | \
  tar -xz --strip=2 vibecut-main/skills/voice-clone

# Or clone with sparse checkout
git clone --filter=blob:none --sparse https://github.com/user/vibecut.git
cd vibecut
git sparse-checkout add skills/voice-clone skills/shared
```

Each skill is self-contained with its own `SKILL.md` documentation.

## Skills

| Skill | What it does | Needs |
|-------|--------------|-------|
| `analyze-video` | AI video understanding | Google AI |
| `find-golden-segments` | Find clip-worthy moments | Google AI |
| `extract-clip` | FFmpeg cutting | - |
| `voice-clone` | Clone voice + TTS | fal.ai |
| `align-captions` | Karaoke timestamps | - |
| `make-video` | Full pipeline | varies |
| `remotion-render` | Motion graphics | Node.js |

## API Keys

| Service | Variable | Get it |
|---------|----------|--------|
| Google AI | `GOOGLE_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| fal.ai | `FAL_KEY` | [fal.ai/dashboard](https://fal.ai/dashboard/keys) |

## Create a Video

```bash
# 1. Find good moments
python skills/find-golden-segments/find_golden.py video.mp4

# 2. Create project
python scripts/new_project.py my_video

# 3. Add source video + edit project.json

# 4. Generate
python skills/make-video/make_video.py projects/my_video/
```

## Project Config

```json
{
  "name": "my_video",
  "source_video": "source.mp4",
  "script": "Your voiceover...",
  "titleCard": {"title": "Title", "subtitle": "Hook"},
  "audio": {"original_volume": 0.02, "voiceover_volume": 1.0}
}
```

## Contributing Skills

Skills are folders in `skills/` with:
- `SKILL.md` - Documentation (required)
- `*.py` - Implementation
- `requirements.txt` - Extra deps (optional)

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0
