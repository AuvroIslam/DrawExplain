// The page flow: open an image -> scan (perception) -> plan a lesson -> play it -> follow-ups -> quiz.
// PDFs open in reader mode: pages are plain images the student turns freely; "Explain this page" scans
// that page only, then teaches it (optionally around the student's question). Lessons are remembered
// per page, so coming back to a page offers "Replay lesson".
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  cleanQuestion,
  documentPageUrl,
  errorMessage,
  isAbort,
  isPdfFile,
  type LessonMeta,
  type StudyLensApi,
} from "../api";
import type { BoardHandle } from "../board/types";
import type { BoardSlot } from "../player/boardSlot";
import { type LessonPlayer, renumberSteps } from "../player/lessonPlayer";
import type { Box, DocumentInfo, FollowupResponse, Lesson, Perception, Point, QuizItem, Step } from "../types";

/** A file upload; for a PDF, `page` is the 1-based page shown and `pages` the page count once known. */
export type PageSource =
  | { kind: "file"; file: File; name: string; page?: number; pages?: number }
  | { kind: "sample"; name: string; url: string };

/** loading: a PDF is being uploaded; idle: a document page is shown but not scanned (reader mode);
 *  scanning: perception in flight; found: regions flash on the board; done: ready to teach. */
export type ScanState = "loading" | "idle" | "scanning" | "found" | "done" | "error";

export interface Section {
  kind: "lesson" | "followup";
  /** Lesson title, or the student's question. */
  title: string;
  /** Index of the section's first step in the player's step list. */
  start: number;
  count: number;
}

export type QuizResult = "first" | "second" | "missed";

export interface QuizState {
  index: number;
  tries: number;
  phase: "asking" | "correct" | "revealed" | "summary";
  results: QuizResult[];
  /** Bumped on every wrong tap so the card can shake. */
  wrongTaps: number;
}

/** What was taught on one document page, kept for "Replay lesson" when the student comes back. */
export interface PageLesson {
  perception: Perception;
  lesson: Lesson;
  sections: Section[];
  followups: FollowupResponse[];
}

/** Reader mode (PDF uploads): the document, the page on the board and the lessons taught so far. */
export interface Reader {
  doc: DocumentInfo;
  /** 1-based page on the board (0 until the first page is shown). */
  page: number;
  /** Lessons taught in this session, by page number. */
  explained: Record<number, PageLesson>;
  /** The page image is still on its way to the board. */
  loading: boolean;
}

export interface Session {
  id: number;
  source: PageSource;
  /** Local preview while the server works ("" for a PDF until a page image is known). */
  previewUrl: string;
  perception: Perception | null;
  scan: ScanState;
  scanError: string | null;
  lesson: Lesson | null;
  /** The lesson is still streaming in: `lesson` holds the steps received so far and no quiz yet. */
  streaming: boolean;
  planning: boolean;
  planStartedAt: number;
  planError: string | null;
  sections: Section[];
  followups: FollowupResponse[];
  asking: string | null;
  askError: string | null;
  quiz: QuizState | null;
  /** Set for PDFs opened in reader mode. */
  reader: Reader | null;
}

export const MAX_SIDE = 1600;
const MIN_SCAN_MS = 1900;
const FOUND_MS = 1500;
const TAP_TOLERANCE = 0.03;
/** Page images kept in memory (turning back and forth, prefetched next page). */
const PAGE_CACHE = 10;

const sleep = (ms: number) => new Promise<void>((r) => window.setTimeout(r, Math.max(0, ms)));

function naturalSize(url: string): Promise<{ w: number; h: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = () => reject(new Error("preview failed"));
    img.src = url;
  });
}

/** Size the server will give the processed image (max side MAX_SIDE, aspect kept). */
function processedSize({ w, h }: { w: number; h: number }) {
  const k = Math.min(1, MAX_SIDE / Math.max(w, h));
  return { w: Math.max(1, Math.round(w * k)), h: Math.max(1, Math.round(h * k)) };
}

export function expandBox(b: Box, margin: number): Box {
  return { x: b.x - margin, y: b.y - margin, w: b.w + 2 * margin, h: b.h + 2 * margin };
}

export function insideBox(b: Box, p: Point): boolean {
  return p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h;
}

function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 4000);
}

