import { useCallback, useEffect, useRef, useState } from "react";

export type ToastKind = "info" | "success" | "error";

export interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

/** Small auto-dismissing notices (voice fallback, saved notes, errors that need no action). */
export function useToasts(ttlMs = 4800) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, number>());

  const dismiss = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
    const timer = timers.current.get(id);
    if (timer) window.clearTimeout(timer);
    timers.current.delete(id);
  }, []);

  const push = useCallback(
    (message: string, kind: ToastKind = "info") => {
      const id = nextId.current++;
      setToasts((t) => [...t.filter((x) => x.message !== message), { id, kind, message }].slice(-3));
      timers.current.set(
        id,
        window.setTimeout(() => dismiss(id), ttlMs),
      );
    },
    [dismiss, ttlMs],
  );

  useEffect(() => {
    const map = timers.current;
    return () => {
      for (const t of map.values()) window.clearTimeout(t);
      map.clear();
    };
  }, []);

  return { toasts, push, dismiss };
}
