// App icons: lucide-react (stroke icons, currentColor), under the names the components already use.
import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BookOpen,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Download,
  Eye,
  Files,
  Image,
  Layers,
  type LucideIcon,
  type LucideProps,
  Pause,
  PenLine,
  Play,
  Pointer,
  RotateCcw,
  SkipBack,
  SkipForward,
  Sparkles,
  TriangleAlert,
  Trophy,
  Upload,
  Volume2,
  X,
} from "lucide-react";

type IconProps = LucideProps & { size?: number };

function icon(Glyph: LucideIcon, filled = false) {
  return ({ size = 20, ...rest }: IconProps) => (
    <Glyph size={size} strokeWidth={2} aria-hidden="true" focusable="false" fill={filled ? "currentColor" : "none"} {...rest} />
  );
}

export const PlayIcon = icon(Play, true);
export const PauseIcon = icon(Pause, true);
export const NextIcon = icon(SkipForward);
export const PrevIcon = icon(SkipBack);
export const ReplayIcon = icon(RotateCcw);
export const UploadIcon = icon(Upload);
export const ImageIcon = icon(Image);
export const EyeIcon = icon(Eye);
export const DownloadIcon = icon(Download);
export const SendIcon = icon(ArrowUp);
export const PenIcon = icon(PenLine);
export const CheckIcon = icon(Check);
export const CloseIcon = icon(X);
export const SparkIcon = icon(Sparkles);
export const SpeakerIcon = icon(Volume2);
export const TapIcon = icon(Pointer);
export const ArrowLeftIcon = icon(ArrowLeft);
export const ArrowRightIcon = icon(ArrowRight);
export const ChevronLeftIcon = icon(ChevronLeft);
export const ChevronRightIcon = icon(ChevronRight);
export const AlertIcon = icon(TriangleAlert);
export const QuestionIcon = icon(CircleHelp);
export const LayersIcon = icon(Layers);
export const BookIcon = icon(BookOpen);
export const LinkPagesIcon = icon(Files);
export const TrophyIcon = icon(Trophy);

/** Brand mark: a marker pen drawing a red circle on a dark tile (same as the favicon). */
export function LogoMark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <rect width="64" height="64" rx="16" fill="#1d1b26" />
      <path
        d="M37 15c-12-2-24 4-25 15s9 19 21 18c11-1 19-8 18-17"
        fill="none"
        stroke="#e03131"
        strokeWidth="4.5"
        strokeLinecap="round"
      />
      <path d="M33 37 52 14" stroke="#ffd43b" strokeWidth="7" strokeLinecap="round" />
      <path d="M33 37l-4 7 7-4" fill="#ffd43b" stroke="#ffd43b" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}
