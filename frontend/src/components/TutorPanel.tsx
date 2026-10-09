import { useEffect, useRef, useState } from "react";
import type { Session, StudySession } from "../hooks/useStudySession";
import type { LessonPlayer, PlayerState } from "../player/lessonPlayer";
import type { Perception, RegionKind } from "../types";
import { FollowupBox } from "./FollowupBox";
import { HowItSees } from "./HowItSees";
import { AlertIcon, DownloadIcon, LayersIcon, SparkIcon, TapIcon } from "./Icons";
import { QuizCard } from "./QuizCard";
import { StepList } from "./StepList";
import { Transport } from "./Transport";

const KIND_NAMES: Record<RegionKind, [string, string]> = {
  text: ["text line", "text lines"],
  text_block: ["paragraph", "paragraphs"],
  shape: ["shape", "shapes"],
  figure: ["figure", "figures"],
};

function KindChips({ perception }: { perception: Perception }) {
  const kinds = (Object.keys(KIND_NAMES) as RegionKind[])
    .map((k) => ({ k, n: perception.regions.filter((r) => r.kind === k).length }))
    .filter((x) => x.n > 0);
  return (
    <ul className="kind-chips">
      {kinds.map(({ k, n }) => (
        <li key={k} className={`kind-chip kind-${k}`}>
          <strong>{n}</strong> {KIND_NAMES[k][n === 1 ? 0 : 1]}
        </li>
      ))}
    </ul>
  );
}

function ScanCard() {
  return (
    <div className="panel-card scan-card">
      <p className="kicker">Step 1 of 2 · looking</p>
      <h2>Reading your page</h2>
      <ul className="scan-list">
        <li>
          <span className="spinner" aria-hidden="true" /> Finding text lines with OCR
        </li>
        <li>
          <span className="spinner" aria-hidden="true" /> Detecting shapes and figures with OpenCV
        </li>
        <li>
          <span className="spinner" aria-hidden="true" /> Mapping empty space for the tutor&rsquo;s notes
        </li>
      </ul>
      <div className="skeleton" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}

function ReadyCard({ perception, onTeach }: { perception: Perception; onTeach: () => void }) {
  const n = perception.regions.length;
  return (
    <div className="panel-card ready-card">
      <p className="kicker">Step 2 of 2 · ready</p>
      <h2>
        Found {n} thing{n === 1 ? "" : "s"} on this page
      </h2>
      <p className="muted">
        These are the real parts the tutor is allowed to point at. Switch on <strong>How it sees</strong> to look at
        them.
      </p>
      <KindChips perception={perception} />
      <button type="button" className="btn-primary big" onClick={onTeach}>
        <SparkIcon size={20} /> Teach me this
      </button>
      <p className="fine">The tutor plans a short lesson, then draws and talks you through it.</p>
    </div>
  );
}

function PlanningCard({ startedAt, regions }: { startedAt: number; regions: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 100);
    return () => window.clearInterval(t);
  }, []);
  const elapsed = Math.max(0, (now - startedAt) / 1000);
  return (
    <div className="panel-card planning-card" aria-live="polite">
      <svg className="scribble" viewBox="0 0 120 60" aria-hidden="true">
        <path d="M8 40c14-22 26-24 30-10s-6 22 6 12 18-30 30-22-4 26 10 18 16-20 26-14" pathLength={1} />
      </svg>
      <h2>Planning the lesson...</h2>
      <ol className="plan-list">
        <li>The model looks at your page plus a numbered map of its {regions} regions.</li>
        <li>It writes short steps and, for every drawing, names region ids and guesses a box.</li>
        <li>Fusion cross-checks the two before anything touches the board.</li>
      </ol>
      <p className="elapsed">{elapsed.toFixed(1)} s</p>
    </div>
  );
}

function ErrorCard({ title, message, onRetry, retryLabel = "Try again" }: {
  title: string;
  message: string;
  onRetry: () => void;
  retryLabel?: string;
}) {
  return (
    <div className="panel-card error-card" role="alert">
      <span className="error-icon">
        <AlertIcon size={22} />
      </span>
      <h2>{title}</h2>
      <p>{message}</p>
      <button type="button" className="btn-primary" onClick={onRetry}>
        {retryLabel}
      </button>
    </div>
  );
}

