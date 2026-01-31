# Chunk Process Skill

Split long videos into manageable chunks and process them in parallel.

## Problem Solved
- Gemini 3 Pro has upload limits (~2GB)
- Qwen3-ASR can timeout on very long audio (>30 min)
- FFmpeg handles any size efficiently

## Approach
1. **Split**: FFmpeg segments video at keyframes (5 min chunks)
2. **Extract**: Pull audio from each chunk
3. **Transcribe**: Qwen3-ASR in parallel (N workers)
4. **Merge**: Combine results with global timestamp offsets

## Usage

### Step 1: Split video into chunks
```bash
ffmpeg -i input.mp4 \
  -map 0:0 -map 0:1 \
  -c copy \
  -segment_time 300 \
  -f segment \
  -reset_timestamps 1 \
  "chunks/chunk_%03d.mp4"
```

### Step 2: Process all chunks
```bash
python skills/chunk-process/process_chunks.py chunks/ --workers 2
```

### Options
- `--workers N`: Parallel transcription workers (default: 2)
- `--sequential`: Process one at a time (for debugging)
- `--output FILE`: Output index filename

## Output
Creates `transcript_index.json` with:
- Per-chunk metadata (offset, duration, success/error)
- Merged segments with global timestamps
- Merged words with global timestamps
- Full concatenated text

## Why This Works
- FFmpeg's segment muxer is nearly instant (just copies streams)
- Each 5-min chunk is ~700MB video, ~10MB audio
- Qwen3-ASR handles 5 min audio reliably
- Global offsets maintain timeline continuity
