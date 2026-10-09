// Hand-built perception + lesson for samples/quick/network_basic.png (1280x720), used by ?mock=1.
// Geometry is written in pixels of that image and normalized here, exactly like the backend does.
import type {
  Annotation,
  AnnotationKind,
  Box,
  Color,
  FollowupResponse,
  Grounding,
  Lesson,
  Perception,
  Point,
  Region,
  RegionKind,
  Step,
} from "../types";

export const MOCK_W = 1280;
export const MOCK_H = 720;
export const MOCK_IMAGE_URL = "/mock/network_basic.png";
export const MOCK_SAMPLE_NAME = "quick/network_basic.png";

type Px = [number, number, number, number];

export function pxBox([x0, y0, x1, y1]: Px): Box {
  return { x: x0 / MOCK_W, y: y0 / MOCK_H, w: (x1 - x0) / MOCK_W, h: (y1 - y0) / MOCK_H };
}

function pt(x: number, y: number): Point {
  return { x: x / MOCK_W, y: y / MOCK_H };
}

function region(
  id: string,
  kind: RegionKind,
  px: Px,
  text: string | null,
  parent: string | null = null,
  score = 0.97,
): Region {
  return {
    id,
    kind,
    box: pxBox(px),
    text,
    score,
    source: kind === "shape" ? "merged" : "ocr",
    parent_id: parent,
  };
}

// Shape and line boxes come from network_basic.json; label boxes are the measured ink of the words.
const SHAPES: Record<string, Px> = {
  laptop: [80, 300, 280, 400],
  switch: [380, 300, 580, 400],
  router: [680, 300, 880, 400],
  internet: [980, 280, 1220, 420],
};

export const MOCK_PERCEPTION: Perception = {
  image_id: "mock-network-basic",
  width: MOCK_W,
  height: MOCK_H,
  regions: [
    region("R1", "text", [61, 42, 625, 75], "How Packets Travel Across Networks", null, 0.99),
    region("R2", "shape", SHAPES.laptop, "Laptop", null, 0.95),
    region("R3", "text", [112, 340, 186, 364], "Laptop", "R2", 0.99),
    region("R4", "shape", SHAPES.switch, "Switch", null, 0.95),
    region("R5", "text", [411, 340, 485, 359], "Switch", "R4", 0.99),
    region("R6", "shape", SHAPES.router, "Router", null, 0.95),
    region("R7", "text", [712, 340, 787, 359], "Router", "R6", 0.98),
    region("R8", "shape", SHAPES.internet, "Internet", null, 0.93),
    region("R9", "text", [1012, 320, 1096, 339], "Internet", "R8", 0.99),
    region("R10", "text", [80, 521, 685, 550], "A router forwards packets between different networks", null, 0.96),
  ],
  timings: { prepare: 0.03, ocr: 1.18, shapes: 0.07, regions: 0.02, freespace: 0.04, som: 0.05, total: 1.39 },
  image_url: MOCK_IMAGE_URL,
  marked_url: null,
};

interface AnnSpec {
  kind: AnnotationKind;
  color: Color;
  cue: string;
  target?: string[];
  from?: string[];
  to?: string[];
  span?: string;
  text?: string;
  box?: Px;
  points?: [number, number][];
  labelBox?: Px;
  leader?: [[number, number], [number, number]];
  grounding?: Grounding;
  confidence?: number;
}

function ann(id: string, s: AnnSpec): Annotation {
  return {
    id,
    kind: s.kind,
    color: s.color,
    target_ids: s.target ?? [],
    from_ids: s.from ?? [],
    to_ids: s.to ?? [],
    span: s.span ?? null,
    text: s.text ?? null,
    cue: s.cue,
    geometry: {
      box: s.box ? pxBox(s.box) : null,
      points: s.points ? s.points.map(([x, y]) => pt(x, y)) : null,
      label_box: s.labelBox ? pxBox(s.labelBox) : null,
      leader: s.leader ? s.leader.map(([x, y]) => pt(x, y)) : null,
    },
    confidence: s.confidence ?? 0.93,
    grounding: s.grounding ?? "consensus",
  };
}

