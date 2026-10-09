import { useEffect, useState, useSyncExternalStore } from "react";
import type { StudyLensApi } from "../api";
import type { BoardSlot } from "../player/boardSlot";
import { LessonPlayer } from "../player/lessonPlayer";
import { VoiceBox, type VoiceMode } from "../player/voices";

interface Options {
  api: StudyLensApi;
  slot: BoardSlot;
  mode: VoiceMode;
  speed: number;
  /** Both callbacks must be stable (useCallback); they are bound once. */
  onNotice: (message: string) => void;
  onVoiceFallback: (mode: VoiceMode) => void;
}

/** One LessonPlayer per page load, exposed as React state. */
export function usePlayer({ api, slot, mode, speed, onNotice, onVoiceFallback }: Options) {
  const [player] = useState(() => {
    const voice = new VoiceBox(api);
    voice.silentRate = speed;
    voice.onAutoplayBlocked = () =>
      onNotice("The browser blocked the audio. Click anywhere on the page, then press Replay.");
    return new LessonPlayer({ voice, board: () => slot.current, mode, onNotice, onVoiceFallback });
  });

  useEffect(() => {
    player.setVoice(mode);
  }, [player, mode]);

  useEffect(() => () => player.stop(), [player]);

  const state = useSyncExternalStore(player.subscribe, player.getState);
  return { player, state };
}
