import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';

const fontFamily = '"Inter", "SF Pro Display", "PingFang SC", sans-serif';

interface SpeakerLabelProps {
  name: string;
  title?: string;
  x: number;
  y: number;
}

export const SpeakerLabel: React.FC<SpeakerLabelProps> = ({name, title, x, y}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();

  // Staggered entrance animations
  const lineProgress = spring({
    fps,
    frame,
    config: {damping: 80, stiffness: 300},
    durationInFrames: 12,
  });

  const nameProgress = spring({
    fps,
    frame: Math.max(0, frame - 5),
    config: {damping: 100, stiffness: 200},
    durationInFrames: 15,
  });

  const titleProgress = spring({
    fps,
    frame: Math.max(0, frame - 12),
    config: {damping: 100, stiffness: 180},
    durationInFrames: 15,
  });

  // Clamp position to stay within visible area
  const clampedX = Math.max(200, Math.min(width - 200, x));

  // Accent line width animation
  const lineWidth = interpolate(lineProgress, [0, 1], [0, 4]);

  // Subtle glow pulse
  const glowIntensity = interpolate(
    Math.sin(frame * 0.1),
    [-1, 1],
    [15, 25]
  );

  return (
    <div
      style={{
        position: 'absolute',
        left: clampedX,
        top: y,
        transform: `translateX(-50%)`,
        fontFamily,
      }}
    >
      {/* Animated accent line */}
      <div
        style={{
          width: interpolate(lineProgress, [0, 1], [0, 60]),
          height: 3,
          backgroundColor: '#FFD700',
          marginBottom: 8,
          boxShadow: `0 0 ${glowIntensity}px #FFD700`,
          borderRadius: 2,
        }}
      />

      {/* Main card */}
      <div
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.92)',
          padding: '14px 24px',
          borderRadius: 12,
          borderLeft: `${lineWidth}px solid #FFD700`,
          boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 ${glowIntensity}px rgba(255, 215, 0, 0.15)`,
          transform: `translateY(${(1 - nameProgress) * 20}px)`,
          opacity: nameProgress,
        }}
      >
        {/* Name with character reveal */}
        <div style={{
          color: '#FFFFFF',
          fontSize: 32,
          fontWeight: 700,
          letterSpacing: '0.02em',
          overflow: 'hidden',
        }}>
          {name.split('').map((char, i) => {
            const charDelay = i * 1.5;
            const charProgress = interpolate(
              frame - 5,
              [charDelay, charDelay + 8],
              [0, 1],
              {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
            );
            return (
              <span
                key={i}
                style={{
                  display: 'inline-block',
                  opacity: charProgress,
                  transform: `translateY(${(1 - charProgress) * 10}px)`,
                }}
              >
                {char === ' ' ? '\u00A0' : char}
              </span>
            );
          })}
        </div>

        {/* Title with fade-in */}
        {title && (
          <div style={{
            color: 'rgba(255, 255, 255, 0.85)',
            fontSize: 18,
            fontWeight: 500,
            marginTop: 6,
            opacity: titleProgress,
            transform: `translateX(${(1 - titleProgress) * -10}px)`,
            letterSpacing: '0.01em',
          }}>
            {title}
          </div>
        )}
      </div>
    </div>
  );
};
