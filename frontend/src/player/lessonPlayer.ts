// Plays lesson steps on the whiteboard: narration clock -> cue-timed pen drawings -> auto-advance.
// Invariant: after goTo(i) the board shows steps 1..i-1 complete and animates step i.
import type { BoardHandle, PreviousSteps } from "../board/types";
import { type Step, stepInk } from "../types";
import { errorMessage } from "../api";
import { scheduleCues, tokenize, type TimedWord, wordAt } from "./timing";
import { type Playback, type PreparedNarration, speechAvailable, VOICE_LABELS, type VoiceBox, type VoiceMode } from "./voices";

export type PlayerStatus = "idle" | "preparing" | "playing" | "paused" | "waiting" | "finished";

export interface PlayerState {
  status: PlayerStatus;
  steps: Step[];
  /** Index into steps of the step on the board (-1 before the first one). */
  current: number;
  /** Word spans of the current narration (karaoke). */
  words: TimedWord[];
  /** Word being spoken (-1 none yet, words.length when the narration is over). */
  wordIndex: number;
  /** 0..1 through the current narration. */
  progress: number;
  autoPlay: boolean;
  /** Voice actually used for the current step (after any fallback). */
  voice: VoiceMode;
  /** The lesson is still streaming in and the player is at the end of the steps received so far. */
  awaitingMore: boolean;
}

export interface PlayerOptions {
  voice: VoiceBox;
  board: () => BoardHandle | null;
  mode: VoiceMode;
  autoPlay?: boolean;
  onNotice?: (message: string) => void;
  /** The chosen voice failed and the player switched to another one for the rest of the session. */
  onVoiceFallback?: (mode: VoiceMode) => void;
}

const ADVANCE_PAUSE_MS = 900;
const SETTLE_MS = 600;
/** A step's margin sketch starts once its annotations are under way, about this far into the narration. */
const SKETCH_AT = 0.4;

function placeholderWords(text: string): TimedWord[] {
  return tokenize(text).map((w) => ({ ...w, start: 0, end: 0 }));
}

/** Copy of steps with 1-based indices continuing after `base` and ids made unique by `prefix`. */
export function renumberSteps(steps: Step[], base: number, prefix = ""): Step[] {
  return steps.map((s, i) => ({
    ...s,
    index: base + i + 1,
    annotations: s.annotations.map((a) => ({ ...a, id: prefix + a.id })),
  }));
}

export class LessonPlayer {
  private state: PlayerState;
  private readonly listeners = new Set<() => void>();
  private readonly opts: PlayerOptions;
  private mode: VoiceMode;
  /** Step numbers (1-based) whose drawings are complete on the board. */
  private readonly drawn = new Set<number>();
  private token = 0;
  private ctrl: AbortController | null = null;
  private playback: Playback | null = null;
  private pen: Promise<void> | null = null;
  /** The margin sketch being drawn (beside the page, so it runs alongside the annotation pen). */
  private sketchPen: Promise<void> | null = null;
  private advanceTimer = 0;
  private wantPaused = false;
  /** More steps are on their way (a lesson still streaming in). */
  private expecting = false;
  /** The student pressed Next at the end of the received steps: go on as soon as the next one lands. */
  private advanceOnArrival = false;

  constructor(opts: PlayerOptions) {
    this.opts = opts;
    this.mode = opts.mode;
    this.state = {
      status: "idle",
      steps: [],
      current: -1,
      words: [],
      wordIndex: -1,
      progress: 0,
      autoPlay: opts.autoPlay ?? true,
      voice: opts.mode,
      awaitingMore: false,
    };
  }

  // ------------------------------------------------------------ store

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  readonly getState = (): PlayerState => this.state;

  private set(patch: Partial<PlayerState>) {
    this.state = { ...this.state, ...patch };
    for (const l of this.listeners) l();
  }

  // ------------------------------------------------------------ content

  /** Start over with a new lesson (nothing is played until goTo). `more`: further steps will be appended
   *  as they stream in, so reaching the last step waits for them instead of finishing the lesson. */
  load(steps: Step[], more = false) {
    this.halt();
    this.token++;
    this.drawn.clear();
    this.expecting = more;
    this.advanceOnArrival = false;
    this.opts.board()?.clearTutorDrawings();
    this.set({
      status: "idle",
      steps: renumberSteps(steps, 0),
      current: -1,
      words: [],
      wordIndex: -1,
      progress: 0,
      awaitingMore: false,
    });
  }

