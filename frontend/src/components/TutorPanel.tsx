import { type FormEvent, useEffect, useRef, useState } from "react";
import { type Reader, scanErrorTitle, type Session, type StudySession } from "../hooks/useStudySession";
import type { LessonPlayer, PlayerState } from "../player/lessonPlayer";
import type { Lesson, Perception, RegionKind } from "../types";
import { FollowupBox } from "./FollowupBox";
import { HowItSees } from "./HowItSees";
import {
  AlertIcon,
  BookIcon,
  CheckIcon,
  DownloadIcon,
  LayersIcon,
  LinkPagesIcon,
  QuestionIcon,
  ReplayIcon,
  SparkIcon,
  TapIcon,
} from "./Icons";
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

/** The optional focus question ("What should I focus on?"). Its text lives in the session hook, so the big
 *  button under the page uses it too; remount it (key) to pick up a new page's text. */
function QuestionField({ study, disabled = false }: { study: StudySession; disabled?: boolean }) {
  const [value, setValue] = useState(() => study.getDraft());
  return (
    <label className="focus-field">
      <QuestionIcon size={18} />
      <span className="sr-only">What should I focus on? (optional)</span>
      <input
        type="text"
        value={value}
        maxLength={300}
        placeholder="What should I focus on? (optional)"
        disabled={disabled}
        onChange={(e) => {
          setValue(e.target.value);
          study.setDraft(e.target.value);
        }}
      />
    </label>
  );
}

const submitWith = (fn: () => void) => (e: FormEvent) => {
  e.preventDefault();
  fn();
};

function ReadyCard({ perception, study }: { perception: Perception; study: StudySession }) {
  const n = perception.regions.length;
  return (
    <form className="panel-card ready-card" onSubmit={submitWith(() => void study.teach())}>
      <p className="kicker">Step 2 of 2 · ready</p>
      <h2>
        Found {n} thing{n === 1 ? "" : "s"} on this page
      </h2>
      <p className="muted">
        These are the real parts the tutor is allowed to point at. Switch on <strong>How it sees</strong> to look at
        them.
      </p>
      <KindChips perception={perception} />
      <QuestionField study={study} />
      <button type="submit" className="btn-primary big">
        <SparkIcon size={20} /> Teach me this
      </button>
      <p className="fine">The tutor plans a short lesson, then draws and talks you through it.</p>
    </form>
  );
}

function OpeningCard({ name }: { name: string }) {
  return (
    <div className="panel-card scan-card">
      <p className="kicker">
        <BookIcon size={14} /> Reader mode
      </p>
      <h2>Opening your PDF</h2>
      <p className="muted doc-name">{name}</p>
      <ul className="scan-list">
        <li>
          <span className="spinner" aria-hidden="true" /> Keeping the file and counting its pages
        </li>
        <li>
          <span className="spinner" aria-hidden="true" /> Reading each page&rsquo;s text, so later pages can build on
          earlier ones
        </li>
      </ul>
      <p className="fine left">Turn pages freely. A page is only scanned when you ask me to explain it.</p>
    </div>
  );
}

/** Pages taught so far in this document: jump back to replay one. */
function ExplainedPages({ reader, onPage }: { reader: Reader; onPage: (page: number) => void }) {
  const pages = Object.keys(reader.explained)
    .map(Number)
    .sort((a, b) => a - b);
  if (!pages.length) return null;
  return (
    <section className="explained" aria-label="Pages explained so far">
      <p className="explained-head">Explained so far</p>
      <ul className="explained-list">
        {pages.map((p) => (
          <li key={p}>
            <button type="button" className={`explained-item${p === reader.page ? " here" : ""}`}
              disabled={p === reader.page} onClick={() => onPage(p)}
              title={p === reader.page ? "You are on this page" : `Go to page ${p} to replay its lesson`}>
              <span className="ep-num">p.&nbsp;{p}</span>
              <span className="ep-title">{reader.explained[p].lesson.title}</span>
              <CheckIcon size={14} />
            </button>
          </li>
        ))}
      </ul>
      <p className="fine left">Later pages build on these lessons instead of repeating them.</p>
    </section>
  );
}

function DocLine({ reader }: { reader: Reader }) {
  const { doc } = reader;
  return (
    <p className="doc-line" title={doc.filename}>
      <BookIcon size={15} />
      <span>{doc.title || doc.filename}</span>
    </p>
  );
}

