import {Composition} from 'remotion';
import {VideoClip} from './VideoClip';
import type {VideoClipProps} from './types';

export const RemotionRoot: React.FC = () => {
  return (
    <>
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
    </>
  );
};
