// Three ways to "speak" a narration, all exposing the same clock so drawings can follow it:
// ElevenLabs audio with real word timings, the browser's speechSynthesis (boundary events with a
// timer fallback) and a silent caption timer.
import type { StudyLensApi } from "../api";
import { estimateTimeline, type Timeline, timelineFromTts, wordAtChar } from "./timing";

export type VoiceMode = "eleven" | "browser" | "silent";

export const VOICE_LABELS: Record<VoiceMode, string> = {
  eleven: "Tutor voice",
  browser: "Browser voice",
  silent: "Silent captions",
};

export interface Playback {
  /** Narration clock in seconds; frozen while paused. */
  time(): number;
  /** Resolves once the narration has finished or was stopped. Never rejects. */
  readonly done: Promise<void>;
  pause(): void;
  resume(): void;
  stop(): void;
}

export interface PreparedNarration {
  mode: VoiceMode;
  timeline: Timeline;
  play(): Playback;
}

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((r) => (resolve = r));
  return { promise, resolve };
}

/** Pausable clock; `rate` > 1 runs faster (quick demos and screenshot runs). */
class Stopwatch {
  private base: number;
  private since: number | null;
  private readonly rate: number;

  constructor(rate = 1, offsetSeconds = 0, running = true) {
    this.rate = rate;
    this.base = offsetSeconds;
    this.since = running ? performance.now() : null;
  }

  seconds(): number {
    const live = this.since === null ? 0 : ((performance.now() - this.since) / 1000) * this.rate;
    return this.base + live;
  }

  pause() {
    if (this.since !== null) {
      this.base = this.seconds();
      this.since = null;
    }
  }

  resume() {
    if (this.since === null) this.since = performance.now();
  }

  reset(running: boolean) {
    this.base = 0;
    this.since = running ? performance.now() : null;
  }

  get paused() {
    return this.since === null;
  }
}

/** Silent narration: the clock simply runs through the estimated timeline. */
export class TimerPlayback implements Playback {
  private readonly watch: Stopwatch;
  private readonly finished = deferred();
  private timer = 0;
  private stopped = false;
  readonly done: Promise<void>;
  private readonly duration: number;
  private readonly rate: number;

  constructor(duration: number, rate = 1, offsetSeconds = 0) {
    this.duration = duration;
    this.rate = rate;
    this.watch = new Stopwatch(rate, offsetSeconds);
    this.done = this.finished.promise;
    this.arm();
  }

  private arm() {
    window.clearTimeout(this.timer);
    if (this.stopped || this.watch.paused) return;
    const left = Math.max(0, this.duration - this.watch.seconds());
    this.timer = window.setTimeout(() => {
      if (this.watch.seconds() >= this.duration - 0.01) this.finish();
      else this.arm();
    }, (left * 1000) / this.rate + 10);
  }

  private finish() {
    this.stopped = true;
    window.clearTimeout(this.timer);
    this.finished.resolve();
  }

  time() {
    return Math.min(this.watch.seconds(), this.duration);
  }

  pause() {
    this.watch.pause();
    window.clearTimeout(this.timer);
  }

  resume() {
    this.watch.resume();
    this.arm();
  }

  stop() {
    this.finish();
  }
}

/** ElevenLabs mp3 with real word timings; the clock is the audio element itself. */
class AudioPlayback implements Playback {
  private readonly audio: HTMLAudioElement;
  private readonly finished = deferred();
  private fallback: TimerPlayback | null = null;
  private stopped = false;
  private lastProgress = performance.now();
  private lastTime = -1;
  private watchdog = 0;
  readonly done: Promise<void>;
  private readonly duration: number;
  private readonly onBlocked: () => void;

  constructor(audio: HTMLAudioElement, duration: number, onBlocked: () => void) {
    this.audio = audio;
    this.duration = duration;
    this.onBlocked = onBlocked;
    this.done = this.finished.promise;
    audio.onended = () => this.finish();
    audio.onerror = () => this.switchToTimer();
    try {
      audio.currentTime = 0;
    } catch {
      // not seekable yet; it starts at 0 anyway
    }
    this.start();
    this.watchdog = window.setInterval(() => this.check(), 500);
  }

  private start() {
    this.audio.play().catch((err: unknown) => {
      if (this.stopped) return;
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (err instanceof DOMException && err.name === "NotAllowedError") this.onBlocked();
      this.switchToTimer();
    });
  }

  /** Autoplay blocked or the audio stalled: keep the lesson moving on a silent clock. */
  private switchToTimer() {
    if (this.fallback || this.stopped) return;
    const at = Number.isFinite(this.audio.currentTime) ? this.audio.currentTime : 0;
    this.audio.pause();
    this.fallback = new TimerPlayback(this.duration, 1, at);
    void this.fallback.done.then(() => this.finish());
  }

