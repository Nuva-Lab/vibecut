import {AbsoluteFill, Sequence, useVideoConfig, staticFile, OffthreadVideo, Audio} from 'remotion';
import {RollingCaption} from './components/RollingCaption';
import {SpeakerLabel} from './components/SpeakerLabel';
import {ContextBadge} from './components/ContextBadge';
import {TitleCard} from './components/TitleCard';
import type {VideoClipProps} from './types';

export const VideoClip: React.FC<VideoClipProps> = ({
  videoSrc,
  captions,
  speakers,
  contextBadge,
  titleCard,
  originalAudioVolume = 0.3,
}) => {
  const {fps, width, height} = useVideoConfig();

  // Title card duration (default 3 seconds = 90 frames at 30fps)
  const titleDurationFrames = titleCard?.durationMs
    ? Math.ceil((titleCard.durationMs / 1000) * fps)
    : 90;

  const videoSource = videoSrc?.startsWith('http') ? videoSrc : staticFile(videoSrc);

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {videoSrc && (
        <>
          <OffthreadVideo
            src={videoSource}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
            loop
          />
          {/* Include original video audio - OffthreadVideo doesn't output audio */}
          <Audio src={videoSource} volume={originalAudioVolume} />
        </>
      )}

      {/* Title card at the start */}
      {titleCard && (
        <Sequence from={0} durationInFrames={titleDurationFrames}>
          <TitleCard
            title={titleCard.title}
            subtitle={titleCard.subtitle}
            durationFrames={titleDurationFrames}
          />
        </Sequence>
      )}

      {/* Context badge appears after title card */}
      <Sequence from={titleCard ? titleDurationFrames - 30 : 0}>
        <ContextBadge {...contextBadge} />
      </Sequence>

      {/* Speaker labels */}
      {speakers.map((speaker, index) => {
        const startFrame = (speaker.showFromMs / 1000) * fps;
        const endFrame = (speaker.showUntilMs / 1000) * fps;
        const durationInFrames = endFrame - startFrame;

        if (durationInFrames <= 0) return null;

        const x = (speaker.box2d[1] / 1000) * width;
        const y = (speaker.box2d[0] / 1000) * height;

        return (
          <Sequence
            key={`speaker-${index}`}
            from={Math.floor(startFrame)}
            durationInFrames={Math.ceil(durationInFrames)}
          >
            <SpeakerLabel name={speaker.name} title={speaker.title} x={x} y={y} />
          </Sequence>
        );
      })}

      {/* Rolling captions with karaoke word highlighting */}
      {captions.map((caption, index) => {
        // Use raw timestamps - karaoke highlighting handles sync
        const startFrame = Math.floor((caption.startMs / 1000) * fps);
        const endFrame = Math.ceil((caption.endMs / 1000) * fps);
        const durationInFrames = endFrame - startFrame;

        if (durationInFrames <= 0) return null;

        return (
          <Sequence
            key={`caption-${index}`}
            from={startFrame}
            durationInFrames={durationInFrames}
          >
            <RollingCaption caption={caption} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
