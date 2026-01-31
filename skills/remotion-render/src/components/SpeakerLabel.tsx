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
  const containerProgress = spring({
    fps,
    frame,
    config: {damping: 15, stiffness: 100},
    durationInFrames: 20,
  });

  const nameProgress = spring({
    fps,
    frame: Math.max(0, frame - 8),
    config: {damping: 20, stiffness: 150},
    durationInFrames: 18,
  });

  const titleProgress = spring({
    fps,
    frame: Math.max(0, frame - 15),
    config: {damping: 25, stiffness: 120},
    durationInFrames: 15,
  });

  // Clamp position to stay within visible area
  const clampedX = Math.max(300, Math.min(width - 300, x));

  // Animated gradient position
  const gradientShift = interpolate(frame, [0, 60], [0, 100], {extrapolateRight: 'clamp'});

  // Glow pulse
  const glowIntensity = interpolate(Math.sin(frame * 0.08), [-1, 1], [20, 40]);

  return (
    <div
      style={{
        position: 'absolute',
        left: clampedX,
        top: y,
        transform: `translateX(-50%) scale(${interpolate(containerProgress, [0, 1], [0.8, 1])})`,
        opacity: containerProgress,
        fontFamily,
      }}
    >
      {/* Main card with gradient border */}
      <div
        style={{
          background: `linear-gradient(135deg, #FFD700 ${gradientShift}%, #FF6B35 ${gradientShift + 50}%)`,
          padding: 4,
          borderRadius: 16,
          boxShadow: `0 12px 40px rgba(0,0,0,0.5), 0 0 ${glowIntensity}px rgba(255, 215, 0, 0.3)`,
        }}
      >
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            padding: '20px 36px',
            borderRadius: 12,
          }}
        >
          {/* Name with slide-in */}
          <div style={{
            color: '#FFFFFF',
            fontSize: 52,
            fontWeight: 800,
            letterSpacing: '-0.01em',
            overflow: 'hidden',
            transform: `translateX(${(1 - nameProgress) * -30}px)`,
            opacity: nameProgress,
          }}>
            {name}
          </div>

          {/* Title with gradient text */}
          {title && (
            <div style={{
              background: 'linear-gradient(90deg, #FFD700, #FF6B35)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              fontSize: 28,
              fontWeight: 600,
              marginTop: 8,
              opacity: titleProgress,
              transform: `translateX(${(1 - titleProgress) * -20}px)`,
              letterSpacing: '0.02em',
            }}>
              {title}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
