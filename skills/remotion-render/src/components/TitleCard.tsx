import {AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';

const fontFamily = '"PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif';

interface TitleCardProps {
  title: string;
  subtitle?: string;
  durationFrames?: number;
}

export const TitleCard: React.FC<TitleCardProps> = ({
  title,
  subtitle,
  durationFrames = 90,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Entrance animation
  const enterProgress = spring({
    fps,
    frame,
    config: {damping: 100, stiffness: 200},
    durationInFrames: 20,
  });

  // Exit animation (fade out in last 15 frames)
  const exitProgress = interpolate(
    frame,
    [durationFrames - 15, durationFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const opacity = enterProgress * exitProgress;
  const translateY = interpolate(enterProgress, [0, 1], [60, 0]);

  // Staggered subtitle entrance
  const subtitleDelay = 10;
  const subtitleEnter = spring({
    fps,
    frame: Math.max(0, frame - subtitleDelay),
    config: {damping: 100},
    durationInFrames: 15,
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        opacity,
      }}
    >
      <div
        style={{
          textAlign: 'center',
          transform: `translateY(${translateY}px)`,
          maxWidth: '80%',
        }}
      >
        <h1
          style={{
            fontSize: 72,
            fontWeight: 800,
            fontFamily,
            color: '#FFFFFF',
            margin: 0,
            lineHeight: 1.3,
            textShadow: '0 4px 30px rgba(0,0,0,0.8)',
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              fontSize: 36,
              fontWeight: 500,
              fontFamily,
              color: 'rgba(255,255,255,0.85)',
              marginTop: 24,
              opacity: subtitleEnter,
              transform: `translateY(${(1 - subtitleEnter) * 20}px)`,
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
    </AbsoluteFill>
  );
};
