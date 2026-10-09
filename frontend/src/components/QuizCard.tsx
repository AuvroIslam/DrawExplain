import type { QuizState } from "../hooks/useStudySession";
import type { QuizItem } from "../types";
import { ArrowRightIcon, CheckIcon, CloseIcon, ReplayIcon, TapIcon, TrophyIcon } from "./Icons";

interface Props {
  quiz: QuizState;
  items: QuizItem[];
  onNext: () => void;
  onDone: () => void;
  onRestart: () => void;
}

function verdict(score: number, total: number) {
  if (score === total) return "Perfect. You really know this page.";
  if (score >= total / 2) return "Nice work. Replay the steps you missed to lock it in.";
  return "Good start. Run the lesson again and try once more.";
}

export function QuizCard({ quiz, items, onNext, onDone, onRestart }: Props) {
  const total = items.length;
  const score = quiz.results.filter((r) => r !== "missed").length;

  if (quiz.phase === "summary") {
    return (
      <section className="quiz-card summary" aria-live="polite">
        <span className="quiz-trophy">
          <TrophyIcon size={30} />
        </span>
        <p className="quiz-kicker">Quiz complete</p>
        <p className="quiz-score">
          {score}
          <span>/ {total}</span>
        </p>
        <ul className="quiz-dots" aria-label="Your answers">
          {quiz.results.map((r, i) => (
            <li key={i} className={r}>
              {r === "missed" ? <CloseIcon size={14} strokeWidth={3} /> : <CheckIcon size={14} strokeWidth={3} />}
              <span>Q{i + 1}</span>
              <em>{r === "first" ? "first try" : r === "second" ? "second try" : "shown"}</em>
            </li>
          ))}
        </ul>
        <p className="quiz-verdict">{verdict(score, total)}</p>
        <div className="card-actions">
          <button type="button" className="btn-primary" onClick={onDone}>
            Done
          </button>
          <button type="button" className="btn-ghost" onClick={onRestart}>
            <ReplayIcon size={16} /> Try again
          </button>
        </div>
      </section>
    );
  }

  const item = items[quiz.index];
  if (!item) return null;
  const last = quiz.index + 1 >= total;
  const answered = quiz.phase === "correct" || quiz.phase === "revealed";

  return (
    <section className={`quiz-card ${quiz.phase}`} aria-live="polite">
      <div className="quiz-top">
        <span className="quiz-kicker">
          Quiz · question {quiz.index + 1} of {total}
        </span>
        <span className="quiz-tries" title="Tries">
          {[0, 1].map((t) => (
            <i key={t} className={t < quiz.tries ? "used" : ""} />
          ))}
        </span>
      </div>
      <h3 className="quiz-q">{item.question}</h3>

      {quiz.phase === "asking" && (
        <p key={quiz.wrongTaps} className={`quiz-prompt${quiz.tries > 0 ? " wrong" : ""}`}>
          <TapIcon size={18} />
          {quiz.tries === 0 ? "Tap your answer right on the image." : "Not quite. One more try."}
        </p>
      )}

      {answered && (
        <div className={`quiz-feedback ${quiz.phase}`}>
          <p className="qf-title">
            {quiz.phase === "correct" ? <CheckIcon size={18} strokeWidth={3} /> : <ArrowRightIcon size={18} />}
            {quiz.phase === "correct"
              ? quiz.tries === 0
                ? "Correct, first try!"
                : "Correct!"
              : "Here it is, circled on the board."}
          </p>
          <p className="qf-text">{item.explanation}</p>
          <button type="button" className="btn-primary" onClick={onNext}>
            {last ? "See my score" : "Next question"} <ArrowRightIcon size={16} />
          </button>
        </div>
      )}
    </section>
  );
}
