# Getting Started

## Install

```bash
git clone https://github.com/yourusername/vibecut.git
cd vibecut

# With uv (recommended)
uv sync --extra all

# Or pip
pip install -e ".[all]"
```

## Configure

```bash
cp .env.example .env
# Add your API keys
```

## First Video

```bash
# Find good moments in a video
python skills/find-golden-segments/find_golden.py /path/to/video.mp4

# Create a project
python scripts/new_project.py my_video --template commentary

# Copy your source video
cp /path/to/video.mp4 projects/my_video/source_video.mp4

# Edit projects/my_video/project.json with your script

# Generate
python skills/make-video/make_video.py projects/my_video/
```

## Just Need One Skill?

```bash
# Sparse checkout
git clone --filter=blob:none --sparse https://github.com/user/vibecut.git
cd vibecut
git sparse-checkout add skills/voice-clone skills/shared
```

## Templates

- `commentary` - Voiceover + karaoke captions
- `highlights` - Auto-selected golden moments
- `raw-clip` - Simple extraction

```bash
python scripts/new_project.py --list
```
