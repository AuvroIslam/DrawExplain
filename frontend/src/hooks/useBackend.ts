import { useCallback, useEffect, useState } from "react";
import type { StudyLensApi } from "../api";
import { speechAvailable, type VoiceMode } from "../player/voices";
import type { Health, SampleInfo } from "../types";
import { type AppEnv, safeStorage } from "./useAppEnv";

export interface BackendInfo {
  health: Health | null;
  offline: boolean;
  samples: SampleInfo[] | null;
  retry: () => void;
}

/** Health + sample list, fetched once (and again on retry). */
export function useBackend(api: StudyLensApi): BackendInfo {
  const [health, setHealth] = useState<Health | null>(null);
  const [offline, setOffline] = useState(false);
  const [samples, setSamples] = useState<SampleInfo[] | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    api.health().then(
      (h) => {
        if (!live) return;
        setHealth(h);
        setOffline(false);
      },
      () => live && setOffline(true),
    );
    api.listSamples().then(
      (s) => live && setSamples(s),
      () => live && setSamples([]),
    );
    return () => {
      live = false;
    };
  }, [api, attempt]);

  const retry = useCallback(() => setAttempt((a) => a + 1), []);
  return { health, offline, samples, retry };
}

const VOICE_KEY = "studylens.voice";

/** Voice preference: URL flag > saved choice > best available (ElevenLabs when the server has a key). */
export function useVoiceMode(env: AppEnv, health: Health | null) {
  const elevenAvailable = !env.mock && health?.tts !== false;
  const [chosen, setChosen] = useState<VoiceMode | null>(() => {
    if (env.voice) return env.voice;
    const saved = safeStorage.get(VOICE_KEY) as VoiceMode | null;
    return saved === "eleven" || saved === "browser" || saved === "silent" ? saved : null;
  });
  const fallback: VoiceMode = speechAvailable() ? "browser" : "silent";
  const preferred: VoiceMode = chosen ?? (env.mock ? fallback : "eleven");
  const mode: VoiceMode = preferred === "eleven" && !elevenAvailable ? fallback : preferred;

  const choose = useCallback((m: VoiceMode) => {
    setChosen(m);
    safeStorage.set(VOICE_KEY, m);
  }, []);
  /** Automatic switch after a failure: not saved, so a fixed server gets the tutor voice back next time. */
  const fallBack = useCallback((m: VoiceMode) => setChosen(m), []);

  return { mode, choose, fallBack, elevenAvailable };
}