  /** Append steps (already renumbered): streamed lesson steps or follow-ups. Returns the index of the
   *  first new step. A player waiting at the end of a streaming lesson moves on to it (auto-play or Next). */
  append(steps: Step[]): number {
    const first = this.state.steps.length;
    this.set({ steps: [...this.state.steps, ...steps] });
    if (steps.length && this.state.awaitingMore) {
      const go = this.state.autoPlay || this.advanceOnArrival;
      this.advanceOnArrival = false;
      this.set({ awaitingMore: false });
      if (go) void this.goTo(first);
    }
    return first;
  }

  /** The streamed lesson is complete (`false`): a player waiting for more steps finishes the lesson. */
  setExpectingMore(on: boolean) {
    this.expecting = on;
    if (on || !this.state.awaitingMore) return;
    this.advanceOnArrival = false;
    const index = this.state.current;
    this.opts.board()?.setCurrentStep(index + 1, "show");
    this.set({ status: "finished", awaitingMore: false });
  }

  get stepCount() {
    return this.state.steps.length;
  }

  // ------------------------------------------------------------ transport

  async goTo(index: number): Promise<void> {
    const steps = this.state.steps;
    if (index < 0 || index >= steps.length) return;
    const token = ++this.token;
    this.advanceOnArrival = false;
    await this.settle();
    if (token !== this.token) return;
    this.syncBoard(index + 1);
    this.wantPaused = false;
    await this.run(index, token);
  }

  next() {
    const { current, steps, status, awaitingMore } = this.state;
    if (current < steps.length - 1) void this.goTo(current + 1);
    else if (awaitingMore) this.advanceOnArrival = true;
    else if (current >= 0 && status !== "finished") void this.finishNow();
  }

  prev() {
    const { current } = this.state;
    void this.goTo(Math.max(0, current - 1));
  }

  replay() {
    const { current } = this.state;
    void this.goTo(Math.max(0, current));
  }

  pause() {
    const { status } = this.state;
    if (status !== "playing" && status !== "preparing") return;
    this.wantPaused = true;
    this.playback?.pause();
    this.set({ status: "paused" });
  }

  resume() {
    if (this.state.status !== "paused") return;
    this.wantPaused = false;
    if (this.playback) {
      this.playback.resume();
      this.set({ status: "playing" });
    } else {
      this.set({ status: "preparing" });
    }
  }

  /** Space bar: pause/resume, continue when waiting, start when idle. */
  toggle() {
    const { status, current } = this.state;
    if (status === "playing" || status === "preparing") this.pause();
    else if (status === "paused") this.resume();
    else if (status === "waiting") this.next();
    else if (status === "idle" && this.state.steps.length) void this.goTo(Math.max(0, current));
  }

  setAutoPlay(on: boolean) {
    this.set({ autoPlay: on });
    const { status, current, awaitingMore } = this.state;
    if (on && status === "waiting" && !awaitingMore) {
      const token = this.token;
      window.clearTimeout(this.advanceTimer);
      this.advanceTimer = window.setTimeout(() => {
        if (token === this.token) void this.goTo(current + 1);
      }, ADVANCE_PAUSE_MS / 2);
    }
  }

  /** Switch voices; a narration in progress restarts with the new voice. */
  setVoice(mode: VoiceMode) {
    if (mode === this.mode) return;
    this.mode = mode;
    const { status, current } = this.state;
    if (status === "playing" || status === "preparing" || status === "paused") void this.goTo(current);
  }

  /** Stop narration and drawing; the board keeps what is already drawn. */
  stop() {
    this.token++;
    this.halt();
    const { status } = this.state;
    if (status === "playing" || status === "preparing" || status === "paused") {
      this.set({ status: "waiting" });
    }
  }

