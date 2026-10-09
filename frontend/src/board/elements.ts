// Excalidraw element factories and the customData tags that tell board layers apart.
import { convertToExcalidrawElements, FONT_FAMILY, ROUNDNESS } from "@excalidraw/excalidraw";
import type { ExcalidrawElementSkeleton } from "@excalidraw/excalidraw/data/transform";
import type { ExcalidrawElement, FileId } from "@excalidraw/excalidraw/element/types";
import type { AnnotationKind, Grounding } from "../types";
import { hashString, type PxBox, type Stroke, type XY } from "./strokes";

export type El = ExcalidrawElement;

export type TutorKind = AnnotationKind | "check" | "cross";

/** customData of every tutor element (one annotation may own several elements, see `part`). */
export interface TutorData {
  tutor: true;
  annotationId: string;
  stepIndex: number;
  kind: TutorKind;
  grounding: Grounding;
  confidence: number;
  /** `${stepIndex}:${annotationId}`: identifies the annotation on the board. */
  key: string;
  part: string;
  /** Opacity when fully visible (highlights are translucent). */
  baseOpacity: number;
}

export interface OverlayData {
  overlay: "regions" | "badges";
  key?: string;
  stepIndex?: number;
  baseOpacity: number;
}

export interface BoardData {
  board: "image" | "frame";
}

export const tutorData = (el: El): TutorData | null =>
  el.customData && el.customData.tutor === true ? (el.customData as TutorData) : null;

export const overlayData = (el: El): OverlayData | null =>
  el.customData && typeof el.customData.overlay === "string" ? (el.customData as OverlayData) : null;

export const isBoardImage = (el: El) => !!el.customData && typeof el.customData.board === "string";

/** Anything the student made (no board tag at all). */
export const isStudentElement = (el: El) => !tutorData(el) && !overlayData(el) && !isBoardImage(el);

/** Pen stroke width per Excalidraw freedraw strokeWidth unit at the pressures used here. */
const FREEHAND_GAIN = 2 * 4.25 * Math.sin((0.53 * Math.PI) / 2);

export function freedrawStrokeWidth(px: number): number {
  return px / FREEHAND_GAIN;
}

function sizeFromPoints(points: XY[]) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [x, y] of points) {
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  }
  return { width: maxX - minX, height: maxY - minY };
}

const relative = (abs: XY[]): XY[] => abs.map(([x, y]) => [x - abs[0][0], y - abs[0][1]]);

export interface Pen {
  color: string;
  /** Visible stroke width in scene px. */
  width: number;
  opacity: number;
}

/** A locked freedraw element. `done` marks the stroke as finished (pen lifted at the last point). */
export function freedrawElement(id: string, stroke: Stroke, pen: Pen, data: object, done: boolean): El {
  const points = relative(stroke.points);
  return {
    id,
    type: "freedraw",
    x: stroke.points[0][0],
    y: stroke.points[0][1],
    ...sizeFromPoints(points),
    angle: 0,
    strokeColor: pen.color,
    backgroundColor: "transparent",
    fillStyle: "solid",
    strokeWidth: freedrawStrokeWidth(pen.width),
    strokeStyle: "solid",
    roughness: 0,
    opacity: pen.opacity,
    groupIds: [],
    frameId: null,
    index: null,
    roundness: null,
    seed: hashString(id),
    version: 1,
    versionNonce: 0,
    isDeleted: false,
    boundElements: null,
    updated: Date.now(),
    link: null,
    locked: true,
    customData: data,
    points,
    pressures: stroke.pressures,
    simulatePressure: false,
    lastCommittedPoint: done ? points[points.length - 1] : null,
  } as unknown as El;
}

function fromSkeleton(skeleton: ExcalidrawElementSkeleton): El {
  const [el] = convertToExcalidrawElements([skeleton], { regenerateIds: false });
  return { ...el, index: null } as El;
}

/** Arrow template (no points yet); feed it to `arrowWithPoints` on every frame. */
export function arrowTemplate(id: string, pen: Pen, data: object): El {
  return fromSkeleton({
    type: "arrow",
    id,
    x: 0,
    y: 0,
    points: [
      [0, 0],
      [1, 1],
    ],
    strokeColor: pen.color,
    strokeWidth: pen.width,
    roughness: 1,
    opacity: pen.opacity,
    roundness: { type: ROUNDNESS.PROPORTIONAL_RADIUS },
    startArrowhead: null,
    endArrowhead: null,
    locked: true,
    customData: data,
    seed: hashString(id),
  } as unknown as ExcalidrawElementSkeleton);
}

export function arrowWithPoints(template: El, abs: XY[], head: boolean): El {
  const points = relative(abs);
  return {
    ...template,
    x: abs[0][0],
    y: abs[0][1],
    ...sizeFromPoints(points),
    points,
    endArrowhead: head ? "arrow" : null,
  } as unknown as El;
}

export interface TextStyle {
  fontSize: number;
  fontFamily: number;
  color: string;
  opacity: number;
}

/** A locked text element measured with Excalidraw's own text metrics (left/top anchored at x, y). */
export function textElement(id: string, text: string, x: number, y: number, style: TextStyle, data: object): El {
  return fromSkeleton({
    type: "text",
    id,
    x,
    y,
    text,
    fontSize: style.fontSize,
    fontFamily: style.fontFamily,
    strokeColor: style.color,
    opacity: style.opacity,
    textAlign: "left",
    verticalAlign: "top",
    locked: true,
    customData: data,
  } as ExcalidrawElementSkeleton);
}

export const HAND_FONT = FONT_FAMILY.Excalifont;
export const MONO_FONT = FONT_FAMILY.Cascadia;

/** The partially written text: same element box (left anchored), fewer characters. */
export function textPrefix(full: El, chars: number): El {
  const text = (full as unknown as { text: string }).text.slice(0, Math.max(1, chars));
  return { ...full, text, originalText: text } as unknown as El;
}

export interface RectStyle {
  stroke: string;
  fill: string;
  fillStyle?: "solid" | "hachure";
  strokeStyle?: "solid" | "dashed" | "dotted";
  strokeWidth: number;
  roughness: number;
  opacity: number;
  rounded?: boolean;
}

export function rectElement(id: string, box: PxBox, style: RectStyle, data: object): El {
  return fromSkeleton({
    type: "rectangle",
    id,
    x: box.x,
    y: box.y,
    width: Math.max(1, box.w),
    height: Math.max(1, box.h),
    strokeColor: style.stroke,
    backgroundColor: style.fill,
    fillStyle: style.fillStyle ?? "solid",
    strokeStyle: style.strokeStyle ?? "solid",
    strokeWidth: style.strokeWidth,
    roughness: style.roughness,
    opacity: style.opacity,
    roundness: style.rounded ? { type: ROUNDNESS.ADAPTIVE_RADIUS } : null,
    locked: true,
    customData: data,
    seed: hashString(id),
  } as unknown as ExcalidrawElementSkeleton);
}

export function imageElement(id: string, fileId: string, w: number, h: number): El {
  return fromSkeleton({
    type: "image",
    id,
    x: 0,
    y: 0,
    width: w,
    height: h,
    fileId: fileId as FileId,
    status: "saved",
    locked: true,
    customData: { board: "image" } satisfies BoardData,
  } as ExcalidrawElementSkeleton);
}