function freshSession(id: number, source: PageSource, previewUrl: string, scan: ScanState, reader: Reader | null): Session {
  return {
    id,
    source,
    previewUrl,
    perception: null,
    scan,
    scanError: null,
    lesson: null,
    streaming: false,
    planning: false,
    planStartedAt: 0,
    planError: null,
    sections: [],
    followups: [],
    asking: null,
    askError: null,
    quiz: null,
    reader,
  };
}

/** Headline of a failed open: the PDF upload, a page image (reader mode) or a scan. */
export function scanErrorTitle(session: Session): string {
  if (session.reader) return "This page didn’t load";
  if (session.source.kind === "file" && isPdfFile(session.source.file) && !session.source.page) {
    return "I couldn’t open this PDF";
  }
  return "I couldn’t read this page";
}

/** Reader mode: file a finished lesson (with its follow-ups) under its page, for Replay. */
function remember(s: Session): Session {
  const r = s.reader;
  if (!r || r.page < 1 || !s.perception || !s.lesson || s.streaming || s.planning) return s;
  const prev = r.explained[r.page];
  if (prev && prev.lesson === s.lesson && prev.sections === s.sections && prev.followups === s.followups) return s;
  const entry: PageLesson = { perception: s.perception, lesson: s.lesson, sections: s.sections, followups: s.followups };
  return { ...s, reader: { ...r, explained: { ...r.explained, [r.page]: entry } } };
}

/** The player's step list of a remembered lesson: its steps, then each follow-up's (as `ask` built it). */
function replaySteps(saved: PageLesson): Step[] {
  const steps = [...saved.lesson.steps];
  saved.followups.forEach((f, i) => steps.push(...renumberSteps(f.steps, steps.length, `q${i + 1}-`)));
  return steps;
}

interface Deps {
  api: StudyLensApi;
  player: LessonPlayer;
  slot: BoardSlot;
  notify: (message: string, kind?: "info" | "success" | "error") => void;
}

