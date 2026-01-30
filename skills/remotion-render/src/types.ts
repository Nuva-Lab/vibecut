export interface CaptionSegment {
  text: string;
  startMs: number;
  endMs: number;
}

export interface SpeakerAnnotation {
  name: string;
  title?: string;
  box2d: [number, number, number, number];
  showFromMs: number;
  showUntilMs: number;
}

export interface ContextBadgeProps {
  location: string;
  event: string;
  date?: string;
}

export interface TitleCardProps {
  title: string;
  subtitle?: string;
  durationMs?: number;
}

export interface VideoClipProps {
  videoSrc: string;
  captions: CaptionSegment[];
  speakers: SpeakerAnnotation[];
  contextBadge: ContextBadgeProps;
  titleCard?: TitleCardProps;
  originalAudioVolume?: number;  // 0-1, default 0.3
}
