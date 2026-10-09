import { useEffect, useMemo, useRef } from "react";
import type { Section } from "../hooks/useStudySession";
import type { PlayerStatus } from "../player/lessonPlayer";
import type { WordSpan } from "../player/timing";
import type { Step } from "../types";
import { CheckIcon, PenIcon, QuestionIcon } from "./Icons";

/** Narration with the spoken word marked like a highlighter pen. */
export function Karaoke({ text, words, index }: { text: string; words: WordSpan[]; index: number }) {
  const parts = useMemo(() => {
    const out: { text: string; word: number }[] = [];
    let at = 0;
    words.forEach((w, i) => {
      const s = Math.max(w.charStart, at);
      const e = Math.min(Math.max(w.charEnd, s), text.length);
      if (s > at) out.push({ text: text.slice(at, s), word: -1 });
      if (e > s) out.push({ text: text.slice(s, e), word: i });
      at = Math.max(at, e);
    });
    if (at < text.length) out.push({ text: text.slice(at), word: -1 });
    return out;
  }, [text, words]);

  return (
    <p className="karaoke">
      {parts.map((p, i) =>
        p.word < 0 ? (
          <span key={i}>{p.text}</span>
        ) : (
          <span key={i} className={p.word < index ? "w said" : p.word === index ? "w now" : "w"}>
            {p.text}
          </span>
        ),
      )}
    </p>
  );
}

interface Props {
  steps: Step[];
  sections: Section[];
  current: number;
  status: PlayerStatus;
  words: WordSpan[];
  wordIndex: number;
  progress: number;
  asking: string | null;
  /** The lesson is still streaming in (more steps are being written). */
  writing?: boolean;
  /** The player reached the last step received so far and waits for the next one. */
  awaiting?: boolean;
  onJump: (index: number) => void;
}

const STATUS_TEXT: Partial<Record<PlayerStatus, string>> = {
  preparing: "warming up the voice",
  paused: "paused",
  waiting: "done",
  finished: "done",
};

export function StepList({
  steps,
  sections,
  current,
  status,
  words,
  wordIndex,
  progress,
  asking,
  writing = false,
  awaiting = false,
  onJump,
}: Props) {
  const currentRef = useRef<HTMLLIElement>(null);
  const pendingRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    currentRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [current]);

  useEffect(() => {
    if (asking) pendingRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [asking]);

  const finishedCurrent = status === "waiting" || status === "finished";

  return (
    <ol className="steps">
      {sections.map((sec, si) => (
        <li key={`${sec.kind}-${si}`} className={`section ${sec.kind}`}>
          {sec.kind === "followup" && (
            <div className="q-head">
              <QuestionIcon size={16} />
              <span>
                <span className="q-mark">Q:</span> {sec.title}
              </span>
            </div>
          )}
          <ol className="section-steps">
            {steps.slice(sec.start, sec.start + sec.count).map((step, k) => {
              const i = sec.start + k;
              const isCurrent = i === current;
              const done = i < current || (isCurrent && finishedCurrent);
              const cls = ["step", isCurrent ? "current" : "", done ? "done" : "", i > current ? "todo" : ""]
                .filter(Boolean)
                .join(" ");
              return (
                <li key={step.index} className={cls} ref={isCurrent ? currentRef : undefined}
                  aria-current={isCurrent ? "step" : undefined}>
                  <button type="button" className="step-head" onClick={() => onJump(i)}
                    title={isCurrent ? "Replay this step" : `Go to step ${step.index}`}>
                    <span className="step-num">{done ? <CheckIcon size={14} strokeWidth={3} /> : step.index}</span>
                    <span className="step-title">{step.title}</span>
                    {isCurrent && STATUS_TEXT[status] && <span className="step-state">{STATUS_TEXT[status]}</span>}
                  </button>
                  {isCurrent && (
                    <div className="step-body">
                      <Karaoke text={step.narration} words={words} index={wordIndex} />
                      <div className="step-progress" aria-hidden="true">
                        <span style={{ transform: `scaleX(${progress})` }} />
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
            {writing && sec.kind === "lesson" && (
              <li className={`step writing${awaiting ? " waiting" : ""}`} aria-live="polite">
                <span className="step-head">
                  <span className="step-num">
                    <PenIcon size={13} />
                  </span>
                  <span className="step-title">
                    {awaiting ? "Writing the next step" : "The tutor is writing more steps"}
                    <span className="dots" aria-hidden="true" />
                  </span>
                </span>
              </li>
            )}
          </ol>
        </li>
      ))}
      {asking && (
        <li className="section followup pending" ref={pendingRef}>
          <div className="q-head">
            <QuestionIcon size={16} />
            <span>
              <span className="q-mark">Q:</span> {asking}
            </span>
          </div>
          <div className="thinking">
            <span className="spinner purple" aria-hidden="true" /> Thinking about your question
            <span className="dots" aria-hidden="true" />
          </div>
        </li>
      )}
    </ol>
  );
}
