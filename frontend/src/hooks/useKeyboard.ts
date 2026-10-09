import { useEffect, useRef } from "react";

export interface KeyHandlers {
  onSpace?: () => void;
  onLeft?: () => void;
  onRight?: () => void;
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}

/** Space / Left / Right transport shortcuts, ignored while the student is typing. */
export function useKeyboard(handlers: KeyHandlers, enabled: boolean) {
  const ref = useRef(handlers);
  useEffect(() => {
    ref.current = handlers;
  });

  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.repeat) return;
      if (isTyping(e.target) || document.querySelector(".excalidraw-textEditorContainer textarea")) return;
      const h = ref.current;
      if (e.code === "Space" || e.key === " ") {
        if (!h.onSpace) return;
        e.preventDefault();
        h.onSpace();
      } else if (e.key === "ArrowLeft" && h.onLeft) {
        e.preventDefault();
        h.onLeft();
      } else if (e.key === "ArrowRight" && h.onRight) {
        e.preventDefault();
        h.onRight();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled]);
}
