import {Composition} from 'remotion';
import {VideoClip} from './VideoClip';
import {TalkingHeadClip} from './TalkingHeadClip';
import type {VideoClipProps, TalkingHeadClipProps} from './types';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Commentary video (with voiceover) - 16:9 */}
      <Composition
        id="VideoClip"
        component={VideoClip}
        durationInFrames={928}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          videoSrc: '',
          captions: [],
          speakers: [],
          contextBadge: {
            location: 'USA House',
            event: 'Davos 2026',
          },
          titleCard: undefined,
          originalAudioVolume: 0.3,
        } satisfies VideoClipProps}
      />

      {/* Talking-head video - 16:9 horizontal */}
      <Composition
        id="TalkingHead"
        component={TalkingHeadClip}
        durationInFrames={4324}  // 144s at 30fps
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          videoSrc: '',
          captions: [],
          sections: [],
          speakers: [],
          titleCard: undefined,
          cropToVertical: false,
          speakerCenterX: 0.5,
          audioVolume: 1.0,
        } satisfies TalkingHeadClipProps}
      />

      {/* Talking-head video - 9:16 vertical (TikTok/Reels) */}
      <Composition
        id="TalkingHeadVertical"
        component={TalkingHeadClip}
        durationInFrames={4324}  // 144s at 30fps
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          videoSrc: '',
          captions: [],
          sections: [],
          speakers: [],
          titleCard: undefined,
          cropToVertical: true,
          speakerCenterX: 0.5,
          audioVolume: 1.0,
        } satisfies TalkingHeadClipProps}
      />
    </>
  );
};
