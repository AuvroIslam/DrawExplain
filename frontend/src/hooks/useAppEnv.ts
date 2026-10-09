// URL flags: ?mock=1 (no backend), ?voice=eleven|browser|silent, ?speed=N (faster demo clock).
import { useState } from "react";
import type { VoiceMode } from "../player/voices";

export interface AppEnv {
  mock: boolean;
  voice: VoiceMode | null;
  speed: number;
}

const VOICES: VoiceMode[] = ["eleven", "browser", "silent"];

export function readAppEnv(search: string = window.location.search): AppEnv {
  const q = new URLSearchParams(search);
  const mock = ["1", "true", "yes"].includes((q.get("mock") ?? "").toLowerCase());
  const v = q.get("voice") as VoiceMode | null;
  const speed = Number(q.get("speed") ?? "1");
  return {
    mock,
    voice: v && VOICES.includes(v) ? v : null,
    speed: Number.isFinite(speed) && speed > 0 ? Math.min(speed, 20) : 1,
  };
}

export function useAppEnv(): AppEnv {
  const [env] = useState(() => readAppEnv());
  return env;
}

/** localStorage that never throws (private windows, blocked storage). */
export const safeStorage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // storage unavailable: preference lasts for this page only
    }
  },
};
