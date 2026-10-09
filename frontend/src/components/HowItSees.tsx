// "How it sees": the evidence behind every drawing (CV regions, LLM plan, grounding fusion).
import type { FollowupResponse, Grounding, Lesson, Perception, RegionKind, Step } from "../types";
import { CloseIcon, EyeIcon } from "./Icons";

interface Props {
  perception: Perception;
  lesson: Lesson | null;
  steps: Step[];
  followups: FollowupResponse[];
  onClose: () => void;
}

const STAGE_LABELS: Record<string, string> = {
  prepare: "Prepare image",
  ocr: "OCR text (RapidOCR)",
  shapes: "Shapes (OpenCV)",
  figures: "Figures (OpenCV)",
  blocks: "Text blocks",
  regions: "Merge regions",
  layout: "Layout",
  freespace: "Free-space map",
  ink: "Ink mask",
  som: "Set-of-Mark image",
  marks: "Set-of-Mark image",
  llm: "LLM call",
  grounding: "Grounding fusion",
  geometry: "Geometry",
  validate: "Validator",
};

const KIND_LABELS: Record<RegionKind, [string, string]> = {
  text: ["text line", "text lines"],
  text_block: ["text block", "text blocks"],
  shape: ["shape", "shapes"],
  figure: ["figure", "figures"],
};

/** Ordered from strongest to weakest evidence; one blue ramp (dark = strong), purple = student. */
const GROUNDING_INFO: { key: Grounding; label: string; detail: string; color: string }[] = [
  { key: "consensus", label: "Consensus", detail: "region id and the model's own box agree; drawn on the pixel-tight CV box", color: "#0d366b" },
  { key: "cv_snap", label: "CV snap", detail: "the model's box snapped to a better-matching CV region", color: "#1c5cab" },
  { key: "id_only", label: "ID only", detail: "boxes disagreed, but the region's OCR text matches the target", color: "#2a78d6" },
  { key: "llm_refined", label: "LLM refined", detail: "no region matched; the model's box tightened to the ink inside it", color: "#5598e7" },
  { key: "llm_only", label: "LLM only", detail: "raw model estimate, lowest confidence", color: "#86b6ef" },
  { key: "user", label: "Your selection", detail: "the part you circled with the pen", color: "#9c36b5" },
];

function prettyStage(key: string): string {
  return STAGE_LABELS[key] ?? key.replace(/[_-]+/g, " ").replace(/^./, (c) => c.toUpperCase());
}

function secs(v: number | undefined): string {
  if (v === undefined || !Number.isFinite(v)) return "n/a";
  if (v < 0.01) return `${Math.max(1, Math.round(v * 1000))} ms`;
  return v < 10 ? `${v.toFixed(2)} s` : `${v.toFixed(1)} s`;
}

function stages(timings: Record<string, number>): { key: string; value: number }[] {
  return Object.entries(timings)
    .filter(([k, v]) => k !== "total" && Number.isFinite(v) && v >= 0)
    .map(([key, value]) => ({ key, value }));
}

function total(timings: Record<string, number>): number {
  if (Number.isFinite(timings.total)) return timings.total;
  return stages(timings).reduce((a, s) => a + s.value, 0);
}

function StageBars({ timings }: { timings: Record<string, number> }) {
  const rows = stages(timings);
  const max = Math.max(...rows.map((r) => r.value), 1e-6);
  if (!rows.length) return null;
  return (
    <ul className="stage-bars">
      {rows.map((r) => (
        <li key={r.key} title={`${prettyStage(r.key)}: ${secs(r.value)}`}>
          <span className="sb-label">{prettyStage(r.key)}</span>
          <span className="sb-track">
            <span className="sb-bar" style={{ width: `${Math.max(1.5, (r.value / max) * 100)}%` }} />
          </span>
          <span className="sb-value">{secs(r.value)}</span>
        </li>
      ))}
    </ul>
  );
}

