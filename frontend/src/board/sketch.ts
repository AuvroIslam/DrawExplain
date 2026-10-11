// Margin sketches: Step.sketch is a small Mermaid flowchart. mermaid-to-excalidraw lays it out (the
// parser pulls in mermaid, so it is loaded on first use), then the chart is restyled as the tutor's
// own hand-drawn ink and handed to the engine, which places it beside the page and reveals it.
import { convertToExcalidrawElements, getCommonBounds, ROUNDNESS } from "@excalidraw/excalidraw";
import type { ExcalidrawElementSkeleton } from "@excalidraw/excalidraw/data/transform";
import { type El, HAND_FONT } from "./elements";
import { clamp, hashString, type XY } from "./strokes";

/** Label font size mermaid lays the chart out with (it is scaled with the chart afterwards). */
export const SKETCH_FONT = 20;

/** "down": a column for the margin beside the page; "across": a row for under it. */
export type SketchFlow = "down" | "across";

export type Bounds = [number, number, number, number];

/** The parts of a mermaid-to-excalidraw skeleton used here (the package types them loosely). */
interface Skel {
  type: string;
  id?: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  points?: XY[];
  fontSize?: number;
  label?: { text?: string; fontSize?: number; verticalAlign?: string };
  start?: { id?: string };
  end?: { id?: string };
  strokeStyle?: string;
  strokeWidth?: number;
}

export interface SketchLayout {
  skeletons: Skel[];
  bounds: Bounds;
}

/** Elements that appear together: a node with its label, or an arrow (first) with its label. */
export interface SketchPiece {
  els: El[];
  arrow: boolean;
}

export interface BuiltSketch {
  /** In pen order. */
  pieces: SketchPiece[];
  bounds: Bounds;
}

const SHAPES = new Set(["rectangle", "ellipse", "diamond"]);
/** Excalidraw wraps a label bound to these to their inscribed box (half a diamond's width), which splits
 *  short words ("Vali/d?"); mermaid sized the shape to hold the label, so it is centred as plain text. */
const FREE_LABEL_SHAPES = new Set(["ellipse", "diamond"]);
const LINES = new Set(["arrow", "line"]);
const HEADER = /^\s*(flowchart|graph)\s+(TD|TB|BT|LR|RL)\b/i;
const FONT_STACK = "Excalifont, Xiaolai, sans-serif";

/** Mermaid settings: labels are measured in the board's hand font (so node boxes fit its wider letters) and
 *  wrap only when really long (the board draws a short label on one line); compact spacing. */
const MERMAID_CONFIG = {
  startOnLoad: false,
  suppressErrorRendering: true,
  fontFamily: FONT_STACK,
  flowchart: { curve: "linear", nodeSpacing: 30, rankSpacing: 32, padding: 7, wrappingWidth: 360 },
  themeVariables: { fontSize: `${SKETCH_FONT}px`, fontFamily: FONT_STACK },
  maxEdges: 80,
  maxTextSize: 4000,
};

/** The chart turned for its spot (a margin column reads top to bottom), or null if it is not a flowchart. */
export function sketchSource(raw: string, flow: SketchFlow): string | null {
  const text = raw
    .trim()
    .replace(/^```(?:mermaid)?\s*/i, "")
    .replace(/\s*```$/, "");
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  const m = lines.length ? HEADER.exec(lines[0]) : null;
  if (!m) return null;
  const reversed = /^(BT|RL)$/i.test(m[2]);
  const dir = flow === "down" ? (reversed ? "BT" : "TD") : reversed ? "RL" : "LR";
  lines[0] = lines[0].replace(HEADER, `flowchart ${dir}`);
  return lines.join("\n");
}

type Parser = typeof import("@excalidraw/mermaid-to-excalidraw");
let parser: Promise<Parser> | null = null;
const layouts = new Map<string, Promise<SketchLayout>>();

function loadParser(): Promise<Parser> {
  parser ??= import("@excalidraw/mermaid-to-excalidraw").catch((err: unknown) => {
    parser = null; // a chunk that failed to load may load next time
    throw err;
  });
  return parser;
}

function skeletonBounds(skeletons: Skel[]): Bounds {
  const b: Bounds = [Infinity, Infinity, -Infinity, -Infinity];
  const add = (x: number, y: number) => {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    b[0] = Math.min(b[0], x);
    b[1] = Math.min(b[1], y);
    b[2] = Math.max(b[2], x);
    b[3] = Math.max(b[3], y);
  };
  for (const s of skeletons) {
    const x = s.x ?? 0;
    const y = s.y ?? 0;
    add(x, y);
    if (s.points) for (const [px, py] of s.points) add(x + px, y + py);
    else add(x + (s.width ?? 0), y + (s.height ?? 0));
  }
  return b[0] <= b[2] ? b : [0, 0, 1, 1];
}

