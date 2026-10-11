import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { api as realApi } from "./api";
import { BoardStage } from "./components/BoardStage";
import { preloadBoard } from "./components/boardLoader";
import { Landing } from "./components/Landing";
import { Toasts } from "./components/Toasts";
import { TopBar } from "./components/TopBar";
import { TutorPanel } from "./components/TutorPanel";
import { useAppEnv } from "./hooks/useAppEnv";
import { useBackend, useVoiceMode } from "./hooks/useBackend";
import { useKeyboard } from "./hooks/useKeyboard";
import { usePlayer } from "./hooks/usePlayer";
import { useStudySession } from "./hooks/useStudySession";
import { useToasts } from "./hooks/useToasts";
import { mockApi } from "./mock/mockApi";
import { BoardSlot } from "./player/boardSlot";

export default function App() {
  const env = useAppEnv();
  const api = env.mock ? mockApi : realApi;
  const { toasts, push, dismiss } = useToasts();
  const backend = useBackend(api);
  const voice = useVoiceMode(env, backend.health);
  const [slot] = useState(() => new BoardSlot());
  const [hasDrawing, setHasDrawing] = useState(false);

  const { player, state } = usePlayer({
    api,
    slot,
    mode: voice.mode,
    speed: env.speed,
    onNotice: push,
    onVoiceFallback: voice.fallBack,
  });
  const study = useStudySession({ api, player, slot, notify: push });
  const { session } = study;
  const lessonActive = !!session?.lesson && !session.quiz;

  useKeyboard(
    {
      onSpace: () => player.toggle(),
      onLeft: () => player.prev(),
      onRight: () => player.next(),
    },
    lessonActive && !study.debug,
  );

  useEffect(() => {
    const idle = window.setTimeout(preloadBoard, 600);
    return () => window.clearTimeout(idle);
  }, []);

  const onStudentDrawing = useCallback((has: boolean) => setHasDrawing(has), []);

  const { reset } = study;
  const goHome = useCallback(() => {
    reset();
    setHasDrawing(false);
  }, [reset]);

  return (
    <div className={`app${session ? " in-workspace" : ""}`}>
      <TopBar
        workspace={!!session}
        mock={api.mock}
        voice={voice.mode}
        elevenAvailable={voice.elevenAvailable}
        onVoice={voice.choose}
        debug={study.debug}
        debugEnabled={!!session?.perception}
        onDebug={study.setDebug}
        canSave={!!session?.perception}
        onSave={() => void study.saveNotes()}
        onHome={goHome}
      />
      {session ? (
        <main className="workspace">
          <BoardStage
            session={session}
            onBoardReady={study.onBoardReady}
            onStudentDrawing={onStudentDrawing}
            onTeach={() => void study.teach()}
            onReplay={study.replayLesson}
            onRetryScan={study.retryScan}
            onHome={goHome}
            onPage={study.openPage}
          />
          <TutorPanel session={session} state={state} player={player} study={study} hasDrawing={hasDrawing} />
        </main>
      ) : (
        <Landing
          samples={backend.samples}
          offline={backend.offline}
          mock={api.mock}
          onFile={(file) => void study.open({ kind: "file", file, name: file.name })}
          onSample={(s) => void study.open({ kind: "sample", name: s.name, url: s.url })}
          onRetry={backend.retry}
        />
      )}
      <Toasts toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
