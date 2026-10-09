// Pure geometry for the tutor's hand-drawn strokes, in scene pixels. No Excalidraw imports, so it
// stays cheap to call on every animation frame. Randomness is seeded by the annotation id: the
// same lesson always looks the same, but no two circles are identical.

export type XY = [number, number];

export interface PxBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** A freedraw stroke: absolute points plus a pen pressure (0..1) per point. */
export interface Stroke {
  points: XY[];
  pressures: number[];
}

const TAU = Math.PI * 2;
const DEG = Math.PI / 180;

export const clamp = (v: number, lo: number, hi: number) => (v < lo ? lo : v > hi ? hi : v);
const clampInt = (v: number, lo: number, hi: number) => clamp(Math.round(v), lo, hi);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerpXY = (a: XY, b: XY, t: number): XY => [lerp(a[0], b[0], t), lerp(a[1], b[1], t)];
const dist = (a: XY, b: XY) => Math.hypot(b[0] - a[0], b[1] - a[1]);

function smoothstep(e0: number, e1: number, x: number): number {
  const t = clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
}

export const easeInOutSine = (t: number) => 0.5 - 0.5 * Math.cos(Math.PI * clamp(t, 0, 1));
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);

/** FNV-1a 32-bit hash: stable seed from an annotation id. */
export function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** mulberry32 PRNG in [0, 1). */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Marker pressure along a stroke (u in 0..1): light touch-down, steady middle, lifted end. */
function pressure(u: number, phase: number, down = 0.08, lift = 0.88): number {
  const p = 0.34 + 0.24 * smoothstep(0, down, u) - 0.2 * smoothstep(lift, 1, u);
  return clamp(p + 0.025 * Math.sin(u * 17 + phase), 0.2, 0.75);
}

function withPressure(points: XY[], phase: number, down?: number, lift?: number): Stroke {
  const n = points.length;
  return { points, pressures: points.map((_, i) => pressure(n > 1 ? i / (n - 1) : 1, phase, down, lift)) };
}

/** Evenly spaced points (by arc length) along a polyline. */
export function resample(pts: XY[], n: number): XY[] {
  if (pts.length < 2 || n < 2) return pts.slice();
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + dist(pts[i - 1], pts[i]));
  const total = cum[cum.length - 1];
  if (total <= 0) return [pts[0], pts[pts.length - 1]];
  const out: XY[] = [];
  let j = 1;
  for (let i = 0; i < n; i++) {
    const d = (total * i) / (n - 1);
    while (j < pts.length - 1 && cum[j] < d) j++;
    const seg = cum[j] - cum[j - 1] || 1;
    out.push(lerpXY(pts[j - 1], pts[j], clamp((d - cum[j - 1]) / seg, 0, 1)));
  }
  return out;
}

export function polylineLength(pts: XY[]): number {
  let s = 0;
  for (let i = 1; i < pts.length; i++) s += dist(pts[i - 1], pts[i]);
  return s;
}

export function quadAt(p0: XY, c: XY, p1: XY, t: number): XY {
  const u = 1 - t;
  return [u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]];
}

/** n points on the quadratic Bezier p0 -> c -> p1 restricted to [0, t] (de Casteljau split). */
export function quadPrefix(p0: XY, c: XY, p1: XY, t: number, n: number): XY[] {
  const t1 = clamp(t, 0, 1);
  const c1 = lerpXY(p0, c, t1);
  const e1 = quadAt(p0, c, p1, t1);
  const out: XY[] = [];
  for (let i = 0; i < n; i++) out.push(quadAt(p0, c1, e1, i / (n - 1)));
  return out;
}

function sampleQuad(p0: XY, c: XY, p1: XY, n: number, out: XY[]) {
  for (let i = 1; i <= n; i++) out.push(quadAt(p0, c, p1, i / n));
}

