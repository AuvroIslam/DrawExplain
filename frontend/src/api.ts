// Typed client for the StudyLens backend (FastAPI, prefix /api; Vite proxies it in dev).
import type {
  FollowupRequest,
  FollowupResponse,
  Health,
  Lesson,
  Perception,
  SampleInfo,
  Step,
  TTSResponse,
} from "./types";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Callbacks of a streamed lesson, in arrival order: meta, header, then one call per step. */
export interface LessonStreamHandlers {
  onMeta?: (meta: { lesson_id: string; image_id: string; model: string }) => void;
  onHeader?: (header: { title: string; summary: string }) => void;
  /** A grounded, validated step (same shape as Lesson.steps[i]), as soon as the model has written it. */
  onStep?: (step: Step) => void;
}

/** Everything the app needs from the server; the mock (?mock=1) implements the same shape. */
export interface StudyLensApi {
  readonly mock: boolean;
  health(): Promise<Health>;
  /** `page` (1-based) picks the page of a PDF upload; images ignore it. */
  uploadImage(file: File, signal?: AbortSignal, page?: number): Promise<Perception>;
  listSamples(): Promise<SampleInfo[]>;
  loadSample(name: string, signal?: AbortSignal): Promise<Perception>;
  createLesson(imageId: string, model?: string | null, signal?: AbortSignal): Promise<Lesson>;
  /** POST /api/lessons/stream (NDJSON): steps arrive through `handlers`; resolves with the full lesson
   *  (steps + quiz) and rejects on an HTTP error, an in-band {"type":"error"} or a stream cut short. */
  streamLesson(
    imageId: string,
    handlers: LessonStreamHandlers,
    model?: string | null,
    signal?: AbortSignal,
  ): Promise<Lesson>;
  askFollowup(req: FollowupRequest, signal?: AbortSignal): Promise<FollowupResponse>;
  tts(text: string, voiceId?: string | null, signal?: AbortSignal): Promise<TTSResponse>;
}

export const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;
export const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp", "application/pdf"];

/** PDFs are rendered one page at a time by the server (POST /api/images with a `page` field). */
export function isPdfFile(file: File): boolean {
  return file.type === "application/pdf" || /\.pdf$/i.test(file.name);
}

/** Backend origin when the API is deployed apart from the frontend (e.g. Vercel + Render); "" = same origin. */
export const API_BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? "").trim().replace(/\/+$/, "");

/** Absolute URL for a server path ("/api/...") when the API lives on another origin. */
export function apiUrl(path: string): string;
export function apiUrl(path: string | null): string | null;
export function apiUrl(path: string | null): string | null {
  if (!path || !API_BASE || !path.startsWith("/")) return path;
  return API_BASE + path;
}

const withPerceptionUrls = (p: Perception): Perception => ({
  ...p,
  image_url: apiUrl(p.image_url),
  marked_url: apiUrl(p.marked_url),
});

const OFFLINE_MESSAGE = API_BASE
  ? "Can't reach the StudyLens server. Please try again in a moment."
  : "Can't reach the StudyLens server. Is the backend running on port 8000?";
const TIMEOUT_MS = 120_000;

function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : null))
      .filter((m): m is string => !!m);
    if (parts.length) return parts.join("; ");
  }
  return null;
}

function fallbackMessage(status: number): string {
  if (status === 404) return "The server doesn't know this image any more. Please upload it again.";
  if (status === 413) return "That image is too large (the limit is 15 MB).";
  if (status === 502) return "The AI service didn't answer. Please try again.";
  if (status >= 500) return OFFLINE_MESSAGE;
  return `Request failed (${status}).`;
}

function withTimeout(signal?: AbortSignal): AbortSignal {
  const timeout = AbortSignal.timeout(TIMEOUT_MS);
  return signal ? AbortSignal.any([signal, timeout]) : timeout;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), { ...init, signal: withTimeout(init.signal ?? undefined) });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    if (err instanceof DOMException && err.name === "TimeoutError") {
      throw new ApiError("The server took too long to answer. Please try again.", 0);
    }
    throw new ApiError(OFFLINE_MESSAGE, 0);
  }
  const isJson = (res.headers.get("content-type") ?? "").includes("application/json");
  if (!res.ok) {
    let message: string | null = null;
    if (isJson) {
      try {
        message = describeDetail(((await res.json()) as { detail?: unknown }).detail);
      } catch {
        message = null;
      }
    }
    throw new ApiError(message ?? fallbackMessage(res.status), res.status);
  }
  if (!isJson) throw new ApiError(OFFLINE_MESSAGE, res.status);
  return (await res.json()) as T;
}

