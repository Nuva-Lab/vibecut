# API Setup Guide

vibecut uses external AI services for video understanding and voice generation.
This guide explains how to get and configure the required API keys.

## Required: Google AI (Gemini)

Google AI is required for video analysis and understanding.

### Getting Your Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key

### Configuration

Add to your `.env` file:

```bash
GOOGLE_API_KEY=AIzaSy...your_key_here
```

### What It's Used For

- `analyze-video/` - Understanding video content, identifying speakers
- `find-golden-segments/` - Finding clip-worthy moments
- `inspect-video/` - Quality verification of rendered videos

### Pricing

Google AI has a generous free tier. Check [Google AI pricing](https://ai.google.dev/pricing) for current limits.

---

## Optional: fal.ai

fal.ai provides voice cloning and audio enhancement capabilities.

### Getting Your Key

1. Go to [fal.ai Dashboard](https://fal.ai/dashboard/keys)
2. Create an account or sign in
3. Navigate to "API Keys"
4. Create a new key and copy it

### Configuration

Add to your `.env` file:

```bash
FAL_KEY=fac4064e-...your_key_here
```

### What It's Used For

- `voice-clone/` - Clone voices from audio samples
- `voice-clone/speak.py` - Generate speech with cloned voice (Qwen3-TTS)
- `audio-process/` - Audio enhancement (DeepFilterNet3)

### Pricing

fal.ai has pay-per-use pricing. Voice cloning and TTS are relatively affordable.
Check [fal.ai pricing](https://fal.ai/pricing) for current rates.

---

## Verifying Your Setup

Run this command to check your configuration:

```bash
python -c "from skills.shared.config import config; config.print_status()"
```

Output will show which features are available:

```
vibecut Configuration Status
========================================
  video_analysis       ✓ Ready
  voice_cloning        ✓ Ready
  audio_enhancement    ✓ Ready
========================================
```

---

## Troubleshooting

### "GOOGLE_API_KEY not found"

Make sure:
1. `.env` file exists in the project root
2. The key is set correctly (no extra spaces)
3. You're running from the project directory

### "FAL_KEY not found"

This is optional. If you don't need voice cloning, you can skip it.
The `make-video` pipeline will work without it (no voiceover generation).

### API key not working

- Google AI: Check if the key is enabled for the Gemini API
- fal.ai: Check if your account has credits

---

## Security Notes

- Never commit `.env` to git (it's in `.gitignore`)
- Don't share your API keys publicly
- Rotate keys if they're accidentally exposed
