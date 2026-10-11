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
  doc_id?: string | null; // set when this image is a page of an uploaded document
  page?: number | null; // 1-based page number within that document
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
  sketch?: string | null; // Mermaid flowchart drawn beside the page (process / algorithm summary)
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
  question?: string | null; // the student's focus question, when one was asked
  context_pages?: number[]; // earlier document pages the lesson builds on
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
  question?: string | null; // optional: what the student wants explained on this page
}

/** An uploaded PDF: pages are browsed as plain images (no scan); a page is perceived only when the
 *  student asks for it to be explained (POST /api/documents/{doc_id}/pages/{page}/perceive). */
export interface DocumentInfo {
  doc_id: string;
  filename: string;
  pages: number;
  title: string | null;
  page_sizes: [number, number][]; // [width, height] px of each rendered page image (page i -> index i-1)
  page_url: string; // template like "/api/documents/<doc_id>/pages/{page}.png"
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
  red: "#c92a2a",
  blue: "#1864ab",
  green: "#2b8a3e",
  orange: "#d9480f",
  purple: "#862e9c",
};

/** Ink of a step's margin sketch: the colour its annotations use most (orange reads poorly as text), else blue. */
export function stepInk(annotations: Annotation[]): Color {
  const count = new Map<Color, number>();
  for (const a of annotations) if (a.color !== "orange" && a.color in PALETTE) count.set(a.color, (count.get(a.color) ?? 0) + 1);
  let best: Color = "blue";
  let most = 0;
  for (const [color, n] of count) {
    if (n > most) {
      best = color;
      most = n;
    }
  }
  return best;
}
