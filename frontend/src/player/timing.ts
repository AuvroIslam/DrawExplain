// Narration timelines (real ElevenLabs word timings or estimates) and cue scheduling.
import type { Annotation, WordTiming } from "../types";

export interface WordSpan {
  charStart: number;
  charEnd: number; // exclusive
}

export interface TimedWord extends WordSpan {
  start: number; // seconds from narration start
  end: number;
}

export interface Timeline {
  words: TimedWord[];
  duration: number; // seconds
}

/** Words of a narration as character spans (whitespace separated). */
export function tokenize(text: string): WordSpan[] {
  const spans: WordSpan[] = [];
  for (const m of text.matchAll(/\S+/g)) {
    spans.push({ charStart: m.index, charEnd: m.index + m[0].length });
  }
  return spans;
}

/** Reading-speed estimate: longer words take longer, punctuation adds a breath. */
export function estimateTimeline(text: string, wpm = 170): Timeline {
  const spans = tokenize(text);
  if (!spans.length) return { words: [], duration: 0 };
  const letters = spans.map((s) => text.slice(s.charStart, s.charEnd).replace(/[^\p{L}\p{N}]/gu, "").length || 1);
  const avg = letters.reduce((a, b) => a + b, 0) / letters.length;
  const perWord = 60 / wpm;
  let t = 0;
  const words = spans.map((s, i) => {
    const d = perWord * (0.5 + 0.5 * (letters[i] / avg)) * 0.86;
    const start = t;
    const end = start + d;
    const tail = text[s.charEnd - 1] ?? "";
    t = end + (/[.!?]/.test(tail) ? 0.34 : /[,;:]/.test(tail) ? 0.16 : 0.02);
    return { ...s, start, end };
  });
  return { words, duration: t };
}

/** Real word timings from /api/tts; falls back to a scaled estimate when they are unusable. */
export function timelineFromTts(text: string, words: WordTiming[], duration: number): Timeline {
  const ok =
    words.length > 0 &&
    words.every((w) => w.char_end > w.char_start && w.char_start >= 0 && w.char_end <= text.length + 1);
  if (ok) {
    const sorted = [...words].sort((a, b) => a.char_start - b.char_start);
    return {
      words: sorted.map((w) => ({
        charStart: w.char_start,
        charEnd: Math.min(w.char_end, text.length),
        start: w.start,
        end: Math.max(w.end, w.start),
      })),
      duration: Math.max(duration, sorted[sorted.length - 1].end),
    };
  }
  return scaleTimeline(estimateTimeline(text), duration);
}

export function scaleTimeline(tl: Timeline, duration: number): Timeline {
  if (!(duration > 0) || !(tl.duration > 0)) return tl;
  const k = duration / tl.duration;
  return {
    words: tl.words.map((w) => ({ ...w, start: w.start * k, end: w.end * k })),
    duration,
  };
}

/** Index of the word being spoken at time t (-1 before the first word). */
export function wordAt(words: TimedWord[], t: number): number {
  let lo = 0;
  let hi = words.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (words[mid].start <= t) {
      ans = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return ans;
}

/** Index of the word containing (or, inside whitespace, following) a character offset. */
export function wordAtChar(words: WordSpan[], charIndex: number): number {
  for (let i = 0; i < words.length; i++) {
    if (words[i].charEnd > charIndex) return i;
  }
  return words.length - 1;
}

const squash = (s: string) => s.toLowerCase().replace(/\s+/g, " ");

function findCue(narration: string, cue: string, used: Map<string, number>): number {
  const hay = squash(narration);
  const variants = [squash(cue).trim(), squash(cue).replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "").trim()];
  for (const needle of variants) {
    if (!needle) continue;
    const from = used.get(needle) ?? 0;
    let at = hay.indexOf(needle, from);
    if (at < 0 && from > 0) at = hay.indexOf(needle);
    if (at >= 0) {
      used.set(needle, at + 1);
      return squashedToRaw(narration, at);
    }
  }
  return -1;
}

/** Map an index in the whitespace-squashed text back to the original narration. */
function squashedToRaw(text: string, squashedIndex: number): number {
  let si = 0;
  let prevSpace = false;
  for (let i = 0; i < text.length; i++) {
    const space = /\s/.test(text[i]);
    if (space && prevSpace) continue;
    if (si === squashedIndex) return i;
    si++;
    prevSpace = space;
  }
  return text.length - 1;
}

export interface CueTime {
  annotation: Annotation;
  time: number; // seconds into the narration
  cued: boolean; // false = no usable cue, spread evenly
}

/**
 * When each annotation should start drawing: cue phrase -> character offset in the narration
 * (case-insensitive) -> start time of the word containing it. Annotations without a usable cue
 * are spread evenly over the narration. Sorted by time, stable.
 */
export function scheduleCues(narration: string, timeline: Timeline, annotations: Annotation[]): CueTime[] {
  const used = new Map<string, number>();
  const raw = annotations.map((annotation) => {
    const at = annotation.cue ? findCue(narration, annotation.cue, used) : -1;
    if (at < 0 || !timeline.words.length) return { annotation, time: -1, cued: false };
    const w = timeline.words[wordAtChar(timeline.words, at)];
    return { annotation, time: Math.max(0, w.start - 0.05), cued: true };
  });
  const loose = raw.filter((r) => !r.cued);
  loose.forEach((r, k) => {
    r.time = (timeline.duration * (k + 1)) / (loose.length + 1);
  });
  return raw
    .map((r, i) => ({ r, i }))
    .sort((a, b) => a.r.time - b.r.time || a.i - b.i)
    .map(({ r }) => r);
}
