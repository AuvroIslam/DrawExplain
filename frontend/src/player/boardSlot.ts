import type { BoardHandle } from "../board/types";

/** Holds the whiteboard handle once the (lazy) board has mounted; callers can wait for it. */
export class BoardSlot {
  private handle: BoardHandle | null = null;
  private waiters: ((b: BoardHandle) => void)[] = [];

  get current(): BoardHandle | null {
    return this.handle;
  }

  set(handle: BoardHandle) {
    this.handle = handle;
    const waiting = this.waiters;
    this.waiters = [];
    for (const fn of waiting) fn(handle);
  }

  when(): Promise<BoardHandle> {
    if (this.handle) return Promise.resolve(this.handle);
    return new Promise((resolve) => this.waiters.push(resolve));
  }

  /** The board unmounted (back to the landing page). */
  reset() {
    this.handle = null;
    this.waiters = [];
  }
}