/** Reader mode, page not explained yet: optional question + "Explain this page". */
function ExplainCard({ session, study }: { session: Session; study: StudySession }) {
  const r = session.reader as Reader;
  return (
    <form className="panel-card explain-card" onSubmit={submitWith(() => void study.teach())}>
      <DocLine reader={r} />
      <h2>
        Page {Math.max(1, r.page)} <span className="of-pages">of {r.doc.pages}</span>
      </h2>
      <p className="muted">
        Read at your own pace. When a page needs explaining, I scan just that page and teach it, building on the pages
        before it.
      </p>
      <QuestionField key={session.id} study={study} />
      <button type="submit" className="btn-primary big" disabled={r.loading}>
        <SparkIcon size={20} /> Explain this page
      </button>
      {session.planError ? (
        <p className="fu-error" role="alert">
          <AlertIcon size={15} />
          <span>{session.planError}</span>
        </p>
      ) : (
        <p className="fine">
          <kbd>&larr;</kbd> <kbd>&rarr;</kbd> turn pages &middot; nothing is scanned until you ask
        </p>
      )}
      <ExplainedPages reader={r} onPage={study.openPage} />
    </form>
  );
}

/** Reader mode, back on a page explained before: replay that lesson or explain it again. */
function ExplainedCard({ session, study }: { session: Session; study: StudySession }) {
  const r = session.reader as Reader;
  const saved = r.explained[r.page];
  return (
    <form className="panel-card explain-card explained-card" onSubmit={submitWith(study.explainAgain)}>
      <DocLine reader={r} />
      <p className="kicker done-kicker">
        <CheckIcon size={14} /> Page {r.page} of {r.doc.pages} &middot; explained
      </p>
      <h2>{saved.lesson.title}</h2>
      <LessonContext lesson={saved.lesson} />
      {saved.lesson.summary && <p className="big-idea">{saved.lesson.summary}</p>}
      <button type="button" className="btn-primary big" onClick={study.replayLesson}>
        <ReplayIcon size={19} /> Replay lesson
      </button>
      <div className="again">
        <p className="again-head">Or explain it again</p>
        <QuestionField key={session.id} study={study} />
        <button type="submit" className="btn-ghost wide">
          <SparkIcon size={17} /> Explain again
        </button>
      </div>
      <ExplainedPages reader={r} onPage={study.openPage} />
    </form>
  );
}

/** "pages 2-3" for [2, 3]; "page 2" for [2]; "pages 1-3, 5" for [1, 2, 3, 5]. */
function pagesLabel(pages: number[]): string {
  const sorted = [...new Set(pages.filter((p) => Number.isFinite(p)))].sort((a, b) => a - b);
  const parts: string[] = [];
  for (let i = 0; i < sorted.length; ) {
    let j = i;
    while (j + 1 < sorted.length && sorted[j + 1] === sorted[j] + 1) j++;
    parts.push(j > i ? `${sorted[i]}-${sorted[j]}` : String(sorted[i]));
    i = j + 1;
  }
  return `${sorted.length === 1 ? "page" : "pages"} ${parts.join(", ")}`;
}

/** The student's focus question and the earlier pages this lesson builds on. */
function LessonContext({ lesson }: { lesson: Lesson }) {
  const pages = lesson.context_pages ?? [];
  if (!lesson.question && !pages.length) return null;
  return (
    <div className="lesson-context">
      {pages.length > 0 && (
        <span className="context-chip" title="The tutor read the earlier pages and builds on them">
          <LinkPagesIcon size={14} /> Builds on {pagesLabel(pages)}
        </span>
      )}
      {lesson.question && (
        <p className="asked">
          <span className="asked-label">You asked</span>
          <span className="asked-q">{lesson.question}</span>
        </p>
      )}
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
      <ErrorCard title={scanErrorTitle(session)} message={session.scanError ?? "Something went wrong."}
        onRetry={study.retryScan} />
    );
  } else if (session.scan === "loading") {
    body = <OpeningCard name={session.source.name} />;
  } else if (session.reader && !lesson && !session.planning && (session.scan === "idle" || session.scan === "done")) {
    body = session.reader.explained[session.reader.page] ? (
      <ExplainedCard session={session} study={study} />
    ) : (
      <ExplainCard session={session} study={study} />
    );
  } else if (!perception || session.scan === "scanning") {
    body = <ScanCard />;
  } else if (!lesson && session.planning) {
    body = <PlanningCard startedAt={session.planStartedAt} regions={perception.regions.length} />;
  } else if (!lesson && session.planError) {
    body = (
      <ErrorCard title="The tutor couldn't plan this lesson" message={session.planError}
        onRetry={() => void study.teach()} />
    );
  } else if (!lesson) {
    body = <ReadyCard key={session.id} perception={perception} study={study} />;
  } else {
    body = (
      <div className="lesson">
        <header className="lesson-head">
          <p className="kicker">
            <LayersIcon size={14} /> Lesson · {lesson.steps.length} step{lesson.steps.length === 1 ? "" : "s"}
            {session.streaming ? " so far" : ""}
          </p>
          <h2>{lesson.title}</h2>
          <LessonContext lesson={lesson} />
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
