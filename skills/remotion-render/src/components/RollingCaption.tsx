import {AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';

// Use system fonts for Chinese support
const fontFamily = '"PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif';

const TEXT_COLOR = '#FFFFFF';
const HIGHLIGHT_COLOR = '#FFD700';  // Gold for current word
const BG_COLOR = 'rgba(0, 0, 0, 0.75)';
const FONT_SIZE = 48;

interface WordSegment {
  text: string;
  startMs: number;
  endMs: number;
}

export interface CaptionSegment {
  text: string;
  startMs: number;
  endMs: number;
  words?: WordSegment[];  // Word-level timestamps for karaoke
}

interface RollingCaptionProps {
  caption: CaptionSegment;
}

export const RollingCaption: React.FC<RollingCaptionProps> = ({caption}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Current time in ms relative to caption start
  const currentMs = (frame / fps) * 1000 + caption.startMs;

  // Quick entrance animation
  const enterProgress = spring({
    fps,
    frame,
    config: {damping: 100, stiffness: 500},
    durationInFrames: 2,
  });

  // If we have word-level timing, render karaoke style
  const hasWordTiming = caption.words && caption.words.length > 0;

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        paddingBottom: 100,
      }}
    >
      <div
        style={{
          backgroundColor: BG_COLOR,
          padding: '16px 32px',
          borderRadius: 12,
          maxWidth: '90%',
          transform: `translateY(${(1 - enterProgress) * 30}px)`,
          opacity: enterProgress,
          boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        }}
      >
        <div
          style={{
            fontSize: FONT_SIZE,
            fontWeight: 700,
            fontFamily,
            textAlign: 'center',
            lineHeight: 1.4,
            letterSpacing: '0.01em',
          }}
        >
          {hasWordTiming ? (
            // Karaoke style: highlight current word
            caption.words!.map((word, i) => {
              // Handle edge case where startMs == endMs (alignment failed for this word)
              // Use a minimum duration of 1ms to avoid interpolation errors
              const safeEndMs = word.endMs > word.startMs ? word.endMs : word.startMs + 1;

              // Word states: upcoming (white), active (gold), spoken (white)
              const isActive = currentMs >= word.startMs && currentMs <= safeEndMs;
              const isSpoken = currentMs > safeEndMs;

              return (
                <span
                  key={i}
                  style={{
                    color: isActive ? HIGHLIGHT_COLOR : TEXT_COLOR,
                    opacity: isSpoken ? 0.9 : 1,
                    transition: 'color 0.05s ease',
                    // Slight scale on active word
                    transform: isActive ? 'scale(1.05)' : 'scale(1)',
                    display: 'inline-block',
                  }}
                >
                  {word.text}
                </span>
              );
            })
          ) : (
            // Fallback: no word timing, just show text
            <span style={{color: TEXT_COLOR}}>{caption.text}</span>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