  /** Draw every step instantly (end of lesson, after the quiz). */
  showAll(previous: PreviousSteps = "show") {
    this.token++;
    this.halt();
    const board = this.opts.board();
    const steps = this.state.steps;
    if (!board || !steps.length) return;
    board.clearTutorDrawings();
    this.drawn.clear();
    steps.forEach((s, i) => {
      board.drawInstant(s.annotations, i + 1, s.sketch);
      this.drawn.add(i + 1);
    });
    board.setCurrentStep(steps.length, previous);
  }

  dispose() {
    this.token++;
    this.halt();
    this.listeners.clear();
  }

  // ------------------------------------------------------------ internals

  /** Abort the running step: audio stops, in-flight pen strokes complete instantly. */
  private halt() {
    window.clearTimeout(this.advanceTimer);
    this.ctrl?.abort();
    this.ctrl = null;
    this.playback?.stop();
    this.playback = null;
    this.voice.hush();
  }

  private get voice(): VoiceBox {
    return this.opts.voice;
  }

  /** halt() and wait (briefly) until aborted strokes have landed, so clearing removes them. */
  private async settle() {
    this.halt();
    const pens = [this.pen, this.sketchPen].filter((p): p is Promise<void> => !!p);
    if (pens.length) {
      await Promise.race([Promise.all(pens), new Promise((r) => window.setTimeout(r, SETTLE_MS))]);
    }
  }

  /** Make the board show steps 1..k-1 complete and nothing from step k on. */
  private syncBoard(k: number) {
    const board = this.opts.board();
    if (!board) return;
    let first = k;
    for (let s = 1; s < k; s++) {
      if (!this.drawn.has(s)) {
        first = s;
        break;
      }
    }
    board.clearTutorDrawings(first);
    for (const s of [...this.drawn]) if (s >= first) this.drawn.delete(s);
    for (let s = first; s < k; s++) {
      const step = this.state.steps[s - 1];
      board.drawInstant(step.annotations, s, step.sketch);
      this.drawn.add(s);
    }
    board.setCurrentStep(k, "dim");
  }

  private async prepare(text: string, signal: AbortSignal): Promise<PreparedNarration> {
    try {
      return await this.voice.prepare(this.mode, text, signal);
    } catch (err) {
      if (signal.aborted) throw err;
      const fallback: VoiceMode = this.mode !== "browser" && speechAvailable() ? "browser" : "silent";
      this.opts.onNotice?.(`${errorMessage(err)} Switching to ${VOICE_LABELS[fallback].toLowerCase()}.`);
      this.mode = fallback;
      this.opts.onVoiceFallback?.(fallback);
      return this.voice.prepare(fallback, text, signal);
    }
  }

  private startPen(board: BoardHandle, step: Step, annotationIndex: number, signal: AbortSignal) {
    const annotation = step.annotations[annotationIndex];
    const p: Promise<void> = Promise.resolve()
      .then(() => board.drawAnnotation(annotation, { stepIndex: step.index, signal }))
      .catch((err: unknown) => {
        if (!signal.aborted) console.warn("drawAnnotation failed", annotation.id, err);
      })
      .finally(() => {
        if (this.pen === p) this.pen = null;
      });
    this.pen = p;
  }

  private startSketch(board: BoardHandle, step: Step, mermaid: string, signal: AbortSignal): Promise<void> {
    const p: Promise<void> = Promise.resolve()
      .then(() => board.drawSketch(mermaid, { stepIndex: step.index, signal, color: stepInk(step.annotations) }))
      .catch((err: unknown) => {
        if (!signal.aborted) console.warn("drawSketch failed", err);
      })
      .finally(() => {
        if (this.sketchPen === p) this.sketchPen = null;
      });
    this.sketchPen = p;
    return p;
  }

