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
├── talking-head/          # Direct-to-camera video pipeline
│   ├── process_video.py   # Main pipeline orchestrator
│   ├── sentence_split.py  # Split at pauses, build sentence index
│   ├── analyze_script.py  # Text-first: Gemini reads transcript
│   ├── stitch_clips.py    # Concatenate approved clips
│   ├── lowres_convert.py  # Optional: video verification
│   └── batch_analyze.py   # Optional: video verification
├── chunk-process/         # Smart video chunking + transcription
│   ├── smart_chunk.py     # Split at natural pauses (2.5-3.5 min)
│   └── mlx_transcribe.py  # MLX Qwen3-ASR (--word-timestamps)
├── analyze-video/         # Gemini: content understanding, speaker ID
├── extract-clip/          # FFmpeg: video cutting
├── transcribe-audio/      # Qwen3-ASR: speech → text with timestamps
├── align-captions/        # Qwen3-ForcedAligner + jieba: karaoke captions
├── separate-audio/        # SAM-Audio (mlx-audio): source separation
├── write-script/          # Opus 4.5: generate voiceover scripts
├── audio-process/         # fal.ai DeepFilterNet3: audio enhancement
├── voice-clone/           # fal.ai Qwen3-TTS: voice cloning + speech
├── make-video/            # Orchestrator: full video production pipeline
├── remotion-render/       # Remotion: motion graphics + captions
├── validate-media/        # ffprobe: pre-flight media validation
├── inspect-video/         # Gemini: quality inspection & verification
└── shared/                # gemini_client.py (with multi-file upload)

raw_assets/                # Shared raw footage (H.264 converted)
video_projects/<name>/     # Self-contained project folders
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
- [x] Phase 8: Talking-Head Pipeline - MLX transcription + smart chunking + golden segments
- [x] Phase 8.5: V3 Pipeline - Sentence-level clipping + batch Gemini analysis
- [ ] Phase 9: Speaker Detection - Gemini bounding boxes for annotations
- [ ] Phase 10: Vertical Format - 9:16 cropping for TikTok/Reels

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

## 2025-01-30: Phase 8 - Talking-Head Pipeline
- **Problem**: Long talking-head videos (47+ min) too large for single Gemini upload
- **Solution**: Smart chunking + MLX transcription + interactive golden segment selection
- **New skills**:
  - `skills/chunk-process/smart_chunk.py` - Split at natural pauses (silence detection)
  - `skills/chunk-process/mlx_transcribe.py` - MLX Qwen3-ASR with auto language detection
  - `skills/talking-head/find_golden_segments.py` - Gemini finds clip-worthy moments
  - `skills/talking-head/process_video.py` - Full pipeline orchestrator
  - `skills/shared/gemini_client.py` - Added multi-file upload support
- **Key improvements**:
  - MLX-accelerated ASR (3-5x faster than CPU on Mac)
  - Auto language detection (Chinese/English/Mixed)
  - Smart chunking at 2.5-3.5 min boundaries (not mid-sentence)
  - Interactive golden segment review with Claude Code
- **Demo video**: `video_projects/fundraising_tips/output/final_clip.mp4` (86s from 47 min raw)
  - 3 golden segments stitched: Intro → VC Hypocrisy → Signaling Risk
  - Source: `raw_assets/fundraising_tips_raw.mp4`
- **Removed**: `skills/koubo-edit/` (replaced by `talking-head/`)

## 2025-01-30: Talking-Head Pipeline Rewrite (Text-First Analysis)
- **Problem**: Uploading video clips to Gemini was slow and expensive
- **Solution**: Text-first analysis with sentence-level precision
- **Key insight**: Send full transcript as text, map highlights to clips via sentence index
- **Architecture**:
  ```
  skills/talking-head/
  ├── process_video.py    # Main pipeline orchestrator
  ├── sentence_split.py   # Split at pauses >500ms, build sentence index
  ├── analyze_script.py   # Text-first: Gemini reads full transcript
  ├── stitch_clips.py     # Concatenate approved clips
  ├── lowres_convert.py   # Optional: video verification
  └── batch_analyze.py    # Optional: video verification
  ```
- **Benefits**:
  | Before | After |
  |--------|-------|
  | Upload 40+ video clips | Send full transcript as text |
  | Gemini sees chunks only | Gemini sees entire narrative |
  | ~30 min analysis | ~30 sec analysis |
- **Removed**: V1/V2 code, find_golden_segments.py, analyze_content.py, propose_narrative.py, verify_output.py
- **Usage**: `python skills/talking-head/process_video.py raw.mp4 -o project/`

