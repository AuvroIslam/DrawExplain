// A 3-page demo PDF for reader mode (?mock=1). Page 2 is the network slide with its full lesson; pages 1
// and 3 are small slides (public/mock/doc/page-N.png, 1280x720) with short lessons of their own.
// Pixel boxes were measured on the rendered pages.
import type { DocumentInfo, Lesson, Perception } from "../types";
import { circleAround, MOCK_LESSON, MOCK_PERCEPTION, pad, type Px, pxBox, region, step } from "./networkBasic";

export const MOCK_DOC_ID = "mock-doc";
const PAGES = 3;
const pageImageId = (page: number) => `${MOCK_DOC_ID}-p${page}`;

/** Page number of a mock document image id ("mock-doc-p2" -> 2), else null. */
export function mockDocPage(imageId: string): number | null {
  const m = /^mock-doc-p(\d+)$/.exec(imageId);
  return m ? Number(m[1]) : null;
}

/** Template like the server's; absolute, so apiUrl() keeps it on this origin when the API lives elsewhere. */
function pageUrlTemplate(): string {
  return `${window.location.origin}/mock/doc/page-{page}.png`;
}

export function mockDocument(filename: string): DocumentInfo {
  return {
    doc_id: MOCK_DOC_ID,
    filename: filename || "networks-lecture-3.pdf",
    pages: PAGES,
    title: "Networks and Packets",
    page_sizes: Array.from({ length: PAGES }, () => [1280, 720] as [number, number]),
    page_url: pageUrlTemplate(),
  };
}

// ---------------------------------------------------------------- page 1: title slide

const P1 = {
  kicker: [80, 122, 441, 148],
  title: [78, 205, 794, 277],
  sub: [80, 312, 745, 346],
  today: [80, 472, 262, 498],
  packets: [80, 520, 300, 590],
  packetsT: [109, 545, 202, 571],
  switches: [360, 520, 580, 590],
  switchesT: [389, 545, 493, 571],
  routers: [640, 520, 860, 590],
  routersT: [669, 545, 760, 571],
} satisfies Record<string, Px>;

const PAGE1_REGIONS = [
  region("R1", "text", P1.kicker, "Computer Networks · Lecture 3", null, 0.98),
  region("R2", "text", P1.title, "Networks and Packets", null, 0.99),
  region("R3", "text", P1.sub, "What really happens when you press Send?", null, 0.98),
  region("R4", "text", P1.today, "Today we meet:", null, 0.97),
  region("R5", "shape", P1.packets, "Packets", null, 0.95),
  region("R6", "text", P1.packetsT, "Packets", "R5", 0.99),
  region("R7", "shape", P1.switches, "Switches", null, 0.95),
  region("R8", "text", P1.switchesT, "Switches", "R7", 0.99),
  region("R9", "shape", P1.routers, "Routers", null, 0.95),
  region("R10", "text", P1.routersT, "Routers", "R9", 0.99),
];

const PAGE1_LESSON: Lesson = {
  lesson_id: "mock-doc-lesson-p1",
  image_id: pageImageId(1),
  title: "What this lecture is about",
  summary: "The lecture follows one packet from the moment you press Send, meeting the three things that move it along.",
  steps: [
    step(
      1,
      "The question for today",
      "This first slide sets up the whole lecture: networks and packets. The real question is what happens when you press Send.",
      [
        { kind: "underline", color: "blue", cue: "networks and packets", target: ["R2"], points: [[78, 288], [796, 288]], confidence: 0.96 },
        { kind: "box", color: "red", cue: "what happens when you press Send", target: ["R3"], box: pad(P1.sub, 12), confidence: 0.94 },
      ],
    ),
    step(
      2,
      "Three things to meet",
      "Along the way we meet three things today: packets, switches and routers. Keep an eye on the router, it is the star of the next page.",
      [
        { kind: "box", color: "blue", cue: "three things today", target: ["R5", "R7", "R9"], box: [66, 506, 874, 604], confidence: 0.92 },
        { kind: "circle", color: "red", cue: "Keep an eye on the router", target: ["R9"], box: circleAround(P1.routers, 1.18, 1.5), confidence: 0.95 },
        {
          kind: "label",
          color: "red",
          cue: "the star of the next page",
          target: ["R9"],
          text: "star of page 2!",
          box: P1.routers,
          labelBox: [912, 538, 1132, 572],
          leader: [[906, 555], [868, 555]],
          confidence: 0.9,
        },
      ],
    ),
  ],
  quiz: [
    {
      question: "Tap the device the lecture says to keep an eye on.",
      answer_ids: ["R9"],
      answer_box: pxBox(P1.routers),
      explanation: "The router: it forwards packets between networks, which is what the next page shows.",
    },
  ],
  model: "gpt-5.4-mini",
  timings: { llm: 1.84, grounding: 0.01, total: 1.86 },
  warnings: [],
};

// ---------------------------------------------------------------- page 3: recap table

const P3 = {
  title: [60, 44, 407, 76],
  table: [80, 150, 1142, 468],
  hDevice: [106, 170, 190, 196],
  hJob: [346, 170, 423, 196],
  switch: [106, 244, 183, 270],
  switchJob: [346, 244, 804, 270],
  router: [106, 328, 184, 354],
  routerJob: [346, 328, 869, 354],
  internet: [106, 412, 194, 438],
  internetJob: [346, 412, 823, 438],
  note: [80, 562, 884, 588],
} satisfies Record<string, Px>;

