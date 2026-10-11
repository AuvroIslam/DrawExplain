import type { MouseEvent } from "react";
import type { PlayerState } from "../player/lessonPlayer";
import { VOICE_LABELS } from "../player/voices";
import { NextIcon, PauseIcon, PlayIcon, PrevIcon, ReplayIcon } from "./Icons";

interface Props {
  state: PlayerState;
  /** The lesson is still streaming in, so the step count is not final. */
  streaming?: boolean;
  onToggle: () => void;
  onPrev: () => void;
  onNext: () => void;
  onReplay: () => void;
  onRestart: () => void;
  onAutoPlay: (on: boolean) => void;
}

/** Buttons keep keyboard focus off themselves on click, so Space stays play/pause. */
const noFocus = (e: MouseEvent) => e.preventDefault();

export function Transport({ state, streaming = false, onToggle, onPrev, onNext, onReplay, onRestart, onAutoPlay }: Props) {
  const { status, current, steps, autoPlay } = state;
  const n = steps.length;
  const running = status === "playing" || status === "preparing";
  const finished = status === "finished";
  const label = running ? "Pause (Space)" : finished ? "Play the lesson again" : status === "waiting" ? "Next step (Space)" : "Play (Space)";

  let meta = `Step ${Math.max(1, current + 1)} of ${n}${streaming ? "+" : ""}`;
  if (state.awaitingMore) meta += " · the tutor is writing the next step";
  else if (status === "preparing") meta += " · getting the voice ready";
  else if (status === "paused") meta += " · paused";
  else if (status === "waiting" && !autoPlay) meta += " · press Next when ready";
  else if (finished) meta = `All ${n} steps done`;

  return (
    <div className="transport">
      <div className="transport-row">
        <button type="button" className="t-btn" onMouseDown={noFocus} onClick={onReplay} disabled={current < 0}
          title="Replay this step" aria-label="Replay this step">
          <ReplayIcon size={18} />
        </button>
        <button type="button" className="t-btn" onMouseDown={noFocus} onClick={onPrev} disabled={current <= 0}
          title="Previous step (Left arrow)" aria-label="Previous step">
          <PrevIcon size={18} />
        </button>
        <button type="button" className={`t-play${status === "preparing" ? " busy" : ""}`} onMouseDown={noFocus}
          onClick={finished ? onRestart : onToggle} title={label} aria-label={label}>
          {status === "preparing" ? (
            <span className="spinner light" aria-hidden="true" />
          ) : running ? (
            <PauseIcon size={22} />
          ) : finished ? (
            <ReplayIcon size={22} />
          ) : (
            <PlayIcon size={22} />
          )}
        </button>
        <button type="button" className="t-btn" onMouseDown={noFocus} onClick={onNext}
          disabled={current < 0 || finished} title="Next step (Right arrow)" aria-label="Next step">
          <NextIcon size={18} />
        </button>
        <label className="autoplay" title="Move on to the next step automatically">
          <input type="checkbox" checked={autoPlay} onChange={(e) => onAutoPlay(e.target.checked)} />
          <span className="switch" aria-hidden="true" />
          Auto-play
        </label>
      </div>
      <div className="transport-meta">
        <span>{meta}</span>
        <span className="voice-tag">{VOICE_LABELS[state.voice]}</span>
      </div>
    </div>
  );
}
