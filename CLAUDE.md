# Project
This is the vibecut. It's like claude code vibe coding verison of capcut that helps you to make video clips from raw video assets.

Fully agentic driven by LLM agent brain, a set of atomic skills following claude's best practice of agents, orchestrate all the skills for various intent of video cliping and production tasks.

# Why
Capcut sucks and I paid for it three times in a row in the last ~3 months for simple features:
1) I used the rolling caption feature just to realize it locks you at export unless you subscribe
2) I tried to buy 3 seats for my team just to find out you can either buy 2 or 5 seats
3) Then it just bumped its price by 2x+ for no reason.

So I decided to build an open source alternative. Who says video editing has to use hands? 
Multi-modality models can be used as brain and eyes, agents with programmatic access can act as hands, so you can just chill as the creative director.

## Context
This is a media project using claude code + skills to automatically make short videos from a library of raw video assets.
We will also need to clone the voice of the social media account owner with her various audio clips as if commenting on the clips from 3rd person view, given she attended the event. We will provide clips of her voice for cloning in a folder but likely we need some trial and error to find out which clip is the best for qwen3-tts voice cloning, and use background noise removal / speaker enhancement / emotion, or even rely on gemini-3-pro a bit for full loop verification for speaker similarity and "non-robotic" tone.

All videos are raw recording from Davos 2026 with notable speakers and panel discussions.

They vary in size from 77MB to 5.4GB. I have access to the google drive folder that we have access to which is https://drive.google.com/drive/u/0/folders/1qnrn8eQiHntdiqcADHtwDyGKc_XQ2aVA in case we can just pass video urls to avoid encoding and sending the entire video. One key challenge could be how to best leverage gemini-3-pro for video understanding without requiring to encode entire video or lose precision and accuracy by splitting into too many smaller clips when we don't need to. I have google ai api keys written in .env file in current directory.

`./joyce_original_edit_example.mov` is the example of the production from the raw assets after a whole day of editing that we're trying to use agentic flow to automate better and create new videos from the pool of raw video footage.

# Model & Essential Tools 
- For agentic orchestration, we can use our local claude code with opus 4.5.
- For multi-modality understanding, definitely use gemini-3-pro that supports text/image/audio/video inputs. 
It also supports passing in url for large video file https://ai.google.dev/gemini-api/docs/video-understanding
- For manupulating video files and clips, ffmpeg is super handy.
- For generation motion graphics, captions, remotion is the way to go: https://github.com/remotion-dev/remotion
- There're many other community resources of doing similar stuff such as https://x.com/chengfeng240928/status/2011613934114030008 that you should read, which links to github repo of https://github.com/Ceeon/videocut-skills 
- For voice cloning, use qwen3-tts that's hosted on https://fal.ai/models/fal-ai/qwen-3-tts/clone-voice/1.7b/api, we have API key stored in .env, and i will provide the files.
- We can use opus 4.5 in claude code now for scripting writing for the video clip commentary.
- You might also need some captioning tools / models given that gemini-3-pro likely cannot give precise timestamp to 0.00 two decimal points, but latest qwen3-asr and qwen3-forcedaligner should help for exactly this, for both parsing, verification and visual-audio alignment.
- Always welcomed to come up with more tools for the task as long as we're full aware being agentic and add new atomic & agentic skills for each task involved.

# Project Plan

## Architecture
```
skills/
├── analyze-video/         # Gemini: content understanding, speaker ID
├── find-golden-segments/  # Gemini: find naturally clean, clip-worthy moments
├── extract-clip/          # FFmpeg: video cutting
├── transcribe-audio/      # Qwen3-ASR: speech → text with timestamps
├── align-captions/        # Qwen3-ForcedAligner + jieba: karaoke captions
├── separate-audio/        # SAM-Audio (mlx-audio): source separation
├── write-script/          # Opus 4.5: generate voiceover scripts
├── audio-process/         # fal.ai DeepFilterNet3: audio enhancement
├── voice-clone/           # fal.ai Qwen3-TTS: voice cloning + speech
├── make-video/            # Orchestrator: full video production pipeline
├── remotion-render/       # Remotion: motion graphics + captions
│   ├── src/VideoClip.tsx  # Main composition
│   └── src/components/    # RollingCaption (karaoke), SpeakerLabel, etc.
├── validate-media/        # ffprobe: pre-flight media validation
├── inspect-video/         # Gemini: quality inspection & verification
└── shared/                # gemini_client.py, common utilities

raw_assets/                # Shared raw footage (H.264 converted)
video_projects/<name>/     # Self-contained project folders
    ├── project.json       # Config: script, speakers, audio levels
    ├── source_video.mp4   # Input video
    ├── voiceover.wav      # Generated voiceover
    ├── captions.json      # Phrase + word-level timestamps
    └── output/final.mp4   # Rendered output
```

