# Remotion Render Skill

Generic video rendering with motion graphics overlays.

## Components

- `VideoClip.tsx` - Main composition (video + captions + annotations)
- `components/RollingCaption.tsx` - Karaoke-style word highlighting
- `components/SpeakerLabel.tsx` - Positioned speaker annotations
- `components/ContextBadge.tsx` - Location/event badge

## Usage

Called by `make-video` skill. Not typically invoked directly.

```bash
npx remotion render VideoClip output.mp4 --props=props.json
```

## Props Interface

```typescript
{
  videoSrc: string;           // Video filename in public/
  captions: Caption[];        // Timed caption segments
  speakers: SpeakerAnnotation[];  // Speaker labels with positions
  contextBadge: {
    location: string;
    event: string;
  }
}
```

## Dependencies

- @remotion/captions - TikTok-style caption pages
- @remotion/media - Video embedding
- System fonts (PingFang SC) for Chinese text

## Best Practices (rules/)

Reference documentation for Remotion patterns:

- `rules/display-captions.md` - TikTok-style captions with word highlighting
- `rules/videos.md` - Video embedding, trimming, volume, speed
- `rules/text-animations.md` - Typewriter, word highlight effects
- `rules/fonts.md` - Loading Google Fonts and local fonts
- `rules/animations.md` - Interpolation, spring, easing
- `rules/timing.md` - Frame-based timing and curves
- `rules/sequencing.md` - Sequence patterns for timeline control

See `rules/` folder for complete documentation.
