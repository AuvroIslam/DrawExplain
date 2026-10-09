// The whiteboard engine behind WhiteboardBoard: owns the Excalidraw scene and implements BoardHandle.
//
// Every change goes through stage()/flush(): animations stage the next version of their elements,
// and one requestAnimationFrame loop commits everything staged with a single updateScene
// (CaptureUpdateAction.NEVER, so tutor drawing never lands on the student's undo stack). A flush
// rebuilds the element list from the live scene, so student drawings and overlays are never lost.
import {
  CaptureUpdateAction,
  exportToBlob,
  getCommonBounds,
  newElementWith,
  viewportCoordsToSceneCoords,
} from "@excalidraw/excalidraw";
import type { AppState, BinaryFileData, DataURL, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import type { FileId } from "@excalidraw/excalidraw/element/types";
import { type Annotation, type Box, type Color, PALETTE, type Point, type Region, type RegionKind, stepInk } from "../types";
import {
  arrowTemplate,
  arrowWithPoints,
  type El,
  freedrawElement,
  HAND_FONT,
  imageElement,
  isStudentElement,
  MONO_FONT,
  type OverlayData,
  overlayData,
  type Pen,
  rectElement,
  textElement,
  textPrefix,
  type TutorData,
  tutorData,
  type TutorKind,
} from "./elements";
import {
  clamp,
  crossStrokes,
  curvedLine,
  easeInOutSine,
  ellipseStroke,
  hashString,
  type PxBox,
  quadPrefix,
  roundedRectStroke,
  type Stroke,
  strokePrefix,
  wavyLine,
  type XY,
} from "./strokes";
import { arrowPrefix, type Bounds, buildSketch, layoutSketch, SKETCH_FONT, type SketchLayout, type SketchPiece, sketchSource } from "./sketch";
import type { BoardHandle, DrawOptions, PreviousSteps } from "./types";

type Api = ExcalidrawImperativeAPI;

/** Where a margin sketch sits: beside the page, or under a portrait page when that shows it bigger. */
type SketchSide = "right" | "below";

interface SketchArea {
  stepIndex: number;
  side: SketchSide;
  bounds: Bounds;
}

interface View {
  zoom: number;
  scrollX: number;
  scrollY: number;
}

/** Extra hooks for the dev harness and tests (not part of the BoardHandle contract). */
export interface BoardDebug {
  /** Plain snapshot of the scene (no deleted elements). */
  debugScene(): DebugElement[];
  /** Client (page) coordinates of a scene point, e.g. to click on the image in a test. */
  sceneToClient(x: number, y: number): { x: number; y: number } | null;
}

export interface DebugElement {
  id: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  opacity: number;
  locked: boolean;
  text?: string;
  fontSize?: number;
  points?: number;
  bounds: [number, number, number, number];
  customData?: Record<string, unknown>;
}

interface Run {
  key: string;
  stepIndex: number;
  signal?: AbortSignal;
  cancelled: boolean;
}

interface Tick {
  run: Run | null;
  fn: (now: number) => boolean;
  done: () => void;
}

interface Phase {
  ms: number;
  /** Draw the state at linear time t in 0..1 (each phase applies its own easing). */
  frame: (t: number) => void;
}

/** Default pen timings in ms. */
const MS = { circle: 820, box: 860, underline: 420, highlight: 460, arrow: 620, leader: 260, char: 35, check: 720, cross: 150 };
/** Margin sketch: pause while the view widens, then one node or arrow every `piece` ms; view glide length. */
const SKETCH_MS = { lead: 600, piece: 150, glide: 650 };
const SKETCH_ID = "sketch";
/** Sketch box beside the page (fractions of the page): starts at 1.06 x width, fits 0.6 x width by 0.85 x height. */
const SKETCH_BOX = { gap: 0.06, w: 0.6, h: 0.85, belowH: 0.45 };
const DIM = 0.3;
const HIGHLIGHT_OPACITY = 30;
const REGION_COLORS: Record<RegionKind, string> = {
  text: "#1971c2",
  text_block: "#0c8599",
  shape: "#f08c00",
  figure: "#c2255c",
};
const BADGE_COLOR = "#495057";
const FRAME_COLOR = "#d3cfc6";
const FONT_SAMPLE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:!?'\"()-+=/%&";

const annotationKey = (stepIndex: number, id: string) => `${stepIndex}:${id}`;
const elementId = (key: string, part: string) => `tutor:${key}:${part}`;
const unionBounds = (a: Bounds, b: Bounds): Bounds => [
  Math.min(a[0], b[0]),
  Math.min(a[1], b[1]),
  Math.max(a[2], b[2]),
  Math.max(a[3], b[3]),
];

const sleep = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));
const nextFrame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));

function bump(el: El, patch: Record<string, unknown>): El {
  return newElementWith(el, patch as Parameters<typeof newElementWith>[1], true);
}

function finite(...values: number[]): boolean {
  return values.every((v) => Number.isFinite(v));
}

/** Mime type from the first bytes (servers and blob: URLs do not always say). */
function sniffImageType(bytes: Uint8Array): string | null {
  const at = (i: number, ...v: number[]) => v.every((b, k) => bytes[i + k] === b);
  if (at(0, 0x89, 0x50, 0x4e, 0x47)) return "image/png";
  if (at(0, 0xff, 0xd8, 0xff)) return "image/jpeg";
  if (at(0, 0x52, 0x49, 0x46, 0x46) && at(8, 0x57, 0x45, 0x42, 0x50)) return "image/webp";
  if (at(0, 0x47, 0x49, 0x46, 0x38)) return "image/gif";
  return null;
}