async function parse(source: string): Promise<SketchLayout> {
  const { parseMermaidToExcalidraw } = await loadParser();
  const config = MERMAID_CONFIG as unknown as Parameters<typeof parseMermaidToExcalidraw>[1];
  const result = await parseMermaidToExcalidraw(source, config);
  const skeletons = (result.elements ?? []) as unknown as Skel[];
  // anything else (an image fallback for diagrams it cannot convert) is not a sketch we can draw
  if (!skeletons.some((s) => SHAPES.has(s.type)) || skeletons.some((s) => !SHAPES.has(s.type) && !LINES.has(s.type) && s.type !== "text")) {
    throw new Error("not a flowchart the board can draw");
  }
  return { skeletons, bounds: skeletonBounds(skeletons) };
}

/** Mermaid's layout of a flowchart source (cached; rejects when it cannot be parsed). */
export function layoutSketch(source: string): Promise<SketchLayout> {
  const hit = layouts.get(source);
  if (hit) return hit;
  const p = parse(source);
  layouts.set(source, p);
  p.catch(() => layouts.delete(source));
  return p;
}

export interface SketchStyle {
  color: string;
  strokeWidth: number;
}

/**
 * The layout restyled as tutor ink (marker colour, rough strokes, hand font), its top-left at `at`,
 * scaled by `scale`. Every element is locked and tagged with `tag(part)`. Pieces come in pen order:
 * each node right after the arrow that leads into it, so the chart grows the way a teacher draws it.
 */