  private check() {
    if (this.stopped || this.fallback || this.audio.paused) {
      this.lastProgress = performance.now();
      return;
    }
    const t = this.audio.currentTime;
    if (t !== this.lastTime) {
      this.lastTime = t;
      this.lastProgress = performance.now();
    } else if (performance.now() - this.lastProgress > 4000) {
      this.switchToTimer();
    }
  }

  private finish() {
    if (this.stopped) return;
    this.stopped = true;
    window.clearInterval(this.watchdog);
    this.audio.onended = null;
    this.audio.onerror = null;
    this.fallback?.stop();
    this.finished.resolve();
  }

  time() {
    if (this.fallback) return this.fallback.time();
    return this.audio.ended ? this.duration : this.audio.currentTime;
  }

  pause() {
    if (this.fallback) this.fallback.pause();
    else this.audio.pause();
  }

  resume() {
    if (this.fallback) this.fallback.resume();
    else if (!this.stopped) this.start();
  }

  stop() {
    this.audio.pause();
    this.finish();
  }
}

/** Browser speech: boundary events drive the clock; without them an estimated timer does. */
class SpeechPlayback implements Playback {
  private readonly finished = deferred();
  private readonly utterance: SpeechSynthesisUtterance;
  /** Runs from the moment speech actually starts. */
  private readonly watch = new Stopwatch(1, 0, false);
  private boundaryWord = -1;
  private boundaryAt = new Stopwatch();
  private started = false;
  private timerOnly = false;
  private userPaused = false;
  private stopped = false;
  private startTimer = 0;
  private safety = 0;
  readonly done: Promise<void>;
  private readonly timeline: Timeline;

  constructor(text: string, timeline: Timeline, voice: SpeechSynthesisVoice | null) {
    this.timeline = timeline;
    this.done = this.finished.promise;
    const synth = window.speechSynthesis;
    const u = new SpeechSynthesisUtterance(text);
    if (voice) {
      u.voice = voice;
      u.lang = voice.lang;
    }
    u.rate = 1;
    u.onstart = () => {
      if (this.started) return;
      this.started = true;
      this.watch.reset(!this.userPaused);
    };
    u.onboundary = (e) => {
      if (e.name && e.name !== "word") return;
      this.boundaryWord = wordAtChar(this.timeline.words, e.charIndex);
      this.boundaryAt = new Stopwatch(1, 0, !this.userPaused);
    };
    u.onend = () => this.finish();
    u.onerror = () => this.finish();
    this.utterance = u;
    synth.cancel();
    // Chrome keeps the engine paused across cancel(); a paused engine never starts new speech.
    if (synth.paused) synth.resume();
    synth.speak(u);
    // No onstart within 2.5 s: speech is unavailable here (no voices, blocked) -> timer only.
    this.startTimer = window.setTimeout(() => {
      if (this.started || this.stopped) return;
      this.started = true;
      this.timerOnly = true;
      u.onend = null;
      u.onerror = null;
      synth.cancel();
      this.watch.reset(!this.userPaused);
    }, 2500);
    this.armSafety();
  }

  /** Finish even if the engine never reports the end (a known Chrome quirk). */
  private armSafety() {
    window.clearTimeout(this.safety);
    if (this.stopped) return;
    this.safety = window.setTimeout(() => {
      if (this.stopped) return;
      const limit = this.timerOnly ? this.timeline.duration : this.timeline.duration * 1.7 + 2;
      if (!this.watch.paused && this.watch.seconds() > limit) this.finish();
      else this.armSafety();
    }, 250);
  }

  time(): number {
    const words = this.timeline.words;
    if (!this.timerOnly && this.boundaryWord >= 0 && this.boundaryWord < words.length) {
      const w = words[this.boundaryWord];
      return w.start + Math.min(this.boundaryAt.seconds(), w.end - w.start + 0.25);
    }
    return Math.min(this.watch.seconds(), this.timeline.duration);
  }

  pause() {
    this.userPaused = true;
    this.watch.pause();
    this.boundaryAt.pause();
    if (!this.timerOnly) window.speechSynthesis.pause();
  }

  resume() {
    this.userPaused = false;
    if (this.started) this.watch.resume();
    this.boundaryAt.resume();
    if (!this.timerOnly) window.speechSynthesis.resume();
  }

  stop() {
    if (!this.stopped && !this.timerOnly) {
      this.utterance.onend = null;
      this.utterance.onerror = null;
      window.speechSynthesis.cancel();
    }
    this.finish();
  }