function step(index: number, title: string, narration: string, specs: AnnSpec[], sketch: string | null = null): Step {
  return {
    index,
    title,
    narration,
    annotations: specs.map((s, i) => ann(`s${index}a${i + 1}`, s)),
    sketch,
  };
}

/** The recap's margin sketch: the packet's route as a little flowchart beside the slide. */
const ROUTE_SKETCH = [
  "flowchart LR",
  "A[Laptop sends packet] --> B[Switch: same network]",
  "B --> C[Router: next network]",
  "C --> D[Internet]",
  "D -.->|every hop| C",
].join("\n");

/** Ellipse bounds around a rectangle: a hand-drawn circle needs room around the corners. */
function circleAround([x0, y0, x1, y1]: Px, sx = 1.28, sy = 1.42): Px {
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  const w = (x1 - x0) * sx;
  const h = (y1 - y0) * sy;
  return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2];
}

function pad([x0, y0, x1, y1]: Px, p: number): Px {
  return [x0 - p, y0 - p, x1 + p, y1 + p];
}

export const MOCK_LESSON: Lesson = {
  lesson_id: "mock-lesson-1",
  image_id: MOCK_PERCEPTION.image_id,
  title: "How a packet gets from your laptop to the Internet",
  summary:
    "Data travels in small packets: the switch moves them around inside your local network, and the router forwards them between networks, out to the Internet.",
  steps: [
    step(
      1,
      "The big question",
      "This slide asks how packets travel across networks. A packet is just a small chunk of data, and we are going to follow one from your laptop all the way to the Internet.",
      [
        {
          kind: "underline",
          color: "blue",
          cue: "how packets travel across networks",
          target: ["R1"],
          points: [
            [60, 82],
            [629, 82],
          ],
          confidence: 0.95,
        },
        {
          kind: "highlight",
          color: "orange",
          cue: "a packet is just a small chunk of data",
          target: ["R1"],
          span: "Packets",
          box: [136, 41, 263, 77],
          grounding: "id_only",
          confidence: 0.81,
        },
      ],
    ),
    step(
      2,
      "Start at the laptop",
      "Our packet starts at the laptop, the device where you click send. The laptop hands the packet to the switch sitting right next to it.",
      [
        {
          kind: "circle",
          color: "red",
          cue: "starts at the laptop",
          target: ["R2"],
          box: circleAround(SHAPES.laptop),
          confidence: 0.96,
        },
        {
          kind: "arrow",
          color: "orange",
          cue: "hands the packet to the switch",
          from: ["R2"],
          to: ["R4"],
          text: "packet",
          points: [
            [250, 278],
            [335, 200],
            [420, 290],
          ],
          labelBox: [300, 196, 370, 224],
          confidence: 0.92,
        },
      ],
    ),
    step(
      3,
      "The switch keeps it local",
      "The switch connects devices inside the same local network. It reads where the packet is going and passes it along to the router.",
      [
        {
          kind: "box",
          color: "blue",
          cue: "The switch connects devices",
          target: ["R4"],
          box: pad(SHAPES.switch, 10),
          grounding: "cv_snap",
          confidence: 0.84,
        },
        {
          kind: "label",
          color: "blue",
          cue: "inside the same local network",
          target: ["R4"],
          text: "same local network",
          box: SHAPES.switch,
          labelBox: [380, 448, 580, 478],
          leader: [
            [480, 444],
            [480, 414],
          ],
          confidence: 0.9,
        },
      ],
    ),
    step(
      4,
      "The router links networks",
      "Here is the key idea: the router forwards packets between different networks. It is the doorway from your home network out to the Internet.",
      [
        {
          kind: "circle",
          color: "red",
          cue: "the router forwards packets",
          target: ["R6"],
          box: circleAround(SHAPES.router),
          confidence: 0.97,
        },
        {
          kind: "underline",
          color: "green",
          cue: "between different networks",
          target: ["R10"],
          span: "forwards packets between different networks",
          points: [
            [176, 557],
            [686, 557],
          ],
          grounding: "id_only",
          confidence: 0.78,
        },
        {
          kind: "arrow",
          color: "green",
          cue: "out to the Internet",
          from: ["R6"],
          to: ["R8"],
          points: [
            [858, 280],
            [940, 196],
            [1022, 270],
          ],
          confidence: 0.9,
        },
      ],
    ),
    step(
      5,
      "Out to the Internet",
      "Finally, the packet reaches the Internet, which is really a huge web of networks joined by routers. Every hop repeats the same trick until your data arrives.",
      [
        {
          kind: "highlight",
          color: "orange",
          cue: "reaches the Internet",
          target: ["R9"],
          box: [1005, 315, 1103, 345],
          confidence: 0.93,
        },
        {
          kind: "label",
          color: "blue",
          cue: "a huge web of networks",
          target: ["R8"],
          text: "a web of networks",
          box: SHAPES.internet,
          labelBox: [1004, 458, 1196, 488],
          leader: [
            [1100, 454],
            [1100, 424],
          ],
          grounding: "llm_refined",
          confidence: 0.71,
        },
      ],
      ROUTE_SKETCH,
    ),
  ],
  quiz: [
    {
      question: "Tap the device that forwards packets between different networks.",
      answer_ids: ["R6"],
      answer_box: pxBox(SHAPES.router),
      explanation:
        "The router sits between your local network and the Internet and forwards packets from one network to the next.",
    },
    {
      question: "Tap the device that connects machines inside the same local network.",
      answer_ids: ["R4"],
      answer_box: pxBox(SHAPES.switch),
      explanation:
        "The switch delivers packets between devices on the same local network and hands everything else to the router.",
    },
  ],
  model: "gpt-5.4-mini",
  timings: { llm: 2.36, grounding: 0.012, geometry: 0.004, validate: 0.002, total: 2.38 },
  warnings: [],
};