## 2025-01-30: Recall-First Analysis + Precise Cuts
- **Problem 1**: Gemini's "5-10 highlight moments" approach missed context, topics were incomplete
- **Problem 2**: FFmpeg stream copy caused overlapping frames at clip boundaries (repeated words)
- **Problem 3**: 100ms padding caused overlap when consecutive clips had <200ms natural gap
- **Solution 1 - Recall-First Topics**:
  - Changed analyze_script.py prompt to find complete TOPICS with arcs (hook → elaborate → conclude)
  - Each topic includes: full clip range, essential clips, trimming guide, reorder suggestions
  - Optimize for recall first, then trim for precision
- **Solution 2 - Precise Cuts**:
  - sentence_split.py and stitch_clips.py now re-encode by default (not stream copy)
  - FFmpeg uses `-c:v libx264 -crf 18 -c:a aac` for frame-accurate cuts
  - Added `--fast` flag for stream copy when speed matters more than precision
- **Solution 3 - Zero Padding**:
  - Changed default `add_padding_ms` from 100 to 0
  - Qwen3-ForcedAligner timestamps are precise enough (~30ms)
  - Natural speech pauses exist between clips; padding causes overlap
  - Example: clip ends at 1958.59s, next starts at 1958.74s (0.15s gap)
    - With 100ms padding: end=1958.69s, start=1958.64s → 50ms OVERLAP!
    - With 0ms padding: no overlap, clips fit perfectly
- **Results**:
  - Topic 10 "VCs Are Hypocritical" found as complete 17-clip arc (176-192, ~177s)
  - Full topic has proper hook, elaboration, and conclusion
  - Zero repeated words at clip boundaries
- **Key learning**: Better to include extra content and trim than miss key context

## 2025-01-30: Precision Trimming Pipeline
- **Problem**: Raw topic video has fillers, stutters, repetitions that need surgical removal
- **Failed approach**: Use Gemini timestamps directly (~1s accuracy) → cuts words in half, jarring
- **Solution**: Two-stage precision trimming
  1. **MLX ASR + ForcedAligner**: Get word-level timestamps (~30ms precision)
  2. **Gemini**: Identify WHAT to cut by word index (semantic understanding)
  3. **Map**: Convert word indices to precise timestamps
  4. **FFmpeg filter_complex**: Cut exactly at word boundaries
- **New skill**: `skills/talking-head/precision_trim.py`
  ```bash
  # Full pipeline
  python precision_trim.py run video.mp4 -o output/

  # Step by step
  python precision_trim.py transcribe video.mp4 -o transcript.json
  python precision_trim.py identify video.mp4 transcript.json -o cuts.json
  python precision_trim.py apply video.mp4 cuts.json transcript.json -o trimmed.mp4
  ```
- **Micro-segment jitter fix**:
  - Problem: Cutting tiny fillers creates 0.3s segments → jittery playback
  - Solution: `min_keep_duration=1.0s` - drop segments shorter than 1s
  - Result: Smooth flow, all segments ≥1.2s