## Workflow
```
Raw Video (4K HEVC MOV)
    ↓ ffmpeg convert
1080p H.264 (raw_assets/)
    ↓ find-golden-segments
Golden Segments JSON
    ↓ [human review]
project.json (script, speakers, config)
    ↓ voice-clone/speak
voiceover.wav
    ↓ align-captions (Qwen3-ForcedAligner + jieba)
captions.json (phrases + words with timestamps)
    ↓ make-video (Remotion)
final.mp4 (karaoke captions, speaker labels, motion graphics)
    ↓ inspect-video (Gemini verification)
✓ Quality verified
```

## Milestones
- [x] Phase 1: Foundation - Skills structure + Gemini integration
- [x] Phase 2: Minimal Pipeline - Extract + transcribe + caption with FFmpeg
- [x] Phase 3: Golden Segments - Selection over repair approach
- [x] Phase 4: Script Writing - Joyce's voiceover style guide
- [x] Phase 5: Voice Cloning - qwen3-tts + DeepFilterNet3 enhancement
- [x] Phase 6: Remotion Integration - Karaoke captions + motion graphics
- [x] Phase 7: Advanced Audio - mlx-audio ASR + SAM-Audio separation
- [ ] Phase 8: Speaker Detection - Gemini bounding boxes for annotations
- [ ] Phase 9: Vertical Format - 9:16 cropping for TikTok/Reels

## Clip Criteria (all valued)
- Notable quotes from speakers
- Visual highlights (gestures, reveals)
- Panel exchanges
- Audience reactions

## Output Formats
- Vertical (9:16) for TikTok/Reels/Shorts
- Horizontal (16:9) for YouTube/LinkedIn

# Work Log

## 2025-01-28: Phase 1 Complete
- Created skills folder structure
- Built `skills/shared/gemini_client.py` (Gemini 3 Pro integration)
- Built `skills/analyze-video/` skill with SKILL.md + analyze.py
- Tested on 77MB sample video - successfully identified:
  - 2 speakers (Jihan Wu, Moderator)
  - 9 topics
  - 4 notable quotes with timestamps
  - 5 clip opportunities scored 7-10/10
- Output: `assets/outputs/analysis/*.json`

## 2025-01-28: Phase 2 Complete
- Built initial skills for video clip production:
  - `extract-clip/` - FFmpeg segment cutting with precise timestamps
  - `transcribe-clip/` - Gemini segment-level transcription
- Tested on clip 01:48-02:25 (Jihan Wu on Bitcoin mining paying for AI CapEx)
- Note: FFmpeg caption burning later replaced by Remotion in Phase 6

## 2025-01-28: Phase 3 - Golden Segments
- Learned: "repair mode" (cut every filler) creates jarring micro-cuts
- New approach: "selection mode" - find naturally clean moments
- Built `find-golden-segments/` skill:
  - Scans video for 10-30s continuous clean segments
  - Scores by quality (7+ threshold)
  - Skips problematic sections entirely
- **Key insight**: 4K HEVC MOV files must be converted to 1080p H.264 for Gemini
- Tested on IMG_2664 (space investing panel) - found 3 golden segments (44s total from 167s video)

## 2025-01-28: Phase 4 - Script Writing
- Analyzed `joyce_original_edit_example.mov` to understand her style:
  - 100% voiceover (no original speaker audio)
  - Structure: Hook → Context → Insight → Analysis → Pivot
  - Clout-first intros ("Ex-Google CEO Eric Schmidt...")
  - Contrarian framing, synthesis over reporting
