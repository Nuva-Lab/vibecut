export interface WordSegment {
  text: string;
  startMs: number;
  endMs: number;
}

export interface CaptionSegment {
  text: string;
  startMs: number;
  endMs: number;
  words?: WordSegment[];  // For karaoke-style highlighting
}

export interface SectionMarker {
  title: string;
  subtitle?: string;
  startMs: number;
  durationMs: number;
  style?: 'minimal' | 'bold' | 'pill';
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

export interface TalkingHeadClipProps {
  videoSrc: string;
  captions: CaptionSegment[];
  sections?: SectionMarker[];
  speakers?: SpeakerAnnotation[];
  titleCard?: TitleCardProps;
  // Vertical (9:16) options
  cropToVertical?: boolean;
  speakerCenterX?: number;  // X position (0-1) to center crop on speaker
  // Audio
  audioVolume?: number;  // Default 1.0 (full volume)
}