  private finish() {
    if (this.stopped) return;
    this.stopped = true;
    window.clearTimeout(this.startTimer);
    window.clearTimeout(this.safety);
    this.utterance.onend = null;
    this.utterance.onerror = null;
    this.utterance.onboundary = null;
    this.finished.resolve();
  }
}

export function speechAvailable(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

const PREFERRED = [
  /natural/i,
  /\b(aria|jenny|ava|emma|andrew|brian|libby|sonia)\b/i,
  /google us english/i,
  /\b(samantha|alex|daniel|karen)\b/i,
  /\b(zira|david|mark|hazel)\b/i,
];

export function pickBrowserVoice(): SpeechSynthesisVoice | null {
  if (!speechAvailable()) return null;
  const voices = window.speechSynthesis.getVoices();
  const english = voices.filter((v) => /^en([-_]|$)/i.test(v.lang));
  for (const re of PREFERRED) {
    const v = english.find((x) => re.test(x.name));
    if (v) return v;
  }
  return english.find((v) => /en[-_]US/i.test(v.lang)) ?? english[0] ?? voices[0] ?? null;
}

interface ElevenAsset {
  timeline: Timeline;
  audio: HTMLAudioElement;
}

function waitForAudio(audio: HTMLAudioElement, ms: number): Promise<void> {
  return new Promise((resolve) => {
    if (audio.readyState >= 3) {
      resolve();
      return;
    }
    const done = () => {
      window.clearTimeout(timer);
      audio.removeEventListener("canplaythrough", done);
      audio.removeEventListener("error", done);
      resolve();
    };
    const timer = window.setTimeout(done, ms);
    audio.addEventListener("canplaythrough", done);
    audio.addEventListener("error", done);
    audio.load();
  });
}

function abortable<T>(promise: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return promise;
  if (signal.aborted) return Promise.reject(new DOMException("Aborted", "AbortError"));
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => reject(new DOMException("Aborted", "AbortError"));
    signal.addEventListener("abort", onAbort, { once: true });
    promise.then(
      (v) => {
        signal.removeEventListener("abort", onAbort);
        resolve(v);
      },
      (e: unknown) => {
        signal.removeEventListener("abort", onAbort);
        reject(e instanceof Error ? e : new Error(String(e)));
      },
    );
  });
}

/** Prepares narrations for the selected voice; caches ElevenLabs results by text. */
export class VoiceBox {
  private readonly api: StudyLensApi;
  private readonly eleven = new Map<string, Promise<ElevenAsset>>();
  /** Silent clock speed (1 = ~170 wpm); ?speed=N in the URL for quick demos. */
  silentRate = 1;
  onAutoplayBlocked: () => void = () => {};

  constructor(api: StudyLensApi) {
    this.api = api;
    if (speechAvailable()) {
      // Chrome fills the voice list asynchronously.
      window.speechSynthesis.getVoices();
      window.speechSynthesis.addEventListener?.("voiceschanged", () => window.speechSynthesis.getVoices());
    }
  }

  private loadEleven(text: string): Promise<ElevenAsset> {
    let p = this.eleven.get(text);
    if (!p) {
      p = (async () => {
        const res = await this.api.tts(text);
        const audio = new Audio(res.audio_url);
        audio.preload = "auto";
        await waitForAudio(audio, 6000);
        const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : res.duration;
        return { audio, timeline: timelineFromTts(text, res.words, duration) };
      })();
      this.eleven.set(text, p);
      p.catch(() => this.eleven.delete(text));
    }
    return p;
  }

  /** Warm up the next narration so steps follow each other without a gap. */
  prefetch(mode: VoiceMode, text: string) {
    if (mode === "eleven" && text.trim()) this.loadEleven(text).catch(() => undefined);
  }

  async prepare(mode: VoiceMode, text: string, signal?: AbortSignal): Promise<PreparedNarration> {
    if (mode === "eleven") {
      const asset = await abortable(this.loadEleven(text), signal);
      return {
        mode,
        timeline: asset.timeline,
        play: () => new AudioPlayback(asset.audio, asset.timeline.duration, () => this.onAutoplayBlocked()),
      };
    }
    if (mode === "browser" && speechAvailable()) {
      const timeline = estimateTimeline(text, 165);
      const voice = pickBrowserVoice();
      return { mode, timeline, play: () => new SpeechPlayback(text, timeline, voice) };
    }
    const timeline = estimateTimeline(text, 170);
    const rate = this.silentRate;
    return { mode: "silent", timeline, play: () => new TimerPlayback(timeline.duration, rate) };
  }

  /** Cancel any speech still queued in the browser engine. */
  hush() {
    if (speechAvailable()) window.speechSynthesis.cancel();
  }
}