- Built `write-script/` skill with `style_guide.md`
- Generated test script for space investing golden segments

## 2025-01-28: Phase 5 - Voice Cloning
- Built `audio-process/enhance.py` - AI enhancement via fal.ai DeepFilterNet3
- Built `voice-clone/clone.py` and `speak.py` - qwen3-tts via fal.ai
- Best voice sample: 45s segment (02:22-03:07) with varied emotions
- Pipeline: Extract audio → AI enhance → Clone → TTS
- **Best embedding**: `assets/outputs/voice_embeddings/joyce_sample_long_enhanced_embedding.safetensors`
- Successfully generated Chinese voiceover matching Joyce's voice

## 2025-01-28: Phase 6 - Remotion Integration
- Installed Remotion best practices via `npx skills add remotion-dev/skills` → `.agents/skills/`
- Built `skills/remotion-render/` - Generic Remotion rendering engine
  - `VideoClip.tsx` - Composition driven by props (project-agnostic)
  - `RollingCaption.tsx` - Karaoke-style word highlighting
  - `SpeakerLabel.tsx` - Speaker annotations with positioning
  - `ContextBadge.tsx` - Location/event badge
- Built `skills/make-video/` - Orchestrates full video production pipeline
- Organized `video_projects/` - Self-contained project folders
- Organized `raw_assets/` - Shared source footage (H.264 converted)
- **First video**: `video_projects/space_investing/output/final.mp4`
  - 37s, 1920x1080, karaoke captions, Joyce's voiceover
- Uses `OffthreadVideo` for memory-efficient rendering
- System fonts (PingFang SC) for Chinese text

## 2025-01-28: Phase 6.1 - Quality Fixes & Diagnostics
- **Issue**: Captions were character-by-character (too distracting)
  - **Fix**: Changed to phrase-by-phrase display
- **Issue**: Original speaker audio not audible
  - **Root cause**: `OffthreadVideo` only renders video frames, no audio
  - **Fix**: Added `<Audio>` component alongside `OffthreadVideo`
- **Issue**: Video freezes at end
  - **Root cause**: Source video (35.14s) shorter than voiceover (37.07s)
  - **Fix**: Added `loop` prop to video component
- **New skills**:
  - `validate-media/` - Pre-flight media validation using ffprobe
  - `inspect-video/` - Gemini-powered quality inspection
- **Key learnings documented** (see Remotion Learnings below)

## 2025-01-29: Phase 7 - Advanced Audio & Karaoke Captions
- **Context**: Qwen3-ASR released with SOTA accuracy + ForcedAligner (~30ms precision)
- **Solution**: Use qwen-asr package on CPU (quality first, works on Mac M2)
- **New skills**:
  - `transcribe-audio/` - Qwen3-ASR-1.7B for speech recognition
  - `separate-audio/` - SAM-Audio via mlx-audio for source separation
  - `align-captions/` - Qwen3-ForcedAligner + jieba for karaoke captions
- **Karaoke caption pipeline** (the key breakthrough):
  1. Voiceover audio → Qwen3-ForcedAligner → character-level timestamps
  2. Character timestamps → jieba segmentation → Chinese word-level timestamps
  3. Words grouped into phrases → Remotion renders with gold word highlighting
- **Debugging journey**:
  - Initial: Captions lagged voice by ~300ms (animation too slow)
  - Fix: Reduced spring animation from 10 frames to 2 frames (66ms)
  - Issue: Last 1-2 sentences missing captions
  - Root cause: Phrase-word matching algorithm was sequential, got misaligned
  - Fix: Position-based text matching instead of sequential accumulation
- **Final result**: Perfect karaoke-style captions with word-by-word gold highlighting

## 2025-01-29: Second Video + Pipeline Improvements
- **New video**: `video_projects/space_future/` - Dylan Taylor's "baby vs combat death" thought experiment
- **TTS improvements**:
  - Fixed `max_new_tokens: 8192` in speak.py (was defaulting to 200, limiting audio to ~16s)
  - Added `--style` parameter for pacing control (e.g., "Thoughtful, contemplative")