/** A purple follow-up answer; circles the student's selection when there is one. */
export function mockFollowup(question: string, selection: Box | null): FollowupResponse {
  const narration =
    "A switch only knows the devices plugged into your own network. To leave that network, a packet has to go through the router, which knows the way to other networks.";
  const first: Annotation = selection
    ? {
        id: "f1a1",
        kind: "circle",
        color: "purple",
        target_ids: [],
        from_ids: [],
        to_ids: [],
        span: null,
        text: null,
        cue: "A switch only knows",
        geometry: {
          box: {
            x: selection.x - selection.w * 0.12,
            y: selection.y - selection.h * 0.18,
            w: selection.w * 1.24,
            h: selection.h * 1.36,
          },
          points: null,
          label_box: null,
          leader: null,
        },
        confidence: 1,
        grounding: "user",
      }
    : ann("f1a1", {
        kind: "circle",
        color: "purple",
        cue: "A switch only knows",
        target: ["R4"],
        box: circleAround(SHAPES.switch),
        confidence: 0.95,
      });
  return {
    title: question.length > 48 ? `${question.slice(0, 45).trimEnd()}...` : question,
    steps: [
      {
        index: 1,
        title: "Switches stay local",
        narration,
        annotations: [
          first,
          ann("f1a2", {
            kind: "arrow",
            color: "purple",
            cue: "has to go through the router",
            from: ["R4"],
            to: ["R6"],
            text: "the way out",
            points: [
              [548, 282],
              [630, 206],
              [712, 281],
            ],
            labelBox: [572, 190, 688, 218],
            confidence: 0.91,
          }),
        ],
      },
    ],
    model: "gpt-5.4-mini",
    timings: { llm: 1.64, grounding: 0.008, total: 1.66 },
    warnings: [],
  };
}
