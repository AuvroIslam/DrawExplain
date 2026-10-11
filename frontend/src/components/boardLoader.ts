// Picks the whiteboard implementation: the Excalidraw board (src/board/WhiteboardBoard.tsx) when it
// exists, else the SVG stub. ?board=stub forces the stub. Both are lazy chunks (Excalidraw is ~2 MB).
import { type ComponentType, lazy } from "react";
import type { WhiteboardBoardProps } from "../board/types";

type BoardModule = { default: ComponentType<WhiteboardBoardProps> };

const found = import.meta.glob<BoardModule>("../board/WhiteboardBoard.tsx");
const loadReal = found["../board/WhiteboardBoard.tsx"] as (() => Promise<BoardModule>) | undefined;
const wantStub = new URLSearchParams(window.location.search).get("board") === "stub";
const load: () => Promise<BoardModule> = !wantStub && loadReal ? loadReal : () => import("./BoardStub");

export const BOARD_KIND: "excalidraw" | "stub" = !wantStub && loadReal ? "excalidraw" : "stub";

export const LazyBoard = lazy(load);

let warm: Promise<unknown> | null = null;

/** Start downloading the board chunk early (landing page idle time). */
export function preloadBoard() {
  warm ??= load().catch(() => undefined);
}