const PAGE3_REGIONS = [
  region("R1", "text", P3.title, "What Each Device Does", null, 0.99),
  region("R2", "shape", P3.table, null, null, 0.93),
  region("R3", "text", P3.hDevice, "Device", "R2", 0.99),
  region("R4", "text", P3.hJob, "Its job", "R2", 0.98),
  region("R5", "text", P3.switch, "Switch", "R2", 0.99),
  region("R6", "text", P3.switchJob, "Moves packets inside one local network", "R2", 0.97),
  region("R7", "text", P3.router, "Router", "R2", 0.99),
  region("R8", "text", P3.routerJob, "Forwards packets between different networks", "R2", 0.97),
  region("R9", "text", P3.internet, "Internet", "R2", 0.99),
  region("R10", "text", P3.internetJob, "Many networks joined together by routers", "R2", 0.97),
  region("R11", "text", P3.note, "Every hop repeats the same trick: read the address, pick the next link.", null, 0.96),
];

const HOP_SKETCH = ["flowchart LR", "A[Read the address] --> B[Pick the next link]", "B --> C[Next hop]", "C -.->|repeat| A"].join("\n");

const PAGE3_LESSON: Lesson = {
  lesson_id: "mock-doc-lesson-p3",
  image_id: pageImageId(3),
  title: "One job per device",
  summary: "The switch keeps packets inside one network, the router moves them between networks, and the Internet is many networks joined by routers.",
  steps: [
    step(
      1,
      "Same devices, new view",
      "On the last page we followed one packet from the laptop to the Internet. This table names the job of each device we met on the way.",
      [
        { kind: "underline", color: "blue", cue: "This table names", target: ["R1"], points: [[60, 86], [410, 86]], confidence: 0.96 },
        { kind: "box", color: "orange", cue: "each device we met", target: ["R4"], box: pad(P3.hJob, 10), confidence: 0.9 },
      ],
    ),
    step(
      2,
      "Switch versus router",
      "The switch keeps packets inside one local network, while the router forwards them between different networks. That difference is the whole point of the last slide.",
      [
        { kind: "circle", color: "blue", cue: "The switch keeps packets", target: ["R5"], box: circleAround(P3.switch, 1.5, 1.9), confidence: 0.95 },
        { kind: "underline", color: "blue", cue: "inside one local network", target: ["R6"], points: [[346, 278], [806, 278]], confidence: 0.93 },
        { kind: "circle", color: "red", cue: "the router forwards them", target: ["R7"], box: circleAround(P3.router, 1.5, 1.9), confidence: 0.95 },
        { kind: "underline", color: "red", cue: "between different networks", target: ["R8"], points: [[346, 362], [871, 362]], confidence: 0.93 },
      ],
    ),
    step(
      3,
      "Hop by hop",
      "The Internet is just many networks joined by routers. Every hop repeats the same trick: read the address, then pick the next link.",
      [
        { kind: "highlight", color: "orange", cue: "many networks joined by routers", target: ["R10"], box: [340, 406, 829, 444], confidence: 0.92 },
        { kind: "underline", color: "green", cue: "read the address", target: ["R11"], points: [[80, 596], [886, 596]], confidence: 0.9 },
      ],
      HOP_SKETCH,
    ),
  ],
  quiz: [
    {
      question: "Tap the job that belongs to the router.",
      answer_ids: ["R8"],
      answer_box: pxBox([336, 318, 879, 364]),
      explanation: "Routers forward packets between different networks; switches only move them inside one network.",
    },
  ],
  model: "gpt-5.4-mini",
  timings: { llm: 2.02, grounding: 0.01, total: 2.04 },
  warnings: [],
};

// ---------------------------------------------------------------- lookups

export function mockPagePerception(page: number): Perception {
  const base: Perception =
    page === 2
      ? structuredClone(MOCK_PERCEPTION)
      : {
          image_id: "",
          width: 1280,
          height: 720,
          regions: structuredClone(page === 1 ? PAGE1_REGIONS : PAGE3_REGIONS),
          timings: { prepare: 0.02, ocr: 0.96, shapes: 0.05, regions: 0.02, freespace: 0.03, total: 1.08 },
          image_url: null,
          marked_url: null,
        };
  return {
    ...base,
    image_id: pageImageId(page),
    image_url: pageUrlTemplate().replace("{page}", String(page)),
    doc_id: MOCK_DOC_ID,
    page,
  };
}

/** The canned lesson for an image id: a mock document page's own lesson, else the network slide's. */
export function mockLessonFor(imageId: string): Lesson {
  const page = mockDocPage(imageId);
  const lesson = page === 1 ? PAGE1_LESSON : page === 3 ? PAGE3_LESSON : MOCK_LESSON;
  return { ...structuredClone(lesson), image_id: imageId };
}

/** Earlier pages a mock document lesson "builds on" (like the server: the pages before, at most three). */
export function mockContextPages(imageId: string): number[] {
  const page = mockDocPage(imageId);
  if (!page) return [];
  const out: number[] = [];
  for (let p = Math.max(1, page - 3); p < page; p++) out.push(p);
  return out;
}
