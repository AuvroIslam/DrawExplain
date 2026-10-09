// Stand-in whiteboard (?board=stub, or while src/board/WhiteboardBoard.tsx does not exist):
// the image plus plain SVG shapes, implementing the full BoardHandle contract.
import { type PointerEvent, type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import type { BoardHandle, PreviousSteps, WhiteboardBoardProps } from "../board/types";
import { type Annotation, type Box, type Color, PALETTE, type Point, type Region } from "../types";

interface Drawn {
  key: string;
  annotation: Annotation;
  step: number;
  animate: boolean;
}

interface Mark {
  key: string;
  kind: "check" | "cross";
  box?: Box;
  at?: Point;
  color: Color;
}

interface Img {
  url: string;
  w: number;
  h: number;
}

const sleep = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));

function waitOrAbort(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal?.aborted) return resolve();
    const t = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(t);
        resolve();
      },
      { once: true },
    );
  });
}

function Shape({ d, img, opacity, badge }: { d: Drawn; img: Img; opacity: number; badge: boolean }) {
  const a = d.annotation;
  const g = a.geometry;
  const color = PALETTE[a.color] ?? PALETTE.red;
  const X = (v: number) => v * img.w;
  const Y = (v: number) => v * img.h;
  const sw = Math.max(3, img.w / 320);
  const cls = d.animate ? "stub-draw" : undefined;
  const parts: ReactNode[] = [];
  const box = g.box;
  if ((a.kind === "circle" || a.kind === "box" || a.kind === "highlight") && box) {
    if (a.kind === "circle") {
      parts.push(
        <ellipse key="e" className={cls} pathLength={1} cx={X(box.x + box.w / 2)} cy={Y(box.y + box.h / 2)}
          rx={X(box.w) / 2} ry={Y(box.h) / 2} fill="none" stroke={color} strokeWidth={sw} />,
      );
    } else if (a.kind === "box") {
      parts.push(
        <rect key="r" className={cls} pathLength={1} x={X(box.x)} y={Y(box.y)} width={X(box.w)} height={Y(box.h)}
          rx={sw * 2} fill="none" stroke={color} strokeWidth={sw} />,
      );
    } else {
      parts.push(
        <rect key="h" x={X(box.x)} y={Y(box.y)} width={X(box.w)} height={Y(box.h)} fill={color} opacity={0.28} />,
      );
    }
  }
  const pts = g.points;
  if (a.kind === "underline" && pts && pts.length >= 2) {
    parts.push(
      <line key="u" className={cls} pathLength={1} x1={X(pts[0].x)} y1={Y(pts[0].y)} x2={X(pts[1].x)} y2={Y(pts[1].y)}
        stroke={color} strokeWidth={sw} strokeLinecap="round" />,
    );
  }
  if (a.kind === "arrow" && pts && pts.length >= 2) {
    const [s, c, e] = pts.length >= 3 ? pts : [pts[0], pts[0], pts[1]];
    const ang = Math.atan2(Y(e.y) - Y(c.y), X(e.x) - X(c.x));
    const head = sw * 5;
    const hx = (t: number) => X(e.x) - head * Math.cos(ang + t);
    const hy = (t: number) => Y(e.y) - head * Math.sin(ang + t);
    parts.push(
      <path key="a" className={cls} pathLength={1} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round"
        d={`M${X(s.x)},${Y(s.y)} Q${X(c.x)},${Y(c.y)} ${X(e.x)},${Y(e.y)}`} />,
      <path key="ah" fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"
        d={`M${hx(0.45)},${hy(0.45)} L${X(e.x)},${Y(e.y)} L${hx(-0.45)},${hy(-0.45)}`} />,
    );
  }
  if (a.kind === "label" && g.leader && g.leader.length >= 2) {
    const [f, t] = g.leader;
    parts.push(
      <line key="l" x1={X(f.x)} y1={Y(f.y)} x2={X(t.x)} y2={Y(t.y)} stroke={color} strokeWidth={sw * 0.8}
        strokeLinecap="round" />,
    );
  }
  if (a.text && g.label_box) {
    const lb = g.label_box;
    parts.push(
      <text key="t" x={X(lb.x + lb.w / 2)} y={Y(lb.y + lb.h / 2)} fill={color} fontSize={Y(lb.h) * 0.72}
        textAnchor="middle" dominantBaseline="central" className="stub-hand">
        {a.text}
      </text>,
    );
  }
  const anchor = box ?? g.label_box ?? (pts ? { x: pts[0].x, y: pts[0].y, w: 0, h: 0 } : null);
  if (badge && anchor) {
    parts.push(
      <text key="b" x={X(anchor.x)} y={Y(anchor.y) - 8} fontSize={Math.max(14, img.h / 48)} fill="#1d1b26"
        className="stub-badge">
        {a.grounding} {Math.round(a.confidence * 100)}%
      </text>,
    );
  }
  return <g opacity={opacity}>{parts}</g>;
}

