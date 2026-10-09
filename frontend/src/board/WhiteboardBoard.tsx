// React wrapper around the Excalidraw canvas: one BoardEngine per mounted board.
// The engine owns the scene (see engine.ts); this component only mounts Excalidraw, wires its
// callbacks to the engine and hands the BoardHandle to the app once the canvas is live.
import { Excalidraw } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";
import type { ExcalidrawProps } from "@excalidraw/excalidraw/types";
import { useEffect, useRef, useState } from "react";
import { type BoardDebug, BoardEngine } from "./engine";
import type { BoardHandle, WhiteboardBoardProps } from "./types";

declare global {
  interface Window {
    /** Dev builds only: the live board, for the screenshot/test harness. */
    __studylensBoard?: BoardHandle & BoardDebug;
  }
}

/** Only the drawing tools: no file dialogs, canvas reset, background picker, theme toggle or image tool. */
const UI_OPTIONS: ExcalidrawProps["UIOptions"] = {
  canvasActions: {
    changeViewBackgroundColor: false,
    clearCanvas: false,
    export: false,
    loadScene: false,
    saveToActiveFile: false,
    saveAsImage: false,
    toggleTheme: false,
  },
  tools: { image: false },
};

/** The student's own pen: a dark ink that stays apart from the tutor's five marker colours. */
const INITIAL_DATA: ExcalidrawProps["initialData"] = {
  elements: [],
  appState: {
    viewBackgroundColor: "#ffffff",
    currentItemStrokeColor: "#1e1e1e",
    currentItemStrokeWidth: 2,
    currentItemRoughness: 1,
    gridModeEnabled: false,
  },
  scrollToContent: false,
};

export default function WhiteboardBoard({ onReady, onStudentDrawingChange, theme = "light", className }: WhiteboardBoardProps) {
  const [engine] = useState(() => new BoardEngine());
  const [failure, setFailure] = useState<Error | null>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const onReadyRef = useRef(onReady);
  const onStudentRef = useRef(onStudentDrawingChange);

  useEffect(() => {
    onReadyRef.current = onReady;
    onStudentRef.current = onStudentDrawingChange;
  });

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let alive = true;
    engine.attach(host, (has) => onStudentRef.current?.(has));
    engine.whenReady().then(
      () => {
        if (!alive) return;
        if (import.meta.env.DEV) window.__studylensBoard = engine.handle;
        onReadyRef.current(engine.handle);
      },
      (err: unknown) => {
        if (alive) setFailure(err instanceof Error ? err : new Error(String(err)));
      },
    );
    return () => {
      alive = false;
      engine.detach();
    };
  }, [engine]);

  // let the app's error boundary show its "reload" card
  if (failure) throw failure;

  return (
    <div ref={hostRef} className={`whiteboard${className ? ` ${className}` : ""}`} data-board="excalidraw">
      <Excalidraw
        excalidrawAPI={engine.setApi}
        onChange={engine.onSceneChange}
        initialData={INITIAL_DATA}
        UIOptions={UI_OPTIONS}
        theme={theme}
        aiEnabled={false}
        autoFocus={false}
        handleKeyboardGlobally={false}
      />
    </div>
  );
}
