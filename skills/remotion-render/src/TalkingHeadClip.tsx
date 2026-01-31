import {AbsoluteFill, Sequence, useVideoConfig, staticFile, OffthreadVideo, Audio} from 'remotion';
import {RollingCaption} from './components/RollingCaption';
import {SpeakerLabel} from './components/SpeakerLabel';
import {SectionTitle} from './components/SectionTitle';
import {TitleCard} from './components/TitleCard';
import type {TalkingHeadClipProps} from './types';

/**
 * TalkingHeadClip - Composition for direct-to-camera videos
 *
 * Features:
 * - Rolling captions with karaoke-style word highlighting
 * - Pop-up section titles for topic transitions
 * - Optional vertical (9:16) crop centered on speaker
 * - Full original audio (no voiceover)
 */
export const TalkingHeadClip: React.FC<TalkingHeadClipProps> = ({
  videoSrc,
  captions,
  sections = [],
  speakers = [],
  titleCard,
  cropToVertical = false,
  speakerCenterX = 0.5,
  audioVolume = 1.0,
}) => {
  const {fps, width, height} = useVideoConfig();

  // Title card duration
  const titleDurationFrames = titleCard?.durationMs
    ? Math.ceil((titleCard.durationMs / 1000) * fps)
    : 0;

  const videoSource = videoSrc?.startsWith('http') ? videoSrc : staticFile(videoSrc);

  // Calculate crop for vertical format
  // For 9:16 from 16:9, we need to crop width to height * (9/16)
  const verticalWidth = height * (9 / 16);
  const cropOffsetX = cropToVertical ? (width - verticalWidth) * speakerCenterX : 0;

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {/* Video layer */}
      {videoSrc && (
        <>
          <div
            style={{
              width: '100%',
              height: '100%',
              overflow: 'hidden',
            }}
          >
            <OffthreadVideo
              src={videoSource}
              style={{
                width: cropToVertical ? `${(width / verticalWidth) * 100}%` : '100%',
                height: '100%',
                objectFit: 'cover',
                marginLeft: cropToVertical ? `-${cropOffsetX}px` : 0,
              }}
            />
          </div>
          {/* Original audio at specified volume */}
          <Audio src={videoSource} volume={audioVolume} />
        </>
      )}

      {/* Title card at the start */}
      {titleCard && titleDurationFrames > 0 && (
        <Sequence from={0} durationInFrames={titleDurationFrames}>
          <TitleCard
            title={titleCard.title}
            subtitle={titleCard.subtitle}
            durationFrames={titleDurationFrames}
          />
        </Sequence>
      )}

      {/* Section titles (pop-up topic markers) */}
      {sections.map((section, index) => {
        const startFrame = Math.floor((section.startMs / 1000) * fps) + titleDurationFrames;
        const durationFrames = Math.ceil((section.durationMs / 1000) * fps);

        return (
          <Sequence
            key={`section-${index}`}
            from={startFrame}
            durationInFrames={durationFrames}
          >
            <SectionTitle
              title={section.title}
              subtitle={section.subtitle}
              durationFrames={durationFrames}
              style={section.style || 'cinematic'}
              position="center"
            />
          </Sequence>
        );
      })}

      {/* Speaker labels */}
      {speakers.map((speaker, index) => {
        const startFrame = Math.floor((speaker.showFromMs / 1000) * fps) + titleDurationFrames;
        const endFrame = Math.ceil((speaker.showUntilMs / 1000) * fps) + titleDurationFrames;
        const durationInFrames = endFrame - startFrame;

        if (durationInFrames <= 0) return null;

        const x = (speaker.box2d[1] / 1000) * width;
        const y = (speaker.box2d[0] / 1000) * height;

        return (
          <Sequence
            key={`speaker-${index}`}
            from={startFrame}
            durationInFrames={durationInFrames}
          >
            <SpeakerLabel name={speaker.name} title={speaker.title} x={x} y={y} />
          </Sequence>
        );
      })}

      {/* Rolling captions with karaoke word highlighting */}
      {captions.map((caption, index) => {
        const startFrame = Math.floor((caption.startMs / 1000) * fps) + titleDurationFrames;
        const endFrame = Math.ceil((caption.endMs / 1000) * fps) + titleDurationFrames;
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
