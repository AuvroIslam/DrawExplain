// Backend-free API for ?mock=1: same shape as the real client, canned data, realistic delays.
import { ApiError, cleanQuestion, type StudyLensApi } from "../api";
import type { Lesson, Perception } from "../types";
import { MOCK_DOC_ID, mockContextPages, mockDocument, mockLessonFor, mockPagePerception } from "./mockDocument";
import { MOCK_IMAGE_URL, MOCK_PERCEPTION, MOCK_SAMPLE_NAME, mockFollowup } from "./networkBasic";

function delay<T>(ms: number, value: () => T, signal?: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(() => {
      try {
        resolve(value());
      } catch (err) {
        reject(err);
      }
    }, ms);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

function speed(): number {
  const raw = Number(new URLSearchParams(window.location.search).get("speed") ?? "1");
  return Number.isFinite(raw) && raw > 0 ? raw : 1;
}

const perception = (): Perception => structuredClone(MOCK_PERCEPTION);

let lessonCount = 0;

/** The canned lesson for this image, carrying the student's question and the pages it builds on. */
function lessonFor(imageId: string, question?: string | null): Lesson {
  return {
    ...mockLessonFor(imageId),
    lesson_id: `mock-lesson-${++lessonCount}`,
    question: cleanQuestion(question),
    context_pages: mockContextPages(imageId),
  };
}

export const mockApi: StudyLensApi = {
  mock: true,
  health: () => delay(60, () => ({ ok: true, model: "gpt-5.4-mini (demo data)", tts: false })),
  // The demo only knows one page, so any upload is "perceived" as the network slide.
  uploadImage: (_file, signal) => delay(2600 / speed(), perception, signal),
  listSamples: () => delay(80, () => [{ name: MOCK_SAMPLE_NAME, url: MOCK_IMAGE_URL }]),
  loadSample: (name, signal) =>
    delay(
      2600 / speed(),
      () => {
        if (name !== MOCK_SAMPLE_NAME) throw new ApiError(`Unknown sample: ${name}`, 404);
        return perception();
      },
      signal,
    ),
  // A 3-page demo document whatever PDF is chosen; nothing is scanned until a page is explained.
  uploadDocument: (file, signal) => delay(900 / speed(), () => mockDocument(file.name), signal),
  perceivePage: (docId, page, signal) =>
    delay(
      2600 / speed(),
      () => {
        if (docId !== MOCK_DOC_ID) throw new ApiError("The server doesn't know this document any more.", 404);
        if (!Number.isInteger(page) || page < 1 || page > 3) throw new ApiError(`There is no page ${page}.`, 400);
        return mockPagePerception(page);
      },
      signal,
    ),
  createLesson: (imageId, _model, signal, question) => delay(3200 / speed(), () => lessonFor(imageId, question), signal),
  // Like the real stream: header first, step 1 after a few seconds, later steps every couple of seconds.
  streamLesson: async (imageId, handlers, _model, signal, question) => {
    const lesson = lessonFor(imageId, question);
    const k = speed();
    await delay(1200 / k, () => undefined, signal);
    handlers.onMeta?.({ lesson_id: lesson.lesson_id, image_id: lesson.image_id, model: lesson.model });
    handlers.onHeader?.({ title: lesson.title, summary: lesson.summary });
    for (const [i, step] of lesson.steps.entries()) {
      await delay((i === 0 ? 1800 : 2400) / k, () => undefined, signal);
      handlers.onStep?.(structuredClone(step));
    }
    return delay(900 / k, () => lesson, signal);
  },
  askFollowup: (req, signal) =>
    delay(1800 / speed(), () => mockFollowup(req.question, req.selection ?? null), signal),
  tts: () => Promise.reject(new ApiError("The tutor voice is not available in demo mode.", 503)),
};