async function fetchImage(url: string): Promise<{ dataURL: string; mimeType: string }> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Could not load the image (${res.status})`);
  let blob = await res.blob();
  const head = new Uint8Array(await blob.slice(0, 16).arrayBuffer());
  const mimeType = blob.type.startsWith("image/") ? blob.type : (sniffImageType(head) ?? "image/png");
  if (blob.type !== mimeType) blob = new Blob([blob], { type: mimeType });
  const dataURL = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the image"));
    reader.readAsDataURL(blob);
  });
  return { dataURL, mimeType };
}

export class BoardEngine {
  private candidates: Api[] = [];
  private api: Api | null = null;
  private readyPromise: Promise<void> | null = null;
  private container: HTMLElement | null = null;
  private img: { w: number; h: number } | null = null;
  private loadToken = 0;

  private pending = new Map<string, El>();
  private removals = new Set<string>();
  private ticks = new Set<Tick>();
  private runs = new Set<Run>();
  private raf = 0;

  private currentStep = 0;
  private previous: PreviousSteps = "show";
  private badgesOn = false;
  private regionsToken = 0;
  private markSeq = 0;

  private lastFit: View | null = null;
  private autoFit = true;
  /** Screen px at the bottom of the board the fitted page keeps clear of (overlay buttons). */
  private bottomInset = 0;
  /** Bumped by every view change, so a glide in progress stops. */
  private viewToken = 0;
  private refitQueued = false;
  /** Margin sketches on the board, by annotation key (the fitted view includes the visible ones). */
  private sketchAreas = new Map<string, SketchArea>();
  private resizeObserver: ResizeObserver | null = null;
  private unsubscribeScroll: (() => void) | null = null;
  private tapCleanup: (() => void) | null = null;

  private onStudentChange: ((has: boolean) => void) | null = null;
  private studentLatest = false;
  private studentReported = false;
  private studentTimer = 0;

  readonly handle: BoardHandle & BoardDebug = {
    loadImage: (url, width, height) => this.loadImage(url, width, height),
    drawAnnotation: (annotation, options) => this.drawAnnotation(annotation, options),
    drawSketch: (mermaid, options) => this.drawSketch(mermaid, options),
    drawInstant: (annotations, stepIndex, sketch) => this.drawInstant(annotations, stepIndex, sketch),
    clearTutorDrawings: (fromStep) => this.clearTutorDrawings(fromStep),
    setCurrentStep: (stepIndex, previous) => this.setCurrentStep(stepIndex, previous),
    showRegions: (regions) => this.showRegions(regions),
    showBadges: (on) => this.showBadges(on),
    getStudentSelection: () => this.getStudentSelection(),
    clearStudentDrawings: () => this.clearStudentDrawings(),
    enableTapMode: (onTap) => this.enableTapMode(onTap),
    drawCheck: (box, color) => this.drawCheck(box, color),
    drawCross: (at, color) => this.drawCross(at, color),
    exportPng: () => this.exportPng(),
    fitToImage: () => this.fitToImage(),
    debugScene: () => this.debugScene(),
    sceneToClient: (x, y) => this.sceneToClient(x, y),
  };

  // ------------------------------------------------------------------ lifecycle

  /** Excalidraw's excalidrawAPI callback (may fire for a discarded StrictMode instance too). */
  readonly setApi = (api: Api) => {
    if (!this.candidates.includes(api)) this.candidates.push(api);
  };

  attach(container: HTMLElement, onStudentChange: (has: boolean) => void) {
    this.container = container;
    this.onStudentChange = onStudentChange;
    this.resizeObserver = new ResizeObserver(() => {
      if (this.autoFit) this.fitToImage();
    });
    this.resizeObserver.observe(container);
  }

  detach() {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    this.tapCleanup?.();
    this.unsubscribeScroll?.();
    this.unsubscribeScroll = null;
    window.clearTimeout(this.studentTimer);
    this.cancelRuns(() => true);
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
    this.container = null;
    this.onStudentChange = null;
  }

  /** Resolves once the mounted Excalidraw instance finished its own scene initialisation. */
  whenReady(): Promise<void> {
    this.readyPromise ??= (async () => {
      const started = performance.now();
      for (;;) {
        await nextFrame();
        const live = this.candidates.find((api) => !api.getAppState().isLoading);
        if (live) {
          await nextFrame();
          if (!live.getAppState().isLoading) {
            this.api = live;
            break;
          }
        }
        if (performance.now() - started > 15000) throw new Error("The whiteboard did not start");
      }
      this.unsubscribeScroll = this.api.onScrollChange((scrollX, scrollY, zoom) => {
        const f = this.lastFit;
        if (!f) return;
        const moved =
          Math.abs(f.zoom - zoom.value) > 1e-3 || Math.abs(f.scrollX - scrollX) > 0.5 || Math.abs(f.scrollY - scrollY) > 0.5;
        if (moved) this.autoFit = false;
      });
      void this.preloadFonts();
    })();
    return this.readyPromise;
  }

  /** Excalidraw onChange: report whether the student has drawings of their own (debounced). */
  readonly onSceneChange = (elements: readonly El[]) => {
    let has = false;
    for (const el of elements) {
      if (!el.isDeleted && isStudentElement(el)) {
        has = true;
        break;
      }
    }
    this.studentLatest = has;
    if (has === this.studentReported) {
      window.clearTimeout(this.studentTimer);
      this.studentTimer = 0;
      return;
    }
    if (this.studentTimer) return;
    this.studentTimer = window.setTimeout(() => {
      this.studentTimer = 0;
      if (this.studentLatest !== this.studentReported) {
        this.studentReported = this.studentLatest;
        this.onStudentChange?.(this.studentReported);
      }
    }, 150);
  };

  private async preloadFonts() {
    try {
      await Promise.race([
        Promise.all([document.fonts.load("20px Excalifont", FONT_SAMPLE), document.fonts.load("20px Cascadia", FONT_SAMPLE)]),
        sleep(2500),
      ]);
    } catch {
      // the browser falls back to a system font; drawings still work
    }
  }

  // ------------------------------------------------------------------ scene plumbing

  private get penWidth(): number {
    const img = this.img;
    return img ? Math.max(2.5, 0.0028 * Math.max(img.w, img.h)) : 3;
  }

  /** Scene size that shows as `px` screen pixels at the fitted zoom (overlay text stays legible on big images). */
  private screenPx(px: number): number {
    const zoom = this.lastFit?.zoom ?? this.api?.getAppState().zoom.value ?? 1;
    return px / clamp(zoom, 0.1, 4);
  }

  private pxBox(b: Box | null | undefined): PxBox | null {
    const img = this.img;
    if (!img || !b || !finite(b.x, b.y, b.w, b.h) || b.w <= 0 || b.h <= 0) return null;
    return { x: b.x * img.w, y: b.y * img.h, w: b.w * img.w, h: b.h * img.h };
  }

  private xy(p: Point | null | undefined): XY | null {
    const img = this.img;
    if (!img || !p || !finite(p.x, p.y)) return null;
    return [p.x * img.w, p.y * img.h];
  }

  private stage(el: El) {
    this.removals.delete(el.id);
    this.pending.set(el.id, el);
    this.schedule();
  }

  private remove(id: string) {
    this.pending.delete(id);
    this.removals.add(id);
    this.schedule();
  }

  private schedule() {
    if (!this.raf) this.raf = requestAnimationFrame(this.loop);
  }

  private readonly loop = (now: number) => {
    this.raf = 0;
    for (const tick of [...this.ticks]) {
      let finished = true;
      try {
        finished = tick.fn(now);
      } catch (err) {
        console.error("whiteboard animation failed", err);
      }
      if (finished && this.ticks.delete(tick)) tick.done();
    }
    this.flush();
    if (this.ticks.size) this.schedule();
  };

  /** Opacity a tutor element (or its badge) should have under the current step emphasis. */
  private targetOpacity(stepIndex: number, base: number): number {
    if (this.currentStep <= 0 || stepIndex >= this.currentStep || this.previous === "show") return base;
    if (this.previous === "hide") return 0;
    return Math.max(1, Math.round(base * DIM));
  }

  private visible(el: El): El {
    const t = tutorData(el);
    const o = t ? null : overlayData(el);
    const step = t ? t.stepIndex : o?.overlay === "badges" ? o.stepIndex : undefined;
    if (step === undefined) return el;
    const want = this.targetOpacity(step, (t ?? o)?.baseOpacity ?? 100);
    return el.opacity === want ? el : bump(el, { opacity: want });
  }

  /** Commit everything staged with one updateScene, keeping every other element as it is. */
  private flush(extraTransform?: (el: El) => El) {
    const api = this.api;
    if (!api) return;
    const current = api.getSceneElementsIncludingDeleted();
    const next: El[] = [];
    const seen = new Set<string>();
    let changed = false;
    for (const el of current) {
      if (this.removals.has(el.id)) {
        changed = true;
        continue;
      }
      let out: El = el;
      const staged = this.pending.get(el.id);
      if (staged) {
        seen.add(el.id);
        const { id: _id, version: _v, versionNonce: _n, updated: _u, index: _i, ...patch } = staged;
        out = bump(el, { ...patch, isDeleted: false });
      }
      if (extraTransform) out = extraTransform(out);
      out = this.visible(out);
      if (out !== el) changed = true;
      next.push(out);
    }
    for (const [id, el] of this.pending) {
      if (seen.has(id)) continue;
      next.push(this.visible({ ...el, index: null } as El));
      changed = true;
    }
    this.pending.clear();
    this.removals.clear();
    if (changed) api.updateScene({ elements: next, captureUpdate: CaptureUpdateAction.NEVER });
  }

  /** Scene elements plus staged ones (staged versions win), excluding removed and deleted. */
  private liveElements(): El[] {
    const api = this.api;
    const out: El[] = [];
    const seen = new Set<string>();
    for (const el of api?.getSceneElements() ?? []) {
      if (this.removals.has(el.id)) continue;
      seen.add(el.id);
      out.push(this.pending.get(el.id) ?? el);
    }
    for (const [id, el] of this.pending) if (!seen.has(id)) out.push(el);
    return out;
  }

  // ------------------------------------------------------------------ animation

  private play(run: Run | null, ms: number, frame: (t: number) => void): Promise<void> {
    if (run?.cancelled) return Promise.resolve();
    if (ms <= 0 || run?.signal?.aborted) {
      frame(1);
      this.schedule();
      return Promise.resolve();
    }
    return new Promise<void>((resolve) => {
      let t0 = -1;
      const signal = run?.signal;
      const tick: Tick = {
        run,
        fn: (now) => {
          if (run?.cancelled) return true;
          if (signal?.aborted) {
            frame(1);
            return true;
          }
          if (t0 < 0) t0 = now;
          const t = Math.min(1, (now - t0) / ms);
          frame(t);
          return t >= 1;
        },
        done: () => {
          signal?.removeEventListener("abort", onAbort);
          resolve();
        },
      };
      // Aborting lands the stroke at once (the player waits for it before clearing the board).
      const onAbort = () => {
        if (!this.ticks.delete(tick)) return;
        if (!run?.cancelled) frame(1);
        this.schedule();
        tick.done();
      };
      signal?.addEventListener("abort", onAbort, { once: true });
      this.ticks.add(tick);
      this.schedule();
    });
  }

  private cancelRuns(match: (run: Run) => boolean) {
    for (const run of [...this.runs]) {
      if (!match(run)) continue;
      run.cancelled = true;
      this.runs.delete(run);
    }
    for (const tick of [...this.ticks]) {
      if (tick.run?.cancelled && this.ticks.delete(tick)) tick.done();
    }
  }

  private async animate(key: string, stepIndex: number, phases: Phase[], options?: DrawOptions) {
    this.cancelRuns((r) => r.key === key);
    const run: Run = { key, stepIndex, signal: options?.signal, cancelled: false };
    this.runs.add(run);
    try {
      const total = phases.reduce((s, p) => s + p.ms, 0);
      const want = options?.durationMs;
      const scale = want && want > 0 && total > 0 ? clamp(want, 120, 8000) / total : 1;
      for (const phase of phases) {
        if (run.cancelled) return;
        await this.play(run, phase.ms * scale, (t) => {
          if (!run.cancelled) phase.frame(t);
        });
      }
      if (!run.cancelled && this.badgesOn) this.stageBadge(key);
    } finally {
      this.runs.delete(run);
    }
  }

  // ------------------------------------------------------------------ pen plans per kind

  private tutorData(a: Pick<Annotation, "id" | "grounding" | "confidence">, kind: TutorKind, step: number, part: string, base = 100): TutorData {
    return {
      tutor: true,
      annotationId: a.id,
      stepIndex: step,
      kind,
      grounding: a.grounding,
      confidence: a.confidence,
      key: annotationKey(step, a.id),
      part,
      baseOpacity: base,
    };
  }

  private strokePhase(id: string, stroke: Stroke, pen: Pen, data: TutorData, ms: number): Phase {
    return {
      ms,
      frame: (t) => this.stage(freedrawElement(id, strokePrefix(stroke, easeInOutSine(t)), pen, data, t >= 1)),
    };
  }

  /** Handwriting: the text element grows one character at a time at its final position. */
  private writePhases(id: string, text: string, box: PxBox, color: string, data: TutorData): Phase[] {
    const clean = text.trim();
    if (!clean) return [];
    const full = this.fitText(id, clean, box, color, data);
    const n = Array.from(clean).length;
    return [
      {
        ms: MS.char * n,
        frame: (t) => this.stage(t >= 1 ? full : textPrefix(full, Math.max(1, Math.ceil(t * n)))),
      },
    ];
  }

  /** Excalifont text sized from the label box height (the server plans boxes as 1.3x its font size from
   *  the page's own text), shrunk only if it would overflow the box width, centred in the box. */
  private fitText(id: string, text: string, box: PxBox, color: string, data: TutorData): El {
    let fontSize = clamp(box.h / 1.3, 10, 160);
    const style = { fontFamily: HAND_FONT, color, opacity: 100 };
    let el = textElement(id, text, box.x, box.y, { ...style, fontSize }, data);
    const room = box.w * 1.04;
    if (el.width > room) {
      fontSize = Math.max(fontSize * 0.6, (fontSize * room) / el.width);
      el = textElement(id, text, box.x, box.y, { ...style, fontSize }, data);
    }
    return { ...el, x: box.x + (box.w - el.width) / 2, y: box.y + (box.h - el.height) / 2 } as El;
  }

  private phasesFor(a: Annotation, step: number): Phase[] {
    const g = a.geometry ?? { box: null, points: null, label_box: null, leader: null };
    const color = PALETTE[a.color] ?? PALETTE.red;
    const key = annotationKey(step, a.id);
    const seed = hashString(key);
    const pen: Pen = { color, width: this.penWidth, opacity: 100 };
    const data = (part: string, base = 100) => this.tutorData(a, a.kind, step, part, base);
    const id = (part: string) => elementId(key, part);
    switch (a.kind) {
      case "circle": {
        const box = this.pxBox(g.box);
        return box ? [this.strokePhase(id("stroke"), ellipseStroke(box, seed), pen, data("stroke"), MS.circle)] : [];
      }
      case "box": {
        const box = this.pxBox(g.box);
        return box ? [this.strokePhase(id("stroke"), roundedRectStroke(box, seed), pen, data("stroke"), MS.box)] : [];
      }
      case "underline": {
        let a0 = this.xy(g.points?.[0]);
        let b0 = this.xy(g.points?.[g.points.length - 1]);
        if (!a0 || !b0 || (a0[0] === b0[0] && a0[1] === b0[1])) {
          const box = this.pxBox(g.box);
          if (!box) return [];
          a0 = [box.x, box.y + box.h];
          b0 = [box.x + box.w, box.y + box.h];
        }
        // keep the ink clear of the letters: the geometry is the line's centre, the marker is wide
        const drop = pen.width * 0.5;
        const stroke = wavyLine([a0[0], a0[1] + drop], [b0[0], b0[1] + drop], seed, Math.max(0.8, 0.28 * pen.width));
        return [this.strokePhase(id("stroke"), stroke, pen, data("stroke"), MS.underline)];
      }
      case "highlight": {
        const box = this.pxBox(g.box);
        if (!box) return [];
        const d = data("fill", HIGHLIGHT_OPACITY);
        return [
          {
            ms: MS.highlight,
            frame: (t) => {
              const w = Math.max(2, box.w * easeInOutSine(t));
              this.stage(
                rectElement(
                  id("fill"),
                  { x: box.x, y: box.y, w, h: box.h },
                  { stroke: "transparent", fill: color, strokeWidth: 1, roughness: 0, opacity: HIGHLIGHT_OPACITY, rounded: true },
                  d,
                ),
              );
            },
          },
        ];
      }
      case "arrow": {
        const pts = (g.points ?? []).map((p) => this.xy(p)).filter((p): p is XY => !!p);
        if (pts.length < 2) return [];
        const s = pts[0];
        const e = pts[pts.length - 1];
        const c: XY = pts.length >= 3 ? pts[1] : [(s[0] + e[0]) / 2, (s[1] + e[1]) / 2];
        const template = arrowTemplate(id("arrow"), { ...pen, width: pen.width * 0.85 }, data("arrow"));
        const phases: Phase[] = [
          {
            ms: MS.arrow,
            frame: (t) => {
              const p = Math.max(0.03, easeInOutSine(t));
              this.stage(arrowWithPoints(template, quadPrefix(s, c, e, p, 6), t >= 1));
            },
          },
        ];
        const lb = this.pxBox(g.label_box);
        if (a.text && lb) phases.push(...this.writePhases(id("caption"), a.text, lb, color, data("caption")));
        return phases;
      }
      case "label": {
        const phases: Phase[] = [];
        const from = this.xy(g.leader?.[0]);
        const to = this.xy(g.leader?.[g.leader.length - 1]);
        if (from && to && Math.hypot(to[0] - from[0], to[1] - from[1]) > 4) {
          const leader = curvedLine(to, from, seed, 0.035, 7);
          const thin = { ...pen, width: Math.max(1.6, pen.width * 0.55) };
          phases.push(this.strokePhase(id("leader"), leader, thin, data("leader"), MS.leader));
        }
        let lb = this.pxBox(g.label_box);
        const target = this.pxBox(g.box);
        if (!lb && target && a.text) {
          const h = Math.max(20, 0.06 * (this.img?.h ?? 600));
          lb = { x: target.x + target.w + 10, y: target.y + target.h / 2 - h / 2, w: 0.6 * h * a.text.length, h };
        }
        if (a.text && lb) phases.push(...this.writePhases(id("text"), a.text, lb, color, data("text")));
        return phases;
      }
      default:
        return [];
    }
  }

  // ------------------------------------------------------------------ BoardHandle

  async loadImage(url: string, width: number, height: number): Promise<void> {
    const token = ++this.loadToken;
    await this.whenReady();
    const api = this.api;
    if (!api) throw new Error("The whiteboard is not ready");
    const { dataURL, mimeType } = await fetchImage(url);
    if (token !== this.loadToken) return;
    this.cancelRuns(() => true);
    this.pending.clear();
    this.removals.clear();
    this.sketchAreas.clear();
    this.regionsToken++;
    this.currentStep = 0;
    this.previous = "show";
    this.img = { w: Math.max(1, width), h: Math.max(1, height) };
    const fileId = `img-${hashString(url).toString(36)}-${Date.now().toString(36)}`;
    const image = imageElement(`board-image-${fileId}`, fileId, this.img.w, this.img.h);
    const frame = rectElement(
      `board-frame-${fileId}`,
      { x: 0, y: 0, w: this.img.w, h: this.img.h },
      { stroke: FRAME_COLOR, fill: "transparent", strokeWidth: 1, roughness: 0, opacity: 100 },
      { board: "frame" },
    );
    api.updateScene({
      elements: [image, frame],
      appState: { selectedElementIds: {}, selectedGroupIds: {}, editingGroupId: null },
      captureUpdate: CaptureUpdateAction.NEVER,
    });
    // the element exists first, so addFiles decodes the picture right away
    const file: BinaryFileData = {
      id: fileId as FileId,
      dataURL: dataURL as DataURL,
      mimeType: mimeType as BinaryFileData["mimeType"],
      created: Date.now(),
    };
    api.addFiles([file]);
    api.history.clear();
    this.autoFit = true;
    this.fitToImage();
    await this.preloadFonts();
    await nextFrame();
    await nextFrame();
  }

  async drawAnnotation(annotation: Annotation, options: DrawOptions): Promise<void> {
    if (!this.img || !this.api) return;
    const step = options.stepIndex;
    const key = annotationKey(step, annotation.id);
    this.removeKey(key);
    let phases: Phase[] = [];
    try {
      phases = this.phasesFor(annotation, step);
    } catch (err) {
      console.warn("whiteboard: cannot draw", annotation.id, err);
    }
    if (!phases.length) return;
    await this.animate(key, step, phases, options);
  }

  drawInstant(annotations: Annotation[], stepIndex: number, sketch?: string | null): void {
    if (!this.img || !this.api) return;
    for (const a of annotations) {
      const key = annotationKey(stepIndex, a.id);
      this.cancelRuns((r) => r.key === key);
      this.removeKey(key);
      try {
        for (const phase of this.phasesFor(a, stepIndex)) phase.frame(1);
      } catch (err) {
        console.warn("whiteboard: cannot draw", a.id, err);
      }
      if (this.badgesOn) this.stageBadge(key);
    }
    this.flush();
    if (sketch) {
      // no animation; it lands as soon as the chart is laid out (at once when it was seen before)
      const done = new AbortController();
      done.abort();
      void this.drawSketch(sketch, { stepIndex, signal: done.signal, color: stepInk(annotations) });
    }
  }

  // ------------------------------------------------------------------ margin sketch

  async drawSketch(mermaid: string, options: DrawOptions): Promise<void> {
    if (!this.img || !this.api) return;
    const step = options.stepIndex;
    const key = annotationKey(step, SKETCH_ID);
    this.cancelRuns((r) => r.key === key);
    this.removeKey(key);
    if (this.sketchAreas.delete(key)) this.refit();
    const run: Run = { key, stepIndex: step, signal: options.signal, cancelled: false };
    this.runs.add(run);
    try {
      const plan = await this.planSketch(mermaid, key, step, options.color ?? "blue", run);
      if (!plan || run.cancelled) return;
      this.sketchAreas.set(key, { stepIndex: step, side: plan.side, bounds: plan.bounds });
      this.refit(); // widen the view first, then sketch into the new space
      const phases: Phase[] = [{ ms: SKETCH_MS.lead, frame: () => {} }, ...plan.pieces.map((p) => this.sketchPhase(p))];
      for (const phase of phases) {
        if (run.cancelled) return;
        await this.play(run, phase.ms, (t) => {
          if (!run.cancelled) phase.frame(t);
        });
      }
    } catch (err) {
      if (!run.cancelled) console.warn("whiteboard: margin sketch skipped", err);
    } finally {
      this.runs.delete(run);
    }
  }

  /** Nodes pop in with their label; arrows are drawn from tail to head, then their label. */
  private sketchPhase(piece: SketchPiece): Phase {
    const [first, ...rest] = piece.els;
    let shown = false;
    return {
      ms: SKETCH_MS.piece,
      frame: (t) => {
        if (piece.arrow) {
          this.stage(arrowPrefix(first, t >= 1 ? 1 : easeInOutSine(t)));
          if (t >= 1) for (const el of rest) this.stage(el);
        } else if (!shown) {
          shown = true;
          for (const el of piece.els) this.stage(el);
        }
      },
    };
  }

  /** Lay the chart out for its spot and restyle it as tutor ink; null when the board moved on meanwhile. */
  private async planSketch(mermaid: string, key: string, step: number, color: Color, run: Run) {
    const portrait = !!this.img && this.img.h > this.img.w * 1.05;
    // beside the page; a portrait page also tries under it and keeps whichever shows the chart bigger
    const sides: SketchSide[] = portrait ? ["right", "below"] : ["right"];
    let best: { side: SketchSide; layout: SketchLayout; at: XY; scale: number; score: number } | null = null;
    for (const side of sides) {
      const source = sketchSource(mermaid, side === "right" ? "down" : "across");
      if (!source) throw new Error("not a Mermaid flowchart");
      const layout = await layoutSketch(source);
      if (run.cancelled || !this.img) return null;
      const spot = this.sketchSpot(layout, side, key);
      if (!best || spot.score > best.score) best = { side, layout, ...spot };
    }
    if (!best) return null;
    const data = (part: string): TutorData => ({
      tutor: true,
      annotationId: SKETCH_ID,
      stepIndex: step,
      kind: "sketch",
      grounding: "llm_only",
      confidence: 1,
      key,
      part,
      baseOpacity: 100,
    });
    const style = { color: PALETTE[color] ?? PALETTE.blue, strokeWidth: Math.max(1.5, this.penWidth * 0.7) };
    const built = buildSketch(best.layout, best.at, best.scale, style, elementId(key, ""), data);
    return { side: best.side, pieces: built.pieces, bounds: built.bounds };
  }

  /** Top-left and scale of a chart in its spot (after other sketches on that side), and how big its text
   *  shows on screen once the view fits page + sketches (to pick a side). Text stays near body-text size. */
  private sketchSpot(layout: SketchLayout, side: SketchSide, key: string): { at: XY; scale: number; score: number } {
    const img = this.img ?? { w: 1, h: 1 };
    const lw = Math.max(1, layout.bounds[2] - layout.bounds[0]);
    const lh = Math.max(1, layout.bounds[3] - layout.bounds[1]);
    const others = [...this.sketchAreas].filter(([k, a]) => k !== key && a.side === side).map(([, a]) => a.bounds);
    // text no bigger than a slide's body text (~36 px on a 1600 px page), so the page stays the main thing
    const maxScale = (0.0225 * Math.max(img.w, img.h)) / SKETCH_FONT;
    let at: XY;
    let scale: number;
    if (side === "right") {
      at = [Math.max(img.w * (1 + SKETCH_BOX.gap), ...others.map((b) => b[2] + img.w * SKETCH_BOX.gap)), 0];
      scale = Math.min((img.w * SKETCH_BOX.w) / lw, (img.h * SKETCH_BOX.h) / lh, maxScale);
    } else {
      at = [0, Math.max(img.h * (1 + SKETCH_BOX.gap), ...others.map((b) => b[3] + img.h * SKETCH_BOX.gap))];
      scale = Math.min(img.w / lw, (img.h * SKETCH_BOX.belowH) / lh, maxScale);
    }
    const area: Bounds = [at[0], at[1], at[0] + lw * scale, at[1] + lh * scale];
    const content = [[0, 0, img.w, img.h] as Bounds, ...others, area].reduce(unionBounds);
    const zoom = this.viewFor(content)?.zoom ?? 1;
    return { at, scale, score: scale * SKETCH_FONT * zoom };
  }

  /** Stage removal of every element (tutor drawing and badge) belonging to an annotation key. */
  private removeKey(key: string) {
    for (const el of this.liveElements()) {
      if (tutorData(el)?.key === key || overlayData(el)?.key === key) this.remove(el.id);
    }
  }

  clearTutorDrawings(fromStep?: number): void {
    const hit = (step: number | undefined) => step !== undefined && (fromStep === undefined || step >= fromStep);
    this.cancelRuns((r) => hit(r.stepIndex));
    for (const el of this.liveElements()) {
      const t = tutorData(el);
      const o = overlayData(el);
      if (hit(t?.stepIndex) || (o?.overlay === "badges" && hit(o.stepIndex))) this.remove(el.id);
    }
    this.flush();
    let sketchGone = false;
    for (const [key, area] of this.sketchAreas) {
      if (!hit(area.stepIndex)) continue;
      this.sketchAreas.delete(key);
      sketchGone = true;
    }
    if (sketchGone) this.refit(); // back to the page
  }

  setCurrentStep(stepIndex: number, previous: PreviousSteps): void {
    this.currentStep = stepIndex;
    this.previous = previous;
    this.flush((el) => el);
    // flush only rewrites elements whose opacity changes; make sure a pure emphasis change lands too
    this.flushVisibility();
    if (this.sketchAreas.size) this.refit(); // a hidden sketch (quiz) leaves the view
  }

  private flushVisibility() {
    const api = this.api;
    if (!api) return;
    let changed = false;
    const next = api.getSceneElementsIncludingDeleted().map((el) => {
      const out = this.visible(el);
      if (out !== el) changed = true;
      return out;
    });
    if (changed) api.updateScene({ elements: next, captureUpdate: CaptureUpdateAction.NEVER });
  }

  showRegions(regions: Region[] | null): void {
    const token = ++this.regionsToken;
    for (const el of this.liveElements()) if (overlayData(el)?.overlay === "regions") this.remove(el.id);
    const img = this.img;
    if (!regions || !regions.length || !img) {
      this.flush();
      return;
    }
    // tags stay legible on screen, a little smaller on dense pages so they do not bury the page
    const dense = regions.length > 30;
    const fontSize = Math.min(
      Math.max(clamp(0.017 * img.h, 11, 22), this.screenPx(dense ? 9.5 : 11.5)),
      Math.max(22, (dense ? 0.02 : 0.03) * img.h),
    );
    const line = Math.max(1.2, 0.0011 * Math.max(img.w, img.h), this.screenPx(1));
    const items: { els: El[]; base: number[] }[] = [];
    // big regions first so small ones (and their tags) stay on top
    const sorted = [...regions].sort((a, b) => b.box.w * b.box.h - a.box.w * a.box.h);
    for (const r of sorted) {
      const b = this.pxBox(r.box);
      if (!b) continue;
      const color = REGION_COLORS[r.kind] ?? REGION_COLORS.text;
      const data: OverlayData = { overlay: "regions", baseOpacity: 100 };
      const outline = rectElement(
        `overlay:region:${r.id}`,
        b,
        { stroke: color, fill: "transparent", strokeStyle: "dashed", strokeWidth: line, roughness: 0, opacity: 0 },
        data,
      );
      const label = textElement(`overlay:region:${r.id}:tag`, r.id, 0, 0, { fontSize, fontFamily: MONO_FONT, color: "#ffffff", opacity: 0 }, data);
      const padX = fontSize * 0.3;
      const padY = fontSize * 0.08;
      const chipW = label.width + 2 * padX;
      const chipH = label.height + 2 * padY;
      const cx = clamp(b.x, 0, Math.max(0, img.w - chipW));
      const cy = b.y - chipH >= 0 ? b.y - chipH : b.y;
      const chip = rectElement(
        `overlay:region:${r.id}:chip`,
        { x: cx, y: cy, w: chipW, h: chipH },
        { stroke: color, fill: color, strokeWidth: 1, roughness: 0, opacity: 0 },
        data,
      );
      const tag = { ...label, x: cx + padX, y: cy + padY } as El;
      items.push({ els: [outline, chip, tag], base: [90, 88, 100] });
    }
    for (const it of items) for (const el of it.els) this.stage(el);
    this.flush();
    // quick staggered reveal: the page "lights up" region by region
    const stagger = Math.min(28, 700 / Math.max(1, items.length));
    const fade = 160;
    const shown = items.map(() => 0);
    void this.play(null, stagger * items.length + fade, (t) => {
      if (token !== this.regionsToken) return;
      const ms = t * (stagger * items.length + fade);
      items.forEach((it, i) => {
        const k = t >= 1 ? 1 : clamp((ms - i * stagger) / fade, 0, 1);
        if (Math.abs(k - shown[i]) < 0.04 && k < 1) return;
        if (k === shown[i]) return;
        shown[i] = k;
        it.els.forEach((el, j) => this.stage({ ...el, opacity: Math.round(it.base[j] * k) } as El));
      });
    });
  }

  showBadges(on: boolean): void {
    this.badgesOn = on;
    const keys = new Set<string>();
    for (const el of this.liveElements()) {
      if (overlayData(el)?.overlay === "badges") this.remove(el.id);
      const t = tutorData(el);
      if (on && t && t.kind !== "check" && t.kind !== "cross" && t.kind !== "sketch") keys.add(t.key);
    }
    for (const key of keys) this.stageBadge(key);
    this.flush();
  }

  /** Tiny grey "consensus 0.93" tag next to an annotation, where it covers the least other ink. */
  private stageBadge(key: string) {
    const img = this.img;
    if (!img) return;
    const live = this.liveElements();
    const own = live.filter((el) => tutorData(el)?.key === key);
    const t = own.length ? tutorData(own[0]) : null;
    if (!t || t.kind === "check" || t.kind === "cross" || t.kind === "sketch") return;
    const [x0, y0, x1, y1] = getCommonBounds(own);
    if (!finite(x0, y0, x1, y1)) return;
    const fontSize = Math.min(Math.max(clamp(0.016 * img.h, 10, 18), this.screenPx(10.5)), Math.max(18, 0.026 * img.h));
    const data: OverlayData = { overlay: "badges", key, stepIndex: t.stepIndex, baseOpacity: 100 };
    const text = `${t.grounding} ${t.confidence.toFixed(2)}`;
    const label = textElement(`overlay:badge:${key}`, text, 0, 0, { fontSize, fontFamily: MONO_FONT, color: BADGE_COLOR, opacity: 100 }, data);
    const pad = fontSize * 0.25;
    const w = label.width + 2 * pad;
    const h = label.height + pad;
    // obstacles: other tutor drawings and labels, other badges, region id tags (not region outlines)
    const obstacles: (readonly [number, number, number, number])[] = [];
    for (const el of live) {
      const td = tutorData(el);
      const od = td ? null : overlayData(el);
      if (td ? td.key === key : !od || od.key === key) continue;
      if (od?.overlay === "regions" && !el.id.endsWith(":chip")) continue;
      const b = getCommonBounds([el]);
      if (finite(...b)) obstacles.push(b);
    }
    const gap = Math.max(2, 0.2 * h);
    const spots: [number, number][] = [
      [x1 - w, y0 - h - gap],
      [x0, y0 - h - gap],
      [x1 - w, y1 + gap],
      [x0, y1 + gap],
      [x1 + gap, (y0 + y1) / 2 - h / 2],
      [x0 - w - gap, (y0 + y1) / 2 - h / 2],
    ];
    let best: [number, number] = [0, 0];
    let bestCost = Infinity;
    for (const [sx, sy] of spots) {
      const x = clamp(sx, 0, Math.max(0, img.w - w));
      const y = clamp(sy, 0, Math.max(0, img.h - h));
      let cost = Math.abs(x - sx) + Math.abs(y - sy); // pushed back onto the page: slight penalty
      for (const [a, b, c, d] of obstacles) {
        const ox = Math.min(x + w, c) - Math.max(x, a);
        const oy = Math.min(y + h, d) - Math.max(y, b);
        if (ox > 0 && oy > 0) cost += ox * oy;
      }
      if (cost < bestCost - 1e-6) {
        bestCost = cost;
        best = [x, y];
      }
    }
    const [x, y] = best;
    const chip = rectElement(
      `overlay:badge:${key}:chip`,
      { x, y, w, h },
      { stroke: "transparent", fill: "#ffffff", strokeWidth: 1, roughness: 0, opacity: 88, rounded: true },
      { ...data, baseOpacity: 88 },
    );
    this.stage(chip);
    this.stage({ ...label, x: x + pad, y: y + pad / 2 } as El);
  }

  getStudentSelection(): Box | null {
    const api = this.api;
    const img = this.img;
    if (!api || !img) return null;
    const mine = api.getSceneElements().filter(isStudentElement);
    if (!mine.length) return null;
    const selected = api.getAppState().selectedElementIds;
    const picked = mine.filter((el) => selected[el.id]);
    const [x0, y0, x1, y1] = getCommonBounds(picked.length ? picked : mine);
    if (!finite(x0, y0, x1, y1)) return null;
    const cx0 = clamp(x0, 0, img.w);
    const cy0 = clamp(y0, 0, img.h);
    const cx1 = clamp(x1, 0, img.w);
    const cy1 = clamp(y1, 0, img.h);
    if (cx1 - cx0 < 1 || cy1 - cy0 < 1) return null;
    return { x: cx0 / img.w, y: cy0 / img.h, w: (cx1 - cx0) / img.w, h: (cy1 - cy0) / img.h };
  }

  clearStudentDrawings(): void {
    const api = this.api;
    if (!api) return;
    this.flush();
    let any = false;
    const next = api.getSceneElementsIncludingDeleted().map((el) => {
      if (el.isDeleted || !isStudentElement(el)) return el;
      any = true;
      return bump(el, { isDeleted: true });
    });
    if (!any) return;
    // undoable on purpose: Ctrl+Z brings the student's drawing back
    api.updateScene({ elements: next, appState: { selectedElementIds: {} }, captureUpdate: CaptureUpdateAction.IMMEDIATELY });
  }

  enableTapMode(onTap: (p: Point) => void): () => void {
    const api = this.api;
    const root = this.container;
    if (!api || !root) return () => {};
    this.tapCleanup?.();
    const before = api.getAppState().activeTool;
    api.setActiveTool({ type: "hand" });
    root.classList.add("is-tap-mode");
    const pointers = new Set<number>();
    let down: { id: number; x: number; y: number } | null = null;
    const onCanvas = (t: EventTarget | null) => t instanceof HTMLCanvasElement && t.classList.contains("interactive");
    const onDown = (e: PointerEvent) => {
      if (!onCanvas(e.target)) return;
      pointers.add(e.pointerId);
      down = pointers.size === 1 && e.button === 0 ? { id: e.pointerId, x: e.clientX, y: e.clientY } : null;
      // any tool other than the hand would draw: keep the tap from reaching Excalidraw
      if (api.getAppState().activeTool.type !== "hand") {
        e.stopPropagation();
        e.preventDefault();
      }
    };
    const onUp = (e: PointerEvent) => {
      pointers.delete(e.pointerId);
      const d = down;
      if (!d || d.id !== e.pointerId) return;
      down = null;
      if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 8) return;
      const p = this.clientToImage(e.clientX, e.clientY);
      if (p) onTap(p);
    };
    const onCancel = (e: PointerEvent) => {
      pointers.delete(e.pointerId);
      if (down?.id === e.pointerId) down = null;
    };
    const onDouble = (e: MouseEvent) => {
      if (!onCanvas(e.target)) return;
      e.stopPropagation();
      e.preventDefault();
    };
    root.addEventListener("pointerdown", onDown, true);
    root.addEventListener("dblclick", onDouble, true);
    window.addEventListener("pointerup", onUp, true);
    window.addEventListener("pointercancel", onCancel, true);
    const cleanup = () => {
      if (this.tapCleanup !== cleanup) return;
      this.tapCleanup = null;
      root.removeEventListener("pointerdown", onDown, true);
      root.removeEventListener("dblclick", onDouble, true);
      window.removeEventListener("pointerup", onUp, true);
      window.removeEventListener("pointercancel", onCancel, true);
      root.classList.remove("is-tap-mode");
      if (this.api !== api) return;
      if (before.type === "custom") api.setActiveTool({ type: "custom", customType: before.customType, locked: before.locked });
      else api.setActiveTool({ type: before.type === "image" ? "selection" : before.type, locked: before.locked });
    };
    this.tapCleanup = cleanup;
    return cleanup;
  }

  private canvasRect(): DOMRect | null {
    const root = this.container;
    if (!root) return null;
    return (root.querySelector(".excalidraw") ?? root).getBoundingClientRect();
  }

  private clientToImage(clientX: number, clientY: number): Point | null {
    const api = this.api;
    const img = this.img;
    const rect = this.canvasRect();
    if (!api || !img || !rect) return null;
    const st = api.getAppState();
    const s = viewportCoordsToSceneCoords(
      { clientX, clientY },
      { zoom: st.zoom, offsetLeft: rect.left, offsetTop: rect.top, scrollX: st.scrollX, scrollY: st.scrollY },
    );
    const x = s.x / img.w;
    const y = s.y / img.h;
    if (!finite(x, y) || x < 0 || y < 0 || x > 1 || y > 1) return null;
    return { x, y };
  }

  private sceneToClient(x: number, y: number): { x: number; y: number } | null {
    const api = this.api;
    const rect = this.canvasRect();
    if (!api || !rect) return null;
    const st = api.getAppState();
    return { x: rect.left + (x + st.scrollX) * st.zoom.value, y: rect.top + (y + st.scrollY) * st.zoom.value };
  }

  private markStep(): number {
    return Math.max(1, this.currentStep);
  }

  async drawCheck(box: Box, color: Color = "green"): Promise<void> {
    const b = this.pxBox(box);
    const img = this.img;
    if (!b || !img) return;
    const step = this.markStep();
    const mark = { id: `check-${++this.markSeq}`, grounding: "user" as const, confidence: 1 };
    const key = annotationKey(step, mark.id);
    const pad = Math.max(8, 0.012 * Math.max(img.w, img.h));
    const rx = (b.w / 2) * 1.32 + pad;
    const ry = (b.h / 2) * 1.32 + pad;
    const ring: PxBox = { x: b.x + b.w / 2 - rx, y: b.y + b.h / 2 - ry, w: 2 * rx, h: 2 * ry };
    const pen: Pen = { color: PALETTE[color] ?? PALETTE.green, width: this.penWidth * 1.15, opacity: 100 };
    const data = this.tutorData(mark, "check", step, "stroke");
    await this.animate(key, step, [this.strokePhase(elementId(key, "stroke"), ellipseStroke(ring, hashString(key)), pen, data, MS.check)]);
  }

  async drawCross(at: Point, color: Color = "red"): Promise<void> {
    const p = this.xy(at);
    const img = this.img;
    if (!p || !img) return;
    const step = this.markStep();
    const mark = { id: `cross-${++this.markSeq}`, grounding: "user" as const, confidence: 1 };
    const key = annotationKey(step, mark.id);
    const size = Math.max(9, 0.012 * Math.max(img.w, img.h));
    const [s1, s2] = crossStrokes(p, size, hashString(key));
    const pen: Pen = { color: PALETTE[color] ?? PALETTE.red, width: this.penWidth * 1.1, opacity: 100 };
    const data = this.tutorData(mark, "cross", step, "stroke");
    await this.animate(key, step, [
      this.strokePhase(elementId(key, "a"), s1, pen, data, MS.cross),
      this.strokePhase(elementId(key, "b"), s2, pen, { ...data, part: "b" }, MS.cross),
    ]);
  }

  async exportPng(): Promise<Blob> {
    const api = this.api;
    if (!api) throw new Error("The whiteboard is not ready");
    this.flush();
    const elements = api.getSceneElements().filter((el) => el.opacity > 0);
    const blob: Blob = await exportToBlob({
      elements,
      files: api.getFiles(),
      mimeType: "image/png",
      exportPadding: 16,
      appState: { exportBackground: true, viewBackgroundColor: "#ffffff", exportWithDarkMode: false, exportScale: 1 },
    });
    return blob;
  }

  /** Overlay buttons under the page need this much room at the bottom of the board (0: none). */
  setBottomInset(px: number) {
    const v = Number.isFinite(px) ? Math.max(0, Math.round(px)) : 0;
    if (v === this.bottomInset) return;
    this.bottomInset = v;
    if (this.img) this.refit();
  }

  /** The page plus the margin sketches currently visible (a hidden sketch does not hold the view). */
  private fitBounds(): Bounds | null {
    const img = this.img;
    if (!img) return null;
    let b: Bounds = [0, 0, img.w, img.h];
    for (const area of this.sketchAreas.values()) {
      if (this.targetOpacity(area.stepIndex, 100) > 0) b = unionBounds(b, area.bounds);
    }
    return b;
  }

  /** Zoom and scroll that fit scene bounds in the board, clear of Excalidraw's toolbar (top), its
   *  zoom/undo footer and any overlay buttons (bottom). */
  private viewFor(b: Bounds): View | null {
    const el = this.container;
    if (!el) return null;
    const W = el.clientWidth;
    const H = el.clientHeight;
    if (W < 40 || H < 40) return null;
    const top = H >= 420 ? 72 : 56;
    const bottom = Math.max(H >= 420 ? 64 : 52, Math.min(this.bottomInset, 0.45 * H));
    const side = W >= 700 ? 28 : 12;
    // Excalidraw's phone layout (its own breakpoint) keeps a lock/hand column at the top right, right where
    // a margin sketch starts
    const phone = W < 730 || (H < 500 && W < 1000);
    const right = phone && b[2] > (this.img?.w ?? Infinity) ? 46 : side;
    const availW = Math.max(40, W - side - right);
    const availH = Math.max(40, H - top - bottom);
    const bw = Math.max(1, b[2] - b[0]);
    const bh = Math.max(1, b[3] - b[1]);
    const zoom = clamp(Math.min(availW / bw, availH / bh) * 0.97, 0.1, 4);
    return {
      zoom,
      scrollX: (side + availW / 2) / zoom - (b[0] + b[2]) / 2,
      scrollY: (top + availH / 2) / zoom - (b[1] + b[3]) / 2,
    };
  }

  private setView(view: View) {
    this.lastFit = view;
    this.autoFit = true;
    this.api?.updateScene({
      appState: { zoom: { value: view.zoom } as AppState["zoom"], scrollX: view.scrollX, scrollY: view.scrollY },
      captureUpdate: CaptureUpdateAction.NEVER,
    });
  }

  fitToImage(): void {
    const b = this.api ? this.fitBounds() : null;
    const view = b && this.viewFor(b);
    if (!view) return;
    this.viewToken++; // a glide in progress stops here
    this.setView(view);
  }

  /** What the view should fit changed (a sketch came or went, overlay room changed): glide there on the
   *  next frame, unless the student zoomed or panned the board. A clear + redraw burst glides once. */
  private refit() {
    if (this.refitQueued) return;
    this.refitQueued = true;
    requestAnimationFrame(() => {
      this.refitQueued = false;
      this.glide();
    });
  }

  private glide() {
    const api = this.api;
    const el = this.container;
    const b = this.fitBounds();
    const to = b && this.viewFor(b);
    if (!api || !el || !to || !this.autoFit) return;
    const st = api.getAppState();
    const from: View = { zoom: st.zoom.value, scrollX: st.scrollX, scrollY: st.scrollY };
    const token = ++this.viewToken;
    if (Math.abs(from.zoom - to.zoom) < 1e-4 && Math.abs(from.scrollX - to.scrollX) < 0.5 && Math.abs(from.scrollY - to.scrollY) < 0.5) {
      return;
    }
    // ease the scene point at the board centre and the zoom (in log space), so the page never swings away
    const W = el.clientWidth;
    const H = el.clientHeight;
    const cx0 = W / 2 / from.zoom - from.scrollX;
    const cy0 = H / 2 / from.zoom - from.scrollY;
    const cx1 = W / 2 / to.zoom - to.scrollX;
    const cy1 = H / 2 / to.zoom - to.scrollY;
    void this.play(null, SKETCH_MS.glide, (t) => {
      if (token !== this.viewToken || !this.autoFit) return;
      if (t >= 1) {
        this.setView(to);
        return;
      }
      const k = easeInOutSine(t);
      const zoom = from.zoom * Math.pow(to.zoom / from.zoom, k);
      this.setView({ zoom, scrollX: W / 2 / zoom - (cx0 + (cx1 - cx0) * k), scrollY: H / 2 / zoom - (cy0 + (cy1 - cy0) * k) });
    });
  }

  // ------------------------------------------------------------------ debug

  private debugScene(): DebugElement[] {
    const api = this.api;
    if (!api) return [];
    return api.getSceneElements().map((el) => {
      const raw = el as unknown as { text?: string; fontSize?: number; points?: unknown[] };
      const [x0, y0, x1, y1] = getCommonBounds([el]);
      return {
        id: el.id,
        type: el.type,
        x: el.x,
        y: el.y,
        width: el.width,
        height: el.height,
        opacity: el.opacity,
        locked: el.locked,
        text: raw.text,
        fontSize: raw.fontSize,
        points: raw.points?.length,
        bounds: [x0, y0, x1, y1],
        customData: el.customData,
      };
    });
  }
}