function fetchError(err: unknown): unknown {
  if (err instanceof DOMException && err.name === "AbortError") return err;
  if (err instanceof DOMException && err.name === "TimeoutError") {
    return new ApiError("The server took too long to answer. Please try again.", 0);
  }
  if (err instanceof ApiError) return err;
  return new ApiError(OFFLINE_MESSAGE, 0);
}

type StreamEvent =
  | { type: "meta"; lesson_id: string; image_id: string; model: string }
  | { type: "header"; title: string; summary: string }
  | { type: "step"; step: Step }
  | { type: "lesson"; lesson: Lesson }
  | { type: "error"; detail: unknown };

async function streamLesson(
  imageId: string,
  handlers: LessonStreamHandlers,
  model?: string | null,
  signal?: AbortSignal,
): Promise<Lesson> {
  let res: Response;
  try {
    res = await fetch(apiUrl("/api/lessons/stream"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/x-ndjson" },
      body: JSON.stringify({ image_id: imageId, model: model ?? null }),
      signal: withTimeout(signal),
    });
  } catch (err) {
    throw fetchError(err);
  }
  if (!res.ok) {
    let message: string | null = null;
    if ((res.headers.get("content-type") ?? "").includes("application/json")) {
      try {
        message = describeDetail(((await res.json()) as { detail?: unknown }).detail);
      } catch {
        message = null;
      }
    }
    throw new ApiError(message ?? fallbackMessage(res.status), res.status);
  }
  if (!res.body) throw new ApiError("This browser cannot read a streamed answer.", 0);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let lesson: Lesson | null = null;
  const safely = (fn: () => void) => {
    try {
      fn();
    } catch (err) {
      console.error("lesson stream handler failed", err);
    }
  };
  const handle = (line: string) => {
    const text = line.trim();
    if (!text) return;
    let ev: StreamEvent;
    try {
      ev = JSON.parse(text) as StreamEvent;
    } catch {
      throw new ApiError("The lesson stream sent something unreadable.", 0);
    }
    if (ev.type === "meta") safely(() => handlers.onMeta?.(ev));
    else if (ev.type === "header") safely(() => handlers.onHeader?.({ title: ev.title, summary: ev.summary }));
    else if (ev.type === "step") safely(() => handlers.onStep?.(ev.step));
    else if (ev.type === "lesson") lesson = ev.lesson;
    else if (ev.type === "error") throw new ApiError(describeDetail(ev.detail) ?? "Lesson planning failed.", 502);
  };
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl = buffer.indexOf("\n");
      while (nl >= 0) {
        handle(buffer.slice(0, nl));
        buffer = buffer.slice(nl + 1);
        nl = buffer.indexOf("\n");
      }
    }
    handle(buffer + decoder.decode());
  } catch (err) {
    void reader.cancel().catch(() => undefined);
    throw fetchError(err);
  }
  if (!lesson) throw new ApiError("The lesson stream ended before the lesson was complete.", 0);
  return lesson;
}

function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

/** Client-side checks that mirror the server's upload rules; returns an error message or null. */
export function validateImageFile(file: File): string | null {
  if (file.type && !ACCEPTED_TYPES.includes(file.type) && !isPdfFile(file)) {
    return "Please choose a PNG, JPG or WebP image, or a PDF.";
  }
  if (file.size > MAX_UPLOAD_BYTES) return "That file is too large (the limit is 15 MB).";
  if (file.size === 0) return "That file is empty.";
  return null;
}

export const api: StudyLensApi = {
  mock: false,
  health: () => request<Health>("/api/health"),
  uploadImage(file, signal, page) {
    const form = new FormData();
    form.append("file", file, file.name || (isPdfFile(file) ? "upload.pdf" : "upload.png"));
    if (page && page > 1) form.append("page", String(Math.round(page)));
    return request<Perception>("/api/images", { method: "POST", body: form, signal }).then(withPerceptionUrls);
  },
  listSamples: () =>
    request<SampleInfo[]>("/api/samples").then((list) => list.map((s) => ({ ...s, url: apiUrl(s.url) }))),
  loadSample: (name, signal) =>
    postJson<Perception>("/api/samples/load", { name }, signal).then(withPerceptionUrls),
  createLesson: (imageId, model, signal) =>
    postJson<Lesson>("/api/lessons", { image_id: imageId, model: model ?? null }, signal),
  streamLesson,
  askFollowup: (req, signal) => postJson<FollowupResponse>("/api/followups", req, signal),
  tts: (text, voiceId, signal) =>
    postJson<TTSResponse>("/api/tts", { text, voice_id: voiceId ?? null }, signal).then((r) => ({
      ...r,
      audio_url: apiUrl(r.audio_url),
    })),
};

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error && err.message) return err.message;
  return "Something went wrong.";
}

export function isAbort(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}
