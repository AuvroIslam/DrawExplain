// The page flow: open an image -> scan (perception) -> plan a lesson -> play it -> follow-ups -> quiz.
import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage, isAbort, isPdfFile, type StudyLensApi } from "../api";
import type { BoardHandle } from "../board/types";
import type { BoardSlot } from "../player/boardSlot";
import { type LessonPlayer, renumberSteps } from "../player/lessonPlayer";
import type { Box, FollowupResponse, Lesson, Perception, Point, QuizItem, Step } from "../types";

/** A file upload; for a PDF, `page` is the 1-based page shown and `pages` the page count once known. */
export type PageSource =
  | { kind: "file"; file: File; name: string; page?: number; pages?: number }
  | { kind: "sample"; name: string; url: string };

/** scanning: perception in flight; found: regions flash on the board; done: ready to teach. */
export type ScanState = "scanning" | "found" | "done" | "error";

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

export interface Session {
  id: number;
  source: PageSource;
  /** Local preview while the server works ("" for a PDF: only the server can render its pages). */
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
}

export const MAX_SIDE = 1600;
const MIN_SCAN_MS = 1900;
const FOUND_MS = 1500;
const TAP_TOLERANCE = 0.03;

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

  const commit = useCallback((next: Session | null) => {
    ref.current = next;
    setSession(next);
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
      const pdf = source.kind === "file" && isPdfFile(source.file);
      const previewUrl = source.kind === "sample" ? source.url : pdf ? "" : URL.createObjectURL(source.file);
      if (source.kind === "file" && previewUrl) oldUrls.current.push(previewUrl);
      commit({
        id,
        source,
        previewUrl,
        perception: null,
        scan: "scanning",
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
      });
      const alive = () => counter.current === id && !ctrl.signal.aborted;
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
    [api, commit, patch, player, slot],
  );

  const retryScan = useCallback(() => {
    const cur = ref.current;
    if (cur) void open(cur.source);
  }, [open]);

  /** PDF uploads: perceive another page of the same file (a fresh page, so a fresh lesson). */
  const openPage = useCallback(
    (page: number) => {
      const cur = ref.current;
      if (!cur || cur.source.kind !== "file") return;
      const pages = cur.perception?.source_pages ?? cur.source.pages ?? 0;
      const p = Math.round(page);
      if (!Number.isFinite(p) || p < 1 || p > pages || p === (cur.source.page ?? 1)) return;
      void open({ ...cur.source, page: p, pages });
    },
    [open],
  );

  /** Back to the landing page. */
  const reset = useCallback(() => {
    counter.current++;
    abortRef.current?.abort();
    stopQuizTaps();
    player.load([]);
    slot.reset();
    releaseUrls();
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

  /** Plan the lesson over the streaming endpoint: step 1 starts playing as soon as it lands and later
   *  steps append while it plays. Falls back to POST /api/lessons when the stream fails before any step. */
  const teach = useCallback(async () => {
    const cur = ref.current;
    if (!cur?.perception || cur.planning || cur.lesson) return;
    const id = cur.id;
    const imageId = cur.perception.image_id;
    const signal = abortRef.current?.signal;
    const live = () => ref.current?.id === id && !signal?.aborted;
    patch(id, () => ({ planning: true, planStartedAt: Date.now(), planError: null }));

    let meta = { lesson_id: "", model: "" };
    let header = { title: "", summary: "" };
    let received = 0;
    const onStep = (raw: Step) => {
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

    try {
      const lesson = await api.streamLesson(
        imageId,
        {
          onMeta: (m) => (meta = { lesson_id: m.lesson_id, model: m.model }),
          onHeader: (h) => (header = h),
          onStep,
        },
        null,
        signal,
      );
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
        const lesson = await api.createLesson(imageId, null, signal);
        if (live()) startLesson(id, lesson);
      } catch (err2) {
        if (isAbort(err2) || !live()) return;
        patch(id, () => ({ planning: false, planError: errorMessage(err2) }));
      }
    }
  }, [api, notify, patch, player, startLesson]);

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
    try {
      const blob = await b.exportPng();
      downloadBlob(blob, "studylens-notes.png");
      notify("Saved your notes as studylens-notes.png", "success");
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
    reset,
    teach,
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