  private async run(index: number, token: number) {
    const step = this.state.steps[index];
    const ctrl = new AbortController();
    this.ctrl = ctrl;
    this.set({
      status: this.wantPaused ? "paused" : "preparing",
      current: index,
      words: placeholderWords(step.narration),
      wordIndex: -1,
      progress: 0,
      awaitingMore: false,
    });

    let prepared: PreparedNarration;
    try {
      prepared = await this.prepare(step.narration, ctrl.signal);
    } catch {
      return; // aborted
    }
    if (ctrl.signal.aborted || token !== this.token) return;

    const following = this.state.steps[index + 1];
    if (following) this.voice.prefetch(this.mode, following.narration);

    const timeline = prepared.timeline;
    const cues = scheduleCues(step.narration, timeline, step.annotations);
    const order = cues.map((c) => step.annotations.indexOf(c.annotation));
    const playback = prepared.play();
    this.playback = playback;
    if (this.wantPaused) playback.pause();
    this.set({
      status: this.wantPaused ? "paused" : "playing",
      words: timeline.words,
      wordIndex: -1,
      progress: 0,
      voice: prepared.mode,
    });

    let narrationDone = false;
    void playback.done.then(() => {
      narrationDone = true;
    });
    const duration = timeline.duration > 0 ? timeline.duration : 1;
    let nextCue = 0;
    // margin sketch: due once every annotation has started and ~40% of the narration is spoken
    let sketch: "none" | "due" | "drawing" | "done" = step.sketch ? "due" : "none";

    await new Promise<void>((resolve) => {
      const tick = () => {
        if (ctrl.signal.aborted) {
          window.clearInterval(timer);
          resolve();
          return;
        }
        const t = narrationDone ? duration : playback.time();
        const wordIndex = narrationDone ? timeline.words.length : wordAt(timeline.words, t);
        const progress = Math.min(1, Math.max(0, t / duration));
        if (wordIndex !== this.state.wordIndex || Math.abs(progress - this.state.progress) >= 0.01) {
          this.set({ wordIndex, progress });
        }
        const board = this.opts.board();
        const paused = this.state.status === "paused";
        if (!this.pen && !paused && nextCue < cues.length && (narrationDone || cues[nextCue].time <= t)) {
          const i = order[nextCue++];
          if (board && i >= 0) this.startPen(board, step, i, ctrl.signal);
        }
        if (sketch === "due" && !paused && nextCue >= cues.length && (narrationDone || t >= SKETCH_AT * duration)) {
          if (board && step.sketch) {
            sketch = "drawing";
            void this.startSketch(board, step, step.sketch, ctrl.signal).then(() => {
              sketch = "done";
            });
          } else {
            sketch = "done";
          }
        }
        if (narrationDone && !this.pen && nextCue >= cues.length && (sketch === "none" || sketch === "done")) {
          window.clearInterval(timer);
          resolve();
        }
      };
      const timer = window.setInterval(tick, 40);
      tick();
    });
    if (ctrl.signal.aborted || token !== this.token) return;

    this.playback = null;
    this.ctrl = null;
    this.drawn.add(index + 1);
    const last = index === this.state.steps.length - 1;
    if (last && this.expecting) {
      // the lesson is still being written: wait here, append() moves on when the next step lands
      this.set({ status: "waiting", awaitingMore: true, wordIndex: timeline.words.length, progress: 1 });
      return;
    }
    this.set({ status: last ? "finished" : "waiting", wordIndex: timeline.words.length, progress: 1 });
    if (last) {
      this.opts.board()?.setCurrentStep(index + 1, "show");
    } else if (this.state.autoPlay) {
      this.advanceTimer = window.setTimeout(() => {
        if (token === this.token && this.state.autoPlay) void this.goTo(index + 1);
      }, ADVANCE_PAUSE_MS);
    }
  }

  /** "Next" on the last step: complete it instantly. */
  private async finishNow() {
    const index = this.state.current;
    const token = ++this.token;
    await this.settle();
    if (token !== this.token) return;
    const board = this.opts.board();
    const step = this.state.steps[index];
    if (board && step) {
      board.clearTutorDrawings(index + 1);
      board.drawInstant(step.annotations, index + 1, step.sketch);
      if (!this.expecting) board.setCurrentStep(index + 1, "show");
    }
    this.drawn.add(index + 1);
    if (index < this.state.steps.length - 1) {
      void this.goTo(index + 1); // the next step landed while this one was being completed
      return;
    }
    if (this.expecting) {
      // Next on the last step received so far: done with it, go on as soon as the next one lands
      this.advanceOnArrival = true;
      this.set({ status: "waiting", awaitingMore: true, wordIndex: this.state.words.length, progress: 1 });
      return;
    }
    this.set({ status: "finished", wordIndex: this.state.words.length, progress: 1 });
  }
}
