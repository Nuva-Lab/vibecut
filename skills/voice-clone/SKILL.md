---
name: voice-clone
description: Clone a voice using qwen3-tts and generate speech from text
---

# Voice Clone Skill

Use this skill to clone a speaker's voice and generate text-to-speech audio.

## Two-Step Process

### Step 1: Clone Voice (one-time)
```bash
python skills/voice-clone/clone.py <audio_sample.wav> [--transcript "text"]
```
Creates a speaker embedding file that can be reused.

### Step 2: Generate Speech
```bash
python skills/voice-clone/speak.py <embedding.safetensors> "Text to speak"
```
Generates audio using the cloned voice.

## Requirements

- FAL_KEY in .env (fal.ai API key)
- Voice sample: 10-30 seconds of clear speech (WAV/MP3)
- Optional: Transcript of the sample for better quality

## Output

- `assets/outputs/voice_embeddings/<name>_embedding.safetensors` - Reusable voice model
- `assets/outputs/audio/<name>_speech.wav` - Generated audio

## Notes

- qwen3-tts works best with Chinese speech samples
- Cross-lingual cloning (Chinese voice → English speech) may have quality variations
- Provide reference transcript for best quality