- **Results on Topic 10**:
  - Original: 177s → Recall clips: 175s → Precision trimmed: 144s (18% reduction)
  - Removed: Chinese practice talk, "uh/um/like" fillers, stutters, repetitions
  - Single speaker only (camera holder's voice removed)
- **Key insight**: Gemini for semantics (WHAT to cut), ASR for precision (WHERE to cut)

## 2025-01-31: Rolling Captions + Vertical Format + Cinematic Overlays
- **Problem**: Trimmed video needs captions + vertical (9:16) format for TikTok/Reels
- **Challenge**: Word timestamps are from ORIGINAL video, but trimmed video has different timing
- **Solution**: Timestamp remapping + Remotion multi-format rendering + Gemini section titles
- **New skills**:
  - `skills/talking-head/generate_captions.py` - Maps timestamps, groups words into phrases
  - `skills/talking-head/generate_sections.py` - Gemini generates meaningful section titles
  - `skills/talking-head/render_with_captions.py` - Renders both 16:9 and 9:16 with Remotion
- **Remotion components**:
  - `TalkingHeadClip.tsx` - Composition for talking-head videos
  - `SectionTitle.tsx` - Cinematic section titles with gradient text + animated lines
  - `SpeakerLabel.tsx` - Gradient border speaker card with slide-in animation
  - `RollingCaption.tsx` - Karaoke captions with gold word highlighting
- **Caption formatting**:
  | Aspect | Max Words | Max Chars | Reason |
  |--------|-----------|-----------|--------|
  | Horizontal (16:9) | 8 | 50 | Wider screen |
  | Vertical (9:16) | 5 | 30 | Narrow screen |
- **Word spacing fix**: CSS `display: inline-block` collapses spaces → use `marginRight: 0.3em`
- **Section titles**: Gemini analyzes transcript, generates punchy titles like "VC HYPOCRISY EXPOSED"
- **Output**: Full pipeline from 47-min raw → 144s polished clip with captions in both formats

## End-to-End Pipeline Achievement
```
Raw Video (47 min, 4K HEVC)
    ↓ Convert to H.264
    ↓ Smart chunk (2.5-3.5 min)
    ↓ MLX transcribe (word timestamps)
    ↓ Sentence split (frame-accurate)
    ↓ Gemini topic analysis (recall-first)
    ↓ Stitch selected topic
    ↓ Precision trim (remove fillers)
    ↓ Generate captions (timestamp remap)
    ↓ Gemini section titles
    ↓ Remotion render
Final: 16:9 + 9:16 with rolling captions, speaker labels, section titles
```

# Talking-Head Video Pipeline

For direct-to-camera videos where speaker's original audio is kept (no voiceover).

```
Raw Video (47+ min)
    ↓ smart_chunk.py
Chunks (2.5-3.5 min)
    ↓ mlx_transcribe.py --word-timestamps
Transcript (word-level timestamps)
    ↓ sentence_split.py (PRECISE CUTS - re-encode, no overlap)
Sentence Clips (~10s each, frame-accurate)
    ↓ analyze_script.py (RECALL-FIRST)
    │  Gemini reads full transcript
    │  Returns TOPICS with complete arcs (hook → elaborate → conclude)
    │  Each topic has: full range, trimming guide, reorder suggestions
Topics with clip ranges
    ↓ [Claude Code: Select topic - full or trimmed]
    ↓ stitch_clips.py (PRECISE CUTS)
Final Clip (complete narrative arc)
```

## Key Insights

### 1. Recall-First Topic Analysis (not precision-first highlights)
**Old approach:** Find 5-10 "highlight moments" → Often incomplete thoughts, missing context
**New approach:** Find complete TOPICS with full arcs → Then trim for precision

For each topic, Gemini identifies:
- **Full clip range**: ALL clips that might be relevant (optimize for recall)
- **Arc structure**: Hook → Elaboration → Conclusion
- **Trimming guide**: Essential vs supporting vs skippable clips
- **Reorder suggestions**: If moving clips would improve flow

### 2. Precise Cuts (zero overlap between clips)
**Problem:** FFmpeg stream copy (`-c copy`) cuts on keyframes, causing:
- Extra frames at clip start (seeks to previous keyframe)
- Repeated words/phrases at clip boundaries when stitched

**Solution:** Always re-encode clips with exact timestamps:
```bash
# sentence_split.py now uses by default:
ffmpeg -ss START -i input.mp4 -t DURATION \
  -c:v libx264 -preset fast -crf 18 \
  -c:a aac -b:a 192k \
  -async 1 -avoid_negative_ts make_zero \
  output.mp4
```

Use `--fast` flag only when speed matters more than precision.

**Quick Start:**
```bash
# Full pipeline (pauses for topic selection)
python skills/talking-head/process_video.py raw_footage.mp4 -o project/

# Auto-stitch top clips
python skills/talking-head/process_video.py raw_footage.mp4 -o project/ --auto-stitch
```

### 3. Two-Phase Editing: Recall → Precision

**Phase 1 - RECALL (done):**
- Find complete topics with full arcs
- Include ALL potentially relevant clips
- Output: ~60-180s raw topic video

**Phase 2 - PRECISION (next):**
- Upload raw topic video to Gemini (fits in context window)
- Gemini identifies: filler words, pauses, repetitions, speaking errors
- Generate precise trim list with timestamps
- Cut out imperfections for polished final clip
- Target: ~30-60s polished video

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
# === Talking-Head Pipeline ===
# Full pipeline (pauses for clip selection)
python skills/talking-head/process_video.py raw_footage.mp4 -o ./output/

# Auto-stitch top clips (score >= 6)
python skills/talking-head/process_video.py raw_footage.mp4 -o ./output/ --auto-stitch

# Step by step:
python skills/chunk-process/smart_chunk.py raw_footage.mp4 -o chunks/
python skills/chunk-process/mlx_transcribe.py chunks/ --batch --word-timestamps
python skills/talking-head/sentence_split.py raw_footage.mp4 chunks/transcript.json -o sentence_clips/
python skills/talking-head/analyze_script.py sentence_clips/clip_index.json -o clip_scores.json
python skills/talking-head/stitch_clips.py clip_scores.json --approved 1,3,5,7 -o final.mp4

# === Video Preparation ===
# Convert 4K MOV to H.264 for processing
ffmpeg -i input.MOV -c:v libx264 -preset fast -crf 23 -vf "scale=1920:1080" -c:a aac raw_assets/output.mp4

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
  - `video_projects/space_investing/output/final.mp4` (commentary style)
  - `video_projects/space_future/output/final.mp4` (commentary style)
  - `video_projects/fundraising_tips/output/final_clip.mp4` (talking-head, 86s)

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


