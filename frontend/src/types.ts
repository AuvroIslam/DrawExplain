// Mirror of backend/app/schemas.py (the data contract). Keep the two files in sync.
// All Box/Point values are normalized to the processed image: x, y in [0, 1] from the
// top-left; w, h are fractions of Perception.width / Perception.height.

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Point {
  x: number;
  y: number;
}

// ---------------------------------------------------------------- perception

export type RegionKind = "text" | "text_block" | "shape" | "figure";
export type RegionSource = "ocr" | "opencv" | "merged" | "user";

export interface Region {
  id: string; // "R1".."Rn" in reading order
  kind: RegionKind;
  box: Box;
  text: string | null;
  score: number;
  source: RegionSource;
  parent_id: string | null;
}

export interface Perception {
  image_id: string;
  width: number; // processed image size in pixels
  height: number;
  regions: Region[];
  timings: Record<string, number>;
  image_url: string | null;
  marked_url: string | null;
  source_pages?: number | null; // page count when the upload was a PDF
}

// ---------------------------------------------------------------- lesson

export type AnnotationKind = "circle" | "box" | "underline" | "highlight" | "arrow" | "label";
export type Color = "red" | "blue" | "green" | "orange" | "purple";
export type Grounding = "consensus" | "cv_snap" | "id_only" | "llm_refined" | "llm_only" | "user";

/** circle/box/highlight -> box; underline -> points [start, end];
 *  arrow -> points [start, control, end] (+ label_box when text);
 *  label -> label_box + leader [from, to] + box (target). */
export interface Geometry {
  box: Box | null;
  points: Point[] | null;
  label_box: Box | null;
  leader: Point[] | null;
}

export interface Annotation {
  id: string;
  kind: AnnotationKind;
  color: Color;
  target_ids: string[];
  from_ids: string[];
  to_ids: string[];
  span: string | null;
  text: string | null;
  cue: string | null; // exact phrase in the step narration; draw when spoken
  geometry: Geometry;
  confidence: number;
  grounding: Grounding;
}

export interface Step {
  index: number; // 1-based
  title: string;
  narration: string;
  annotations: Annotation[];
}

export interface QuizItem {
  question: string;
  answer_ids: string[];
  answer_box: Box;
  explanation: string;
}

export interface Lesson {
  lesson_id: string;
  image_id: string;
  title: string;
  summary: string;
  steps: Step[];
  quiz: QuizItem[];
  model: string;
  timings: Record<string, number>;
  warnings: string[];
}

export interface LocatedTarget {
  query: string;
  box: Box | null;
  region_ids: string[];
  grounding: Grounding;
  confidence: number;
  llm_box: Box | null;
}

// ---------------------------------------------------------------- API

export interface LessonRequest {
  image_id: string;
  model?: string | null;
}

export interface FollowupRequest {
  image_id: string;
  lesson_id?: string | null;
  question: string;
  selection?: Box | null;
  model?: string | null;
}

export interface FollowupResponse {
  title: string;
  steps: Step[];
  model: string;
  timings: Record<string, number>;
  warnings: string[];
}

export interface TTSRequest {
  text: string;
  voice_id?: string | null;
}

export interface WordTiming {
  word: string;
  start: number; // seconds
  end: number;
  char_start: number; // index into the request text
  char_end: number; // exclusive
}

export interface TTSResponse {
  audio_url: string;
  duration: number;
  words: WordTiming[];
  cached: boolean;
}

export interface SampleInfo {
  name: string;
  url: string;
}

export interface LoadSampleRequest {
  name: string;
}

export interface Health {
  ok: boolean;
  model: string;
  tts: boolean;
}

/** Marker palette shared by the board and the UI. */
export const PALETTE: Record<Color, string> = {
  red: "#e03131",
  blue: "#1971c2",
  green: "#2f9e44",
  orange: "#f08c00",
  purple: "#9c36b5",
};