/** The part of a stroke drawn after `t` (0..1) of its time, with an interpolated pen tip. */
export function strokePrefix(s: Stroke, t: number): Stroke {
  const n = s.points.length;
  if (t >= 1 || n < 2) return s;
  const k = Math.max(1, clamp(t, 0, 1) * (n - 1));
  const i = Math.floor(k);
  const f = k - i;
  const points = s.points.slice(0, i + 1);
  const pressures = s.pressures.slice(0, i + 1);
  if (f > 1e-3 && i + 1 < n) {
    points.push(lerpXY(s.points[i], s.points[i + 1], f));
    pressures.push(lerp(s.pressures[i], s.pressures[i + 1], f));
  }
  return { points, pressures };
}

/**
 * A hand-drawn ellipse around `box` (its bounds): starts near -110 deg (top, slightly left),
 * runs counter-clockwise ~380 deg so the end overlaps the start, slightly egg-shaped, and
 * spirals a little outward so the overlap reads as a second pass of the marker. Never dips
 * far inside the given bounds, so the target stays enclosed.
 */
export function ellipseStroke(box: PxBox, seed: number): Stroke {
  const r = rng(seed);
  const cx = box.x + box.w / 2;
  const cy = box.y + box.h / 2;
  const rx = Math.max(3, box.w / 2);
  const ry = Math.max(3, box.h / 2);
  const start = (-110 + (r() - 0.5) * 14) * DEG;
  const sweep = (374 + r() * 12) * DEG;
  const p1 = r() * TAU;
  const p2 = r() * TAU;
  const a1 = 0.012 + 0.008 * r();
  const a2 = 0.005 + 0.004 * r();
  const perim = Math.PI * (3 * (rx + ry) - Math.sqrt((3 * rx + ry) * (rx + 3 * ry)));
  const n = clampInt((perim * sweep) / TAU / 8, 40, 90);
  const pts: XY[] = [];
  for (let i = 0; i < n; i++) {
    const u = i / (n - 1);
    const th = start - sweep * u;
    const k = 1.04 + a1 * Math.sin(2 * th + p1) + a2 * Math.sin(3 * th + p2) + 0.04 * (u - 0.25);
    pts.push([cx + rx * k * Math.cos(th), cy + ry * k * Math.sin(th)]);
  }
  return withPressure(pts, r() * TAU);
}

/**
 * A hand-drawn rounded rectangle along `box`: starts on the top edge after the top-left corner,
 * goes clockwise, edges slightly bowed and corners slightly off, and overshoots past the start.
 */
export function roundedRectStroke(box: PxBox, seed: number): Stroke {
  const r = rng(seed);
  const w = Math.max(4, box.w);
  const h = Math.max(4, box.h);
  const jit = Math.min(2.2, 0.01 * Math.min(w, h) + 0.6);
  const j = () => (r() - 0.5) * 2 * jit;
  const tl: XY = [box.x + j(), box.y + j()];
  const tr: XY = [box.x + w + j(), box.y + j()];
  const br: XY = [box.x + w + j(), box.y + h + j()];
  const bl: XY = [box.x + j(), box.y + h + j()];
  const rc = Math.min(14, 0.2 * Math.min(w, h));
  const toward = (a: XY, b: XY, d: number): XY => {
    const L = dist(a, b) || 1;
    return [a[0] + ((b[0] - a[0]) * d) / L, a[1] + ((b[1] - a[1]) * d) / L];
  };
  const bowed = (a: XY, b: XY, out: XY[]) => {
    const L = dist(a, b) || 1;
    const amp = (r() < 0.5 ? -1 : 1) * Math.min(2.5, 0.007 * L) * (0.5 + r());
    const m: XY = [(a[0] + b[0]) / 2 + (-(b[1] - a[1]) / L) * amp, (a[1] + b[1]) / 2 + ((b[0] - a[0]) / L) * amp];
    sampleQuad(a, m, b, 10, out);
  };
  const lead = rc + 0.035 * w;
  const over = Math.max(10, (0.05 + 0.04 * r()) * w);
  const start: XY = [toward(tl, tr, lead)[0], toward(tl, tr, lead)[1] + 0.8];
  const dense: XY[] = [start];
  bowed(start, toward(tr, tl, rc), dense);
  sampleQuad(toward(tr, tl, rc), tr, toward(tr, br, rc), 6, dense);
  bowed(toward(tr, br, rc), toward(br, tr, rc), dense);
  sampleQuad(toward(br, tr, rc), br, toward(br, bl, rc), 6, dense);
  bowed(toward(br, bl, rc), toward(bl, br, rc), dense);
  sampleQuad(toward(bl, br, rc), bl, toward(bl, tl, rc), 6, dense);
  bowed(toward(bl, tl, rc), toward(tl, bl, rc), dense);
  sampleQuad(toward(tl, bl, rc), tl, toward(tl, tr, rc), 6, dense);
  const end = toward(tl, tr, lead + over);
  sampleQuad(toward(tl, tr, rc), toward(tl, tr, rc + 0.5 * (lead + over - rc)), [end[0], end[1] - 1.6], 6, dense);
  const n = clampInt(polylineLength(dense) / 10, 40, 90);
  return withPressure(resample(dense, n), r() * TAU, 0.05, 0.92);
}

