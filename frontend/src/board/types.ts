// Contract between the whiteboard engine (src/board/**) and the app shell.
// The board is an Excalidraw canvas: the processed image sits at scene (0, 0) with its
// pixel size, so scene coordinates = normalized coordinates x (width, height).
import type { Annotation, Box, Color, Point, Region } from "../types";

export interface DrawOptions {
  /** 1-based step the drawing belongs to (follow-up steps continue the numbering). */
  stepIndex: number;
  /** Pen animation length; defaults depend on the kind (about 400-1200 ms). */
  durationMs?: number;
  /** Aborting finishes the drawing instantly instead of animating. */
  signal?: AbortSignal;
}

export type PreviousSteps = "dim" | "show" | "hide";

export interface BoardHandle {
  /** Put the image on the board (locked, at scene 0,0, pixel size) and fit the view. Clears the board. */
  loadImage(url: string, width: number, height: number): Promise<void>;
  /** Animate one tutor annotation as pen strokes; resolves when it is fully drawn. */
  drawAnnotation(annotation: Annotation, options: DrawOptions): Promise<void>;
  /** Draw annotations immediately without animation (jumping between steps, "show all"). */
  drawInstant(annotations: Annotation[], stepIndex: number): void;
  /** Remove tutor drawings of steps >= fromStep (all when omitted). Student drawings stay. */
  clearTutorDrawings(fromStep?: number): void;
  /** Emphasise the current step; earlier tutor drawings are dimmed, shown or hidden. */
  setCurrentStep(stepIndex: number, previous: PreviousSteps): void;
  /** "How it sees": outline every region with its id (null hides the overlay). */
  showRegions(regions: Region[] | null): void;
  /** Show or hide grounding badges (type + confidence) next to tutor drawings. */
  showBadges(on: boolean): void;
  /** Normalized bounding box of the student's own drawings (or selected elements); null if none. */
  getStudentSelection(): Box | null;
  clearStudentDrawings(): void;
  /** Quiz: route taps on the image to onTap in normalized coordinates. Returns a disposer. */
  enableTapMode(onTap: (p: Point) => void): () => void;
  /** Quiz feedback: green ring around the answer / small cross at a wrong tap. */
  drawCheck(box: Box, color?: Color): Promise<void>;
  drawCross(at: Point, color?: Color): Promise<void>;
  /** PNG of the image plus every drawing ("Save my notes"). */
  exportPng(): Promise<Blob>;
  /** Fit the image in view (with room for margin notes). */
  fitToImage(): void;
}

export interface WhiteboardBoardProps {
  onReady: (handle: BoardHandle) => void;
  /** Called when the student's own drawings change (enables "Ask about my drawing"). */
  onStudentDrawingChange?: (hasDrawing: boolean) => void;
  theme?: "light" | "dark";
  className?: string;
}

// Implementation: src/board/WhiteboardBoard.tsx
//   export default function WhiteboardBoard(props: WhiteboardBoardProps): JSX.Element