export default function BoardStub({ onReady, className }: WhiteboardBoardProps) {
  const [img, setImg] = useState<Img | null>(null);
  const [drawn, setDrawn] = useState<Drawn[]>([]);
  const [current, setCurrent] = useState<{ step: number; previous: PreviousSteps }>({ step: 0, previous: "show" });
  const [regions, setRegions] = useState<Region[] | null>(null);
  const [badges, setBadges] = useState(false);
  const [marks, setMarks] = useState<Mark[]>([]);
  const [tapping, setTapping] = useState(false);
  const tap = useRef<((p: Point) => void) | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const imgRef = useRef<Img | null>(null);
  const seq = useRef(0);

  const handle = useMemo<BoardHandle>(() => {
    const key = (id: string) => `${id}-${++seq.current}`;
    return {
      loadImage: (url, w, h) =>
        new Promise<void>((resolve) => {
          const probe = new Image();
          probe.onload = probe.onerror = () => {
            imgRef.current = { url, w, h };
            setImg(imgRef.current);
            setDrawn([]);
            setMarks([]);
            resolve();
          };
          probe.src = url;
        }),
      drawAnnotation: (annotation, { stepIndex, durationMs, signal }) => {
        setDrawn((d) => [...d, { key: key(annotation.id), annotation, step: stepIndex, animate: true }]);
        return waitOrAbort(durationMs ?? 700, signal);
      },
      drawInstant: (annotations, stepIndex) =>
        setDrawn((d) => [
          ...d,
          ...annotations.map((annotation) => ({ key: key(annotation.id), annotation, step: stepIndex, animate: false })),
        ]),
      clearTutorDrawings: (fromStep) => {
        setDrawn((d) => (fromStep === undefined ? [] : d.filter((x) => x.step < fromStep)));
        if (fromStep === undefined) setMarks([]);
      },
      setCurrentStep: (step, previous) => setCurrent({ step, previous }),
      showRegions: (r) => setRegions(r),
      showBadges: (on) => setBadges(on),
      getStudentSelection: () => null,
      clearStudentDrawings: () => {},
      enableTapMode: (onTap) => {
        tap.current = onTap;
        setTapping(true);
        return () => {
          if (tap.current === onTap) {
            tap.current = null;
            setTapping(false);
          }
        };
      },
      drawCheck: (box, color = "green") => {
        setMarks((m) => [...m, { key: key("check"), kind: "check", box, color }]);
        return sleep(450);
      },
      drawCross: (at, color = "red") => {
        setMarks((m) => [...m, { key: key("cross"), kind: "cross", at, color }]);
        return sleep(300);
      },
      exportPng: async () => {
        const cur = imgRef.current;
        const canvas = document.createElement("canvas");
        canvas.width = cur?.w ?? 1;
        canvas.height = cur?.h ?? 1;
        const ctx = canvas.getContext("2d");
        if (cur && ctx) {
          const el = new Image();
          el.src = cur.url;
          await el.decode().catch(() => undefined);
          ctx.fillStyle = "#fff";
          ctx.fillRect(0, 0, cur.w, cur.h);
          ctx.drawImage(el, 0, 0, cur.w, cur.h);
        }
        return new Promise<Blob>((resolve) => canvas.toBlob((b) => resolve(b ?? new Blob()), "image/png"));
      },
      fitToImage: () => {},
    };
  }, []);

  useEffect(() => {
    onReady(handle);
  }, [handle, onReady]);

  const onPointerDown = (e: PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    const cur = imgRef.current;
    const ctm = svg?.getScreenCTM();
    if (!tap.current || !svg || !cur || !ctm) return;
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
    tap.current({ x: p.x / cur.w, y: p.y / cur.h });
  };

  const opacityFor = (step: number) => {
    if (step >= current.step) return 1;
    return current.previous === "dim" ? 0.35 : current.previous === "hide" ? 0 : 1;
  };

  return (
    <div className={`board-stub ${className ?? ""}`} data-board="stub">
      {img && (
        <svg
          ref={svgRef}
          viewBox={`0 0 ${img.w} ${img.h}`}
          preserveAspectRatio="xMidYMid meet"
          onPointerDown={onPointerDown}
          style={{ cursor: tapping ? "crosshair" : "default" }}
        >
          <image href={img.url} width={img.w} height={img.h} />
          {regions?.map((r) => (
            <g key={r.id} className="stub-region">
              <rect x={r.box.x * img.w} y={r.box.y * img.h} width={r.box.w * img.w} height={r.box.h * img.h}
                fill="none" stroke="#1971c2" strokeWidth={2} strokeDasharray="6 4" />
              <text x={r.box.x * img.w + 3} y={r.box.y * img.h - 4} fontSize={14} fill="#1971c2">
                {r.id}
              </text>
            </g>
          ))}
          {drawn.map((d) => (
            <Shape key={d.key} d={d} img={img} opacity={opacityFor(d.step)} badge={badges} />
          ))}
          {marks.map((m) => {
            const color = PALETTE[m.color];
            if (m.kind === "check" && m.box) {
              const b = m.box;
              return (
                <ellipse key={m.key} className="stub-draw" pathLength={1} cx={(b.x + b.w / 2) * img.w}
                  cy={(b.y + b.h / 2) * img.h} rx={(b.w * img.w) / 2 + 14} ry={(b.h * img.h) / 2 + 14}
                  fill="none" stroke={color} strokeWidth={6} />
              );
            }
            if (m.at) {
              const x = m.at.x * img.w;
              const y = m.at.y * img.h;
              return (
                <path key={m.key} d={`M${x - 14},${y - 14}L${x + 14},${y + 14}M${x + 14},${y - 14}L${x - 14},${y + 14}`}
                  stroke={color} strokeWidth={6} strokeLinecap="round" />
              );
            }
            return null;
          })}
        </svg>
      )}
    </div>
  );
}