interface Props {
  session: Session;
  state: PlayerState;
  player: LessonPlayer;
  study: StudySession;
  hasDrawing: boolean;
}

export function TutorPanel({ session, state, player, study, hasDrawing }: Props) {
  const { perception, lesson, quiz } = session;
  const bodyRef = useRef<HTMLDivElement>(null);
  const finished = state.status === "finished" && state.current === state.steps.length - 1;
  const quizCount = lesson?.quiz.length ?? 0;

  useEffect(() => {
    if (finished) bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [finished]);

  let body;
  if (study.debug && perception) {
    body = (
      <HowItSees
        perception={perception}
        lesson={lesson}
        steps={state.steps}
        followups={session.followups}
        onClose={() => study.setDebug(false)}
      />
    );
  } else if (quiz && lesson) {
    body = (
      <QuizCard quiz={quiz} items={lesson.quiz} onNext={study.nextQuestion} onDone={study.endQuiz}
        onRestart={study.startQuiz} />
    );
  } else if (session.scan === "error") {
    body = (
      <ErrorCard title="I couldn't read this page" message={session.scanError ?? "Something went wrong."}
        onRetry={study.retryScan} />
    );
  } else if (!perception || session.scan === "scanning") {
    body = <ScanCard />;
  } else if (!lesson && session.planning) {
    body = <PlanningCard startedAt={session.planStartedAt} regions={perception.regions.length} />;
  } else if (!lesson && session.planError) {
    body = <ErrorCard title="The tutor couldn't plan this lesson" message={session.planError} onRetry={study.teach} />;
  } else if (!lesson) {
    body = <ReadyCard perception={perception} onTeach={study.teach} />;
  } else {
    body = (
      <div className="lesson">
        <header className="lesson-head">
          <p className="kicker">
            <LayersIcon size={14} /> Lesson · {lesson.steps.length} step{lesson.steps.length === 1 ? "" : "s"}
            {session.streaming ? " so far" : ""}
          </p>
          <h2>{lesson.title}</h2>
          <p className="big-idea">{lesson.summary}</p>
        </header>
        <StepList
          steps={state.steps}
          sections={session.sections}
          current={state.current}
          status={state.status}
          words={state.words}
          wordIndex={state.wordIndex}
          progress={state.progress}
          asking={session.asking}
          writing={session.streaming}
          awaiting={state.awaitingMore}
          onJump={(i) => void player.goTo(i)}
        />
        {finished && !session.asking && (
          <div className="panel-card done-card">
            {quizCount > 0 ? (
              <>
                <h3>Ready to check yourself?</h3>
                <p>
                  {quizCount} quick question{quizCount === 1 ? "" : "s"}. Tap the answers right on the image.
                </p>
                <button type="button" className="btn-primary" onClick={study.startQuiz}>
                  <TapIcon size={18} /> Quiz me
                </button>
              </>
            ) : (
              <>
                <h3>That&rsquo;s the whole page.</h3>
                <p>Ask a follow-up below, or keep the annotated page.</p>
                <button type="button" className="btn-ghost" onClick={() => void study.saveNotes()}>
                  <DownloadIcon size={16} /> Save notes
                </button>
              </>
            )}
          </div>
        )}
      </div>
    );
  }

  const showControls = !!lesson && !quiz;
  return (
    <aside className="tutor-panel" aria-label="Tutor">
      <div className="panel-body" ref={bodyRef}>
        {body}
      </div>
      {showControls && (
        <div className="panel-foot">
          <Transport
            state={state}
            streaming={session.streaming}
            onToggle={() => player.toggle()}
            onPrev={() => player.prev()}
            onNext={() => player.next()}
            onReplay={() => player.replay()}
            onRestart={() => void player.goTo(0)}
            onAutoPlay={(on) => player.setAutoPlay(on)}
          />
          <FollowupBox
            asking={!!session.asking}
            locked={session.streaming}
            error={session.askError}
            hasDrawing={hasDrawing}
            onAsk={(q) => void study.ask(q)}
            onClearError={study.clearAskError}
          />
        </div>
      )}
    </aside>
  );
}