export function useStudySession({ api, player, slot, notify }: Deps) {
  const [session, setSession] = useState<Session | null>(null);
  const [debug, setDebugState] = useState(false);
  const ref = useRef<Session | null>(null);
  const debugRef = useRef(false);
  const counter = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const tapOff = useRef<(() => void) | null>(null);
  const oldUrls = useRef<string[]>([]);
  /** The optional focus question being typed ("What should I focus on?"); read when the lesson is asked for. */
  const draft = useRef("");
  /** Page image URL -> local object URL (LRU). */
  const pageImages = useRef(new Map<string, Promise<string>>());

  const commit = useCallback((next: Session | null) => {
    const s = next && remember(next);
    ref.current = s;
    setSession(s);
  }, []);

  /** Update the session `id` if it is still the current one. */
  const patch = useCallback(
    (id: number, fn: (s: Session) => Partial<Session>): boolean => {
      const cur = ref.current;
      if (!cur || cur.id !== id) return false;
      commit({ ...cur, ...fn(cur) });
      return true;
    },
    [commit],
  );

  const onBoardReady = useCallback((handle: BoardHandle) => slot.set(handle), [slot]);

  const stopQuizTaps = () => {
    tapOff.current?.();
    tapOff.current = null;
  };

  const releaseUrls = () => {
    const urls = oldUrls.current;
    oldUrls.current = [];
    window.setTimeout(() => urls.forEach((u) => URL.revokeObjectURL(u)), 10_000);
  };

  const dropPageImages = () => {
    const cache = pageImages.current;
    const all = [...cache.values()];
    cache.clear();
    for (const p of all) void p.then((u) => window.setTimeout(() => URL.revokeObjectURL(u), 10_000), () => undefined);
  };

  const debugOff = () => {
    if (!debugRef.current) return;
    debugRef.current = false;
    setDebugState(false);
  };

  /** A document page as a local object URL: fetched once, so turning back (or onto a prefetched page) is instant. */
  const pageImage = useCallback((url: string): Promise<string> => {
    const cache = pageImages.current;
    const hit = cache.get(url);
    if (hit) {
      cache.delete(url);
      cache.set(url, hit);
      return hit;
    }
    const load = fetch(url).then(async (res) => {
      if (!res.ok) throw new ApiError(`The page image didn't load (${res.status}).`, res.status);
      return URL.createObjectURL(await res.blob());
    });
    cache.set(url, load);
    load.catch(() => {
      if (cache.get(url) === load) cache.delete(url);
    });
    while (cache.size > PAGE_CACHE) {
      const [oldest, gone] = cache.entries().next().value as [string, Promise<string>];
      cache.delete(oldest);
      void gone.then((u) => window.setTimeout(() => URL.revokeObjectURL(u), 10_000), () => undefined);
    }
    return load;
  }, []);

  // ---------------------------------------------------------------- reader mode (PDF)

  /** Show page `page` of the open document as a plain image (nothing is scanned). A playing lesson stops and
   *  its drawings go; a page explained before comes back with its lesson ready to replay. */
  const showPage = useCallback(
    async (page: number, force = false) => {
      const cur = ref.current;
      const r = cur?.reader;
      if (!cur || !r) return;
      const p = Math.round(page);
      if (!Number.isFinite(p) || p < 1 || p > r.doc.pages || (p === r.page && !force)) return;
      const id = ++counter.current;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      stopQuizTaps();
      player.load([]);
      debugOff();
      const saved = r.explained[p] ?? null;
      draft.current = saved?.lesson.question ?? "";
      const url = documentPageUrl(r.doc, p);
      commit({
        ...freshSession(id, cur.source, url, saved ? "done" : "idle", { ...r, page: p, loading: true }),
        perception: saved?.perception ?? null,
      });
      const alive = () => counter.current === id && !ctrl.signal.aborted;
      const [w, h] = r.doc.page_sizes[p - 1] ?? r.doc.page_sizes[0] ?? [1280, 720];
      try {
        const [b, local] = await Promise.all([slot.when(), pageImage(url)]);
        if (!alive()) return;
        await b.loadImage(local, w, h);
      } catch (err) {
        if (!alive()) return;
        patch(id, (s) => ({
          scan: "error",
          scanError: errorMessage(err),
          reader: s.reader && { ...s.reader, loading: false },
        }));
        return;
      }
      if (!alive()) return;
      patch(id, (s) => ({ reader: s.reader && { ...s.reader, loading: false } }));
      // warm the neighbours so the next turn is instant
      if (p < r.doc.pages) pageImage(documentPageUrl(r.doc, p + 1)).catch(() => undefined);
      if (p > 1) pageImage(documentPageUrl(r.doc, p - 1)).catch(() => undefined);
    },
    [commit, pageImage, patch, player, slot],
  );

  /** Left / Right arrows in reader mode. */
  const turnPage = useCallback(
    (delta: number) => {
      const r = ref.current?.reader;
      if (r) void showPage(r.page + delta);
    },
    [showPage],
  );

  // ---------------------------------------------------------------- page

  const open = useCallback(
    async (source: PageSource) => {
      const id = ++counter.current;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      stopQuizTaps();
      player.load([]);
      releaseUrls();
      dropPageImages();
      debugOff();
      draft.current = "";
      const alive = () => counter.current === id && !ctrl.signal.aborted;
      const pdf = source.kind === "file" && isPdfFile(source.file);

      // PDFs: reader mode. The file is stored, page 1 is shown, nothing is scanned yet.
      if (pdf && source.kind === "file" && !source.page) {
        commit(freshSession(id, source, "", "loading", null));
        let doc: DocumentInfo | null = null;
        try {
          doc = await api.uploadDocument(source.file, ctrl.signal);
        } catch (err) {
          if (!alive() || isAbort(err)) return;
          const noReader = err instanceof ApiError && (err.status === 404 || err.status === 405);
          if (!noReader) {
            patch(id, () => ({ scan: "error", scanError: errorMessage(err) }));
            return;
          }
          // a server without /api/documents: scan the PDF a page at a time (POST /api/images) below
        }
        if (doc) {
          if (!alive()) return;
          const d = doc;
          patch(id, () => ({ scan: "idle", reader: { doc: d, page: 0, explained: {}, loading: true } }));
          void showPage(1);
          return;
        }
      }

      const previewUrl = source.kind === "sample" ? source.url : pdf ? "" : URL.createObjectURL(source.file);
      if (source.kind === "file" && previewUrl) oldUrls.current.push(previewUrl);
      commit(freshSession(id, source, previewUrl, "scanning", null));
      const started = performance.now();

      // Show the picture right away while perception runs.
      const estimate = previewUrl ? await naturalSize(previewUrl).then(processedSize, () => null) : null;
      const shown = slot.when().then(async (b) => {
        if (alive() && estimate) await b.loadImage(previewUrl, estimate.w, estimate.h);
        return b;
      });

      let perception: Perception;
      try {
        perception =
          source.kind === "file"
            ? await api.uploadImage(source.file, ctrl.signal, source.page)
            : await api.loadSample(source.name, ctrl.signal);
      } catch (err) {
        if (!alive() || isAbort(err)) return;
        patch(id, () => ({ scan: "error", scanError: errorMessage(err) }));
        return;
      }
      const b = await shown;
      if (!alive()) return;
      const sameShape =
        !!estimate && Math.abs(estimate.w / estimate.h - perception.width / perception.height) < 0.01;
      const otherPicture = api.mock && perception.image_url !== previewUrl;
      const pictureUrl = perception.image_url ?? previewUrl;
      if ((!sameShape || otherPicture) && pictureUrl) {
        await b.loadImage(pictureUrl, perception.width, perception.height);
      }
      await sleep(started + MIN_SCAN_MS - performance.now());
      if (!alive()) return;
      patch(id, (s) => ({ perception, scan: "found", previewUrl: s.previewUrl || pictureUrl }));
      b.showRegions(perception.regions);
      await sleep(FOUND_MS);
      if (!alive()) return;
      b.showRegions(debugRef.current ? perception.regions : null);
      b.showBadges(debugRef.current);
      patch(id, () => ({ scan: "done" }));
    },
    [api, commit, patch, player, showPage, slot],
  );

  const retryScan = useCallback(() => {
    const cur = ref.current;
    if (!cur) return;
    if (cur.reader && cur.reader.page > 0) void showPage(cur.reader.page, true);
    else void open(cur.source);
  }, [open, showPage]);

  /** Page picker: reader mode turns the page; PDFs on a server without reader mode re-scan the new page. */
  const openPage = useCallback(
    (page: number) => {
      const cur = ref.current;
      if (!cur) return;
      if (cur.reader) {
        void showPage(page);
        return;
      }
      if (cur.source.kind !== "file") return;
      const pages = cur.perception?.source_pages ?? cur.source.pages ?? 0;
      const p = Math.round(page);
      if (!Number.isFinite(p) || p < 1 || p > pages || p === (cur.source.page ?? 1)) return;
      void open({ ...cur.source, page: p, pages });
    },
    [open, showPage],
  );

  /** Back to the landing page. */
  const reset = useCallback(() => {
    counter.current++;
    abortRef.current?.abort();
    stopQuizTaps();
    player.load([]);
    slot.reset();
    releaseUrls();
    dropPageImages();
    draft.current = "";
    commit(null);
  }, [commit, player, slot]);

  // ---------------------------------------------------------------- lesson

  /** Whole lesson in hand (non-streamed endpoint, or a stream that delivered everything at once). */
  const startLesson = useCallback(
    (id: number, lesson: Lesson) => {
      player.load(lesson.steps);
      patch(id, () => ({
        lesson,
        streaming: false,
        planning: false,
        sections: [{ kind: "lesson", title: lesson.title, start: 0, count: lesson.steps.length }],
      }));
      if (lesson.steps.length) void player.goTo(0);
    },
    [patch, player],
  );

  /** Plan the lesson over the streaming endpoint: step 1 starts playing as soon as it lands and later steps
   *  append while it plays. Falls back to POST /api/lessons when the stream fails before any step.
   *  `gate`: the model starts at once, but steps wait on the board until it resolves (the scan's found moment). */
  const plan = useCallback(
    async (id: number, imageId: string, question: string | null, signal: AbortSignal | undefined, gate?: Promise<void>) => {
      const live = () => ref.current?.id === id && !signal?.aborted;
      patch(id, () => ({ planning: true, planStartedAt: Date.now(), planError: null }));

      let meta: LessonMeta = { lesson_id: "", image_id: imageId, model: "" };
      let header = { title: "", summary: "" };
      let received = 0;
      const deliver = (raw: Step) => {
        if (!live()) return;
        const [step] = renumberSteps([raw], received);
        received += 1;
        if (received === 1) {
          player.load([step], true);
          const lesson: Lesson = {
            lesson_id: meta.lesson_id,
            image_id: imageId,
            title: header.title || "Your lesson",
            summary: header.summary,
            steps: [step],
            quiz: [],
            model: meta.model,
            timings: {},
            warnings: [],
            question: meta.question ?? question,
            context_pages: meta.context_pages ?? [],
          };
          patch(id, () => ({
            lesson,
            streaming: true,
            planning: false,
            sections: [{ kind: "lesson", title: lesson.title, start: 0, count: 1 }],
          }));
          void player.goTo(0);
          return;
        }
        player.append([step]);
        patch(id, (s) => ({
          lesson: s.lesson && { ...s.lesson, steps: [...s.lesson.steps, step] },
          sections: s.sections.map((sec) => (sec.kind === "lesson" ? { ...sec, count: received } : sec)),
        }));
      };
      let gateOpen = !gate;
      const held: Step[] = [];
      const onStep = (raw: Step) => {
        if (!live()) return;
        if (gateOpen) deliver(raw);
        else held.push(raw);
      };
      const opened = gate?.then(() => {
        gateOpen = true;
        for (const s of held.splice(0)) deliver(s);
      });
      const withQuestion = (l: Lesson): Lesson => ({ ...l, question: l.question ?? question });

      try {
        const lesson = withQuestion(
          await api.streamLesson(
            imageId,
            { onMeta: (m) => (meta = m), onHeader: (h) => (header = h), onStep },
            null,
            signal,
            question,
          ),
        );
        await opened;
        if (!live()) return;
        if (received === 0) {
          startLesson(id, lesson);
          return;
        }
        // steps the stream did not deliver one by one (should not happen): add them now
        const missing = lesson.steps.slice(received);
        if (missing.length) player.append(renumberSteps(missing, received));
        const count = received + missing.length;
        player.setExpectingMore(false);
        patch(id, (s) => ({
          lesson: { ...lesson, steps: s.lesson ? [...s.lesson.steps, ...missing] : lesson.steps },
          streaming: false,
          sections: s.sections.map((sec) => (sec.kind === "lesson" ? { ...sec, title: lesson.title, count } : sec)),
        }));
      } catch (err) {
        await opened;
        if (isAbort(err) || !live()) return;
        if (received > 0) {
          // part of the lesson already plays: keep it rather than start over
          player.setExpectingMore(false);
          patch(id, () => ({ streaming: false }));
          notify(`The rest of the lesson didn't arrive: ${errorMessage(err)}`, "error");
          return;
        }
        console.warn("lesson stream failed, using /api/lessons", err);
        try {
          const lesson = await api.createLesson(imageId, null, signal, question);
          if (live()) startLesson(id, withQuestion(lesson));
        } catch (err2) {
          if (isAbort(err2) || !live()) return;
          patch(id, () => ({ planning: false, planError: errorMessage(err2) }));
        }
      }
    },
    [api, notify, patch, player, startLesson],
  );

  /** "Teach me this" / "Explain this page", with the optional focus question being typed. In reader mode the
   *  page is scanned first (only this page), and the model starts planning while the found moment plays. */
  const teach = useCallback(async () => {
    const cur = ref.current;
    if (!cur || cur.planning || cur.lesson || cur.streaming) return;
    if (cur.scan !== "done" && cur.scan !== "idle") return;
    const id = cur.id;
    const signal = abortRef.current?.signal;
    const live = () => ref.current?.id === id && !signal?.aborted;
    const question = cleanQuestion(draft.current);
    if (cur.perception) {
      await plan(id, cur.perception.image_id, question, signal);
      return;
    }
    const r = cur.reader;
    if (!r || r.loading || r.page < 1) return;

    patch(id, () => ({ scan: "scanning", scanError: null, planError: null }));
    const started = performance.now();
    let perception: Perception;
    try {
      perception = await api.perceivePage(r.doc.doc_id, r.page, signal);
    } catch (err) {
      if (isAbort(err) || !live()) return;
      patch(id, () => ({ scan: "idle", planError: `I couldn't read this page. ${errorMessage(err)}` }));
      return;
    }
    if (!live()) return;
    const p = perception;
    // the found moment: regions flash on the page, then the lesson draws over it
    const moment = (async () => {
      const b = await slot.when();
      if (!live()) return;
      const [w, h] = r.doc.page_sizes[r.page - 1] ?? [0, 0];
      if (Math.abs(w - p.width) > 1 || Math.abs(h - p.height) > 1) {
        // scanned at another size: show the scan's own picture so the drawings line up
        await b.loadImage(p.image_url ?? documentPageUrl(r.doc, r.page), p.width, p.height);
      }
      await sleep(started + MIN_SCAN_MS - performance.now());
      if (!live()) return;
      patch(id, () => ({ perception: p, scan: "found" }));
      b.showRegions(p.regions);
      await sleep(FOUND_MS);
      if (!live()) return;
      b.showRegions(debugRef.current ? p.regions : null);
      b.showBadges(debugRef.current);
      patch(id, () => ({ scan: "done" }));
    })();
    await plan(id, p.image_id, question, signal, moment);
  }, [api, patch, plan, slot]);

  /** Reader mode: play the lesson this page already had (with its follow-ups) from the start. */
  const replayLesson = useCallback(() => {
    const cur = ref.current;
    const saved = cur?.reader?.explained[cur.reader.page];
    if (!cur || !saved || cur.planning || cur.lesson || cur.scan !== "done") return;
    stopQuizTaps();
    const steps = replaySteps(saved);
    player.load(steps);
    patch(cur.id, () => ({
      perception: saved.perception,
      lesson: saved.lesson,
      sections: saved.sections,
      followups: saved.followups,
      streaming: false,
      planError: null,
      quiz: null,
    }));
    if (steps.length) void player.goTo(0);
  }, [patch, player]);

  /** Reader mode: teach this page again, around the focus question as it is now (the scan is reused). */
  const explainAgain = useCallback(() => {
    const cur = ref.current;
    if (!cur || cur.planning || cur.streaming || cur.scan !== "done") return;
    const perception = cur.perception ?? cur.reader?.explained[cur.reader.page]?.perception ?? null;
    if (!perception) return;
    stopQuizTaps();
    player.load([]);
    patch(cur.id, () => ({
      perception,
      lesson: null,
      sections: [],
      followups: [],
      quiz: null,
      asking: null,
      askError: null,
      planError: null,
    }));
    void plan(cur.id, perception.image_id, cleanQuestion(draft.current), abortRef.current?.signal);
  }, [patch, plan, player]);

  const getDraft = useCallback(() => draft.current, []);
  const setDraft = useCallback((q: string) => {
    draft.current = q;
  }, []);

  const ask = useCallback(
    async (question: string) => {
      const cur = ref.current;
      const q = question.trim();
      if (!cur?.perception || !q || cur.asking || cur.streaming) return;
      const id = cur.id;
      const selection = slot.current?.getStudentSelection() ?? null;
      patch(id, () => ({ asking: q, askError: null }));
      try {
        const res = await api.askFollowup(
          { image_id: cur.perception.image_id, lesson_id: cur.lesson?.lesson_id ?? null, question: q, selection },
          abortRef.current?.signal,
        );
        const now = ref.current;
        if (!now || now.id !== id) return;
        const n = now.sections.filter((s) => s.kind === "followup").length + 1;
        const steps = renumberSteps(res.steps, player.stepCount, `q${n}-`);
        if (!steps.length) {
          patch(id, () => ({ asking: null }));
          notify("The tutor had nothing to add for that question. Try asking it another way.");
          return;
        }
        const first = player.append(steps);
        patch(id, (s) => ({
          asking: null,
          followups: [...s.followups, res],
          sections: [...s.sections, { kind: "followup", title: q, start: first, count: steps.length }],
        }));
        slot.current?.clearStudentDrawings();
        void player.goTo(first);
      } catch (err) {
        if (isAbort(err)) return;
        patch(id, () => ({ asking: null, askError: errorMessage(err) }));
      }
    },
    [api, notify, patch, player, slot],
  );

  const clearAskError = useCallback(() => {
    const cur = ref.current;
    if (cur?.askError) patch(cur.id, () => ({ askError: null }));
  }, [patch]);

  // ---------------------------------------------------------------- quiz

  const quizItem = (s: Session): QuizItem | null => (s.quiz && s.lesson?.quiz[s.quiz.index]) || null;

  const onTap = useCallback(
    (p: Point) => {
      const cur = ref.current;
      const b = slot.current;
      const quiz = cur?.quiz;
      const item = cur && quizItem(cur);
      if (!cur || !b || !quiz || !item || quiz.phase !== "asking") return;
      if (insideBox(expandBox(item.answer_box, TAP_TOLERANCE), p)) {
        void b.drawCheck(item.answer_box, "green");
        patch(cur.id, () => ({
          quiz: { ...quiz, phase: "correct", results: [...quiz.results, quiz.tries === 0 ? "first" : "second"] },
        }));
        return;
      }
      void b.drawCross(p, "red");
      const tries = quiz.tries + 1;
      if (tries >= 2) {
        void b.drawCheck(item.answer_box, "orange");
        patch(cur.id, () => ({
          quiz: { ...quiz, tries, phase: "revealed", results: [...quiz.results, "missed"], wrongTaps: quiz.wrongTaps + 1 },
        }));
      } else {
        patch(cur.id, () => ({ quiz: { ...quiz, tries, wrongTaps: quiz.wrongTaps + 1 } }));
      }
    },
    [patch, slot],
  );

  /** Fresh board for a quiz question: lesson drawings hidden, earlier quiz marks gone. */
  const quizBoard = useCallback(() => {
    player.showAll("hide");
    slot.current?.setCurrentStep(player.stepCount + 1, "hide");
  }, [player, slot]);

  const startQuiz = useCallback(() => {
    const cur = ref.current;
    const b = slot.current;
    if (!cur?.lesson?.quiz.length || !b) return;
    player.stop();
    quizBoard();
    stopQuizTaps();
    tapOff.current = b.enableTapMode(onTap);
    patch(cur.id, () => ({ quiz: { index: 0, tries: 0, phase: "asking", results: [], wrongTaps: 0 } }));
  }, [onTap, patch, player, quizBoard, slot]);

  const nextQuestion = useCallback(() => {
    const cur = ref.current;
    const quiz = cur?.quiz;
    if (!cur?.lesson || !quiz) return;
    if (quiz.index + 1 >= cur.lesson.quiz.length) {
      stopQuizTaps();
      patch(cur.id, () => ({ quiz: { ...quiz, phase: "summary" } }));
      return;
    }
    quizBoard();
    patch(cur.id, () => ({ quiz: { ...quiz, index: quiz.index + 1, tries: 0, phase: "asking" } }));
  }, [patch, quizBoard]);

  const endQuiz = useCallback(() => {
    const cur = ref.current;
    if (!cur) return;
    stopQuizTaps();
    player.showAll("show");
    patch(cur.id, () => ({ quiz: null }));
  }, [patch, player]);

  // ---------------------------------------------------------------- tools

  const setDebug = useCallback(
    (on: boolean) => {
      debugRef.current = on;
      setDebugState(on);
      const cur = ref.current;
      const b = slot.current;
      if (!b || !cur?.perception || cur.scan === "found") return;
      b.showRegions(on ? cur.perception.regions : null);
      b.showBadges(on);
    },
    [slot],
  );

  const saveNotes = useCallback(async () => {
    const b = slot.current;
    if (!b) return;
    const page = ref.current?.reader?.page;
    const name = page ? `studylens-notes-page-${page}.png` : "studylens-notes.png";
    try {
      const blob = await b.exportPng();
      downloadBlob(blob, name);
      notify(`Saved your notes as ${name}`, "success");
    } catch (err) {
      notify(`Couldn't save the notes: ${errorMessage(err)}`, "error");
    }
  }, [notify, slot]);

  useEffect(
    () => () => {
      abortRef.current?.abort();
      tapOff.current?.();
    },
    [],
  );

  return {
    session,
    debug,
    onBoardReady,
    open,
    retryScan,
    openPage,
    turnPage,
    reset,
    teach,
    replayLesson,
    explainAgain,
    getDraft,
    setDraft,
    ask,
    clearAskError,
    startQuiz,
    nextQuestion,
    endQuiz,
    setDebug,
    saveNotes,
  };
}

export type StudySession = ReturnType<typeof useStudySession>;
