import {useCurrentFrame, useVideoConfig, spring} from 'remotion';

const fontFamily = '"PingFang SC", "Inter", "SF Pro Display", sans-serif';

interface ContextBadgeProps {
  location: string;
  event: string;
  date?: string;
}

export const ContextBadge: React.FC<ContextBadgeProps> = ({location, event, date}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const enterProgress = spring({
    fps,
    frame,
    config: {damping: 200},
    durationInFrames: 20,
  });

  return (
    <div
      style={{
        position: 'absolute',
        top: 50,
        left: 50,
        transform: `translateX(${(1 - enterProgress) * -60}px)`,
        opacity: enterProgress,
        fontFamily,
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: '16px 28px',
          borderRadius: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
        }}
      >
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: '#FF4444',
            boxShadow: '0 0 8px #FF4444',
          }}
        />
        <span style={{color: '#FFFFFF', fontSize: 28, fontWeight: 600, letterSpacing: '0.02em'}}>
          {location} {event && `• ${event}`} {date && `• ${date}`}
        </span>
      </div>
    </div>
  );
};
