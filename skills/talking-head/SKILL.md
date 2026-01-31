# Talking-Head Video Processing

Process direct-to-camera videos with sentence-level precision, rolling captions, and multi-format output.

## Full Pipeline Overview

```
Raw Video (47+ min)
    ↓ smart_chunk.py
Chunks (2.5-3.5 min)
    ↓ mlx_transcribe.py --word-timestamps
Transcript (word-level timestamps)
    ↓ sentence_split.py (precise cuts, no overlap)
Sentence Clips (~10s each, frame-accurate)
    ↓ analyze_script.py (RECALL-FIRST)
Topics with complete arcs (hook → elaborate → conclude)
    ↓ [Claude Code: Select topic]
    ↓ stitch_clips.py (precise cuts)
Raw Topic Video (~60-180s)
    ↓ precision_trim.py (remove fillers, stutters)
Polished Video (~30-120s)
    ↓ generate_captions.py (timestamp remapping)
Captions + Section Markers
    ↓ render_with_captions.py (Remotion)
Final Output: 16:9 + 9:16 with rolling captions
```

## Key Insight: Recall-First Topic Analysis

**Old approach (precision-first):** Find 5-10 "highlight moments" → Often incomplete thoughts

**New approach (recall-first):** Find complete TOPICS with full arcs → Then trim for precision

For each topic, Gemini identifies:
- **Full clip range**: ALL clips that might be relevant (optimize for recall)
- **Arc structure**: Hook → Elaboration → Conclusion
- **Trimming guide**: Essential vs supporting vs skippable clips
- **Reorder suggestions**: If moving clips would improve flow

**Why this works:**
- Complete narratives: Each topic has setup, body, and resolution
- No missing context: Better to include extra and trim than miss key content
- Flexible editing: Full version for review, trimmed version for final cut

## Quick Start

```bash
# Full pipeline (pauses for clip selection)
python skills/talking-head/process_video.py raw_footage.mp4 -o ./output/

# Auto-stitch top clips
python skills/talking-head/process_video.py raw_footage.mp4 -o ./output/ --auto-stitch
```

## Claude Code Integration

```python
from process_video import run_pipeline, stitch_selected_clips

# Run pipeline (stops at clip review)
state = run_pipeline("raw_footage.mp4", "./output/")

# Present review to user
if state.get("awaiting_user_input"):
    print(state["clip_review"]["display"])

# After user says "Use clips 7, 12, 3"
result = stitch_selected_clips("./output/", [7, 12, 3])
```

## Skills Reference

### sentence_split.py
Split at sentence boundaries, create sentence index.

```bash
python sentence_split.py video.mp4 transcript.json -o clips/
```

Output: `clip_index.json` with sentence-to-clip mapping.

### analyze_script.py
Text-first highlight analysis.

```bash
python analyze_script.py clips/clip_index.json -o clip_scores.json
```

Gemini reads full transcript, returns highlights with:
- `sentence_range`: Which sentences (e.g., "15-18")
- `clip_ids`: Mapped clip IDs
- `viral_score`, `hook_potential`, `standalone`

### lowres_convert.py (Optional)
Only needed if you want video verification of selected clips.

```bash
python lowres_convert.py clips/ -o lowres/ --resolution 480p
```

### batch_analyze.py (Optional)
Video-based verification of specific clips. Use after script analysis to double-check selected clips visually.

```bash
python batch_analyze.py lowres/ -o verification.json --clips 7,12,3
```

### stitch_clips.py
Concatenate approved clips.

```bash
python stitch_clips.py clip_scores.json --approved 7,12,3 -o final.mp4
```

## Output: clip_scores.json

```json
{
  "analysis_type": "script_first",
  "clips": [
    {
      "clip_id": 7,
      "viral_score": 9,
      "hook_potential": 10,
      "key_quote": "I've raised tens of millions...",
      "recommended_use": "opening"
    }
  ],
  "highlights": [
    {
      "sentence_range": "15-18",
      "clip_ids": [7],
      "quote": "I've raised tens of millions...",
      "type": "hook",
      "viral_score": 9,
      "why": "Strong credibility opener"
    }
  ]
}
```

## Sentence Index

The key data structure that enables precise mapping:

```json
{
  "sentences": [
    {"id": 1, "text": "First sentence.", "clip_id": 1},
    {"id": 2, "text": "Second sentence.", "clip_id": 1},
    {"id": 3, "text": "Third sentence.", "clip_id": 2}
  ],
  "sentence_to_clip": {1: 1, 2: 1, 3: 2},
  "clip_to_sentences": {1: [1, 2], 2: [3]}
}
```

When Gemini says "sentences 15-18 are great", we look up `sentence_to_clip` to get the exact clip IDs.

## Precise Cutting (Zero Overlap)

By default, all clips are cut with **frame-accurate precision** using FFmpeg re-encoding and **zero padding**. This ensures:
- Zero overlapping frames between clips
- No repeated words at clip boundaries
- Clean audio cuts (no pops or artifacts)

```bash
# Default: precise cut (re-encode) with zero padding
python sentence_split.py video.mp4 transcript.json -o clips/

# Fast mode: stream copy (may have keyframe boundary issues)
python sentence_split.py video.mp4 transcript.json -o clips/ --fast

# Add padding only if you want overlap for crossfades
python sentence_split.py video.mp4 transcript.json -o clips/ --padding 100
```