- **Title card**: Added opening animation with title/subtitle as default for commentary videos
- **Bug fixes**:
  - Fixed `context_badge` field name mismatch in make_video.py
  - Fixed RollingCaption interpolation error when word timestamps are identical
- **Final output**: 31s video with title card, karaoke captions, original audio audible in background

# Caption Pipeline (Karaoke Style)

The complete pipeline for perfectly synced karaoke captions:

```
Voiceover.wav
    ↓
Qwen3-ForcedAligner-0.6B (character timestamps, ~30ms precision)
    ↓
Jieba Chinese word segmentation (characters → proper words)
    ↓
Position-based phrase-word matching (words → phrases)
    ↓
Remotion RollingCaption (gold highlight on current word)
```

**Key insight**: For Chinese, must use jieba to group characters into words.
- Wrong: 当-全-世-界 (character by character - too fast)
- Right: 当-全世界-都-在 (word by word - natural reading pace)

**Phrase-word alignment algorithm**:
```python
# Build position map: where each word appears in clean text
all_words_text = "".join(w["text"] for w in word_segments)
# For each phrase, find overlapping words by position
# NOT by sequential accumulation (causes drift)
```

# Qwen3 Models Reference

| Model | Size | Purpose | Runs on |
|-------|------|---------|---------|
| **Qwen3-ASR-1.7B** | 2B params | SOTA speech recognition (52 languages) | CPU/CUDA |
| **Qwen3-ForcedAligner-0.6B** | 0.9B params | Timestamp alignment (~30ms) | CPU/CUDA |
| **Qwen3-TTS-1.7B** | 1.7B params | Voice cloning + TTS | fal.ai API |

**Installation**:
```bash
conda activate nuva
pip install qwen-asr jieba
```

**Usage patterns**:
```python
# Transcribe unknown audio
from transcribe import transcribe_audio
result = transcribe_audio("audio.wav", return_timestamps=True, device="cpu")

# Align known script to audio (best for voiceover - faster)
from align import align_captions
result = align_captions("voiceover.wav", script="Chinese text...", language="Chinese")
# Returns: segments (phrases), word_segments (for karaoke)
```

**Caption mode in project.json**:
```json
"caption_mode": "auto"  // auto (ASR if voiceover exists), asr, character
```

# Remotion Learnings

Critical patterns discovered while building the video pipeline:

| Component | Gotcha | Solution |
|-----------|--------|----------|
| `OffthreadVideo` | Only renders video frames, NO audio | Add separate `<Audio>` component |
| `<Video>` | Includes audio but uses more memory | Use for shorter clips |
| Video duration | Must be >= composition duration | Use `loop` prop or validate beforehand |
| Bundler | Doesn't follow symlinks | Copy files to public/ instead |
| Fonts | Google Fonts can fail for CJK | Use system fonts (PingFang SC) |
| Source files | Don't overwrite source with rendered output! | Keep raw sources in raw_assets/, extract fresh clips |
| Caption animation | Slow spring (10 frames) causes perceived lag | Use fast spring (2 frames = 66ms) |
| Caption sync | Raw timestamps may feel early/late | Test and tune, animation speed matters |

**Audio pattern for video with sound**:
```tsx
<OffthreadVideo src={source} loop style={{...}} />
<Audio src={source} volume={0.02} />  // Background at 2% for ambient context
```

**Optimal audio mix for voiceover content**:
```json
"audio": {
  "original_volume": 0.02,  // Very low - just for ambient presence
  "voiceover_volume": 1.0   // Full volume for clarity
}
```

**Karaoke caption animation** (RollingCaption.tsx):
```tsx
// Fast entrance - 2 frames (66ms) to avoid perceived lag
const enterProgress = spring({
  fps, frame,
  config: {damping: 100, stiffness: 500},
  durationInFrames: 2,
});

// Word highlighting - gold on current word
const isActive = currentMs >= word.startMs && currentMs <= word.endMs;
<span style={{color: isActive ? '#FFD700' : '#FFFFFF'}}>
  {word.text}
</span>
```

