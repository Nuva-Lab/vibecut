# Chunk Process Skill

Smart video chunking and MLX-accelerated transcription for long-form content.

## Problem Solved
- Raw footage too long for single Gemini upload (~47 min = 5GB+)
- Need word-level timestamps for precise cutting
- Fixed-length chunks break mid-sentence

## Smart Chunking

Instead of fixed 5-minute segments, `smart_chunk.py` finds natural break points:

```bash
python skills/chunk-process/smart_chunk.py raw_footage.mp4 -o chunks/
```

**How it works:**
1. Detect silence regions (>500ms gaps)
2. Target 2.5-3.5 minute chunks
3. Split at natural pauses, not mid-sentence
4. Output: `chunk_001.mp4`, `chunk_002.mp4`, ...

**Options:**
- `--min-chunk 150`: Minimum chunk length (seconds)
- `--max-chunk 210`: Maximum chunk length (seconds)
- `--silence-thresh -40`: Silence detection threshold (dB)

## MLX Transcription

`mlx_transcribe.py` uses MLX-accelerated Qwen3-ASR for fast transcription on Mac:

```bash
# Single file
python skills/chunk-process/mlx_transcribe.py audio.wav -o transcript.json

# Batch process chunks
python skills/chunk-process/mlx_transcribe.py chunks/ --batch --word-timestamps
```

**Features:**
- 3-5x faster than CPU on Apple Silicon
- Auto language detection (Chinese/English/Mixed)
- Word-level timestamps (~30ms precision)
- Outputs: `transcript.json` with segments + words

## Combined Pipeline

```bash
# 1. Smart chunk the video
python skills/chunk-process/smart_chunk.py raw.mp4 -o chunks/

# 2. Transcribe all chunks
python skills/chunk-process/mlx_transcribe.py chunks/ --batch --word-timestamps

# Output: chunks/transcript.json (merged from all chunks)
```

## Output Format

```json
{
  "language": "English",
  "segments": [
    {"text": "First sentence.", "start": 0.0, "end": 2.5},
    {"text": "Second sentence.", "start": 2.5, "end": 5.0}
  ],
  "words": [
    {"text": "First", "start": 0.0, "end": 0.3},
    {"text": "sentence", "start": 0.3, "end": 0.8}
  ],
  "full_text": "First sentence. Second sentence..."
}
```

## Why Smart Chunking?

| Fixed Chunks | Smart Chunks |
|--------------|--------------|
| Breaks mid-word | Breaks at pauses |
| 5 min arbitrary | 2.5-3.5 min natural |
| Hard cuts | Clean transitions |
| Timestamp gaps | Continuous timeline |
