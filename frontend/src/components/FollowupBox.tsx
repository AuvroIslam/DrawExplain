import { type FormEvent, useState } from "react";
import { AlertIcon, PenIcon, SendIcon } from "./Icons";

interface Props {
  asking: boolean;
  /** The lesson is still being written: questions wait until it is complete. */
  locked?: boolean;
  error: string | null;
  hasDrawing: boolean;
  onAsk: (question: string) => void;
  onClearError: () => void;
}

export function FollowupBox({ asking, locked = false, error, hasDrawing, onAsk, onClearError }: Props) {
  const [text, setText] = useState("");
  const [last, setLast] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const q = text.trim();
    if (!q || asking || locked) return;
    setLast(q);
    setText("");
    onAsk(q);
  };

  return (
    <form className={`followup${hasDrawing ? " marked" : ""}`} onSubmit={submit}>
      <div className="fu-field">
        <input
          type="text"
          value={text}
          maxLength={400}
          placeholder={locked ? "The tutor is still writing the lesson..." : "Ask about this page..."}
          aria-label="Ask a follow-up question about this page"
          disabled={asking || locked}
          onChange={(e) => {
            setText(e.target.value);
            if (error) onClearError();
          }}
        />
        <button type="submit" className="fu-send" disabled={!text.trim() || asking || locked} aria-label="Ask the tutor">
          {asking ? <span className="spinner light" aria-hidden="true" /> : <SendIcon size={18} />}
        </button>
      </div>
      {error ? (
        <p className="fu-error" role="alert">
          <AlertIcon size={15} />
          <span>{error}</span>
          {last && (
            <button type="button" className="link-btn" onClick={() => onAsk(last)}>
              Retry
            </button>
          )}
        </p>
      ) : (
        <p className="fu-hint">
          <PenIcon size={15} />
          {hasDrawing ? (
            <span>
              <strong>Got your mark.</strong> I&rsquo;ll look at the part you drew around.
            </span>
          ) : (
            <span>Tip: circle the confusing part with the pen first</span>
          )}
        </p>
      )}
    </form>
  );
}