**Pre-flight validation** before render:
```bash
python skills/validate-media/validate.py source_video.mp4
```

# Quick Reference

## Key Commands
```bash
# === Video Preparation ===
# Convert 4K MOV to H.264 for processing
ffmpeg -i input.MOV -c:v libx264 -preset fast -crf 23 -vf "scale=1920:1080" -c:a aac raw_assets/output.mp4

# Find golden segments (clean, clip-worthy moments)
python skills/find-golden-segments/find_golden.py raw_assets/video.mp4

# === Audio Processing ===
# Transcribe audio (when you don't have the script)
python skills/transcribe-audio/transcribe.py audio.wav --output transcript.json

# Align script to audio (for karaoke captions - preferred)
python skills/align-captions/align.py voiceover.wav --script "Chinese text..." --output captions.json

# Separate audio sources
python skills/separate-audio/separate.py panel.wav --prompt "man speaking" --output speaker.wav

# Generate speech with cloned voice
python skills/voice-clone/speak.py embedding.safetensors "Chinese text" output.wav

# === Video Production ===
# Make video (one command - runs full pipeline)
python skills/make-video/make_video.py video_projects/<project_name>/

# === Quality Assurance ===
# Validate media before rendering
python skills/validate-media/validate.py video.mp4 --verbose

# Inspect rendered video with Gemini
python skills/inspect-video/inspect_video.py output.mp4 --prompt "Check caption sync..."
```

## Project.json Template (Commentary Video)

All commentary videos should include a title card by default:

```json
{
  "name": "project_name",
  "source_video": "source_video.mp4",
  "titleCard": {
    "title": "主标题",
    "subtitle": "副标题或问题",
    "durationMs": 3000
  },
  "script": "Chinese voiceover script...",
  "speakers": [
    {"name": "Speaker Name", "title": "Role", "box2d": [300, 400], "showFromMs": 0, "showUntilMs": 5000}
  ],
  "context_badge": {
    "location": "Davos 2026",
    "event": "Event Name"
  },
  "audio": {
    "original_volume": 0.02,
    "voiceover_volume": 1.0
  },
  "voice_embedding": "assets/outputs/voice_embeddings/joyce_sample_long_enhanced_embedding.safetensors",
  "caption_mode": "auto"
}
```

## TTS Speech Style

Use `--style` parameter for pacing control:
```bash
# Slow, contemplative ending
python skills/voice-clone/speak.py embedding.safetensors "Text..." output.wav --style "Thoughtful, contemplative, slow paced."

# Energetic hook
python skills/voice-clone/speak.py embedding.safetensors "Text..." output.wav --style "Excited and energetic."
```

**Important**: Add `max_new_tokens: 8192` in speak.py to allow >16 second audio generation.

## Key Assets
- **Voice embedding**: `assets/outputs/voice_embeddings/joyce_sample_long_enhanced_embedding.safetensors`
- **Raw footage**: `raw_assets/*.mp4` (H.264 converted)
- **Video projects**: `video_projects/<name>/`
- **Example outputs**:
  - `video_projects/space_investing/output/final.mp4`
  - `video_projects/space_future/output/final.mp4`

## Environment
```bash
conda activate nuva  # Python 3.11 with all dependencies
```

# References

## Models Used
| Model | Provider | Purpose |
|-------|----------|---------|
| Qwen3-ASR-1.7B | HuggingFace | Speech recognition |
| Qwen3-ForcedAligner-0.6B | HuggingFace | Timestamp alignment |
| Qwen3-TTS-1.7B | fal.ai | Voice cloning + TTS |
| Gemini 3 Pro | Google | Video understanding |
| SAM-Audio | mlx-audio | Source separation |
| DeepFilterNet3 | fal.ai | Audio enhancement |

## Documentation
- Anthropic agents: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Qwen3-ASR: https://github.com/QwenLM/Qwen3-ASR
- Gemini video: https://ai.google.dev/gemini-api/docs/video-understanding
- Remotion: https://www.remotion.dev/docs
- mlx-audio: https://github.com/Blaizzy/mlx-audio


