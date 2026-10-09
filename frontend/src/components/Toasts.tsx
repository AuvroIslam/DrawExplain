import type { Toast } from "../hooks/useToasts";
import { AlertIcon, CheckIcon, CloseIcon, SpeakerIcon } from "./Icons";

export function Toasts({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.kind}`}>
          {t.kind === "error" ? <AlertIcon size={18} /> : t.kind === "success" ? <CheckIcon size={18} /> : <SpeakerIcon size={18} />}
          <span>{t.message}</span>
          <button type="button" className="icon-btn" onClick={() => onDismiss(t.id)} aria-label="Dismiss">
            <CloseIcon size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
