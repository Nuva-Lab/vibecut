import {AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';

const fontFamily = '"Inter", "SF Pro Display", "PingFang SC", sans-serif';

interface SectionTitleProps {
  title: string;
  subtitle?: string;
  durationFrames: number;
  position?: 'top' | 'center' | 'bottom';
  style?: 'minimal' | 'bold' | 'pill' | 'cinematic';
}

export const SectionTitle: React.FC<SectionTitleProps> = ({
  title,
  subtitle,
  durationFrames,
  position = 'center',
  style = 'cinematic',
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();

  // Animation timing
  const enterDuration = Math.floor(fps * 0.5);
  const exitStart = durationFrames - Math.floor(fps * 0.4);

  // Enter animation with bounce
  const enterProgress = spring({
    fps,
    frame,
    config: {damping: 12, stiffness: 100},
    durationInFrames: enterDuration,
  });

  // Exit animation
  const exitProgress = frame >= exitStart
    ? spring({
        fps,
        frame: frame - exitStart,
        config: {damping: 15, stiffness: 150},
        durationInFrames: Math.floor(fps * 0.4),
      })
    : 0;

  const opacity = interpolate(exitProgress, [0, 1], [1, 0]);
  const scale = interpolate(enterProgress, [0, 1], [0.3, 1]) * interpolate(exitProgress, [0, 1], [1, 0.5]);

  // Line animation for cinematic style
  const lineWidth = interpolate(enterProgress, [0, 0.5, 1], [0, width * 0.3, width * 0.4]);
  const lineOpacity = interpolate(enterProgress, [0, 0.3], [0, 1], {extrapolateRight: 'clamp'});

  // Glow effect
  const glowIntensity = interpolate(Math.sin(frame * 0.1), [-1, 1], [15, 35]);

  // Position styles
  const positionStyles: Record<string, React.CSSProperties> = {
    top: {top: 100, left: '50%', transform: `translateX(-50%) scale(${scale})`},
    center: {top: '50%', left: '50%', transform: `translate(-50%, -50%) scale(${scale})`},
    bottom: {bottom: 250, left: '50%', transform: `translateX(-50%) scale(${scale})`},
  };

  // Cinematic style (new default)
  if (style === 'cinematic') {
    return (
      <AbsoluteFill>
        {/* Background dim */}
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.4)',
          opacity: enterProgress * (1 - exitProgress),
        }} />

        {/* Centered content */}
        <div
          style={{
            position: 'absolute',
            ...positionStyles[position],
            opacity,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 20,
          }}
        >
          {/* Top line */}
          <div style={{
            width: lineWidth,
            height: 3,
            background: 'linear-gradient(90deg, transparent, #FFD700, transparent)',
            opacity: lineOpacity,
          }} />

          {/* Title with gradient */}
          <div style={{
            fontFamily,
            fontSize: 72,
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            background: 'linear-gradient(135deg, #FFFFFF, #FFD700)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            textShadow: `0 0 ${glowIntensity}px rgba(255, 215, 0, 0.5)`,
            filter: `drop-shadow(0 4px 20px rgba(0,0,0,0.8))`,
          }}>
            {title}
          </div>

          {/* Bottom line */}
          <div style={{
            width: lineWidth,
            height: 3,
            background: 'linear-gradient(90deg, transparent, #FFD700, transparent)',
            opacity: lineOpacity,
          }} />

          {/* Subtitle */}
          {subtitle && (
            <div style={{
              fontFamily,
              fontSize: 28,
              fontWeight: 500,
              color: 'rgba(255, 255, 255, 0.8)',
              letterSpacing: '0.05em',
              marginTop: 10,
            }}>
              {subtitle}
            </div>
          )}
        </div>
      </AbsoluteFill>
    );
  }

  // Other styles (bold, pill, minimal)
  const styleVariants = {
    minimal: {
      container: {
        backgroundColor: 'transparent',
        padding: '8px 16px',
      },
      title: {
        fontSize: 32,
        fontWeight: 600,
        color: '#FFFFFF',
        textShadow: '2px 2px 8px rgba(0,0,0,0.8)',
      },
    },
    bold: {
      container: {
        backgroundColor: 'rgba(0, 0, 0, 0.95)',
        padding: '28px 56px',
        borderRadius: 16,
        border: '2px solid #FFD700',
        boxShadow: `0 12px 40px rgba(0,0,0,0.7), 0 0 ${glowIntensity}px rgba(255, 215, 0, 0.2)`,
      },
      title: {
        fontSize: 56,
        fontWeight: 800,
        color: '#FFFFFF',
        textTransform: 'uppercase' as const,
        letterSpacing: '0.08em',
      },
    },
    pill: {
      container: {
        background: 'linear-gradient(135deg, #FFD700, #FF6B35)',
        padding: '16px 40px',
        borderRadius: 50,
        boxShadow: '0 8px 30px rgba(255, 107, 53, 0.4)',
      },
      title: {
        fontSize: 32,
        fontWeight: 700,
        color: '#000000',
        letterSpacing: '0.02em',
      },
    },
  };

  const variant = styleVariants[style as keyof typeof styleVariants] || styleVariants.bold;

  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          ...positionStyles[position],
          opacity,
          transformOrigin: 'center',
        }}
      >
        <div style={{...variant.container, fontFamily}}>
          <div style={variant.title}>{title}</div>
          {subtitle && (
            <div style={{
              fontSize: (variant.title.fontSize as number) * 0.5,
              fontWeight: 400,
              color: style === 'pill' ? '#333' : '#AAA',
              marginTop: 8,
              textAlign: 'center',
            }}>
              {subtitle}
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
