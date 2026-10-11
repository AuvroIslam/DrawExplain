import type { VoiceMode } from "../player/voices";
import { DownloadIcon, EyeIcon, LogoMark, SpeakerIcon } from "./Icons";

interface Props {
  workspace: boolean;
  mock: boolean;
  voice: VoiceMode;
  elevenAvailable: boolean;
  onVoice: (mode: VoiceMode) => void;
  debug: boolean;
  debugEnabled: boolean;
  onDebug: (on: boolean) => void;
  canSave: boolean;
  onSave: () => void;
  onHome: () => void;
}

export function TopBar(p: Props) {
  return (
    <header className="topbar">
      <button type="button" className="brand" onClick={p.onHome} title="Start over with a new page">
        <LogoMark size={32} />
        <span className="brand-name">
          Study<span className="brand-lens">Lens</span>
        </span>
        <span className="brand-tag">Live Whiteboard</span>
      </button>
      {p.mock && (
        <span className="demo-pill" title="Running on built-in demo data (no backend needed)">
          Demo data
        </span>
      )}
      <div className="topbar-tools">
        <label className="voice-select" title="How the tutor speaks">
          <SpeakerIcon size={18} />
          <span className="sr-only">Voice</span>
          <select value={p.voice} onChange={(e) => p.onVoice(e.target.value as VoiceMode)}>
            <option value="eleven" disabled={!p.elevenAvailable}>
              Tutor voice{p.elevenAvailable ? "" : " (needs server)"}
            </option>
            <option value="browser">Browser voice</option>
            <option value="silent">Silent captions</option>
          </select>
        </label>
        {p.workspace && (
          <>
            <button
              type="button"
              className={`tool-toggle${p.debug ? " on" : ""}`}
              aria-pressed={p.debug}
              disabled={!p.debugEnabled}
              onClick={() => p.onDebug(!p.debug)}
              title="Show what the computer vision found and how every drawing was grounded"
            >
              <EyeIcon size={18} />
              <span className="tool-label">How it sees</span>
              <span className="switch" aria-hidden="true" />
            </button>
            <button type="button" className="tool-btn" disabled={!p.canSave} onClick={p.onSave}>
              <DownloadIcon size={18} />
              <span className="tool-label">Save notes</span>
            </button>
          </>
        )}
      </div>
    </header>
  );
}
