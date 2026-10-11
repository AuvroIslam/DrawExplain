import { type DragEvent, useEffect, useRef, useState } from "react";
import { validateImageFile } from "../api";
import type { SampleInfo } from "../types";
import { AlertIcon, ArrowRightIcon, ImageIcon, SpeakerIcon, UploadIcon } from "./Icons";

interface Props {
  samples: SampleInfo[] | null;
  offline: boolean;
  mock: boolean;
  onFile: (file: File) => void;
  onSample: (sample: SampleInfo) => void;
  onRetry: () => void;
}

function prettySampleName(name: string): { title: string; group: string | null } {
  const parts = name.split("/");
  const file = parts.pop() ?? name;
  const stem = file.replace(/\.[a-z0-9]+$/i, "").replace(/[_-]+/g, " ").trim();
  return { title: stem.charAt(0).toUpperCase() + stem.slice(1), group: parts.length ? parts.join(" / ") : null };
}

function firstImage(items: DataTransferItemList | FileList | null | undefined): File | null {
  if (!items) return null;
  for (const item of Array.from(items as ArrayLike<DataTransferItem | File>)) {
    const file = item instanceof File ? item : item.kind === "file" ? item.getAsFile() : null;
    if (file && (file.type.startsWith("image/") || file.type === "application/pdf" || /\.(png|jpe?g|webp|pdf)$/i.test(file.name))) {
      return file;
    }
  }
  return null;
}

/** The product in one picture: a slide with the tutor's marker strokes being drawn on it. */
function HeroDemo() {
  return (
    <div className="hero-demo" aria-hidden="true">
      <div className="hero-card">
        <div className="hero-board">
          <img src="/mock/network_basic.png" alt="" width={1280} height={720} />
          <svg viewBox="0 0 1280 720" className="hero-ink">
            <rect className="ink-hl" x="132" y="38" width="136" height="42" rx="6" />
            <path
              className="ink-stroke ink-red"
              pathLength={1}
              d="M792 284c-78-6-146 14-148 62-2 46 66 72 150 70 82-2 136-26 134-70-2-44-70-66-150-60-40 4-74 14-96 28"
            />
            <path className="ink-stroke ink-orange" pathLength={1} d="M512 282c38-78 168-86 214-6" />
            <path className="ink-stroke ink-orange ink-head" pathLength={1} d="M694 262l34 18 4-38" />
            <path className="ink-stroke ink-red ink-leader" pathLength={1} d="M790 432l-6 40" />
            <text className="ink-text" x="700" y="514">
              forwards packets!
            </text>
          </svg>
        </div>
        <div className="hero-caption">
          <span className="hero-step">Step 4 of 5</span>
          <p>
            <SpeakerIcon size={16} />
            <span className="said">Here is the key idea: the </span>
            <mark>router</mark>
            <span className="todo"> forwards packets between different networks.</span>
          </p>
        </div>
      </div>
    </div>
  );
}

export function Landing({ samples, offline, mock, onFile, onSample, onRetry }: Props) {
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const take = (file: File | null) => {
    if (!file) {
      setError("Please drop an image (PNG, JPG or WebP) or a PDF.");
      return;
    }
    const problem = validateImageFile(file);
    setError(problem);
    if (!problem) onFile(file);
  };

  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const file = firstImage(e.clipboardData?.items);
      if (file) {
        e.preventDefault();
        take(file);
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  });

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    take(firstImage(e.dataTransfer?.files) ?? firstImage(e.dataTransfer?.items));
  };

  return (
    <main className="landing">
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="eyebrow">AI tutor · draws on your page</p>
          <h1>
            Any study page, <span className="hand-underline">explained out loud</span> while it&rsquo;s drawn on.
          </h1>
          <p className="pitch">
            Drop in a lecture slide, a textbook photo or a diagram. StudyLens finds what&rsquo;s on it, then a tutor
            circles, points and labels the real parts, step by step, in sync with its voice.
          </p>

          <label
            className={`dropzone${drag ? " dragging" : ""}`}
            onDragEnter={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragOver={(e) => e.preventDefault()}
            onDragLeave={(e) => {
              if (e.currentTarget.contains(e.relatedTarget as Node | null)) return;
              setDrag(false);
            }}
            onDrop={onDrop}
          >
            <input
              ref={input}
              className="sr-only"
              type="file"
              accept="image/png,image/jpeg,image/webp,application/pdf,.pdf"
              onChange={(e) => {
                take(e.target.files?.[0] ?? null);
                e.target.value = "";
              }}
            />
            <span className="dz-icon">
              <UploadIcon size={28} />
            </span>
            <span className="dz-title">{drag ? "Drop it, I'll take a look" : "Drop a study image or PDF here"}</span>
            <span className="dz-sub">
              or <span className="dz-link">choose a file</span> · paste with Ctrl+V · PNG, JPG, WebP or PDF up to 15 MB
            </span>
          </label>
          {error && (
            <p className="form-error" role="alert">
              <AlertIcon size={16} /> {error}
            </p>
          )}

          {offline && !mock && (
            <div className="offline-note" role="status">
              <AlertIcon size={18} />
              <div>
                <strong>The StudyLens server isn&rsquo;t answering.</strong> Start the backend on port 8000, or{" "}
                <a href="?mock=1">open the demo with built-in data</a>.
              </div>
              <button type="button" className="btn-ghost small" onClick={onRetry}>
                Retry
              </button>
            </div>
          )}
        </div>
        <HeroDemo />
      </section>

      {samples && samples.length > 0 && (
        <section className="samples" aria-label="Sample pages">
          <h2>
            <ImageIcon size={18} /> No image handy? Try a sample
          </h2>
          <ul>
            {samples.map((s) => {
              const { title, group } = prettySampleName(s.name);
              return (
                <li key={s.name}>
                  <button type="button" className="sample-card" onClick={() => onSample(s)}>
                    <span className="sample-thumb">
                      <img src={s.url} alt="" loading="lazy" />
                    </span>
                    <span className="sample-meta">
                      <span className="sample-title">{title}</span>
                      {group && <span className="sample-group">{group}</span>}
                    </span>
                    <ArrowRightIcon size={18} className="sample-go" />
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <footer className="landing-foot">
        <span>Perception: RapidOCR + OpenCV</span>
        <span>Lesson planning: OpenAI, grounded on detected regions</span>
        <span>Voice: ElevenLabs</span>
        <span>Whiteboard: Excalidraw</span>
      </footer>
    </main>
  );
}