/** A quick, slightly wavy marker line from a to b (underlines). `amp` is the wave height in px. */
export function wavyLine(a: XY, b: XY, seed: number, amp: number): Stroke {
  const r = rng(seed);
  const len = Math.max(1, dist(a, b));
  const ux = (b[0] - a[0]) / len;
  const uy = (b[1] - a[1]) / len;
  const nx = -uy;
  const ny = ux;
  const f = 0.9 + 0.7 * r();
  const ph = r() * TAU;
  const bow = (r() - 0.5) * Math.min(3, 0.012 * len);
  const n = clampInt(len / 8, 10, 60);
  const pts: XY[] = [];
  for (let i = 0; i < n; i++) {
    const u = i / (n - 1);
    const lift = u > 0.9 ? -1.4 * amp * ((u - 0.9) / 0.1) ** 2 : 0;
    const off = amp * 0.6 * Math.sin(TAU * f * u + ph) + bow * 4 * u * (1 - u) + lift;
    pts.push([a[0] + ux * len * u + nx * off, a[1] + uy * len * u + ny * off]);
  }
  return withPressure(pts, r() * TAU, 0.12, 0.85);
}

/** A gently curved pen line from a to b (leader lines, cross strokes). */
export function curvedLine(a: XY, b: XY, seed: number, bowFrac = 0.04, spacing = 8): Stroke {
  const r = rng(seed);
  const len = Math.max(1, dist(a, b));
  const amp = (r() - 0.5) * 2 * bowFrac * len;
  const c: XY = [(a[0] + b[0]) / 2 + (-(b[1] - a[1]) / len) * amp, (a[1] + b[1]) / 2 + ((b[0] - a[0]) / len) * amp];
  const n = clampInt(len / spacing, 6, 40);
  const pts: XY[] = [];
  for (let i = 0; i < n; i++) pts.push(quadAt(a, c, b, i / (n - 1)));
  return withPressure(pts, r() * TAU, 0.15, 0.8);
}

/** Two short strokes of a hand-written X centred at `at`; `size` is the half-width in px. */
export function crossStrokes(at: XY, size: number, seed: number): [Stroke, Stroke] {
  const r = rng(seed);
  const s = size;
  const j = () => (r() - 0.5) * 0.18 * s;
  const a = curvedLine([at[0] - s + j(), at[1] - s * 0.92 + j()], [at[0] + s + j(), at[1] + s + j()], seed + 1, 0.05, 4);
  const b = curvedLine([at[0] + s * 0.95 + j(), at[1] - s + j()], [at[0] - s + j(), at[1] + s * 0.9 + j()], seed + 2, 0.05, 4);
  return [a, b];
}
