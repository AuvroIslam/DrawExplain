import { Component, type KeyboardEvent, type ReactNode, Suspense, useState } from "react";
import type { BoardHandle } from "../board/types";
import type { Session } from "../hooks/useStudySession";
import { LazyBoard } from "./boardLoader";
import { AlertIcon, CheckIcon, ChevronLeftIcon, ChevronRightIcon, PenIcon, SparkIcon, TapIcon } from "./Icons";

class BoardBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    console.error("whiteboard crashed", error);
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="stage-center">
          <div className="stage-card" role="alert">
            <AlertIcon size={22} />
            <h3>The whiteboard failed to load</h3>
            <p>Reload the page to try again.</p>
            <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/** "Page [3] of 42" for PDF uploads: prev/next or type a number; each change re-reads that page. */
function PagePicker({ page, pages, busy, onPage }: { page: number; pages: number; busy: boolean; onPage: (p: number) => void }) {
  const [draft, setDraft] = useState(String(page));
  const commitDraft = () => {
    const n = Number.parseInt(draft, 10);
    if (Number.isFinite(n) && n >= 1 && n <= pages && n !== page) onPage(n);
    else setDraft(String(page));
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      e.currentTarget.blur();
    } else if (e.key === "Escape") {
      setDraft(String(page));
      e.currentTarget.blur();
    }
  };
  return (
    <div className={`page-picker${busy ? " busy" : ""}`} role="group" aria-label="PDF page">
      <button type="button" className="pp-btn" onClick={() => onPage(page - 1)} disabled={page <= 1}
        title="Previous page" aria-label="Previous page">
        <ChevronLeftIcon size={18} />
      </button>
      <label className="pp-label">
        <span>Page</span>
        <input type="text" inputMode="numeric" value={draft} style={{ width: `${Math.max(2, String(pages).length) + 1.2}ch` }}
          aria-label={`Page number, 1 to ${pages}`} onChange={(e) => setDraft(e.target.value.replace(/\D+/g, "").slice(0, 5))}
          onFocus={(e) => e.currentTarget.select()} onBlur={commitDraft} onKeyDown={onKey} />
        <span>of {pages}</span>
      </label>
      <button type="button" className="pp-btn" onClick={() => onPage(page + 1)} disabled={page >= pages}
        title="Next page" aria-label="Next page">
        <ChevronRightIcon size={18} />
      </button>
    </div>
  );
}

interface Props {
  session: Session;
  onBoardReady: (handle: BoardHandle) => void;
  onStudentDrawing: (has: boolean) => void;
  onTeach: () => void;
  onRetryScan: () => void;
  onHome: () => void;
  onPage: (page: number) => void;
}

function regionSummary(n: number) {
  return n === 1 ? "Found 1 thing on this page" : `Found ${n} things on this page`;
}

export function BoardStage({ session, onBoardReady, onStudentDrawing, onTeach, onRetryScan, onHome, onPage }: Props) {
  const { scan, perception, lesson, planning, quiz, source } = session;
  const pdfPages = source.kind === "file" ? (perception?.source_pages ?? source.pages ?? 0) : 0;
  const pdfPage = source.kind === "file" ? (source.page ?? 1) : 1;
  const scanning = scan === "scanning" || scan === "found";
  const regions = perception?.regions.length ?? 0;
  const showTeach = scan === "done" && !lesson && !planning;

  let chip: ReactNode = null;
  if (scan === "scanning") {
    chip = (
      <span className="stage-chip">
        <span className="spinner" aria-hidden="true" />
        Reading the page<span className="chip-sub">text, shapes, layout</span>
      </span>
    );
  } else if (scan === "found" || (scan === "done" && !lesson && !planning)) {
    chip = (
      <span className={`stage-chip found${scan === "found" ? " pop" : ""}`}>
        <CheckIcon size={16} />
        {regionSummary(regions)}
      </span>
    );
  } else if (planning) {
    chip = (
      <span className="stage-chip planning">
        <PenIcon size={16} />
        Planning the lesson<span className="dots" aria-hidden="true" />
      </span>
    );
  } else if (quiz?.phase === "asking") {
    chip = (
      <span className="stage-chip quiz">
        <TapIcon size={16} />
        Tap your answer on the image
      </span>
    );
  }

  return (
    <section className={`board-stage${quiz && quiz.phase === "asking" ? " tapping" : ""}`} aria-label="Whiteboard">
      <div className="board-host">
        <BoardBoundary>
          <Suspense
            fallback={
              <div className="board-fallback">
                {session.previewUrl && <img src={session.previewUrl} alt="" />}
                <span className="fallback-note">
                  <span className="spinner" aria-hidden="true" /> Opening the whiteboard
                </span>
              </div>
            }
          >
            <LazyBoard onReady={onBoardReady} onStudentDrawingChange={onStudentDrawing} className="board-canvas" />
          </Suspense>
        </BoardBoundary>
      </div>

      {scanning && (
        <div className={`scan-overlay${scan === "found" ? " found" : ""}`} aria-hidden="true">
          <div className="scan-wash" />
          <div className="scan-line" />
        </div>
      )}
      {planning && <div className="plan-shimmer" aria-hidden="true" />}

      <div className="stage-top" aria-live="polite">
        {chip}
      </div>

      {pdfPages > 1 && !quiz && (
        <PagePicker key={pdfPage} page={pdfPage} pages={pdfPages} busy={scan === "scanning"} onPage={onPage} />
      )}

      {showTeach && (
        <div className="stage-bottom">
          <button type="button" className="teach-btn" onClick={onTeach}>
            <SparkIcon size={22} />
            Teach me this
          </button>
        </div>
      )}

      {scan === "error" && (
        <div className="stage-center">
          <div className="stage-card" role="alert">
            <AlertIcon size={22} />
            <h3>I couldn&rsquo;t read this page</h3>
            <p>{session.scanError}</p>
            <div className="card-actions">
              <button type="button" className="btn-primary" onClick={onRetryScan}>
                Try again
              </button>
              <button type="button" className="btn-ghost" onClick={onHome}>
                Choose another image
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