export function buildSketch(
  layout: SketchLayout,
  at: XY,
  scale: number,
  style: SketchStyle,
  idPrefix: string,
  tag: (part: string) => object,
): BuiltSketch {
  const [bx, by] = layout.bounds;
  const id = (raw: string) => `${idPrefix}${raw}`;
  let anon = 0;
  /** Unbound node labels (diamonds, ellipses) by text id: their node and the point they are centred on. */
  const freeLabels = new Map<string, { node: string; at: XY }>();
  const extra: Record<string, unknown>[] = [];
  const skels = layout.skeletons.map((s) => {
    const sid = id(s.id ?? `part${++anon}`);
    const out: Record<string, unknown> = {
      ...s,
      id: sid,
      x: at[0] + ((s.x ?? 0) - bx) * scale,
      y: at[1] + ((s.y ?? 0) - by) * scale,
      groupIds: [],
      strokeColor: style.color,
      backgroundColor: "transparent",
      fillStyle: "solid",
      strokeWidth: style.strokeWidth * ((s.strokeWidth ?? 2) > 2 ? 1.5 : 1),
      strokeStyle: s.strokeStyle === "dashed" ? "dashed" : "solid",
      roughness: 1,
      opacity: 100,
      locked: true,
      link: null,
      seed: hashString(sid),
    };
    if (s.width !== undefined) out.width = s.width * scale;
    if (s.height !== undefined) out.height = s.height * scale;
    if (s.points) out.points = s.points.map(([px, py]) => [px * scale, py * scale]);
    delete out.label;
    // mermaid lays a <br> out as a line break; the board would print it
    const text = s.label?.text?.replace(/<br\s*\/?>/gi, "\n").trim();
    if (s.label && text) {
      // an arrow's caption is a side note: a little smaller than the node labels
      const fontSize = (s.label.fontSize ?? SKETCH_FONT) * scale * (LINES.has(s.type) ? 0.85 : 1);
      if (FREE_LABEL_SHAPES.has(s.type)) {
        const lid = `${sid}:label`;
        const mid: XY = [Number(out.x) + ((s.width ?? 0) * scale) / 2, Number(out.y) + ((s.height ?? 0) * scale) / 2];
        freeLabels.set(lid, { node: sid, at: mid });
        extra.push({ type: "text", id: lid, x: mid[0], y: mid[1], text, fontSize, fontFamily: HAND_FONT, strokeColor: style.color, textAlign: "center", verticalAlign: "middle", opacity: 100, locked: true });
      } else {
        out.label = {
          text,
          fontSize,
          fontFamily: HAND_FONT,
          strokeColor: style.color,
          ...(s.label.verticalAlign ? { verticalAlign: s.label.verticalAlign } : {}),
        };
      }
    }
    if (s.type === "rectangle") out.roundness = { type: ROUNDNESS.ADAPTIVE_RADIUS };
    if (s.type === "text") {
      out.fontSize = (s.fontSize ?? SKETCH_FONT) * scale;
      out.fontFamily = HAND_FONT;
    }
    if (LINES.has(s.type)) {
      out.start = s.start?.id ? { id: id(s.start.id) } : undefined;
      out.end = s.end?.id ? { id: id(s.end.id) } : undefined;
    }
    return out;
  });

  const converted = convertToExcalidrawElements([...skels, ...extra] as unknown as ExcalidrawElementSkeleton[], { regenerateIds: false });
  // static ink: arrows keep their drawn path, nothing is bound to anything but its own label
  const els = converted.map((el) => {
    const free = freeLabels.get(el.id);
    const container = free?.node ?? (el as { containerId?: string | null }).containerId ?? null;
    const part = el.type === "text" && container ? `label:${container}` : `${el.type}:${el.id}`;
    return {
      ...el,
      ...(free ? { x: free.at[0] - el.width / 2, y: free.at[1] - el.height / 2 } : {}),
      locked: true,
      index: null,
      ...(LINES.has(el.type) ? { startBinding: null, endBinding: null } : {}),
      boundElements: el.boundElements?.filter((b) => b.type === "text") ?? null,
      customData: tag(part),
    } as unknown as El;
  });

  const byId = new Map(els.map((el) => [el.id, el]));
  const labels = new Map<string, El>();
  for (const el of els) {
    const container = freeLabels.get(el.id)?.node ?? (el as { containerId?: string | null }).containerId;
    if (el.type === "text" && container) labels.set(container, el);
  }
  const piece = (el: El): SketchPiece => {
    const label = labels.get(el.id);
    return { els: label ? [el, label] : [el], arrow: LINES.has(el.type) };
  };
  const nodes: { id: string; el: El }[] = [];
  const edges: { el: El; from?: string; to?: string }[] = [];
  for (const s of skels) {
    const el = byId.get(String(s.id));
    if (!el) continue;
    if (SHAPES.has(String(s.type))) nodes.push({ id: el.id, el });
    else if (LINES.has(String(s.type))) {
      const from = (s.start as { id?: string } | undefined)?.id;
      const to = (s.end as { id?: string } | undefined)?.id;
      edges.push({ el, from, to });
    }
  }
  const pieces: SketchPiece[] = [];
  const drawn = new Set<string>();
  const used = new Set<number>();
  const take = (ok: (e: (typeof edges)[number]) => boolean) =>
    edges.forEach((e, i) => {
      if (used.has(i) || !ok(e)) return;
      used.add(i);
      pieces.push(piece(e.el));
    });
  const ready = (end?: string) => !end || drawn.has(end);
  for (const n of nodes) {
    take((e) => e.to === n.id && !!e.from && drawn.has(e.from)); // the arrow that leads here
    pieces.push(piece(n.el));
    drawn.add(n.id);
    take((e) => ready(e.from) && ready(e.to)); // loops back to nodes already drawn
  }
  take(() => true);
  for (const el of els) {
    if (el.type === "text" && !(el as { containerId?: string | null }).containerId && !freeLabels.has(el.id)) {
      pieces.push({ els: [el], arrow: false });
    }
  }
  const [x0, y0, x1, y1] = getCommonBounds(els);
  return { pieces, bounds: [x0, y0, x1, y1] };
}

/** The arrow drawn up to fraction `f` of its length (no head until it is complete). */
export function arrowPrefix(arrow: El, f: number): El {
  const pts = (arrow as unknown as { points: XY[] }).points;
  if (f >= 1 || pts.length < 2) return arrow;
  const want = clamp(f, 0.04, 1);
  const seg: number[] = [];
  let total = 0;
  for (let i = 1; i < pts.length; i++) {
    const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    seg.push(d);
    total += d;
  }
  let left = want * total;
  const out: XY[] = [pts[0]];
  for (let i = 1; i < pts.length; i++) {
    const d = seg[i - 1];
    if (left >= d) {
      out.push(pts[i]);
      left -= d;
      continue;
    }
    const k = d > 0 ? left / d : 0;
    out.push([pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * k, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k]);
    break;
  }
  if (out.length < 2) out.push(pts[1]);
  const xs = out.map((p) => p[0]);
  const ys = out.map((p) => p[1]);
  return {
    ...arrow,
    points: out,
    width: Math.max(...xs) - Math.min(...xs),
    height: Math.max(...ys) - Math.min(...ys),
    endArrowhead: null,
    startArrowhead: null,
  } as unknown as El;
}