**Why zero padding by default?**
- Qwen3-ForcedAligner provides precise word timestamps (~30ms accuracy)
- Natural speech has gaps between sentences (pauses)
- Adding padding (e.g., 100ms) causes clips to overlap:
  - Clip N extracts to `end + 100ms`
  - Clip N+1 extracts from `start - 100ms`
  - If gap < 200ms → overlap and repeated words!
- Zero padding = clips fit together perfectly with natural pauses

**Why re-encode (not stream copy)?**
- Stream copy (`-c copy`) cuts on keyframes, not exact timestamps
- This causes extra frames at start (previous keyframe) or missing frames at end
- Re-encoding with `-crf 18` maintains quality while ensuring exact cuts

## Key Learnings

**Why text-first?** Earlier versions uploaded 60s+ video clips to Gemini:
- Slow: ~30s upload per 20MB clip
- Expensive: Video processing tokens
- Limited context: Gemini only saw chunks, not full narrative

**Why sentence index?** Clips are cut at pauses, roughly 1:1 with sentences. The index handles edge cases where sentences span clips.

**Why precise cuts?** Stream copy creates overlapping frames:
- FFmpeg seeks to nearest keyframe (not exact timestamp)
- Adjacent clips may share the same frames at boundaries
- Re-encoding fixes this by decoding and re-encoding at exact timestamps

**When to use video analysis?** Only for final verification of selected clips if you want to check:
- Speaker visibility
- Audio quality
- Visual issues

## Phase 2: Precision Trimming

After selecting a topic, remove filler words, stutters, and repetitions.

### precision_trim.py

Two-stage approach: ASR for precise timestamps, Gemini for semantic decisions.

```bash
# Full pipeline
python precision_trim.py run topic_video.mp4 -o output/

# Step by step
python precision_trim.py transcribe topic_video.mp4 -o word_transcript.json
python precision_trim.py identify topic_video.mp4 word_transcript.json -o cuts.json
python precision_trim.py apply topic_video.mp4 cuts.json word_transcript.json -o trimmed.mp4
```

**Key insight:** Gemini identifies WHAT to cut (by word index), ASR provides WHERE to cut (~30ms precision).

**Micro-segment fix:** `min_keep_duration=1.0s` prevents jittery playback from tiny segments.

## Phase 3: Rolling Captions + Multi-Format

Add karaoke-style captions and render both horizontal and vertical formats.

### generate_captions.py

Maps word timestamps from original video to trimmed video, groups into phrases.

```bash
python generate_captions.py word_transcript.json kept_segments.json -o output/
```

**Timestamp remapping logic:**
```python
# For each word in original video:
adjusted_time = word_start - segment_start + cumulative_offset
```

**Phrase grouping rules:**
- Max 12 words per phrase
- Max 4 seconds duration
- Break on 300ms+ pauses
- Break on sentence-ending punctuation

**Output:**
- `captions.json`: Phrases with word-level timestamps for karaoke
- `sections.json`: Pop-up section markers at topic transitions

### render_with_captions.py

Renders both 16:9 and 9:16 formats using Remotion.

```bash
python render_with_captions.py trimmed.mp4 captions.json \
  --sections sections.json \
  --speaker-center 0.5 \
  -o output/
```

**Output:**
| Format | Resolution | Use Case |
|--------|------------|----------|
| `*_captioned.mp4` | 1920x1080 | YouTube, LinkedIn |
| `*_vertical.mp4` | 1080x1920 | TikTok, Reels, Shorts |

**Vertical crop:** Centers on speaker position (`--speaker-center 0.5` = center, `0.3` = left third).

## Remotion Components

The pipeline uses these Remotion components:

- `TalkingHeadClip.tsx`: Main composition for talking-head videos
- `RollingCaption.tsx`: Karaoke-style captions with gold word highlighting
- `SectionTitle.tsx`: Pop-up "pill" style section markers

**Caption styling:**
- Background: Semi-transparent black
- Text: White, gold highlight on current word
- Animation: 2-frame spring entrance (66ms)

## Complete Example

```bash
# 1. Chunk and transcribe
python skills/chunk-process/smart_chunk.py raw.mp4 -o chunks/
python skills/chunk-process/mlx_transcribe.py chunks/ --batch --word-timestamps

# 2. Split into sentences and analyze
python skills/talking-head/sentence_split.py raw.mp4 chunks/transcript.json -o clips/
python skills/talking-head/analyze_script.py clips/clip_index.json -o topics.json

# 3. Select topic and stitch
python skills/talking-head/stitch_clips.py topics.json --topic 10 -o topic10_raw.mp4

# 4. Precision trim
python skills/talking-head/precision_trim.py run topic10_raw.mp4 -o trimmed/

# 5. Generate captions and render
python skills/talking-head/generate_captions.py \
  trimmed/word_transcript.json trimmed/kept_segments.json -o trimmed/
python skills/talking-head/render_with_captions.py \
  trimmed/trimmed.mp4 trimmed/captions.json \
  --sections trimmed/sections.json -o final/
```

**Result:** `final/trimmed_captioned.mp4` (16:9) + `final/trimmed_vertical.mp4` (9:16)