export function HowItSees({ perception, lesson, steps, followups, onClose }: Props) {
  const regions = perception.regions;
  const kinds = (Object.keys(KIND_LABELS) as RegionKind[])
    .map((k) => ({ kind: k, n: regions.filter((r) => r.kind === k).length }))
    .filter((k) => k.n > 0);
  const annotations = steps.flatMap((s) => s.annotations);
  const mix = GROUNDING_INFO.map((g) => ({ ...g, n: annotations.filter((a) => a.grounding === g.key).length }));
  const shown = mix.filter((g) => g.n > 0 || g.key !== "user");
  const meanConf = annotations.length
    ? annotations.reduce((a, x) => a + (Number.isFinite(x.confidence) ? x.confidence : 0), 0) / annotations.length
    : null;
  const cvBacked = mix.filter((g) => g.key === "consensus" || g.key === "cv_snap" || g.key === "id_only").reduce((a, g) => a + g.n, 0);
  const perceiveTotal = total(perception.timings);
  // timings.llm is the original generation time even when the response was replayed from the cache
  const llm = lesson ? (lesson.timings.llm ?? total(lesson.timings)) : null;
  const llmText = llm === null ? "" : `${secs(llm)}${lesson?.timings.llm_cached ? " (cached)" : ""}`;
  const agreement = lesson?.timings.approx_agreement;
  const followTime = followups.reduce((a, f) => a + (f.timings.llm ?? total(f.timings)), 0);
  const warnings = [...(lesson?.warnings ?? []), ...followups.flatMap((f) => f.warnings)];

  return (
    <section className="how" aria-label="How it sees">
      <header className="how-head">
        <span className="how-icon">
          <EyeIcon size={18} />
        </span>
        <div>
          <h2>How StudyLens sees this page</h2>
          <p>Computer vision finds the real parts first; the model can only point at what is there.</p>
        </div>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Close How it sees">
          <CloseIcon size={18} />
        </button>
      </header>

      <div className="kpis">
        <div className="kpi">
          <span className="kpi-label">Regions found</span>
          <span className="kpi-value">{regions.length}</span>
          <span className="kpi-sub">in {secs(perceiveTotal)}, no AI</span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Lesson plan</span>
          <span className="kpi-value">{llm === null ? "not yet" : secs(llm)}</span>
          <span className="kpi-sub">
            {lesson ? `${lesson.model}${lesson.timings.llm_cached ? " · cached" : ""}` : "waiting for Teach me this"}
          </span>
        </div>
        <div className="kpi">
          <span className="kpi-label">On CV regions</span>
          <span className="kpi-value">{annotations.length ? `${cvBacked}/${annotations.length}` : "0"}</span>
          <span className="kpi-sub">
            {meanConf === null ? "drawings so far" : `mean confidence ${Math.round(meanConf * 100)}%`}
          </span>
        </div>
      </div>

      <ol className="how-stages">
        <li>
          <div className="hs-head">
            <span className="hs-num">1</span>
            <h3>Perceive</h3>
            <span className="hs-what">RapidOCR + OpenCV</span>
            <span className="hs-time">{secs(perceiveTotal)}</span>
          </div>
          <p className="hs-text">
            Text lines, shapes and figures become numbered regions R1 to R{regions.length}, outlined on the board.
          </p>
          <StageBars timings={perception.timings} />
          {kinds.length > 0 && (
            <ul className="kind-chips">
              {kinds.map((k) => (
                <li key={k.kind} className={`kind-chip kind-${k.kind}`}>
                  <strong>{k.n}</strong> {KIND_LABELS[k.kind][k.n === 1 ? 0 : 1]}
                </li>
              ))}
            </ul>
          )}
        </li>

        <li>
          <div className="hs-head">
            <span className="hs-num">2</span>
            <h3>Plan</h3>
            <span className="hs-what">{lesson?.model ?? "LLM"}</span>
            <span className="hs-time">{llmText}</span>
          </div>
          <p className="hs-text">
            The model sees the page plus a numbered map of the regions. For every drawing it names region ids
            <em> and</em> gives its own box estimate, so the two can be checked against each other.
          </p>
          {lesson && (
            <p className="hs-facts">
              {lesson.steps.length} steps · {lesson.steps.reduce((a, s) => a + s.annotations.length, 0)} drawings ·{" "}
              {lesson.quiz.length} quiz questions
              {followups.length > 0 && ` · ${followups.length} follow-up${followups.length > 1 ? "s" : ""} (${secs(followTime)})`}
            </p>
          )}
        </li>

        <li>
          <div className="hs-head">
            <span className="hs-num">3</span>
            <h3>Fuse</h3>
            <span className="hs-what">cross-check before drawing</span>
          </div>
          {annotations.length === 0 ? (
            <p className="hs-text">Once the lesson is planned, every drawing target is graded here.</p>
          ) : (
            <>
              <div className="mix-bar" role="img" aria-label="Grounding mix of the drawings">
                {mix
                  .filter((g) => g.n > 0)
                  .map((g) => (
                    <span
                      key={g.key}
                      className="mix-seg"
                      style={{ flexGrow: g.n, background: g.color }}
                      title={`${g.label}: ${g.n}`}
                    />
                  ))}
              </div>
              <ul className="mix-legend">
                {shown.map((g) => (
                  <li key={g.key} className={g.n ? "" : "zero"}>
                    <span className="swatch" style={{ background: g.color }} />
                    <span className="ml-name">{g.label}</span>
                    <span className="ml-detail">{g.detail}</span>
                    <span className="ml-count">{g.n}</span>
                  </li>
                ))}
              </ul>
              {agreement !== undefined && Number.isFinite(agreement) && (
                <p className="hs-facts">
                  Self-consistency {Math.round(agreement * 100)}%:{" "}
                  {agreement >= 0.5
                    ? "the model's own boxes agree with its region choices, so they may arbitrate disagreements."
                    : "the model's own boxes often miss its region choices, so the region ids are trusted instead."}
                </p>
              )}
            </>
          )}
        </li>
      </ol>

      {warnings.length > 0 && (
        <details className="how-warnings">
          <summary>
            {warnings.length} validator note{warnings.length > 1 ? "s" : ""}
          </summary>
          <ul>
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </details>
      )}
      <p className="how-foot">
        On the board: outlines are the detected regions, badges show how each drawing was grounded and how sure the
        tutor is.
      </p>
    </section>
  );
}
